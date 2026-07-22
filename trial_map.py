"""
High-level trial map: visited path + remaining strategy combinations.

This is the engineer orientation layer — not raw COM dumps.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from column_models import ColumnState, Diagnosis, DiagnosisCode, TrialAction, TrialResult


class StrategyStatus(str, Enum):
    OPEN = "open"              # not tried yet
    HELPED = "helped"          # tried and kept / improved
    FAILED = "failed"          # tried and reversed / no help
    NEXT = "next"              # recommended next
    LOCKED = "locked"          # last-resort / blocked until needed
    DONE_OK = "done_ok"        # converged — no more needed


@dataclass(slots=True)
class StrategyDef:
    id: str
    label: str
    family: str
    description: str
    last_resort: bool = False


# Multi-variable playbook — ChemE families A–F (RR is only one B-family option)
STRATEGY_CATALOG: list[StrategyDef] = [
    StrategyDef(
        "refresh_estimates",
        "Refresh / use estimates",
        "A_init",
        "Update inactive rate estimates before changing Active philosophy or GoalValues.",
    ),
    StrategyDef(
        "reflux_nudge_down",
        "Nudge reflux ratio down",
        "B_energy",
        "Decrease active RR GoalValue when over-refluxed or residual says Goal >> Current.",
    ),
    StrategyDef(
        "reflux_nudge_up",
        "Nudge reflux ratio up",
        "B_energy",
        "Increase active RR when separation under-powered / impurity FINAL_TARGET miss.",
    ),
    StrategyDef(
        "reflux_flow_nudge",
        "Nudge reflux flow",
        "B_energy",
        "Bounded move of active reflux-flow GoalValue (energy family, not RR-only).",
    ),
    StrategyDef(
        "boilup_nudge",
        "Nudge boilup / reboiler spec",
        "B_energy",
        "Bounded move of active boilup or reboiler-related GoalValue.",
    ),
    StrategyDef(
        "ovhd_rate_nudge",
        "Nudge overhead / distillate rate",
        "C_split",
        "Bounded move of active Ovhd/distillate rate — split family.",
    ),
    StrategyDef(
        "bottoms_rate_nudge",
        "Nudge bottoms rate",
        "C_split",
        "Bounded move of active bottoms rate — split / dry-bottoms recovery.",
    ),
    StrategyDef(
        "nh3_goal_nudge",
        "Nudge NH3 bottoms goal (blocked if locked)",
        "D_target",
        "FINAL_TARGET purity GoalValue — blocked while locked; monitor only.",
        last_resort=True,
    ),
    StrategyDef(
        "lower_damping",
        "Lower solver damping",
        "A_init",
        "Manual in HYSYS — cautious Inside-Out steps when residuals oscillate.",
    ),
    StrategyDef(
        "raise_iterations",
        "Increase max iterations",
        "A_init",
        "Manual in HYSYS — more iterations when progress is slow but healthy.",
    ),
    StrategyDef(
        "spec_swap_last_resort",
        "1-for-1 temporary spec swap",
        "A_init",
        "Deactivate one Active, activate one estimate — DOF stays 0; condenser-aware.",
        last_resort=True,
    ),
    StrategyDef(
        "fix_dof",
        "Fix degrees of freedom",
        "A_init",
        "DOF ≠ 0: activate/deactivate specs manually before numerical trials.",
    ),
    StrategyDef(
        "feed_or_case_change",
        "Feed / case change (external)",
        "E_feed",
        "Feed F/T/P/comp changed outside Assist — log as context.",
    ),
    StrategyDef(
        "feed_stage_change",
        "Change feed stage",
        "F_structural",
        "Approval-only structural move — not auto-executed.",
        last_resort=True,
    ),
    StrategyDef(
        "stage_count_change",
        "Change stage count",
        "F_structural",
        "Approval-only structural move — not auto-executed.",
        last_resort=True,
    ),
    StrategyDef(
        "report_state_f",
        "Report State F / stop",
        "Stop",
        "Category-1 families exhausted or flat product response — do not relax FINAL_TARGET.",
        last_resort=True,
    ),
]


@dataclass(slots=True)
class PathNode:
    index: int
    strategy_id: str
    label: str
    summary: str
    kept: bool
    dry_run: bool
    before_score: float
    after_score: float
    message: str


@dataclass(slots=True)
class BoardRow:
    strategy_id: str
    label: str
    family: str
    status: StrategyStatus
    status_text: str
    description: str
    last_resort: bool = False


@dataclass(slots=True)
class TrialMapSnapshot:
    column_name: str
    you_are_here: str
    next_suggested: str
    converged: bool
    path: list[PathNode] = field(default_factory=list)
    board: list[BoardRow] = field(default_factory=list)
    path_text: str = ""


def classify_strategy(action: TrialAction) -> str:
    """Map a TrialAction onto a high-level strategy id."""
    kind = action.kind
    payload = action.payload or {}
    if "strategy_id" in payload:
        return str(payload["strategy_id"])
    if kind in {"none", "stop"} and "converg" in action.description.lower():
        return "converged"
    if kind == "manual_dof" or kind == "stop" and "dof" in action.description.lower():
        return "fix_dof"
    if kind == "solve_only":
        return "refresh_estimates"
    if kind == "set_goal":
        name = str(payload.get("spec_name", "")).lower()
        prev = payload.get("previous")
        goal = payload.get("goal")
        if "reflux" in name and "ratio" in name and prev is not None and goal is not None:
            return "reflux_nudge_down" if float(goal) < float(prev) else "reflux_nudge_up"
        if "reflux" in name and "ratio" not in name:
            return "reflux_flow_nudge"
        if "boilup" in name or "boil" in name or ("reb" in name and "duty" in name):
            return "boilup_nudge"
        if "ovhd" in name or "distill" in name or "overhead" in name:
            return "ovhd_rate_nudge"
        if "btms" in name or "bottoms" in name:
            return "bottoms_rate_nudge"
        if "nh3" in name or "ammonia" in name or "mass frac" in name or "frac" in name:
            return "nh3_goal_nudge"
        return str(payload.get("strategy_id", "reflux_nudge_up"))
    if "damp" in action.description.lower():
        return "lower_damping"
    if "estimate" in action.description.lower():
        return "refresh_estimates"
    if "swap" in action.description.lower():
        return "spec_swap_last_resort"
    if "feed" in action.description.lower():
        return "feed_or_case_change"
    return "refresh_estimates"


def suggest_next(
    board_status: dict[str, StrategyStatus],
    diagnosis: Diagnosis | None,
    converged: bool,
) -> str:
    if converged:
        return "None — column appears converged."
    if diagnosis and diagnosis.recommended_strategy == "fix_dof":
        return "Fix degrees of freedom (DOF ≠ 0) before other trials."
    # Prefer first OPEN (non-last-resort), else last-resort OPEN
    for spec in STRATEGY_CATALOG:
        if spec.last_resort:
            continue
        if board_status.get(spec.id, StrategyStatus.OPEN) == StrategyStatus.OPEN:
            return spec.label
    for spec in STRATEGY_CATALOG:
        if board_status.get(spec.id, StrategyStatus.OPEN) == StrategyStatus.OPEN:
            return f"{spec.label} (last resort)"
    return "All listed combinations tried — review trail or change the case manually."


def build_trial_map(
    column_name: str,
    history: list[TrialResult],
    state: ColumnState | None = None,
    diagnosis: Diagnosis | None = None,
) -> TrialMapSnapshot:
    path: list[PathNode] = []
    outcomes: dict[str, list[str]] = {s.id: [] for s in STRATEGY_CATALOG}

    for index, trial in enumerate(history, start=1):
        sid = classify_strategy(trial.action)
        dry = trial.message.upper().startswith("DRY RUN")
        label = next((s.label for s in STRATEGY_CATALOG if s.id == sid), sid)
        summary = trial.action.description
        path.append(
            PathNode(
                index=index,
                strategy_id=sid,
                label=label,
                summary=summary,
                kept=trial.kept,
                dry_run=dry,
                before_score=trial.before_score,
                after_score=trial.after_score,
                message=trial.message,
            )
        )
        if sid in outcomes:
            if dry:
                outcomes[sid].append("dry")
            elif trial.action.kind in {"none", "stop"} and trial.kept:
                outcomes[sid].append("ok")
            elif trial.kept:
                outcomes[sid].append("helped")
            else:
                outcomes[sid].append("failed")

    converged = bool(state and state.appears_converged) or (
        diagnosis is not None and DiagnosisCode.CONVERGED in diagnosis.codes
    )

    board_status: dict[str, StrategyStatus] = {}
    board: list[BoardRow] = []
    for spec in STRATEGY_CATALOG:
        events = outcomes.get(spec.id, [])
        if converged and not events:
            status = StrategyStatus.DONE_OK
            text = "Not needed (converged)"
        elif "helped" in events or "ok" in events:
            status = StrategyStatus.HELPED
            text = "Tried — helped / kept"
        elif "failed" in events:
            status = StrategyStatus.FAILED
            text = "Tried — failed / reversed"
        elif "dry" in events and not any(e in events for e in ("helped", "failed")):
            status = StrategyStatus.OPEN
            text = "Dry-run only — not committed"
        elif spec.last_resort:
            status = StrategyStatus.LOCKED
            text = "Locked (last resort)"
        else:
            status = StrategyStatus.OPEN
            text = "Open — not tried yet"
        board_status[spec.id] = status
        board.append(
            BoardRow(
                strategy_id=spec.id,
                label=spec.label,
                family=spec.family,
                status=status,
                status_text=text,
                description=spec.description,
                last_resort=spec.last_resort,
            )
        )

    next_label = suggest_next(board_status, diagnosis, converged)
    # Mark NEXT on board
    for row in board:
        if row.label == next_label or (
            next_label.startswith(row.label) and row.status in {StrategyStatus.OPEN, StrategyStatus.LOCKED}
        ):
            if not converged and row.status in {StrategyStatus.OPEN, StrategyStatus.LOCKED}:
                row.status = StrategyStatus.NEXT
                row.status_text = "NEXT suggested → " + row.status_text.replace("Open — ", "").replace("Locked ", "")
            break

    if state is None:
        here = f"{column_name}: no live inspect yet"
    else:
        status = "Converged" if state.appears_converged else "Not converged"
        here = (
            f"{column_name} · {status} · DOF={state.degrees_of_freedom} · "
            f"max residual={state.max_active_spec_error:.3g}"
        )
        if diagnosis is not None:
            here += f" · {diagnosis.severity}: {diagnosis.summary}"

    # Path strip text
    if not path:
        path_text = "Start -> (no trials yet) -> YOU ARE HERE"
    else:
        bits = ["Start"]
        for node in path:
            mark = "dry" if node.dry_run else ("kept" if node.kept else "rev")
            bits.append(f"{node.label} ({mark})")
        bits.append("YOU ARE HERE")
        path_text = " -> ".join(bits)

    return TrialMapSnapshot(
        column_name=column_name,
        you_are_here=here,
        next_suggested=next_label if not converged else "None — converged",
        converged=converged,
        path=path,
        board=board,
        path_text=path_text,
    )


def manual_map_event(description: str, strategy_id: str = "feed_or_case_change") -> TrialResult:
    """Create a history entry for an external change (e.g. feed stress) without COM writes."""
    return TrialResult(
        action=TrialAction(
            kind="manual_note",
            description=description,
            payload={"strategy_id": strategy_id},
        ),
        before_score=0.0,
        after_score=0.0,
        kept=True,
        message=f"LOGGED — {description}",
        after_state=None,
    )
