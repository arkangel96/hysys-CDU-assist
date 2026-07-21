"""
Distillation convergence assistant engine.

Layer 2 intelligence (expert workflow):
  Classify States A–F → protect FINAL_TARGET → one bounded move →
  solve → response class → keep/reverse → PE board

Never auto-relaxes locked product FINAL_TARGETs (e.g. cut / ASTM / TBP).
Never adds an extra Active spec when DOF is already 0 without a 1-for-1 swap.
"""
from __future__ import annotations

from column_api import ColumnController, is_sentinel
from cdu_case_config import CduCaseConfig, load_case_config
from cdu_t100_knowledge import format_side_ops_board, format_subsystem_board
from cdu_expert_engine import build_expert_context, format_expert_board, propose_from_expert
from cdu_quality_engine import (
    build_product_quality_state,
    format_quality_board,
    quality_targets_to_final_targets,
)
from cdu_spec_philosophy import audit_spec_philosophy, format_spec_philosophy_board
from column_models import (
    ColumnState,
    ConvergenceLimits,
    Diagnosis,
    DiagnosisCode,
    EngineeringState,
    FinalTarget,
    ResponseClass,
    TrialAction,
    TrialResult,
    default_cdu_targets,
)
from column_spec_catalog import recommend_add_spec, recommend_specs_summary_clicks


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

    if not state.physical_solution:
        score += 40.0

    temps = state.profile.temperatures
    if temps:
        if any(t != t for t in temps):  # NaN
            score += 30.0
        spread = max(temps) - min(temps)
        if spread < 0.05:
            score += 5.0
        drops = sum(1 for i in range(1, len(temps)) if temps[i] < temps[i - 1] - 15.0)
        score += 2.0 * drops

    for duty in (state.condenser_duty, state.reboiler_duty):
        if duty is not None and abs(duty) > 1e8:
            score += 20.0

    if state.appears_converged and state.physical_solution:
        score *= 0.1
    return score


def _spec_matches_final_target(spec_name: str, targets: list[FinalTarget]) -> FinalTarget | None:
    lower = spec_name.lower()
    for target in targets:
        if target.spec_name_contains.lower() in lower:
            return target
    return None


def _final_target_value(state: ColumnState, target: FinalTarget) -> float | None:
    if target.stream == "bottoms":
        return state.bottoms_nh3_mass_frac
    return None


def _final_target_met(value: float | None, target: FinalTarget) -> bool:
    if value is None or is_sentinel(value):
        return False
    tol = target.tolerance
    if target.relationship == "less_or_equal":
        return value <= target.target_value + tol
    if target.relationship == "greater_or_equal":
        return value >= target.target_value - tol
    return abs(value - target.target_value) <= max(tol, abs(target.target_value) * 1e-6)


def evaluate_final_targets(
    state: ColumnState, targets: list[FinalTarget]
) -> dict[str, dict]:
    status: dict[str, dict] = {}
    for target in targets:
        value = _final_target_value(state, target)
        status[target.id] = {
            "description": target.description,
            "target": target.target_value,
            "measured": value,
            "met": _final_target_met(value, target),
            "locked": target.locked,
        }
    return status


def operable(state: ColumnState, limits: ConvergenceLimits) -> bool:
    if not state.physical_solution:
        return False
    # CDU multi-product: residue/draw rates may substitute for stripper-style btms flow
    if state.product_streams and len(state.product_streams) > 2:
        draw_specs = [
            s
            for s in state.specs
            if s.is_active
            and (
                "prod rate" in s.name.lower()
                or "draw" in s.name.lower()
                or "_ss" in s.name.lower()
            )
        ]
        if draw_specs:
            flows = [
                s.current_display or s.current_value
                for s in draw_specs
                if s.current_display is not None or s.current_value is not None
            ]
            if flows and all(
                f is None or is_sentinel(f) or abs(float(f)) < 1e-9 for f in flows
            ):
                return False
        if state.bottoms_molar_flow_kgmole_h is None and state.bottoms_molar_flow is None:
            return True
    if state.bottoms_molar_flow_kgmole_h is not None:
        return state.bottoms_molar_flow_kgmole_h >= limits.min_bottoms_flow_kgmole_h
    flow = state.bottoms_molar_flow
    if flow is None or is_sentinel(flow):
        return False
    return abs(float(flow)) > 1e-6


def classify_engineering_state(
    state: ColumnState,
    limits: ConvergenceLimits,
    targets: list[FinalTarget],
    target_status: dict[str, dict] | None = None,
) -> EngineeringState:
    dof = state.degrees_of_freedom
    if dof is not None and dof != 0:
        return EngineeringState.A_INVALID

    if not state.physical_solution:
        return EngineeringState.B_NUMERICAL

    target_status = target_status or evaluate_final_targets(state, targets)
    hard_by_id = {t.id: t for t in targets}
    hard_miss = any(
        (not info["met"]) and hard_by_id[tid].hard for tid, info in target_status.items()
    )
    hard_ok = all(
        info["met"] or not hard_by_id[tid].hard for tid, info in target_status.items()
    )

    if hard_ok and state.appears_converged and operable(state, limits):
        return EngineeringState.E_ACCEPTABLE

    if hard_ok and state.appears_converged and not operable(state, limits):
        return EngineeringState.D_CONSTRAINT

    if hard_miss:
        return EngineeringState.C_OFF_SPEC

    if state.appears_converged:
        return EngineeringState.C_OFF_SPEC

    return EngineeringState.B_NUMERICAL


def diagnose(
    state: ColumnState,
    limits: ConvergenceLimits | None = None,
    targets: list[FinalTarget] | None = None,
    history: list[TrialResult] | None = None,
    *,
    columns: ColumnController | None = None,
    case_config: CduCaseConfig | None = None,
) -> Diagnosis:
    limits = limits or ConvergenceLimits()
    case = case_config or load_case_config()
    targets = targets if targets is not None else default_cdu_targets()
    if not targets:
        targets = quality_targets_to_final_targets(case)
    if not targets:
        targets = default_cdu_targets()

    spec_report = audit_spec_philosophy(state, case)
    product_quality = build_product_quality_state(state, case, columns)
    codes: list[DiagnosisCode] = []
    details: list[str] = []
    target_status = evaluate_final_targets(state, targets)

    dof = state.degrees_of_freedom
    if dof is not None and dof > 0:
        codes.append(DiagnosisCode.UNDER_SPECIFIED)
        details.append(f"Degrees of freedom = {dof}. Activate additional primary specs.")
    elif dof is not None and dof < 0:
        codes.append(DiagnosisCode.OVER_SPECIFIED)
        details.append(f"Degrees of freedom = {dof}. Deactivate conflicting specs.")

    if not state.physical_solution:
        codes.append(DiagnosisCode.STATE_B_NUMERICAL)
        details.append(
            "Nonphysical / sentinel duties or bottoms T — State B numerical recovery first."
        )

    if state.max_active_spec_error > limits.max_active_spec_error:
        codes.append(DiagnosisCode.SPEC_ERROR_HIGH)
        details.append(
            f"Max active spec error = {state.max_active_spec_error:.3g} "
            f"(limit {limits.max_active_spec_error:.3g})."
        )

    for tid, info in target_status.items():
        measured = info["measured"]
        details.append(
            f"FINAL_TARGET {tid}: measured={measured} target={info['target']} "
            f"met={info['met']} locked={info['locked']}"
        )
        if not info["met"]:
            codes.append(DiagnosisCode.FINAL_TARGET_MISS)

    if state.physical_solution and not operable(state, limits):
        codes.append(DiagnosisCode.OPERABILITY_FAIL)
        details.append(
            f"Bottoms flow operability gate failed "
            f"(need ≥ {limits.min_bottoms_flow_kgmole_h:g} kgmole/h)."
        )

    temps = state.profile.temperatures
    if temps:
        if max(temps) > limits.max_temperature_c or min(temps) < limits.min_temperature_c:
            codes.append(DiagnosisCode.PROFILE_UNPHYSICAL)
            details.append("Stage temperatures outside engineering window.")

    for label, duty in (("Condenser", state.condenser_duty), ("Reboiler", state.reboiler_duty)):
        if duty is not None and not is_sentinel(duty) and abs(duty) > limits.max_duty_abs:
            codes.append(DiagnosisCode.DUTY_EXTREME)
            details.append(f"{label} duty |{duty:.3g}| exceeds engineering limit.")

    eng = classify_engineering_state(state, limits, targets, target_status)

    if eng == EngineeringState.E_ACCEPTABLE:
        codes = [DiagnosisCode.CONVERGED]
        strategy = "none_converged"
        summary = "State E — physical solve, FINAL_TARGETs met, operability OK."
        severity = "info"
        pe_read = "Acceptable converged solution."
        potential = "success"
    elif eng == EngineeringState.A_INVALID:
        strategy = "fix_dof"
        summary = "State A — DOF invalid. Fix specification set before tuning."
        severity = "critical"
        pe_read = "Model not properly posed."
        potential = "nowhere"
    elif eng == EngineeringState.B_NUMERICAL:
        strategy = "numerical_recovery"
        summary = (
            "State B — numerically unhealthy. Refresh estimates / baseline Active swap "
            "before product targeting. Do not relax FINAL_TARGET."
        )
        severity = "critical"
        pe_read = "Bottoms/duties not trustworthy; recover physical solution first."
        potential = "marginal"
    elif eng == EngineeringState.D_CONSTRAINT:
        strategy = "operability_review"
        summary = "State D — targets look met but operability/constraints fail."
        severity = "warn"
        pe_read = "Green residuals with unrealistic bottoms/duties — not plant-acceptable."
        potential = "nowhere"
        if "full reflux" in (state.condenser_type or "").lower():
            details.append(
                "Connections: Full Reflux condenser — Ovhd is vapor product; "
                "Active Ovhd rate can drive near-zero bottoms if set too high."
            )
    elif eng == EngineeringState.C_OFF_SPEC:
        strategy = "nudge_operating_mv"
        summary = (
            "State C — physical (or partially) but FINAL_TARGET / active residuals unmet. "
            "Nudge Category-1 operating MVs only; FINAL_TARGET locked."
        )
        severity = "warn"
        pe_read = "Separation/energy/split path — adjust Category-1 MVs (draws/PA/OH), not product GoalValue."
        potential = "going_somewhere"
    else:
        strategy = "report_infeasible"
        summary = "State F — likely infeasible under current structure/assumptions."
        severity = "critical"
        pe_read = "Operating MVs exhausted or weak response — escalate or stop."
        potential = "nowhere"

    if not codes:
        codes.append(DiagnosisCode.UNKNOWN_FAILURE)

    has_rr = any("reflux ratio" in s.name.lower() for s in state.specs)
    has_comp_target = bool(targets) or any(
        any(
            tok in s.name.lower()
            for tok in ("cut", "astm", "tbp", "frac", "nh3", "gap", "rvp")
        )
        for s in state.specs
    )
    final_met = all(info["met"] for info in target_status.values()) if target_status else False
    add_recs = recommend_add_spec(
        existing_spec_names=[s.name for s in state.specs],
        engineering_state=eng.value,
        has_reflux_ratio=has_rr,
        has_composition_final_target=has_comp_target,
        physical_solution=state.physical_solution,
        final_target_met=final_met,
        weak_operating_response=False,
    )
    add_lines = [
        f"{r.action}: {r.hysys_type_name or '(none)'} — {r.reason}" for r in add_recs
    ]

    click_recs = recommend_specs_summary_clicks(
        spec_rows=[
            {
                "name": s.name,
                "is_active": s.is_active,
                "is_estimate": s.use_as_estimate,
            }
            for s in state.specs
        ],
        engineering_state=eng.value,
        bottoms_flow_kgmole_h=state.bottoms_molar_flow_kgmole_h,
        min_bottoms_flow_kgmole_h=limits.min_bottoms_flow_kgmole_h,
        final_target_monitor_only=bool(targets),
    )
    click_lines = []
    for c in click_recs:
        bits = [c.spec_name]
        if c.set_active is True:
            bits.append("Active=ON")
        elif c.set_active is False:
            bits.append("Active=OFF")
        if c.set_estimate is True:
            bits.append("Estimate=ON")
        elif c.set_estimate is False:
            bits.append("Estimate=OFF")
        if c.sync_goal_from_current:
            bits.append("Sync Current→Goal")
        click_lines.append(f"{' | '.join(bits)} — {c.reason}")

    expert = build_expert_context(
        state,
        eng,
        limits,
        target_status,
        history=history,
        spec_report=spec_report,
        product_quality=product_quality,
        mv_preference=case.mv_preference,
        case_config=case,
    )
    if spec_report.blocks_tuning:
        strategy = "fix_dof"
        summary = f"{spec_report.summary} — audit spec set before tuning."
        pe_read = "Spec philosophy blocks MV moves — fix DOF/spec conflicts first."
    elif expert.selected_hypothesis:
        strategy = expert.selected_hypothesis.strategy_id
    elif eng == EngineeringState.F_INFEASIBLE:
        strategy = "report_infeasible"
    elif eng == EngineeringState.D_CONSTRAINT:
        strategy = "operability_review"

    return Diagnosis(
        codes=codes,
        summary=summary,
        recommended_strategy=strategy,
        details=details,
        severity=severity,
        engineering_state=eng,
        pe_read=pe_read,
        potential=potential,
        final_target_status=target_status,
        add_spec_recommendations=add_lines,
        specs_summary_clicks=click_lines,
        expert_context=expert,
        product_quality=product_quality,
        spec_philosophy=spec_report,
        case_objective=case.objective,
        interactive_only=case.interactive_only,
    )


def format_connections_block(state: ColumnState) -> str:
    """HYSYS Design → Connections snapshot for PE board / UI."""
    feeds = ", ".join(state.feed_streams) if state.feed_streams else "—"
    feed_loc = state.feed_stage_label or (
        str(state.feed_stage) if state.feed_stage is not None else "—"
    )
    lines = [
        "CONNECTIONS (Design → Connections) [READ]",
        f"  Stages={state.number_of_stages} numbering={state.stage_numbering or '—'}",
        f"  Feed={feeds} @ {feed_loc}",
        f"  Condenser={state.condenser_type or '—'}  "
        f"P_cond={state.condenser_pressure_bar} bar  dP={state.condenser_dp_bar}",
        f"  Reboiler P_reb={state.reboiler_pressure_bar} bar  dP={state.reboiler_dp_bar}",
        f"  Ovhd product={state.top_vapour_product or '—'}  "
        f"Btms product={state.bottoms_liquid_product or '—'}",
        f"  Energy={', '.join(state.energy_streams) or '—'}",
    ]
    if state.monitor_equilibrium_error is not None or state.monitor_heat_spec_error is not None:
        lines.append(
            f"  Monitor(COM): iter={state.monitor_iteration} "
            f"EquilibriumError={state.monitor_equilibrium_error} "
            f"HeatSpecError={state.monitor_heat_spec_error}"
        )
    return "\n".join(lines)


def format_pe_board(state: ColumnState, diagnosis: Diagnosis) -> str:
    lines = [
        f"PE BOARD | State {diagnosis.engineering_state.value} | potential={diagnosis.potential}",
        f"  {diagnosis.pe_read}",
        f"  Strategy: {diagnosis.recommended_strategy}",
        f"  DOF={state.degrees_of_freedom} physical={state.physical_solution} "
        f"converged_flag={state.appears_converged} score={score_state(state):.4g}",
        f"  CondQ={state.condenser_duty} RebQ={state.reboiler_duty}",
        f"  Offgas={state.overhead_molar_flow_kgmole_h} kgmole/h | "
        f"Btms={state.bottoms_molar_flow_kgmole_h} kgmole/h | BtmsT={state.bottoms_temperature}",
    ]
    lines.append(format_connections_block(state))
    if diagnosis.case_objective:
        lines.append(f"  L0 OBJECTIVE: {diagnosis.case_objective}")
    lines.append(format_side_ops_board())
    if diagnosis.interactive_only:
        lines.append("  MODE: interactive_only (PE approves each trial)")
    if diagnosis.product_quality is not None:
        lines.append(format_quality_board(diagnosis.product_quality))
    if diagnosis.spec_philosophy is not None:
        lines.append(format_spec_philosophy_board(diagnosis.spec_philosophy))
    if diagnosis.case_objective:
        lines.append(format_subsystem_board(state, load_case_config()))
    for sp in state.active_specs():
        goal = sp.goal_display if sp.goal_display is not None else sp.goal_value
        cur = sp.current_display if sp.current_display is not None else sp.current_value
        unit = f" {sp.display_unit}" if sp.display_unit else ""
        lines.append(
            f"  ACTIVE {sp.name}: goal={goal}{unit} current={cur}{unit} err={sp.error}"
        )
    for tid, info in diagnosis.final_target_status.items():
        lines.append(
            f"  TARGET {tid}: {info['measured']} vs {info['target']} "
            f"(met={info['met']}, locked={info['locked']})"
        )
    if diagnosis.add_spec_recommendations:
        lines.append("  ADD SPEC intelligence:")
        for rec in diagnosis.add_spec_recommendations:
            lines.append(f"    - {rec}")
    if diagnosis.specs_summary_clicks:
        lines.append("  SPECS SUMMARY clicks (Design → Specs Summary):")
        for rec in diagnosis.specs_summary_clicks:
            lines.append(f"    → {rec}")
    lines.append(f"  Summary: {diagnosis.summary}")
    if diagnosis.expert_context is not None:
        lines.append(format_expert_board(diagnosis.expert_context))
    for detail in diagnosis.details[:6]:
        lines.append(f"  • {detail}")
    return "\n".join(lines)


def _is_locked_final_spec(
    spec_name: str, targets: list[FinalTarget], limits: ConvergenceLimits
) -> bool:
    if limits.allow_relax_final_targets:
        return False
    target = _spec_matches_final_target(spec_name, targets)
    return bool(target and target.locked)


def propose_action(
    state: ColumnState,
    limits: ConvergenceLimits,
    diagnosis: Diagnosis,
    targets: list[FinalTarget] | None = None,
    history: list[TrialResult] | None = None,
) -> TrialAction | None:
    targets = targets if targets is not None else default_cdu_targets()
    strategy = diagnosis.recommended_strategy

    if strategy == "none_converged":
        return None

    expert = diagnosis.expert_context
    if expert is None:
        expert = build_expert_context(
            state,
            diagnosis.engineering_state,
            limits,
            diagnosis.final_target_status,
            history=history,
            case_config=load_case_config(),
        )
    expert_action = propose_from_expert(state, expert, limits)
    if expert_action is not None:
        return expert_action

    if strategy == "fix_dof":
        return TrialAction(
            kind="manual_dof",
            description="DOF must be fixed manually (activate/deactivate specs to reach 0).",
            payload={"dof": state.degrees_of_freedom, "strategy_id": "fix_dof"},
        )

    if strategy == "operability_review":
        return TrialAction(
            kind="stop",
            description=(
                "State D — FINAL_TARGET may be met but bottoms flow/operability fails. "
                "Manual PE review required (not auto-relaxing product specs)."
            ),
            payload={"strategy_id": "feed_or_case_change", "response": "STOP_INFEASIBLE"},
        )

    if strategy == "report_infeasible":
        return TrialAction(
            kind="stop",
            description="State F — likely infeasible; stop without relaxing FINAL_TARGET.",
            payload={"strategy_id": "fix_dof", "response": "STOP_INFEASIBLE"},
        )

    if strategy == "numerical_recovery":
        return TrialAction(
            kind="refresh_estimates",
            description="State B recovery: refresh composition estimates and re-solve.",
            payload={"strategy_id": "refresh_estimates"},
        )

    # Legacy fallback: baseline swap if a locked FINAL_TARGET is incorrectly Active
    if limits.allow_baseline_spec_swap and state.degrees_of_freedom == 0:
        locked_active = next(
            (
                s
                for s in state.active_specs()
                if _is_locked_final_spec(s.name, targets, limits)
            ),
            None,
        )
        ovhd = next((s for s in state.specs if "ovhd" in s.name.lower()), None)
        if (
            locked_active is not None
            and ovhd is not None
            and not ovhd.is_active
        ):
            goal = ovhd.current_value
            if goal is None or is_sentinel(goal):
                goal = state.overhead_molar_flow
            if goal is not None and not is_sentinel(goal):
                return TrialAction(
                    kind="baseline_swap",
                    description=(
                        f"1-for-1 baseline swap: deactivate '{locked_active.name}', "
                        f"activate '{ovhd.name}' (FINAL_TARGET stays locked as monitor)."
                    ),
                    payload={
                        "deactivate": locked_active.name,
                        "activate": ovhd.name,
                        "activate_goal": float(goal),
                        "strategy_id": "spec_swap_last_resort",
                    },
                )

    remaining = [s for s in state.active_specs() if s.goal_value is not None]
    remaining.sort(key=lambda s: s.score_error(), reverse=True)
    for spec in remaining:
        if _is_locked_final_spec(spec.name, targets, limits):
            continue
        base = float(spec.goal_value)
        new_goal = base * (1.0 - limits.reflux_nudge_fraction)
        if abs(new_goal - base) < 1e-30:
            continue
        return TrialAction(
            kind="set_goal",
            description=f"Fallback nudge '{spec.name}' GoalValue {base:.4g} → {new_goal:.4g}",
            payload={
                "spec_name": spec.name,
                "goal": new_goal,
                "previous": base,
                "strategy_id": "side_draw_rate_nudge",
            },
        )

    locked_active = [
        s for s in state.active_specs() if _is_locked_final_spec(s.name, targets, limits)
    ]
    if locked_active:
        return TrialAction(
            kind="stop",
            description=(
                "FINAL_TARGET still active/unmet and no safe operating MV left. "
                "Stop — do not auto-relax product GoalValue (State F evidence)."
            ),
            payload={"strategy_id": "fix_dof", "response": "STOP_INFEASIBLE"},
        )

    return TrialAction(
        kind="refresh_estimates",
        description="No safe knob found; refresh estimates and re-evaluate.",
        payload={"strategy_id": "refresh_estimates"},
    )


def classify_response(
    before: ColumnState,
    after: ColumnState,
    before_score: float,
    after_score: float,
    kept: bool,
    limits: ConvergenceLimits,
    targets: list[FinalTarget],
) -> ResponseClass:
    if not after.physical_solution:
        return ResponseClass.UNCONVERGED_RECOVERABLE

    after_t = evaluate_final_targets(after, targets)
    if all(info["met"] for info in after_t.values()) and operable(after, limits):
        if after.appears_converged:
            return ResponseClass.TARGET_MET

    rel = 0.0
    if before_score > 1e-12:
        rel = (before_score - after_score) / before_score

    if not kept:
        if after_score > before_score * 1.02:
            return ResponseClass.CONVERGED_WORSENED
        if abs(rel) < limits.weak_response_relative:
            return ResponseClass.CONVERGED_NO_MATERIAL_CHANGE
        return ResponseClass.CONVERGED_WORSENED

    if rel > 0.25:
        return ResponseClass.CONVERGED_STRONGLY_IMPROVED
    if rel > limits.weak_response_relative:
        return ResponseClass.CONVERGED_IMPROVED
    return ResponseClass.CONVERGED_NO_MATERIAL_CHANGE


class ConvergenceAssistant:
    def __init__(
        self,
        columns: ColumnController,
        limits: ConvergenceLimits | None = None,
        targets: list[FinalTarget] | None = None,
        case_config: CduCaseConfig | None = None,
    ) -> None:
        self.columns = columns
        self.limits = limits or ConvergenceLimits()
        self.case_config = case_config or load_case_config()
        if targets is not None:
            self.targets = targets
        else:
            from_targets = quality_targets_to_final_targets(self.case_config)
            self.targets = from_targets if from_targets else default_cdu_targets()
        self.history: list[TrialResult] = []
        self._estimates_refreshed = False

    def _diagnose(self, state: ColumnState) -> Diagnosis:
        return diagnose(
            state,
            self.limits,
            self.targets,
            self.history,
            columns=self.columns,
            case_config=self.case_config,
        )

    def inspect(self, column_name: str) -> ColumnState:
        return self.columns.inspect(column_name)

    def diagnose_column(self, column_name: str) -> tuple[ColumnState, Diagnosis]:
        state = self.inspect(column_name)
        return state, self._diagnose(state)

    def pe_board(self, column_name: str) -> str:
        state, diagnosis = self.diagnose_column(column_name)
        return format_pe_board(state, diagnosis)

    def run_one_trial(self, column_name: str, dry_run: bool = False) -> TrialResult:
        before = self.inspect(column_name)
        diagnosis = self._diagnose(before)
        action = propose_action(
            before, self.limits, diagnosis, self.targets, self.history
        )
        before_score = score_state(before)
        board = format_pe_board(before, diagnosis)

        if action is None:
            result = TrialResult(
                action=TrialAction("none", "Already converged (State E)"),
                before_score=before_score,
                after_score=before_score,
                kept=True,
                message=diagnosis.summary,
                after_state=before,
                response_class=ResponseClass.TARGET_MET,
                pe_board=board,
            )
            self.history.append(result)
            return result

        if action.kind in {"manual_dof", "stop"}:
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=before_score,
                kept=False,
                message=action.description,
                after_state=before,
                response_class=ResponseClass.STOP_INFEASIBLE
                if action.kind == "stop"
                else ResponseClass.INVALID_STATE,
                pe_board=board,
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
                response_class=None,
                pe_board=board,
            )
            self.history.append(result)
            return result

        if (
            action.kind == "refresh_estimates"
            and self._estimates_refreshed
            and self.limits.allow_baseline_spec_swap
        ):
            diagnosis.recommended_strategy = "nudge_operating_mv"
            alt = propose_action(
                before, self.limits, diagnosis, self.targets, self.history
            )
            if alt is not None and alt.kind == "baseline_swap":
                action = alt

        snap = self.columns.snapshot(column_name)
        try:
            if action.kind == "set_goal":
                self.columns.set_spec_goal(
                    column_name,
                    action.payload["spec_name"],
                    float(action.payload["goal"]),
                )
            elif action.kind == "refresh_estimates":
                notes = self.columns.refresh_estimates(column_name)
                self._estimates_refreshed = True
                action.description = action.description + " | " + "; ".join(notes)
            elif action.kind == "baseline_swap":
                self.columns.swap_active_spec(
                    column_name,
                    deactivate=str(action.payload["deactivate"]),
                    activate=str(action.payload["activate"]),
                    activate_goal=float(action.payload["activate_goal"]),
                )
                for target in self.targets:
                    if target.locked:
                        for spec in before.specs:
                            if target.spec_name_contains.lower() in spec.name.lower():
                                try:
                                    self.columns.set_spec_goal(
                                        column_name, spec.name, float(target.target_value)
                                    )
                                except Exception:
                                    pass

            self.columns.run_column(column_name)
            after = self.inspect(column_name)
            after_score = score_state(after)
            after_diag = self._diagnose(after)

            unphysical = not after.physical_solution
            if after.profile.temperatures:
                if max(after.profile.temperatures) > self.limits.max_temperature_c:
                    unphysical = True
                if min(after.profile.temperatures) < self.limits.min_temperature_c:
                    unphysical = True
            for duty in (after.condenser_duty, after.reboiler_duty):
                if (
                    duty is not None
                    and not is_sentinel(duty)
                    and abs(duty) > self.limits.max_duty_abs
                ):
                    unphysical = True

            improved = after_score < before_score * 0.98
            if action.kind in {"refresh_estimates", "baseline_swap"}:
                if after.physical_solution and not before.physical_solution:
                    improved = True
                elif after.physical_solution and after_score <= before_score * 1.05:
                    improved = True

            keep = improved and not unphysical
            for tid, before_info in diagnosis.final_target_status.items():
                after_info = after_diag.final_target_status.get(tid, {})
                bval = before_info.get("measured")
                aval = after_info.get("measured")
                if (
                    bval is not None
                    and aval is not None
                    and not is_sentinel(bval)
                    and not is_sentinel(aval)
                ):
                    target = next(t for t in self.targets if t.id == tid)
                    if (
                        target.locked
                        and target.relationship == "less_or_equal"
                        and aval > bval * 1.05
                    ):
                        keep = False

            if not keep:
                self.columns.restore(snap)
                self.columns.run_column(column_name)
                after = self.inspect(column_name)
                after_score = score_state(after)
                response = classify_response(
                    before, after, before_score, after_score, False, self.limits, self.targets
                )
                message = (
                    f"REVERSED [{response.value}] — {action.description}. "
                    f"score {before_score:.4g} → trial worse/unphysical; restored."
                )
            else:
                response = classify_response(
                    before, after, before_score, after_score, True, self.limits, self.targets
                )
                message = (
                    f"KEPT [{response.value}] — {action.description}. "
                    f"score {before_score:.4g} → {after_score:.4g}."
                )

            after_board = format_pe_board(
                after, self._diagnose(after)
            )
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=after_score,
                kept=keep,
                message=message + "\n" + after_board,
                after_state=after,
                response_class=response,
                pe_board=board,
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
                response_class=ResponseClass.UNCONVERGED_RECOVERABLE,
                pe_board=board,
            )
            self.history.append(result)
            return result

    def assist(
        self,
        column_name: str,
        max_iterations: int | None = None,
        dry_run: bool = False,
    ) -> list[TrialResult]:
        """Run the controlled trial loop until State E, blocked, or iteration limit."""
        if self.case_config.interactive_only and not dry_run:
            dry_run = True
        results: list[TrialResult] = []
        limit = max_iterations or self.limits.max_iterations
        for _ in range(limit):
            state, diagnosis = self.diagnose_column(column_name)
            if diagnosis.engineering_state == EngineeringState.E_ACCEPTABLE:
                results.append(
                    TrialResult(
                        action=TrialAction("stop", "State E — acceptable"),
                        before_score=score_state(state),
                        after_score=score_state(state),
                        kept=True,
                        message=format_pe_board(state, diagnosis),
                        after_state=state,
                        response_class=ResponseClass.TARGET_MET,
                        pe_board=format_pe_board(state, diagnosis),
                    )
                )
                break
            if diagnosis.recommended_strategy in {
                "fix_dof",
                "report_infeasible",
                "operability_review",
                "feed_or_case_change",
            }:
                results.append(
                    TrialResult(
                        action=TrialAction("stop", diagnosis.recommended_strategy),
                        before_score=score_state(state),
                        after_score=score_state(state),
                        kept=False,
                        message=format_pe_board(state, diagnosis),
                        after_state=state,
                        response_class=ResponseClass.STOP_INFEASIBLE,
                        pe_board=format_pe_board(state, diagnosis),
                    )
                )
                break
            trial = self.run_one_trial(column_name, dry_run=dry_run)
            results.append(trial)
            if dry_run:
                break
            if trial.action.kind in {"none", "manual_dof", "stop"}:
                break
            if not trial.kept and trial.action.kind in {
                "set_goal",
                "refresh_estimates",
                "baseline_swap",
            }:
                if len(results) >= 3 and all(not r.kept for r in results[-3:]):
                    results.append(
                        TrialResult(
                            action=TrialAction("stop", "No progress"),
                            before_score=trial.after_score,
                            after_score=trial.after_score,
                            kept=False,
                            message=(
                                "Stopped: three consecutive reversed trials "
                                "(State F evidence — not relaxing FINAL_TARGET)."
                            ),
                            after_state=trial.after_state,
                            response_class=ResponseClass.STOP_INFEASIBLE,
                        )
                    )
                    break
        return results
