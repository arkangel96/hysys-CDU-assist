"""
Distillation convergence assistant engine.

Process-engineering policy:
  Inspect → Diagnose → one bounded change → Solve → Evaluate → Keep or Reverse

Never activates an extra specification when DOF is already zero without a
1-for-1 swap. Stops at engineering limits, not only numerical solve.
"""
from __future__ import annotations

from column_api import ColumnController
from column_models import (
    ColumnState,
    ConvergenceLimits,
    Diagnosis,
    DiagnosisCode,
    TrialAction,
    TrialResult,
)


def score_state(state: ColumnState) -> float:
    """Lower is better. Combines DOF mismatch, spec residuals, and soft physics penalties."""
    score = 0.0
    dof = state.degrees_of_freedom
    if dof is None:
        score += 50.0
    elif dof != 0:
        score += 25.0 * abs(dof)

    score += 100.0 * state.max_active_spec_error
    score += 20.0 * state.sum_active_spec_error

    if not state.active_specs():
        score += 40.0

    temps = state.profile.temperatures
    if temps:
        if any(t != t for t in temps):  # NaN
            score += 30.0
        spread = max(temps) - min(temps)
        if spread < 0.05:
            score += 5.0  # suspiciously flat
        # Non-monotonic wild swings (stripper usually rises top→bottom)
        drops = sum(1 for i in range(1, len(temps)) if temps[i] < temps[i - 1] - 15.0)
        score += 2.0 * drops

    for duty in (state.condenser_duty, state.reboiler_duty):
        if duty is not None and abs(duty) > 1e8:
            score += 20.0

    if state.appears_converged:
        score *= 0.1
    return score


def diagnose(state: ColumnState, limits: ConvergenceLimits | None = None) -> Diagnosis:
    limits = limits or ConvergenceLimits()
    codes: list[DiagnosisCode] = []
    details: list[str] = []

    dof = state.degrees_of_freedom
    if dof is not None and dof > 0:
        codes.append(DiagnosisCode.UNDER_SPECIFIED)
        details.append(f"Degrees of freedom = {dof}. Activate additional primary specs.")
    elif dof is not None and dof < 0:
        codes.append(DiagnosisCode.OVER_SPECIFIED)
        details.append(f"Degrees of freedom = {dof}. Deactivate conflicting specs.")

    if state.max_active_spec_error > limits.max_active_spec_error:
        codes.append(DiagnosisCode.SPEC_ERROR_HIGH)
        details.append(
            f"Max active spec weighted/absolute error = {state.max_active_spec_error:.3g} "
            f"(limit {limits.max_active_spec_error:.3g})."
        )

    if state.appears_converged and not codes:
        codes.append(DiagnosisCode.CONVERGED)
        details.append("DOF=0 and active specification residuals are within tolerance.")

    # Estimate quality: inactive draw/rate specs with no useful current
    inactive = state.inactive_specs()
    if inactive and state.max_active_spec_error > limits.max_active_spec_error:
        codes.append(DiagnosisCode.POOR_ESTIMATES)
        details.append(
            "Inactive rate specs exist; first strategy should refresh/use estimates "
            "before changing the active specification set."
        )

    temps = state.profile.temperatures
    if temps:
        if max(temps) > limits.max_temperature_c or min(temps) < limits.min_temperature_c:
            codes.append(DiagnosisCode.PROFILE_UNPHYSICAL)
            details.append(
                f"Stage temperatures outside engineering window "
                f"[{limits.min_temperature_c}, {limits.max_temperature_c}] °C."
            )

    for label, duty in (("Condenser", state.condenser_duty), ("Reboiler", state.reboiler_duty)):
        if duty is not None and abs(duty) > limits.max_duty_abs:
            codes.append(DiagnosisCode.DUTY_EXTREME)
            details.append(f"{label} duty |{duty:.3g}| exceeds engineering limit.")

    if not codes:
        codes.append(DiagnosisCode.UNKNOWN_FAILURE)
        details.append("Column is not clearly converged; residuals or status unclear.")

    # Strategy selection (process priority)
    if DiagnosisCode.CONVERGED in codes:
        strategy = "none_converged"
        summary = "Column appears converged. No trial-and-error needed."
        severity = "info"
    elif DiagnosisCode.UNDER_SPECIFIED in codes or DiagnosisCode.OVER_SPECIFIED in codes:
        strategy = "fix_dof"
        summary = "Specification set is incomplete or conflicting. Fix DOF before tuning."
        severity = "critical"
    elif DiagnosisCode.DUTY_EXTREME in codes or DiagnosisCode.PROFILE_UNPHYSICAL in codes:
        strategy = "relax_or_reverse"
        summary = "Solution is numerically present but physically unreasonable. Reverse / relax."
        severity = "critical"
    elif DiagnosisCode.POOR_ESTIMATES in codes or DiagnosisCode.SPEC_ERROR_HIGH in codes:
        strategy = "nudge_active_goal"
        summary = (
            "Keep the active specification set. Apply one bounded GoalValue nudge "
            "(e.g. reflux ratio), solve, and keep only if residuals improve."
        )
        severity = "warn"
    else:
        strategy = "nudge_active_goal"
        summary = "Attempt a bounded active-spec nudge, then evaluate keep/reverse."
        severity = "warn"

    return Diagnosis(
        codes=codes,
        summary=summary,
        recommended_strategy=strategy,
        details=details,
        severity=severity,
    )


def propose_action(state: ColumnState, limits: ConvergenceLimits, diagnosis: Diagnosis) -> TrialAction | None:
    if diagnosis.recommended_strategy in {"none_converged", "fix_dof", "relax_or_reverse"}:
        if diagnosis.recommended_strategy == "none_converged":
            return None
        if diagnosis.recommended_strategy == "fix_dof":
            return TrialAction(
                kind="manual_dof",
                description="DOF must be fixed manually (activate/deactivate specs to reach 0).",
                payload={"dof": state.degrees_of_freedom},
            )

    # Prefer nudging Reflux Ratio if it is an active spec
    reflux = next((s for s in state.active_specs() if "reflux ratio" in s.name.lower()), None)
    if reflux is not None and reflux.goal_value is not None:
        base = float(reflux.goal_value)
        # Alternate direction using current error sign if available
        direction = -1.0 if (reflux.error or 0.0) > 0 else 1.0
        new_goal = base * (1.0 + direction * limits.reflux_nudge_fraction)
        new_goal = min(max(new_goal, limits.min_reflux_ratio), limits.max_reflux_ratio)
        if abs(new_goal - base) < 1e-12:
            return None
        return TrialAction(
            kind="set_goal",
            description=f"Nudge '{reflux.name}' GoalValue {base:.4g} → {new_goal:.4g}",
            payload={"spec_name": reflux.name, "goal": new_goal, "previous": base},
        )

    # Otherwise nudge first active spec with a numeric goal
    for spec in state.active_specs():
        if spec.goal_value is None:
            continue
        base = float(spec.goal_value)
        if abs(base) < 1e-30:
            new_goal = base + 1e-6
        else:
            new_goal = base * (1.0 - limits.reflux_nudge_fraction)
        return TrialAction(
            kind="set_goal",
            description=f"Nudge '{spec.name}' GoalValue {base:.4g} → {new_goal:.4g}",
            payload={"spec_name": spec.name, "goal": new_goal, "previous": base},
        )

    return TrialAction(
        kind="solve_only",
        description="No safe knob found; request a column run and re-evaluate.",
        payload={},
    )


class ConvergenceAssistant:
    def __init__(
        self,
        columns: ColumnController,
        limits: ConvergenceLimits | None = None,
    ) -> None:
        self.columns = columns
        self.limits = limits or ConvergenceLimits()
        self.history: list[TrialResult] = []

    def inspect(self, column_name: str) -> ColumnState:
        return self.columns.inspect(column_name)

    def diagnose_column(self, column_name: str) -> tuple[ColumnState, Diagnosis]:
        state = self.inspect(column_name)
        return state, diagnose(state, self.limits)

    def run_one_trial(self, column_name: str, dry_run: bool = False) -> TrialResult:
        before = self.inspect(column_name)
        diagnosis = diagnose(before, self.limits)
        action = propose_action(before, self.limits, diagnosis)
        before_score = score_state(before)

        if action is None:
            result = TrialResult(
                action=TrialAction("none", "Already converged"),
                before_score=before_score,
                after_score=before_score,
                kept=True,
                message=diagnosis.summary,
                after_state=before,
            )
            self.history.append(result)
            return result

        if action.kind == "manual_dof":
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=before_score,
                kept=False,
                message=action.description,
                after_state=before,
            )
            self.history.append(result)
            return result

        if dry_run:
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=before_score,
                kept=False,
                message=f"DRY RUN — would: {action.description}",
                after_state=before,
            )
            self.history.append(result)
            return result

        snap = self.columns.snapshot(column_name)
        try:
            if action.kind == "set_goal":
                self.columns.set_spec_goal(
                    column_name,
                    action.payload["spec_name"],
                    float(action.payload["goal"]),
                )
            self.columns.run_column(column_name)
            after = self.inspect(column_name)
            after_score = score_state(after)

            # Engineering rejection even if score improved slightly
            unphysical = False
            if after.profile.temperatures:
                if max(after.profile.temperatures) > self.limits.max_temperature_c:
                    unphysical = True
                if min(after.profile.temperatures) < self.limits.min_temperature_c:
                    unphysical = True
            for duty in (after.condenser_duty, after.reboiler_duty):
                if duty is not None and abs(duty) > self.limits.max_duty_abs:
                    unphysical = True

            improved = after_score < before_score * 0.98  # require clear improvement
            keep = improved and not unphysical

            if not keep:
                self.columns.restore(snap)
                self.columns.run_column(column_name)
                after = self.inspect(column_name)
                after_score = score_state(after)
                message = (
                    f"REVERSED — {action.description}. "
                    f"score {before_score:.4g} → trial worse/unphysical; restored."
                )
            else:
                message = (
                    f"KEPT — {action.description}. "
                    f"score {before_score:.4g} → {after_score:.4g}."
                )

            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=after_score,
                kept=keep,
                message=message,
                after_state=after,
            )
            self.history.append(result)
            return result
        except Exception as exc:
            try:
                self.columns.restore(snap)
                self.columns.run_column(column_name)
            except Exception:
                pass
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=before_score,
                kept=False,
                message=f"FAILED/RESTORED — {action.description}: {exc}",
                after_state=self.inspect(column_name),
            )
            self.history.append(result)
            return result

    def assist(
        self,
        column_name: str,
        max_iterations: int | None = None,
        dry_run: bool = False,
    ) -> list[TrialResult]:
        """Run the controlled trial loop until converged, blocked, or iteration limit."""
        results: list[TrialResult] = []
        limit = max_iterations or self.limits.max_iterations
        for _ in range(limit):
            state, diagnosis = self.diagnose_column(column_name)
            if DiagnosisCode.CONVERGED in diagnosis.codes:
                results.append(
                    TrialResult(
                        action=TrialAction("stop", "Converged"),
                        before_score=score_state(state),
                        after_score=score_state(state),
                        kept=True,
                        message=diagnosis.summary,
                        after_state=state,
                    )
                )
                break
            if diagnosis.recommended_strategy == "fix_dof":
                results.append(
                    TrialResult(
                        action=TrialAction("stop", "DOF blocked"),
                        before_score=score_state(state),
                        after_score=score_state(state),
                        kept=False,
                        message=diagnosis.summary,
                        after_state=state,
                    )
                )
                break
            trial = self.run_one_trial(column_name, dry_run=dry_run)
            results.append(trial)
            if dry_run:
                break
            if trial.action.kind in {"none", "manual_dof"}:
                break
            # If we reversed and made no progress, stop to avoid thrashing
            if not trial.kept and trial.action.kind == "set_goal":
                # allow a few reverses, but stop if score not improving overall
                if len(results) >= 3 and all(not r.kept for r in results[-3:]):
                    results.append(
                        TrialResult(
                            action=TrialAction("stop", "No progress"),
                            before_score=trial.after_score,
                            after_score=trial.after_score,
                            kept=False,
                            message="Stopped: three consecutive reversed trials.",
                            after_state=trial.after_state,
                        )
                    )
                    break
        return results
