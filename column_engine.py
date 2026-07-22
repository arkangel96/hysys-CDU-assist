"""
CDU / atmospheric crude convergence assistant engine.

Multi-variable ChemE intelligence (not RR-only):
  Classify States A–F → choose variable family A/B/C/C2 → one bounded move →
  solve → judge FINAL_TARGET + operability → keep/reverse → switch or State F

Never auto-relaxes locked product FINAL_TARGETs.
Never adds an extra Active spec when DOF is already 0 without a 1-for-1 swap.
Never auto-saves the HYSYS .hsc; structural moves are approval-only.
See docs/MULTI_VARIABLE_ITERATION_MAP.md and column_connections.py
"""
from __future__ import annotations

from column_api import ColumnController, is_sentinel
from column_connections import (
    format_structural_block,
    pick_primary_structural_action,
    recommend_connections_moves,
    structural_moves_as_lines,
)
from column_models import (
    ColumnSpecState,
    ColumnState,
    ConvergenceLimits,
    Diagnosis,
    DiagnosisCode,
    EngineeringState,
    FinalTarget,
    ResponseClass,
    TrialAction,
    TrialResult,
    default_final_targets,
)
from column_spec_catalog import recommend_add_spec, recommend_specs_summary_clicks
from cdu_reasoning import format_d1_board_lines, refine_preferred_family_cdu, trial_cdu_footnote
from cdu_connections import connections_topology_cue
from cdu_monitor import format_monitor_block
from cdu_specs import format_specs_page_block, format_specs_summary_block
from cdu_subcooling import format_subcooling_block
from cdu_side_ops import format_side_ops_block
from cdu_rating import format_rating_block
from hysys_dialog_watcher import (
    clue_engineering_hint,
    clue_to_preferred_family,
    take_last_clues,
)
from hysys_messages_reader import (
    message_engineering_hint,
    take_last_messages,
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
    """Resolve measured value for a FINAL_TARGET (stream composition or matching spec Current)."""
    comps = tuple(c.lower() for c in target.component_name_contains)
    if comps and any(c in {"nh3", "ammonia"} for c in comps) and target.stream == "bottoms":
        if state.bottoms_nh3_mass_frac is not None:
            return state.bottoms_nh3_mass_frac

    needle = (target.spec_name_contains or "").lower().strip()
    if needle:
        for spec in state.specs:
            if needle in spec.name.lower() and spec.current_value is not None:
                if not is_sentinel(spec.current_value):
                    return float(spec.current_value)

    if target.stream == "bottoms" and state.bottoms_nh3_mass_frac is not None:
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
    if state.bottoms_molar_flow_kgmole_h is not None:
        if state.bottoms_molar_flow_kgmole_h < limits.min_bottoms_flow_kgmole_h:
            return False
    else:
        flow = state.bottoms_molar_flow
        if flow is None or is_sentinel(flow) or abs(float(flow)) <= 1e-6:
            return False

    for duty in (state.condenser_duty, state.reboiler_duty):
        if duty is not None and not is_sentinel(duty) and abs(duty) > limits.max_duty_abs:
            return False

    temps = state.profile.temperatures
    if temps:
        if max(temps) > limits.max_temperature_c or min(temps) < limits.min_temperature_c:
            return False
        if limits.require_profile_for_state_e and (max(temps) - min(temps)) < 0.05:
            return False
    return True


def classify_engineering_state(
    state: ColumnState,
    limits: ConvergenceLimits,
    targets: list[FinalTarget],
    target_status: dict[str, dict] | None = None,
    infeasible_evidence: bool = False,
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

    if infeasible_evidence and (hard_miss or not state.appears_converged):
        return EngineeringState.F_INFEASIBLE

    if hard_ok and state.appears_converged and operable(state, limits):
        return EngineeringState.E_ACCEPTABLE

    if hard_ok and state.appears_converged and not operable(state, limits):
        return EngineeringState.D_CONSTRAINT

    if hard_miss:
        return EngineeringState.C_OFF_SPEC

    if state.appears_converged:
        return EngineeringState.C_OFF_SPEC

    return EngineeringState.B_NUMERICAL


def _is_pa_spec(name: str) -> bool:
    lower = name.lower()
    if "pump around" in lower or "pumparound" in lower:
        return True
    if "pa duty" in lower or "pa circ" in lower or "pa return" in lower:
        return True
    if lower.startswith("pa ") and ("duty" in lower or "circ" in lower or "return" in lower):
        return True
    return False


def _is_steam_spec(name: str) -> bool:
    lower = name.lower()
    return "steam" in lower and (
        "strip" in lower or "rate" in lower or "flow" in lower or "duty" in lower
    )


def _is_side_draw_spec(name: str) -> bool:
    lower = name.lower()
    if "ovhd" in lower or "overhead" in lower or "distill" in lower:
        return False
    if "btms" in lower or "bottoms" in lower or "residue" in lower:
        return False
    return "draw" in lower


def _spec_family(name: str) -> str:
    lower = name.lower()
    if (
        "cut" in lower
        or "gap" in lower
        or "astm" in lower
        or "d86" in lower
        or "tbp" in lower
        or "frac" in lower
        or "nh3" in lower
        or "comp" in lower
        or "purity" in lower
    ):
        return "D_target"
    if _is_steam_spec(name):
        return "C2_steam"
    if _is_pa_spec(name):
        return "B_energy"
    if "reflux ratio" in lower or ("reflux" in lower and "ratio" in lower):
        return "B_energy"
    if "reflux" in lower or "boilup" in lower or "boil" in lower:
        return "B_energy"
    if "duty" in lower and ("cond" in lower or "reb" in lower):
        return "B_energy"
    if (
        "ovhd" in lower
        or "distill" in lower
        or "overhead" in lower
        or "btms" in lower
        or "bottoms" in lower
        or "residue" in lower
        or "draw" in lower
    ):
        return "C_split"
    return "B_energy"


def _strategy_for_spec(name: str, new_goal: float, old_goal: float) -> str:
    lower = name.lower()
    fam = _spec_family(name)
    if fam == "C2_steam":
        return "steam_nudge"
    if _is_pa_spec(name):
        if "return" in lower or ("temp" in lower and "pa" in lower):
            return "pa_return_t_nudge"
        if "circ" in lower or ("flow" in lower and "duty" not in lower):
            return "pa_circ_nudge"
        return "pa_duty_nudge"
    if fam == "C_split":
        if "btms" in lower or "bottoms" in lower or "residue" in lower:
            return "bottoms_rate_nudge"
        if "ovhd" in lower or "distill" in lower or "overhead" in lower:
            return "ovhd_rate_nudge"
        if _is_side_draw_spec(name) or "draw" in lower:
            return "side_draw_nudge"
        return "side_draw_nudge"
    if "reflux ratio" in lower or ("reflux" in lower and "ratio" in lower):
        return "reflux_nudge_down" if new_goal < old_goal else "reflux_nudge_up"
    if "reflux" in lower:
        return "reflux_flow_nudge"
    if "boilup" in lower or "boil" in lower or "reb" in lower:
        return "boilup_nudge"
    if fam == "D_target":
        if "cut" in lower or "gap" in lower or "astm" in lower or "d86" in lower or "tbp" in lower:
            return "astm_cut_goal_nudge"
        return "nh3_goal_nudge"
    return "reflux_nudge_up" if new_goal >= old_goal else "reflux_nudge_down"


def _nudge_goal(
    spec: ColumnSpecState,
    *,
    direction: float | None,
    frac: float,
    limits: ConvergenceLimits,
    toward_current: bool = False,
) -> TrialAction | None:
    if spec.goal_value is None:
        return None
    base = float(spec.goal_value)
    current = spec.current_value
    if toward_current and current is not None and not is_sentinel(current):
        cur = float(current)
        if abs(cur - base) < 1e-30:
            return None
        step = abs(base) * frac if abs(base) > 1e-30 else abs(cur) * frac
        if abs(base) > 1e-30:
            gap_ratio = abs(cur - base) / abs(base)
            if gap_ratio > 0.5:
                step = min(abs(cur - base), max(step, abs(base) * min(0.25, frac * 4)))
        new_goal = base + (step if cur > base else -step)
    else:
        d = 1.0 if direction is None else direction
        if abs(base) < 1e-30:
            new_goal = base + d * 1e-6
        else:
            new_goal = base * (1.0 + d * frac)
        if "reflux ratio" in spec.name.lower():
            new_goal = min(max(new_goal, limits.min_reflux_ratio), limits.max_reflux_ratio)

    if abs(new_goal - base) < 1e-30:
        return None
    sid = _strategy_for_spec(spec.name, new_goal, base)
    return TrialAction(
        kind="set_goal",
        description=f"Nudge '{spec.name}' GoalValue {base:.4g} -> {new_goal:.4g} [{_spec_family(spec.name)}]",
        payload={
            "spec_name": spec.name,
            "goal": new_goal,
            "previous": base,
            "strategy_id": sid,
            "family": _spec_family(spec.name),
        },
    )


def _dominant_active_spec(state: ColumnState) -> ColumnSpecState | None:
    actives = [s for s in state.active_specs() if s.goal_value is not None]
    if not actives:
        return None
    actives.sort(key=lambda s: s.score_error(), reverse=True)
    return actives[0]


def _find_active(state: ColumnState, *needles: str) -> ColumnSpecState | None:
    for spec in state.active_specs():
        lower = spec.name.lower()
        if all(n in lower for n in needles):
            return spec
    for spec in state.active_specs():
        lower = spec.name.lower()
        if any(n in lower for n in needles):
            return spec
    return None


def _product_delta(
    before: ColumnState,
    after: ColumnState,
    targets: list[FinalTarget],
) -> tuple[float, bool, bool]:
    """Return (relative impurity improvement, any_improved, any_worsened) for locked targets."""
    before_t = evaluate_final_targets(before, targets)
    after_t = evaluate_final_targets(after, targets)
    improved = False
    worsened = False
    rel = 0.0
    n = 0
    for target in targets:
        if not target.locked:
            continue
        b = before_t.get(target.id, {}).get("measured")
        a = after_t.get(target.id, {}).get("measured")
        if b is None or a is None or is_sentinel(b) or is_sentinel(a):
            continue
        b = float(b)
        a = float(a)
        n += 1
        if target.relationship == "less_or_equal":
            if a < b * (1.0 - 1e-12):
                improved = True
            if a > b * 1.05:
                worsened = True
            if abs(b) > 1e-30:
                rel += (b - a) / abs(b)
        elif target.relationship == "greater_or_equal":
            if a > b * (1.0 + 1e-12):
                improved = True
            if a < b * 0.95:
                worsened = True
            if abs(b) > 1e-30:
                rel += (a - b) / abs(b)
        else:
            if abs(a - target.target_value) < abs(b - target.target_value):
                improved = True
            if abs(a - target.target_value) > abs(b - target.target_value) * 1.05:
                worsened = True
    return (rel / n if n else 0.0, improved, worsened)


def should_keep_trial(
    before: ColumnState,
    after: ColumnState,
    before_score: float,
    after_score: float,
    limits: ConvergenceLimits,
    targets: list[FinalTarget],
) -> bool:
    """Plant judgment: FINAL_TARGET + operability first; residual score second."""
    if not after.physical_solution:
        return False

    before_op = operable(before, limits)
    after_op = operable(after, limits)
    if before_op and not after_op:
        return False

    _rel, product_improved, product_worsened = _product_delta(before, after, targets)
    if product_worsened:
        return False

    residual_improved = after_score < before_score * 0.98
    hard_miss_before = any(
        not info["met"]
        for info in evaluate_final_targets(before, targets).values()
    )

    if hard_miss_before:
        if product_improved and after_op:
            return True
        if after_op and residual_improved and not product_worsened:
            return True
        return False

    if after_op and (product_improved or residual_improved):
        return True
    if not before_op and after_op and after.physical_solution:
        return True
    return False


def diagnose(
    state: ColumnState,
    limits: ConvergenceLimits | None = None,
    targets: list[FinalTarget] | None = None,
    infeasible_evidence: bool = False,
    exhausted_families: set[str] | None = None,
) -> Diagnosis:
    limits = limits or ConvergenceLimits()
    targets = targets if targets is not None else default_final_targets()
    codes: list[DiagnosisCode] = []
    details: list[str] = []
    target_status = evaluate_final_targets(state, targets)
    exhausted_families = exhausted_families or set()

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
            f"Operability gate failed (bottoms flow / duty / T window). "
            f"Need bottoms ≥ {limits.min_bottoms_flow_kgmole_h:g} "
            f"{getattr(state, 'molar_flow_unit', 'kgmole/h')}."
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

    if exhausted_families:
        details.append(f"Exhausted / flat families: {sorted(exhausted_families)}")

    eng = classify_engineering_state(
        state, limits, targets, target_status, infeasible_evidence=infeasible_evidence
    )

    preferred_family = ""
    pe_hypothesis = ""

    if eng == EngineeringState.E_ACCEPTABLE:
        codes = [DiagnosisCode.CONVERGED]
        strategy = "none_converged"
        summary = "State E — physical solve, FINAL_TARGETs met, operability OK."
        severity = "info"
        pe_read = "Acceptable converged solution."
        potential = "success"
        preferred_family = ""
        pe_hypothesis = "No further operating moves required."
    elif eng == EngineeringState.A_INVALID:
        strategy = "fix_dof"
        summary = "State A — DOF invalid. Fix specification set before tuning."
        severity = "critical"
        pe_read = "Model not properly posed."
        potential = "nowhere"
        preferred_family = "A_init"
        pe_hypothesis = "Restore DOF = 0 before any GoalValue iteration."
    elif eng == EngineeringState.B_NUMERICAL:
        strategy = "numerical_recovery"
        summary = (
            "State B — numerically unhealthy. Refresh estimates / baseline Active swap "
            "before product targeting. Do not relax FINAL_TARGET."
        )
        severity = "critical"
        pe_read = "Bottoms/duties not trustworthy; recover physical solution first."
        potential = "marginal"
        preferred_family = "A_init"
        pe_hypothesis = "Family A (init/estimates) before energy or split nudges."
    elif eng == EngineeringState.D_CONSTRAINT:
        strategy = "nudge_operating_mv"
        summary = (
            "State D — targets look met but operability fails. "
            "Prefer split-family (Ovhd/Btms rates) — not purity relax."
        )
        severity = "warn"
        pe_read = "Green residuals with unrealistic bottoms/duties — fix split/energy path."
        potential = "going_somewhere"
        preferred_family = "C_split"
        pe_hypothesis = "Adjust Active Ovhd/Btms rate toward a physical split."
        if "full reflux" in (state.condenser_type or "").lower():
            details.append(
                "Connections: Full Reflux condenser — Ovhd is vapor product; "
                "Active Ovhd rate can drive near-zero bottoms if set too high."
            )
    elif eng == EngineeringState.C_OFF_SPEC:
        strategy = "nudge_operating_mv"
        summary = (
            "State C — FINAL_TARGET / residuals unmet. "
            "Choose Category-1 family (energy OR split) — not RR alone; FINAL_TARGET locked."
        )
        severity = "warn"
        pe_read = "Multi-variable operating path — RR / rates / boilup as Active allows."
        potential = "going_somewhere"
        dom = _dominant_active_spec(state)
        if dom is not None:
            preferred_family = _spec_family(dom.name)
            pe_hypothesis = (
                f"Dominant Active residual on '{dom.name}' -> try family {preferred_family}."
            )
        else:
            preferred_family = "B_energy"
            pe_hypothesis = "No clear dominant Active -- start with energy family if RR Active."
    else:
        strategy = "report_infeasible"
        summary = "State F — likely infeasible under current structure/assumptions."
        severity = "critical"
        pe_read = "Category-1 families exhausted or flat product response — escalate."
        potential = "nowhere"
        preferred_family = "F_structural"
        pe_hypothesis = "Stop operating nudges; structural/feed changes need engineer approval."
        codes.append(DiagnosisCode.LIKELY_INFEASIBLE)

    # Complementary D1 soft hint (does not replace States A–F)
    preferred_family, cdu_hint = refine_preferred_family_cdu(state, eng, preferred_family)
    if cdu_hint:
        pe_hypothesis = f"{pe_hypothesis} {cdu_hint}".strip() if pe_hypothesis else cdu_hint
        details.append(cdu_hint)

    topo_cue = connections_topology_cue(state)
    if topo_cue:
        pe_read = f"{pe_read} {topo_cue}".strip() if pe_read else topo_cue
        details.append(topo_cue)

    if not codes:
        codes.append(DiagnosisCode.UNKNOWN_FAILURE)

    has_rr = any("reflux ratio" in s.name.lower() for s in state.specs)
    has_comp_target = any(
        t.property_type == "composition" or "nh3" in t.spec_name_contains.lower()
        for t in targets
    ) or any(
        "nh3" in s.name.lower() or "frac" in s.name.lower() for s in state.specs
    )
    has_petroleum_target = any(
        t.property_type in {"astm_d86", "tbp", "cut", "gap", "cold_prop"}
        or any(tok in t.spec_name_contains.lower() for tok in ("cut", "gap", "astm", "d86", "tbp"))
        for t in targets
    ) or any(
        any(tok in s.name.lower() for tok in ("cut", "gap", "astm", "d86", "tbp"))
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
        weak_operating_response=infeasible_evidence,
        product_line="cdu",
        has_petroleum_final_target=has_petroleum_target,
    )
    add_lines = [
        f"{r.action}: {r.hysys_type_name or '(none)'} — {r.reason}" for r in add_recs
    ]

    nh3_locked = any(
        "nh3" in t.id.lower() or "nh3" in t.spec_name_contains.lower() for t in targets
    )
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
        nh3_is_final_target=nh3_locked,
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
            bits.append("Sync Current->Goal")
        click_lines.append(f"{' | '.join(bits)} — {c.reason}")

    # HYSYS popup clues — SEE + ACT (feed into family / hypothesis)
    dialog_clues = take_last_clues()
    dialog_lines: list[str] = []
    clue_tags: list[str] = []
    for clue in dialog_clues:
        clue_tags.extend(clue.clue_tags)
        dialog_lines.append(clue.summary())
        details.append(f"HYSYS popup: {clue.summary()}")
        hint = clue_engineering_hint(clue.clue_tags, clue.message)
        if hint and hint not in details:
            details.append(hint)

    # Continuous Messages pane clues
    message_clues = take_last_messages()
    message_lines: list[str] = []
    for clue in message_clues:
        clue_tags.extend(clue.clue_tags)
        message_lines.append(clue.summary())
        details.append(f"HYSYS Messages: {clue.summary()}")
        hint = message_engineering_hint(clue.clue_tags, clue.text)
        if hint and hint not in details:
            details.append(hint)

    if clue_tags:
        fam_from_popup = clue_to_preferred_family(clue_tags)
        if fam_from_popup:
            preferred_family = fam_from_popup
        if "temperature_cross" in clue_tags and not pe_hypothesis:
            pe_hypothesis = message_engineering_hint(clue_tags, message_lines[-1] if message_lines else "")
        if "invalid_temperature" in clue_tags or "poor_spec" in clue_tags:
            if eng not in {EngineeringState.A_INVALID, EngineeringState.B_NUMERICAL}:
                # Prefer numerical/model review over purity chase
                if not state.physical_solution:
                    eng = EngineeringState.B_NUMERICAL
                    strategy = "numerical_recovery"
                    preferred_family = "A_init"
            pe_hypothesis = message_engineering_hint(clue_tags, message_lines[-1] if message_lines else "")
        if "draw_exceeds_feed" in clue_tags:
            pe_hypothesis = clue_engineering_hint(clue_tags, dialog_clues[-1].message if dialog_clues else "")
            if eng == EngineeringState.E_ACCEPTABLE:
                # Illegal draw is not an acceptable plant state for Assist judgment
                eng = EngineeringState.A_INVALID
                strategy = "fix_dof"
                summary = (
                    "State A/D — HYSYS rejected draw spec (draw > feed). "
                    "Fix Ovhd/Btms Active set; do not keep the illegal Goal."
                )
                severity = "critical"
                pe_read = "Popup clue: overhead draw exceeds feed — split/spec invalid."
                potential = "nowhere"
                codes.append(DiagnosisCode.UNDER_SPECIFIED)
            elif eng in {EngineeringState.C_OFF_SPEC, EngineeringState.D_CONSTRAINT}:
                pe_hypothesis = (
                    "HYSYS popup draw>feed — prefer C_split lower Ovhd / restore Btms; "
                    "do not raise Ovhd further."
                )

    # Connections structural intelligence (Family F) — think yes, write only with approval
    structural_moves = recommend_connections_moves(
        state,
        eng,
        preferred_family=preferred_family,
        infeasible_evidence=infeasible_evidence,
        limits=limits,
    )
    structural_lines = structural_moves_as_lines(structural_moves)
    if structural_lines and eng == EngineeringState.F_INFEASIBLE:
        preferred_family = preferred_family or "F_structural"
        if not pe_hypothesis:
            pe_hypothesis = (
                "Mechanical Connections change may be required — approval only; "
                "do not silent-edit stages/P/condenser."
            )

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
        preferred_family=preferred_family,
        pe_hypothesis=pe_hypothesis,
        hysys_dialog_clues=dialog_lines,
        hysys_message_clues=message_lines,
        structural_recommendations=structural_lines,
    )


def format_connections_block(state: ColumnState) -> str:
    """HYSYS Design → Connections snapshot for PE board / UI."""
    p_u = state.pressure_unit or "bar"
    lines = [
        "CONNECTIONS (Design → Connections) [READ]",
        f"  Stages={state.number_of_stages} numbering={state.stage_numbering or '—'}",
        f"  P_top={state.condenser_pressure_bar} {p_u}  "
        f"dP_top={state.condenser_dp_bar}  "
        f"P_bot={state.reboiler_pressure_bar} {p_u}  "
        f"dP_bot={state.reboiler_dp_bar}",
        f"  Condenser={state.condenser_type or '—'}",
    ]
    if state.cdu_topology:
        lines.append("  Topology=CDU (side draws / strippers / PAs)")

    if state.inlet_rows:
        lines.append("  Inlet Streams:")
        for row in state.inlet_rows:
            role = f"  [{row.role}]" if row.role and row.role != "unknown" else ""
            lines.append(f"    {row.display_line()}{role}")
    else:
        feeds = ", ".join(state.feed_streams) if state.feed_streams else "—"
        feed_loc = state.feed_stage_label or (
            str(state.feed_stage) if state.feed_stage is not None else "—"
        )
        lines.append(f"  Feed={feeds} @ {feed_loc}")

    if state.outlet_rows:
        lines.append("  Outlet Streams:")
        for row in state.outlet_rows:
            role = f"  [{row.role}]" if row.role and row.role != "unknown" else ""
            lines.append(f"    {row.display_line()}{role}")
    else:
        lines.append(
            f"  Ovhd product={state.top_vapour_product or '—'}  "
            f"Btms product={state.bottoms_liquid_product or '—'}"
        )
        lines.append(f"  Energy={', '.join(state.energy_streams) or '—'}")

    role_bits: list[str] = []
    if state.feed_stage_label or state.feed_stage is not None:
        role_bits.append(
            f"crude@{state.feed_stage_label or state.feed_stage}"
        )
    if state.overhead_liquid_product:
        role_bits.append(f"naphtha={state.overhead_liquid_product}")
    if state.top_vapour_product:
        role_bits.append(f"offgas={state.top_vapour_product}")
    if state.bottoms_liquid_product:
        role_bits.append(f"residue={state.bottoms_liquid_product}")
    if state.side_products:
        role_bits.append(f"sides={','.join(state.side_products)}")
    if state.steam_streams:
        role_bits.append(f"steam={','.join(state.steam_streams)}")
    if state.pa_energy_streams:
        role_bits.append(f"PA={','.join(state.pa_energy_streams)}")
    if role_bits:
        lines.append("  Roles: " + " | ".join(role_bits))

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
        f"  Family: {diagnosis.preferred_family or '—'} | Strategy: {diagnosis.recommended_strategy}",
        f"  Hypothesis: {diagnosis.pe_hypothesis or '—'}",
    ]
    lines.extend(
        format_d1_board_lines(
            diagnosis.engineering_state,
            state=state,
            preferred_family=diagnosis.preferred_family,
            targets_count=len(diagnosis.final_target_status),
        )
    )
    lines.extend(
        [
        f"  DOF={state.degrees_of_freedom} physical={state.physical_solution} "
        f"converged_flag={state.appears_converged} score={score_state(state):.4g}",
        f"  CondQ={state.condenser_duty} RebQ={state.reboiler_duty}",
        f"  Offgas={state.overhead_molar_flow_kgmole_h} {state.molar_flow_unit} | "
        f"Btms={state.bottoms_molar_flow_kgmole_h} {state.molar_flow_unit} | "
        f"BtmsT={state.bottoms_temperature} {state.temperature_unit}",
        ]
    )
    if state.overhead_liquid_product or state.side_products:
        lines.append(
            f"  Products: naphtha={state.overhead_liquid_product or '—'} | "
            f"sides={', '.join(state.side_products) or '—'} | "
            f"residue={state.bottoms_liquid_product or '—'}"
        )
    lines.append(format_connections_block(state))
    lines.append(format_monitor_block(state))
    lines.append(format_specs_page_block(state))
    lines.append(format_specs_summary_block(state))
    lines.append(format_subcooling_block(state))
    lines.append(format_side_ops_block(state))
    lines.append(format_rating_block(state))
    if diagnosis.structural_recommendations:
        lines.append("CONNECTIONS STRUCTURAL [F] — MECHANICAL / APPROVAL REQUIRED")
        lines.append(
            "  You must confirm before any write. Assist will not silent-edit Connections."
        )
        for rec in diagnosis.structural_recommendations:
            lines.append(f"  -> {rec}")
    else:
        lines.append(
            format_structural_block(
                recommend_connections_moves(
                    state,
                    diagnosis.engineering_state,
                    preferred_family=diagnosis.preferred_family,
                )
            )
        )
    for sp in state.active_specs():
        goal = sp.goal_display if sp.goal_display is not None else sp.goal_value
        cur = sp.current_display if sp.current_display is not None else sp.current_value
        unit = f" {sp.display_unit}" if sp.display_unit else ""
        fam = f" [{sp.mv_family}]" if getattr(sp, "mv_family", "") else ""
        lines.append(
            f"  ACTIVE{fam} {sp.name}: goal={goal}{unit} current={cur}{unit} err={sp.error}"
        )
    for tid, info in diagnosis.final_target_status.items():
        lines.append(
            f"  TARGET {tid}: {info['measured']} vs {info['target']} "
            f"(met={info['met']}, locked={info['locked']})"
        )
    if diagnosis.hysys_dialog_clues:
        lines.append("  HYSYS POPUP CLUES (acted on as PE evidence):")
        for clue in diagnosis.hysys_dialog_clues[-6:]:
            lines.append(f"    !! {clue}")
    if diagnosis.hysys_message_clues:
        lines.append("  HYSYS MESSAGES PANE CLUES:")
        for clue in diagnosis.hysys_message_clues[-8:]:
            lines.append(f"    :: {clue}")
    if diagnosis.add_spec_recommendations:
        lines.append("  ADD SPEC intelligence:")
        for rec in diagnosis.add_spec_recommendations:
            lines.append(f"    - {rec}")
    if diagnosis.specs_summary_clicks:
        lines.append("  SPECS SUMMARY clicks (Design -> Specs Summary):")
        for rec in diagnosis.specs_summary_clicks:
            lines.append(f"    -> {rec}")
    lines.append(f"  Summary: {diagnosis.summary}")
    for detail in diagnosis.details[:8]:
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
    skipped_families: set[str] | None = None,
) -> TrialAction | None:
    """Multi-variable ChemE chooser — energy, split, and init families (not RR alone)."""
    targets = targets if targets is not None else default_final_targets()
    skipped = skipped_families or set()
    strategy = diagnosis.recommended_strategy

    if strategy == "none_converged":
        return None

    if strategy == "fix_dof":
        clue_text = " ".join(diagnosis.hysys_dialog_clues).lower()
        if "draw_exceeds_feed" in clue_text or "draw rate must be less than" in clue_text:
            ovhd = (
                _find_active(state, "ovhd")
                or _find_active(state, "distill")
                or _find_active(state, "overhead")
            )
            if ovhd is not None and not _is_locked_final_spec(ovhd.name, targets, limits):
                action = _nudge_goal(
                    ovhd, direction=-1.0, frac=max(limits.rate_nudge_fraction, 0.15), limits=limits
                )
                if action is not None:
                    action.description += " [popup clue: draw>feed -> lower Ovhd]"
                    return action
            return TrialAction(
                kind="stop",
                description=(
                    "HYSYS popup: Ovhd/draw exceeds feed. Deactivate Ovhd or set Goal < feed "
                    "(manual Specs Summary). Do not raise draw further."
                ),
                payload={
                    "strategy_id": "ovhd_rate_nudge",
                    "family": "C_split",
                    "response": "STOP_INFEASIBLE",
                },
            )
        return TrialAction(
            kind="manual_dof",
            description="DOF must be fixed manually (activate/deactivate specs to reach 0).",
            payload={"dof": state.degrees_of_freedom, "strategy_id": "fix_dof", "family": "A_init"},
        )

    if strategy == "report_infeasible":
        moves = recommend_connections_moves(
            state,
            diagnosis.engineering_state,
            preferred_family="F_structural",
            infeasible_evidence=True,
            limits=limits,
        )
        payload = pick_primary_structural_action(moves)
        if payload is not None:
            return TrialAction(
                kind="structural_approval",
                description=str(payload["description"]),
                payload=payload,
            )
        return TrialAction(
            kind="stop",
            description="State F — likely infeasible; stop without relaxing FINAL_TARGET.",
            payload={
                "strategy_id": "report_state_f",
                "response": "STOP_INFEASIBLE",
                "family": "F_structural",
            },
        )

    if strategy == "numerical_recovery":
        return TrialAction(
            kind="refresh_estimates",
            description="State B recovery: refresh composition estimates and re-solve [A_init].",
            payload={"strategy_id": "refresh_estimates", "family": "A_init"},
        )

    # --- Build candidate nudges across families B, C, C2 ---
    candidates: list[TrialAction] = []

    # Dominant Active residual (any family except locked D)
    dom = _dominant_active_spec(state)
    if dom is not None and not _is_locked_final_spec(dom.name, targets, limits):
        fam = _spec_family(dom.name)
        if fam not in skipped and dom.score_error() > limits.max_active_spec_error:
            action = _nudge_goal(
                dom,
                direction=None,
                frac=limits.rate_nudge_fraction
                if fam in {"C_split", "C2_steam"}
                else limits.reflux_nudge_fraction,
                limits=limits,
                toward_current=True,
            )
            if action is not None:
                candidates.append(action)

    # B_energy: PA first (CDU mid-section), then RR / reflux / boilup
    if "B_energy" not in skipped:
        for spec in state.active_specs():
            if not _is_pa_spec(spec.name):
                continue
            if _is_locked_final_spec(spec.name, targets, limits):
                continue
            action = _nudge_goal(
                spec,
                direction=None,
                frac=limits.reflux_nudge_fraction,
                limits=limits,
                toward_current=True,
            )
            if action is not None:
                # Prefer PA when diagnosis wants energy or mid-cut
                if diagnosis.preferred_family in {None, "", "B_energy"}:
                    candidates.insert(0, action)
                else:
                    candidates.append(action)

        rr = _find_active(state, "reflux ratio") or _find_active(state, "reflux", "ratio")
        if rr is not None and rr.goal_value is not None:
            nh3_miss = any(
                (not info["met"]) and tid.upper().startswith("NH3")
                for tid, info in diagnosis.final_target_status.items()
            )
            hard_miss = bool(diagnosis.final_target_status) and any(
                not info["met"] for info in diagnosis.final_target_status.values()
            )
            # Mid-cut / draw / steam problems: do NOT default to raising top RR
            prefer_rr_up = (
                state.physical_solution
                and (nh3_miss or hard_miss)
                and diagnosis.preferred_family not in {"C_split", "C2_steam"}
            )
            if prefer_rr_up:
                action = _nudge_goal(
                    rr, direction=1.0, frac=limits.reflux_nudge_fraction, limits=limits
                )
            else:
                action = _nudge_goal(
                    rr,
                    direction=None,
                    frac=limits.reflux_nudge_fraction,
                    limits=limits,
                    toward_current=True,
                )
            if action is not None:
                candidates.append(action)

        for needle in (("reflux",), ("boilup",), ("boil",)):
            spec = _find_active(state, *needle)
            if spec is None or spec is rr:
                continue
            if "ratio" in spec.name.lower() and needle == ("reflux",):
                continue
            if _is_pa_spec(spec.name) or _is_steam_spec(spec.name):
                continue
            if _is_locked_final_spec(spec.name, targets, limits):
                continue
            action = _nudge_goal(
                spec,
                direction=None,
                frac=limits.reflux_nudge_fraction,
                limits=limits,
                toward_current=True,
            )
            if action is not None:
                candidates.append(action)

    # C_split: side draws + Ovhd / Btms / residue
    if "C_split" not in skipped:
        prefer_btms_up = (
            diagnosis.engineering_state == EngineeringState.D_CONSTRAINT
            or (
                state.bottoms_molar_flow_kgmole_h is not None
                and state.bottoms_molar_flow_kgmole_h < limits.min_bottoms_flow_kgmole_h
            )
        )
        btms = (
            _find_active(state, "btms")
            or _find_active(state, "bottoms")
            or _find_active(state, "residue")
        )
        ovhd = (
            _find_active(state, "ovhd")
            or _find_active(state, "distill")
            or _find_active(state, "overhead")
        )
        side_draws = [
            s
            for s in state.active_specs()
            if _is_side_draw_spec(s.name) and not _is_locked_final_spec(s.name, targets, limits)
        ]
        for draw in side_draws:
            action = _nudge_goal(
                draw,
                direction=None,
                frac=limits.rate_nudge_fraction,
                limits=limits,
                toward_current=True,
            )
            if action is not None:
                if diagnosis.preferred_family == "C_split":
                    candidates.insert(0, action)
                else:
                    candidates.append(action)

        if prefer_btms_up and btms is not None and not _is_locked_final_spec(btms.name, targets, limits):
            action = _nudge_goal(
                btms, direction=1.0, frac=limits.rate_nudge_fraction, limits=limits
            )
            if action is not None:
                candidates.insert(0, action)
        if prefer_btms_up and ovhd is not None and not _is_locked_final_spec(ovhd.name, targets, limits):
            action = _nudge_goal(
                ovhd,
                direction=-1.0,
                frac=limits.rate_nudge_fraction,
                limits=limits,
                toward_current=True,
            )
            if action is None:
                action = _nudge_goal(
                    ovhd, direction=-1.0, frac=limits.rate_nudge_fraction, limits=limits
                )
            if action is not None:
                candidates.insert(0, action)
        for spec in (btms, ovhd):
            if spec is None or _is_locked_final_spec(spec.name, targets, limits):
                continue
            action = _nudge_goal(
                spec,
                direction=None,
                frac=limits.rate_nudge_fraction,
                limits=limits,
                toward_current=True,
            )
            if action is None and prefer_btms_up:
                direction = 1.0 if spec is btms else -1.0
                action = _nudge_goal(
                    spec, direction=direction, frac=limits.rate_nudge_fraction, limits=limits
                )
            if action is not None:
                candidates.append(action)

    # C2_steam: stripping steam
    if "C2_steam" not in skipped:
        for spec in state.active_specs():
            if not _is_steam_spec(spec.name):
                continue
            if _is_locked_final_spec(spec.name, targets, limits):
                continue
            action = _nudge_goal(
                spec,
                direction=None,
                frac=limits.rate_nudge_fraction,
                limits=limits,
                toward_current=True,
            )
            if action is not None:
                if diagnosis.preferred_family == "C2_steam":
                    candidates.insert(0, action)
                else:
                    candidates.append(action)

    # Deduplicate by spec name (keep first)
    seen: set[str] = set()
    unique: list[TrialAction] = []
    for action in candidates:
        name = str(action.payload.get("spec_name", ""))
        if name in seen:
            continue
        seen.add(name)
        unique.append(action)

    if unique:
        clue_text = " ".join(diagnosis.hysys_dialog_clues).lower()
        block_ovhd_up = "draw_exceeds_feed" in clue_text or "draw rate must be less than" in clue_text
        if block_ovhd_up:
            filtered: list[TrialAction] = []
            for action in unique:
                name = str(action.payload.get("spec_name", "")).lower()
                prev = action.payload.get("previous")
                goal = action.payload.get("goal")
                if (
                    ("ovhd" in name or "distill" in name or "overhead" in name)
                    and prev is not None
                    and goal is not None
                    and float(goal) > float(prev)
                ):
                    continue  # never raise Ovhd after draw>feed popup
                filtered.append(action)
            unique = filtered or unique
        # Prefer diagnosis family if present
        prefer = diagnosis.preferred_family
        if prefer:
            for action in unique:
                if action.payload.get("family") == prefer:
                    return action
        return unique[0]

    # Baseline swap if NH3 locked active (State B follow-on / last resort init)
    if (
        limits.allow_baseline_spec_swap
        and state.degrees_of_freedom == 0
        and "A_init" not in skipped
    ):
        nh3 = next((s for s in state.active_specs() if "nh3" in s.name.lower()), None)
        ovhd = next((s for s in state.specs if "ovhd" in s.name.lower()), None)
        if (
            nh3 is not None
            and _is_locked_final_spec(nh3.name, targets, limits)
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
                        f"1-for-1 baseline swap: deactivate '{nh3.name}', "
                        f"activate '{ovhd.name}' (FINAL_TARGET stays locked as monitor) [A_init]."
                    ),
                    payload={
                        "deactivate": nh3.name,
                        "activate": ovhd.name,
                        "activate_goal": float(goal),
                        "strategy_id": "spec_swap_last_resort",
                        "family": "A_init",
                    },
                )

    locked_active = [
        s for s in state.active_specs() if _is_locked_final_spec(s.name, targets, limits)
    ]
    if locked_active:
        moves = recommend_connections_moves(
            state,
            EngineeringState.F_INFEASIBLE,
            preferred_family="F_structural",
            infeasible_evidence=True,
            limits=limits,
        )
        payload = pick_primary_structural_action(moves)
        if payload is not None:
            return TrialAction(
                kind="structural_approval",
                description=str(payload["description"]),
                payload=payload,
            )
        return TrialAction(
            kind="stop",
            description=(
                "No safe Category-1 MV left (energy/split/init). "
                "FINAL_TARGET still locked — State F evidence; do not auto-relax product GoalValue."
            ),
            payload={
                "strategy_id": "report_state_f",
                "response": "STOP_INFEASIBLE",
                "family": "F_structural",
            },
        )

    return TrialAction(
        kind="refresh_estimates",
        description="No safe knob found; refresh estimates and re-evaluate [A_init].",
        payload={"strategy_id": "refresh_estimates", "family": "A_init"},
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
    ) -> None:
        self.columns = columns
        self.limits = limits or ConvergenceLimits()
        self.targets = targets if targets is not None else default_final_targets()
        self.history: list[TrialResult] = []
        self._estimates_refreshed = False
        self._flat_product_streak = 0
        self._skipped_families: set[str] = set()
        self._family_flat_counts: dict[str, int] = {}
        self._optimize_flat_streak = 0
        # Simple optimize (thin layer) — default min RR
        from column_optimize import SimpleObjective

        self.optimize_objective = SimpleObjective.MIN_REFLUX_RATIO

    def _infeasible_evidence(self) -> bool:
        if self._flat_product_streak >= self.limits.max_flat_trials_before_f:
            return True
        # Both energy and split families flat/exhausted
        if {"B_energy", "C_split"}.issubset(self._skipped_families):
            return True
        return False

    def inspect(self, column_name: str) -> ColumnState:
        return self.columns.inspect(column_name)

    def diagnose_column(self, column_name: str) -> tuple[ColumnState, Diagnosis]:
        state = self.inspect(column_name)
        return state, diagnose(
            state,
            self.limits,
            self.targets,
            infeasible_evidence=self._infeasible_evidence(),
            exhausted_families=self._skipped_families,
        )

    def pe_board(self, column_name: str) -> str:
        state, diagnosis = self.diagnose_column(column_name)
        return format_pe_board(state, diagnosis)

    def run_one_trial(self, column_name: str, dry_run: bool = False) -> TrialResult:
        before = self.inspect(column_name)
        diagnosis = diagnose(
            before,
            self.limits,
            self.targets,
            infeasible_evidence=self._infeasible_evidence(),
            exhausted_families=self._skipped_families,
        )
        action = propose_action(
            before,
            self.limits,
            diagnosis,
            self.targets,
            skipped_families=self._skipped_families,
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

        if action.kind in {"manual_dof", "stop", "structural_approval"}:
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=before_score,
                kept=False,
                message=(
                    action.description
                    if action.kind != "structural_approval"
                    else (
                        "STRUCTURAL HOLD — mechanical Connections change needs your approval. "
                        + action.description
                    )
                ),
                after_state=before,
                response_class=ResponseClass.STOP_INFEASIBLE
                if action.kind in {"stop", "structural_approval"}
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
                before,
                self.limits,
                diagnosis,
                self.targets,
                skipped_families=self._skipped_families | {"A_init"},
            )
            if alt is not None and alt.kind == "baseline_swap":
                action = alt

        snap = self.columns.snapshot(column_name)
        family = str(action.payload.get("family", ""))
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

            keep = (not unphysical) and should_keep_trial(
                before, after, before_score, after_score, self.limits, self.targets
            )
            if action.kind in {"refresh_estimates", "baseline_swap"}:
                if after.physical_solution and not before.physical_solution:
                    keep = True
                elif after.physical_solution and after_score <= before_score * 1.05:
                    keep = keep or operable(after, self.limits)

            rel_prod, _imp, _wors = _product_delta(before, after, self.targets)
            flat_product = abs(rel_prod) < self.limits.flat_product_relative

            if not keep:
                self.columns.restore(snap)
                self.columns.run_column(column_name)
                after = self.inspect(column_name)
                after_score = score_state(after)
                response = classify_response(
                    before, after, before_score, after_score, False, self.limits, self.targets
                )
                if family in {"B_energy", "C_split", "A_init"}:
                    self._family_flat_counts[family] = self._family_flat_counts.get(family, 0) + 1
                    if self._family_flat_counts[family] >= self.limits.max_flat_trials_before_f:
                        self._skipped_families.add(family)
                if flat_product:
                    self._flat_product_streak += 1
                message = (
                    f"REVERSED [{response.value}] — {action.description}. "
                    f"score {before_score:.4g} → trial worse/unphysical/product; restored."
                )
            else:
                response = classify_response(
                    before, after, before_score, after_score, True, self.limits, self.targets
                )
                if flat_product and not _imp:
                    self._flat_product_streak += 1
                    if family:
                        self._family_flat_counts[family] = self._family_flat_counts.get(family, 0) + 1
                        if self._family_flat_counts[family] >= self.limits.max_flat_trials_before_f:
                            self._skipped_families.add(family)
                else:
                    self._flat_product_streak = 0
                message = (
                    f"KEPT [{response.value}] — {action.description}. "
                    f"score {before_score:.4g} → {after_score:.4g}."
                )

            footnote = trial_cdu_footnote(action)
            if footnote:
                message = f"{message}\n  {footnote}"

            after_board = format_pe_board(
                after,
                diagnose(
                    after,
                    self.limits,
                    self.targets,
                    infeasible_evidence=self._infeasible_evidence(),
                    exhausted_families=self._skipped_families,
                ),
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
        """Run the controlled trial loop until State E, State F, blocked, or iteration limit."""
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
            if diagnosis.engineering_state == EngineeringState.F_INFEASIBLE or (
                diagnosis.recommended_strategy in {"fix_dof", "report_infeasible"}
            ):
                results.append(
                    TrialResult(
                        action=TrialAction(
                            "stop",
                            diagnosis.recommended_strategy,
                            payload={"strategy_id": "report_state_f"},
                        ),
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
                    self._flat_product_streak = max(
                        self._flat_product_streak, self.limits.max_flat_trials_before_f
                    )
                    results.append(
                        TrialResult(
                            action=TrialAction(
                                "stop",
                                "No progress",
                                payload={"strategy_id": "report_state_f"},
                            ),
                            before_score=trial.after_score,
                            after_score=trial.after_score,
                            kept=False,
                            message=(
                                "Stopped: three consecutive reversed trials "
                                "(State F evidence — not relaxing FINAL_TARGET). "
                                f"Skipped families={sorted(self._skipped_families)}"
                            ),
                            after_state=trial.after_state,
                            response_class=ResponseClass.STOP_INFEASIBLE,
                        )
                    )
                    break
        return results

    def set_optimize_objective(self, objective: str) -> None:
        from column_optimize import SimpleObjective

        self.optimize_objective = SimpleObjective(str(objective))
        self._optimize_flat_streak = 0

    def optimize_board(self, column_name: str) -> str:
        from column_optimize import format_optimize_board

        state = self.inspect(column_name)
        return format_optimize_board(
            state, self.optimize_objective, self.targets, self.limits
        )

    def run_one_optimize_trial(
        self, column_name: str, dry_run: bool = False
    ) -> TrialResult:
        """One simple optimize step; stages need structural approval."""
        from column_optimize import (
            format_optimize_step_report,
            objective_value,
            propose_optimize_action,
            should_keep_optimize,
        )

        before = self.inspect(column_name)
        action = propose_optimize_action(
            before, self.optimize_objective, self.limits, self.targets
        )
        v0 = objective_value(before, self.optimize_objective)
        before_score = float(v0) if v0 is not None else score_state(before)

        if action.kind in {"stop", "manual_dof", "structural_approval"}:
            report = format_optimize_step_report(
                objective=self.optimize_objective,
                before=before,
                after=None,
                action=action,
                targets=self.targets,
                limits=self.limits,
                kept=None,
                reason=action.description,
            )
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=before_score,
                kept=False,
                message=report,
                after_state=before,
                response_class=ResponseClass.STOP_INFEASIBLE,
                pe_board=report,
            )
            self.history.append(result)
            return result

        if dry_run:
            report = format_optimize_step_report(
                objective=self.optimize_objective,
                before=before,
                after=None,
                action=action,
                targets=self.targets,
                limits=self.limits,
                kept=None,
                reason="dry run",
                dry_run=True,
            )
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=before_score,
                kept=False,
                message=report,
                after_state=before,
                response_class=None,
                pe_board=report,
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
            else:
                raise ValueError(f"Unsupported optimize action kind: {action.kind}")

            self.columns.run_column(column_name)
            after = self.inspect(column_name)
            v1 = objective_value(after, self.optimize_objective)
            after_score = float(v1) if v1 is not None else score_state(after)
            keep, reason = should_keep_optimize(
                before, after, self.optimize_objective, self.targets, self.limits
            )

            if not keep:
                self.columns.restore(snap)
                self.columns.run_column(column_name)
                after = self.inspect(column_name)
                v1 = objective_value(after, self.optimize_objective)
                after_score = float(v1) if v1 is not None else before_score
                self._optimize_flat_streak += 1
                response = ResponseClass.CONVERGED_NO_MATERIAL_CHANGE
            else:
                self._optimize_flat_streak = 0
                response = ResponseClass.CONVERGED_IMPROVED

            report = format_optimize_step_report(
                objective=self.optimize_objective,
                before=before,
                after=after,
                action=action,
                targets=self.targets,
                limits=self.limits,
                kept=keep,
                reason=reason,
            )
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=after_score,
                kept=keep,
                message=report,
                after_state=after,
                response_class=response,
                pe_board=report,
            )
            self.history.append(result)
            return result
        except Exception as exc:
            try:
                self.columns.restore(snap)
                self.columns.run_column(column_name)
            except Exception:
                pass
            report = format_optimize_step_report(
                objective=self.optimize_objective,
                before=before,
                after=None,
                action=action,
                targets=self.targets,
                limits=self.limits,
                kept=False,
                reason=f"FAILED and restored: {exc}",
            )
            result = TrialResult(
                action=action,
                before_score=before_score,
                after_score=before_score,
                kept=False,
                message=report,
                after_state=self.inspect(column_name),
                response_class=ResponseClass.UNCONVERGED_RECOVERABLE,
                pe_board=report,
            )
            self.history.append(result)
            return result

    def assist_optimize(
        self,
        column_name: str,
        max_iterations: int | None = None,
        dry_run: bool = False,
    ) -> list[TrialResult]:
        """Few optimize steps until blocked, flat twice, or structural hold."""
        results: list[TrialResult] = []
        limit = max_iterations or min(6, self.limits.max_iterations)
        for _ in range(limit):
            trial = self.run_one_optimize_trial(column_name, dry_run=dry_run)
            results.append(trial)
            if dry_run:
                break
            if trial.action.kind in {"stop", "manual_dof", "structural_approval", "none"}:
                break
            if not trial.kept and self._optimize_flat_streak >= 2:
                results.append(
                    TrialResult(
                        action=TrialAction(
                            "stop",
                            "Optimize stop — objective flat (product still protected).",
                            payload={
                                "strategy_id": "optimize_done",
                                "objective": self.optimize_objective.value,
                            },
                        ),
                        before_score=trial.after_score,
                        after_score=trial.after_score,
                        kept=False,
                        message="Stopped simple optimize: flat objective twice.",
                        after_state=trial.after_state,
                        response_class=ResponseClass.CONVERGED_NO_MATERIAL_CHANGE,
                    )
                )
                break
        return results

