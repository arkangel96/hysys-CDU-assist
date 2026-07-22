"""
Thin complementary hooks from cdu_intel (Deliverables 1, 6, 8).

Does NOT replace States A–F, FINAL_TARGET lock, or Trial Map.
Adds PE-board labels / soft family hints only — no second state machine.
"""
from __future__ import annotations

from column_models import ColumnState, EngineeringState, TrialAction


# D1 §8 problem classes → Assist State (soft label for PE board only)
_STATE_TO_D1_CLASS: dict[EngineeringState, str] = {
    EngineeringState.A_INVALID: "specification",
    EngineeringState.B_NUMERICAL: "numerical",
    EngineeringState.C_OFF_SPEC: "process_performance",
    EngineeringState.D_CONSTRAINT: "hydraulic",  # operability / traffic gate
    EngineeringState.E_ACCEPTABLE: "validated_acceptable",
    EngineeringState.F_INFEASIBLE: "structural",  # escalate / structure
}


def d1_problem_class(eng: EngineeringState) -> str:
    """Complementary D1 §8 class label for the current Assist State."""
    return _STATE_TO_D1_CLASS.get(eng, "unclassified")


def d1_priority_reminder(eng: EngineeringState) -> str:
    """D1 §3.2 / §7.6 — soft reminder; does not change Assist strategy."""
    if eng == EngineeringState.E_ACCEPTABLE:
        return "D1: model acceptable — optimization only if engineer requests."
    if eng in {EngineeringState.A_INVALID, EngineeringState.B_NUMERICAL}:
        return (
            "D1: stop quality/energy optimize — fix DOF / numerical health first "
            "(assay/structure later if still bad)."
        )
    if eng == EngineeringState.F_INFEASIBLE:
        return "D1: escalate — do not force impossible product specs."
    return (
        "D1: one major family at a time; check neighbor products after draw/PA moves."
    )


def refine_preferred_family_cdu(
    state: ColumnState,
    eng: EngineeringState,
    preferred_family: str,
) -> tuple[str, str]:
    """
    Soft CDU hint from Active spec names (D1 §12 / §14).

    Returns (family, hypothesis_suffix). Does not override A_init / F_structural
    when Assist already chose those for State A/B/F.
    """
    if eng in {
        EngineeringState.A_INVALID,
        EngineeringState.B_NUMERICAL,
        EngineeringState.E_ACCEPTABLE,
        EngineeringState.F_INFEASIBLE,
    }:
        return preferred_family, ""

    actives = [s.name.lower() for s in state.active_specs()]
    has_pa = any(
        "pump around" in n or "pumparound" in n or "pa duty" in n or "pa circ" in n
        for n in actives
    ) or bool(getattr(state, "pa_energy_streams", None)) or bool(
        getattr(state, "active_pa_duty_specs", None)
    ) or bool(getattr(state, "active_pa_rate_specs", None))
    has_side_draw = any(
        "draw" in n
        and "ovhd" not in n
        and "overhead" not in n
        and "distill" not in n
        and "btms" not in n
        and "bottoms" not in n
        for n in actives
    ) or bool(getattr(state, "side_products", None)) or bool(
        getattr(state, "active_side_draw_specs", None)
    )
    has_steam = any("steam" in n for n in actives) or bool(
        getattr(state, "steam_streams", None)
    )

    # Mid-cut / off-spec: prefer draw or PA over default RR when those Actives exist
    if eng == EngineeringState.C_OFF_SPEC:
        if preferred_family in {"", "B_energy"} and has_side_draw:
            return "C_split", "CDU hint: Active side-draw present — prefer draw family before top RR."
        if preferred_family in {"", "B_energy", "C_split"} and has_pa and not has_side_draw:
            return "B_energy", "CDU hint: Active PA present — prefer PA energy for section traffic."
        if has_steam and preferred_family in {"", "B_energy"}:
            return "C2_steam", "CDU hint: Active steam present — consider stripping family."
        if getattr(state, "cdu_topology", False) and preferred_family in {"", "B_energy"}:
            return (
                preferred_family or "C_split",
                "CDU Connections: side strippers + PAs present — prefer draw/PA/steam families over top RR.",
            )
    if eng == EngineeringState.D_CONSTRAINT and has_side_draw:
        return "C_split", "CDU hint: operability — adjust draw/split before purity."

    return preferred_family, ""


def d8_acceptance_cues(state: ColumnState, eng: EngineeringState) -> list[str]:
    """
    Soft D8 acceptance checklist cues for PE board (not hard gates).

    Pass/fail is advisory — Assist States A–F remain the runtime truth.
    """
    cues: list[str] = []
    dof = state.degrees_of_freedom
    if dof is not None and dof != 0:
        cues.append("D8: DOF not zero — material/spec set not ready for quality chase.")
    if not state.physical_solution:
        cues.append("D8: physical/sentinel check failed — do not claim acceptance.")
    if not state.appears_converged:
        cues.append("D8: solver not stably converged.")
    if eng == EngineeringState.E_ACCEPTABLE:
        cues.append(
            "D8 soft OK: physical + converged + operable (+ targets if configured). "
            "Still review MB/HB / profiles / yields with engineer."
        )
    elif eng in {EngineeringState.C_OFF_SPEC, EngineeringState.D_CONSTRAINT}:
        cues.append(
            "D8: before quality/energy optimize — confirm MB/HB, T/P profiles, yields, warnings."
        )
    elif eng == EngineeringState.B_NUMERICAL:
        cues.append("D8: acceptance blocked until numerical health returns.")
    return cues


def d6_neighbor_reminder(family: str, strategy_id: str = "") -> str:
    """D6 rule: after cut/draw/PA moves, recheck neighboring products."""
    sid = (strategy_id or "").lower()
    fam = (family or "").lower()
    if (
        fam in {"c_split", "b_energy", "c2_steam"}
        or "draw" in sid
        or "pa_" in sid
        or "steam" in sid
        or "cut" in sid
    ):
        return (
            "D6: after draw/PA/steam/cut moves — recheck neighbor products "
            "(naphtha/kero/diesel/AGO/residue) before accepting."
        )
    return ""


def trial_cdu_footnote(action: TrialAction | None) -> str:
    """Short note appended to KEPT/REVERSED messages when relevant."""
    if action is None:
        return ""
    payload = action.payload or {}
    return d6_neighbor_reminder(
        str(payload.get("family", "")),
        str(payload.get("strategy_id", "")),
    )


def d3_interaction_tip(preferred_family: str) -> str:
    """Soft D3 coupling tip for PE board (complementary)."""
    fam = (preferred_family or "").lower()
    if fam == "c_split":
        return (
            "D3: side-draw change couples neighbors — watch adjacent cut/overlap "
            "and PA traffic together."
        )
    if fam == "b_energy":
        return (
            "D3: PA/top energy couples section reflux and cut sharpness — "
            "mid-cut often wants PA before more top RR."
        )
    if fam == "c2_steam":
        return (
            "D3: more steam improves stripping but raises vapor traffic + condenser load."
        )
    if fam == "e_feed":
        return (
            "D3: furnace/overflash/feed usually engineer-owned — log context, do not silent-nudge."
        )
    return ""


def format_d1_board_lines(
    eng: EngineeringState,
    state: ColumnState | None = None,
    preferred_family: str = "",
    targets_count: int | None = None,
) -> list[str]:
    """Extra PE-board lines — complementary, not authoritative."""
    lines = [
        f"  D1 class (complementary): {d1_problem_class(eng)}",
        f"  D1 note: {d1_priority_reminder(eng)}",
    ]
    if state is not None:
        try:
            from cdu_connections import connections_topology_cue

            cue = connections_topology_cue(state)
            if cue:
                lines.append(f"  {cue}")
        except Exception:
            pass
        for cue in d8_acceptance_cues(state, eng):
            lines.append(f"  {cue}")
    neigh = d6_neighbor_reminder(preferred_family)
    if neigh:
        lines.append(f"  {neigh}")
    tip = d3_interaction_tip(preferred_family)
    if tip:
        lines.append(f"  {tip}")
    if targets_count is not None and targets_count == 0:
        try:
            from cdu_targets import cdu_targets_config_hint

            lines.append(f"  FINAL_TARGET: {cdu_targets_config_hint()}")
        except Exception:
            lines.append("  FINAL_TARGET: none configured (operability/DOF only).")
    lines.append(
        "  Source: cdu_intel D1/D3/D6/D8 — helps Assist; does not supersede States/FINAL_TARGET."
    )
    return lines
