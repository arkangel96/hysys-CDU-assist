"""
Simple constrained optimization for CDU Assist v1.

Thin layer on top of existing PE intelligence — not a full NLP optimizer.

Objectives (minimize):
  - reboiler duty
  - condenser duty
  - reflux ratio
  - stage count (mechanical — approval-only)

Hard rules:
  - Locked FINAL_TARGETs must stay met
  - Operability / physical must stay OK
  - One bounded move per trial; keep/reverse
  - Stop when objective flat
  - Never auto-save .hsc
  - Never relax product specs to "win"
"""
from __future__ import annotations

from enum import Enum

from column_api import is_sentinel
from column_models import (
    ColumnState,
    ConvergenceLimits,
    FinalTarget,
    TrialAction,
)


class SimpleObjective(str, Enum):
    MIN_REBOILER_DUTY = "min_reboiler_duty"
    MIN_CONDENSER_DUTY = "min_condenser_duty"
    MIN_REFLUX_RATIO = "min_reflux_ratio"
    MIN_STAGE_COUNT = "min_stage_count"


OBJECTIVE_LABELS: dict[SimpleObjective, str] = {
    SimpleObjective.MIN_REBOILER_DUTY: "Min reboiler duty",
    SimpleObjective.MIN_CONDENSER_DUTY: "Min condenser duty",
    SimpleObjective.MIN_REFLUX_RATIO: "Min reflux ratio",
    SimpleObjective.MIN_STAGE_COUNT: "Min stage count (approval)",
}


def objective_value(state: ColumnState, objective: SimpleObjective) -> float | None:
    """Scalar to minimize. None = not measurable yet."""
    from column_engine import _find_active

    if objective == SimpleObjective.MIN_REBOILER_DUTY:
        d = state.reboiler_duty
        if d is None or is_sentinel(d):
            return None
        return abs(float(d))
    if objective == SimpleObjective.MIN_CONDENSER_DUTY:
        d = state.condenser_duty
        if d is None or is_sentinel(d):
            return None
        return abs(float(d))
    if objective == SimpleObjective.MIN_REFLUX_RATIO:
        rr = state.reflux_ratio
        if rr is None or is_sentinel(rr):
            spec = _find_active(state, "reflux ratio") or _find_active(state, "reflux", "ratio")
            if spec is None:
                return None
            v = spec.current_value if spec.current_value is not None else spec.goal_value
            if v is None or is_sentinel(v):
                return None
            return float(v)
        return float(rr)
    if objective == SimpleObjective.MIN_STAGE_COUNT:
        if state.number_of_stages is None:
            return None
        return float(state.number_of_stages)
    return None


def constraints_ok(
    state: ColumnState,
    targets: list[FinalTarget],
    limits: ConvergenceLimits,
) -> tuple[bool, str]:
    """Product + physics gates for simple optimize."""
    from column_engine import evaluate_final_targets, operable

    if not state.physical_solution:
        return False, "not physical"
    if state.degrees_of_freedom not in (0, None) and state.degrees_of_freedom != 0:
        return False, f"DOF={state.degrees_of_freedom}"
    if not operable(state, limits):
        return False, "not operable (bottoms/duties)"
    status = evaluate_final_targets(state, targets)
    if status and not all(info["met"] for info in status.values()):
        missed = [tid for tid, info in status.items() if not info["met"]]
        return False, f"FINAL_TARGET miss: {', '.join(missed)}"
    return True, "ok"


def ready_for_optimize(
    state: ColumnState,
    targets: list[FinalTarget],
    limits: ConvergenceLimits,
) -> tuple[bool, str]:
    """Meet product / State E first — then squeeze duty/RR/stages."""
    ok, why = constraints_ok(state, targets, limits)
    if not ok:
        return False, f"Not ready to optimize — {why}. Meet product / State E first."
    return True, "ready"


def should_keep_optimize(
    before: ColumnState,
    after: ColumnState,
    objective: SimpleObjective,
    targets: list[FinalTarget],
    limits: ConvergenceLimits,
) -> tuple[bool, str]:
    """Keep only if constraints still OK and objective improved."""
    ok_after, why = constraints_ok(after, targets, limits)
    if not ok_after:
        return False, f"constraints broken after move ({why})"

    v0 = objective_value(before, objective)
    v1 = objective_value(after, objective)
    if v0 is None or v1 is None:
        return False, "objective not measurable"
    if v0 <= 0:
        improved = v1 < v0 - 1e-12
        rel = 0.0
    else:
        rel = (v0 - v1) / v0
        improved = rel > limits.weak_response_relative
    if not improved:
        return False, f"objective flat/worse ({v0:.4g} -> {v1:.4g}, rel={rel:.3g})"
    return True, f"objective improved {v0:.4g} -> {v1:.4g} (rel={rel:.3g})"


def propose_optimize_action(
    state: ColumnState,
    objective: SimpleObjective,
    limits: ConvergenceLimits,
    targets: list[FinalTarget],
) -> TrialAction:
    """One bounded optimize move. Stages = approval-only structural."""
    from column_engine import _find_active, _nudge_goal

    ready, why = ready_for_optimize(state, targets, limits)
    if not ready:
        return TrialAction(
            kind="stop",
            description=why,
            payload={
                "strategy_id": "optimize_blocked",
                "family": "optimize",
                "objective": objective.value,
                "response": "STOP_INFEASIBLE",
            },
        )

    v0 = objective_value(state, objective)
    if v0 is None:
        return TrialAction(
            kind="stop",
            description=f"Cannot read objective '{objective.value}' from current state.",
            payload={
                "strategy_id": "optimize_blocked",
                "family": "optimize",
                "objective": objective.value,
            },
        )

    if objective == SimpleObjective.MIN_STAGE_COUNT:
        n = state.number_of_stages
        feed = state.feed_stage
        if n is None or n <= 4:
            return TrialAction(
                kind="stop",
                description="Stage count already at/near practical minimum — stop.",
                payload={
                    "strategy_id": "optimize_done",
                    "family": "F_structural",
                    "objective": objective.value,
                },
            )
        proposed = n - 1
        if feed is not None and proposed <= feed:
            return TrialAction(
                kind="stop",
                description=(
                    f"Cannot cut stages to {proposed} while feed is at {feed} — "
                    "move feed first (approval) or stop."
                ),
                payload={
                    "strategy_id": "optimize_blocked",
                    "family": "F_structural",
                    "objective": objective.value,
                },
            )
        return TrialAction(
            kind="structural_approval",
            description=(
                f"APPROVAL REQUIRED (mechanical optimize): stage_count {n} -> {proposed}. "
                f"Only if FINAL_TARGET still holds after cut."
            ),
            payload={
                "strategy_id": "stage_count_change",
                "family": "F_structural",
                "requires_approval": True,
                "parameter": "stage_count",
                "current": n,
                "proposed": proposed,
                "com_writable": True,
                "objective": objective.value,
                "objective_before": v0,
            },
        )

    rr = _find_active(state, "reflux ratio") or _find_active(state, "reflux", "ratio")
    if rr is not None and not any(
        t.locked and t.spec_name_contains.lower() in rr.name.lower() for t in targets
    ):
        action = _nudge_goal(
            rr,
            direction=-1.0,
            frac=limits.reflux_nudge_fraction,
            limits=limits,
        )
        if action is not None:
            action.description = (
                f"[OPTIMIZE {OBJECTIVE_LABELS[objective]}] " + action.description
            )
            action.payload["family"] = "B_energy"
            action.payload["objective"] = objective.value
            action.payload["objective_before"] = v0
            action.payload["strategy_id"] = {
                SimpleObjective.MIN_REFLUX_RATIO: "optimize_min_rr",
                SimpleObjective.MIN_REBOILER_DUTY: "optimize_min_reb_duty",
                SimpleObjective.MIN_CONDENSER_DUTY: "optimize_min_cond_duty",
            }.get(objective, "optimize_min_rr")
            return action

    if objective == SimpleObjective.MIN_REBOILER_DUTY:
        boil = (
            _find_active(state, "boilup")
            or _find_active(state, "reb", "duty")
            or _find_active(state, "reboiler")
        )
        if boil is not None:
            action = _nudge_goal(
                boil,
                direction=-1.0,
                frac=limits.reflux_nudge_fraction,
                limits=limits,
            )
            if action is not None:
                action.description = (
                    f"[OPTIMIZE {OBJECTIVE_LABELS[objective]}] " + action.description
                )
                action.payload["family"] = "B_energy"
                action.payload["objective"] = objective.value
                action.payload["objective_before"] = v0
                action.payload["strategy_id"] = "optimize_min_reb_duty"
                return action

    return TrialAction(
        kind="stop",
        description=(
            f"No safe Active knob for {OBJECTIVE_LABELS[objective]} "
            "(need Active Reflux Ratio, or Active boilup/duty for reb objective)."
        ),
        payload={
            "strategy_id": "optimize_blocked",
            "family": "optimize",
            "objective": objective.value,
        },
    )


def format_optimize_board(
    state: ColumnState,
    objective: SimpleObjective,
    targets: list[FinalTarget],
    limits: ConvergenceLimits,
) -> str:
    ready, why = ready_for_optimize(state, targets, limits)
    val = objective_value(state, objective)
    lines = [
        f"SIMPLE OPTIMIZE | {OBJECTIVE_LABELS[objective]}",
        f"  Meaning: {_objective_meaning(objective)}",
        f"  ready={ready} — {why}",
        f"  objective_value={_fmt(val)}",
        f"  RR={_fmt(state.reflux_ratio)}  RebQ={_fmt(state.reboiler_duty)}  "
        f"CondQ={_fmt(state.condenser_duty)}",
        f"  stages={state.number_of_stages} feed={state.feed_stage}",
        "  Rules: keep FINAL_TARGET + operable; one step; stop if flat; stages need approval.",
    ]
    return "\n".join(lines)


def _fmt(v: object) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.4g}"
    except Exception:
        return str(v)


def _objective_meaning(objective: SimpleObjective) -> str:
    return {
        SimpleObjective.MIN_REBOILER_DUTY: (
            "Lower reboiler energy (usually by nudging Active RR down a little)"
        ),
        SimpleObjective.MIN_CONDENSER_DUTY: (
            "Lower condenser duty (usually by nudging Active RR down a little)"
        ),
        SimpleObjective.MIN_REFLUX_RATIO: (
            "Lower Active Reflux Ratio Goal while product NH3 still met"
        ),
        SimpleObjective.MIN_STAGE_COUNT: (
            "Propose fewer stages (mechanical — you must approve; not auto-applied)"
        ),
    }.get(objective, objective.value)


def _nh3_line(state: ColumnState, targets: list[FinalTarget]) -> str:
    from column_engine import evaluate_final_targets

    nh3 = state.bottoms_nh3_mass_frac
    ppm = f"{nh3 * 1e6:.4g} ppmw" if nh3 is not None else "—"
    status = evaluate_final_targets(state, targets)
    if not status:
        return f"NH3={ppm}"
    bits = []
    for tid, info in status.items():
        bits.append(f"{tid} met={info['met']} ({info['measured']} vs {info['target']})")
    return f"NH3={ppm}; " + "; ".join(bits)


def format_optimize_step_report(
    *,
    objective: SimpleObjective,
    before: ColumnState,
    after: ColumnState | None,
    action: TrialAction,
    targets: list[FinalTarget],
    limits: ConvergenceLimits,
    kept: bool | None,
    reason: str,
    dry_run: bool = False,
) -> str:
    """Plain-language report so Optimize 1 is obvious to the PE."""
    v0 = objective_value(before, objective)
    v1 = objective_value(after, objective) if after is not None else None
    label = OBJECTIVE_LABELS[objective]

    lines = [
        "=" * 56,
        "OPTIMIZE 1 - WHAT HAPPENED",
        "=" * 56,
        f"Objective selected: {label}",
        f"What that means:    {_objective_meaning(objective)}",
        "",
        "BEFORE",
        f"  {label} value = {_fmt(v0)}",
        f"  RR={_fmt(before.reflux_ratio)}  RebQ={_fmt(before.reboiler_duty)}  "
        f"CondQ={_fmt(before.condenser_duty)}",
        f"  stages={before.number_of_stages}  feed={before.feed_stage}",
        f"  {_nh3_line(before, targets)}",
        "",
        "ACTION",
    ]

    if action.kind == "set_goal":
        spec = action.payload.get("spec_name", "?")
        old_g = action.payload.get("previous", action.payload.get("old_goal"))
        new_g = action.payload.get("goal")
        lines.append(f"  Changed Active GoalValue on: {spec}")
        if old_g is not None and new_g is not None:
            lines.append(f"  GoalValue: {_fmt(old_g)}  ->  {_fmt(new_g)}")
        elif new_g is not None:
            lines.append(f"  New GoalValue = {_fmt(new_g)}")
        lines.append(f"  Detail: {action.description}")
        lines.append(
            "  Why this knob: for strippers, lowering RR usually reduces energy; "
            "product FINAL_TARGET stays locked."
        )
    elif action.kind == "structural_approval":
        lines.append("  NO change applied yet (mechanical / needs your approval).")
        lines.append(
            f"  Proposed: {action.payload.get('parameter')} "
            f"{action.payload.get('current')} -> {action.payload.get('proposed')}"
        )
        lines.append(f"  Detail: {action.description}")
    elif action.kind == "stop":
        lines.append("  No optimize move made.")
        lines.append(f"  Reason: {action.description}")
    else:
        lines.append(f"  kind={action.kind}")
        lines.append(f"  Detail: {action.description}")

    if dry_run:
        lines.extend(["", "RESULT: DRY RUN only — nothing written to HYSYS."])
        lines.append("=" * 56)
        return "\n".join(lines)

    if action.kind in {"stop", "structural_approval"}:
        lines.extend(["", f"RESULT: {reason or action.description}"])
        lines.append("=" * 56)
        return "\n".join(lines)

    lines.extend(["", "AFTER"])
    if after is not None:
        lines.append(f"  {label} value = {_fmt(v1)}")
        lines.append(
            f"  RR={_fmt(after.reflux_ratio)}  RebQ={_fmt(after.reboiler_duty)}  "
            f"CondQ={_fmt(after.condenser_duty)}"
        )
        lines.append(f"  {_nh3_line(after, targets)}")
    if v0 is not None and v1 is not None and v0 != 0:
        delta = v1 - v0
        pct = 100.0 * (v0 - v1) / abs(v0)
        lines.append(f"  Objective change: {_fmt(v0)} -> {_fmt(v1)}  (delta={_fmt(delta)}, improve={pct:.2f}%)")

    lines.append("")
    if kept is True:
        lines.append("DECISION: KEPT - left the new values in HYSYS.")
        lines.append(f"  Why: {reason}")
    elif kept is False:
        lines.append("DECISION: REVERSED - restored previous snapshot.")
        lines.append(f"  Why: {reason}")
    else:
        lines.append(f"DECISION: {reason}")
    lines.append("=" * 56)
    return "\n".join(lines)
