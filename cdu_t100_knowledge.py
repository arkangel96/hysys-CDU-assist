"""T-100 UI / PE knowledge → expert routing (L2–L4).

Source: docs/expert/T100_HYSYS_UI_Click_Map.md + config/cdu_t100_case.json
"""
from __future__ import annotations

from dataclasses import dataclass, field

from cdu_case_config import CduCaseConfig, load_case_config
from column_models import ColumnSpecState, ColumnState, ConvergenceLimits


@dataclass(frozen=True, slots=True)
class SpecKnowledge:
    """One HYSYS spec row on T-100 with engineering metadata."""

    name: str
    subsystem: str
    strategy_id: str
    product: str = ""
    pa_index: int | None = None
    is_rate: bool = False
    is_duty: bool = False
    monitor_only: bool = False


# PE-confirmed T-100 spec map (Design → Specs / Specs Summary / Monitor)
T100_SPEC_KNOWLEDGE: tuple[SpecKnowledge, ...] = (
    SpecKnowledge("Kero_SS Prod Flow", "kerosene_section", "side_draw_rate_nudge", "Kerosene"),
    SpecKnowledge("Diesel_SS Prod Flow", "diesel_section", "side_draw_rate_nudge", "Diesel"),
    SpecKnowledge("AGO_SS Prod Flow", "ago_section", "side_draw_rate_nudge", "AGO"),
    SpecKnowledge("PA_1_Rate(Pa)", "pumparound", "pa_duty_nudge", pa_index=1, is_rate=True),
    SpecKnowledge("PA_1_Duty(Pa)", "pumparound", "pa_duty_nudge", pa_index=1, is_duty=True),
    SpecKnowledge("PA_2_Rate(Pa)", "pumparound", "pa_duty_nudge", pa_index=2, is_rate=True),
    SpecKnowledge("PA_2_Duty(Pa)", "pumparound", "pa_duty_nudge", pa_index=2, is_duty=True),
    SpecKnowledge("PA_3_Rate(Pa)", "pumparound", "pa_duty_nudge", pa_index=3, is_rate=True),
    SpecKnowledge("PA_3_Duty(Pa)", "pumparound", "pa_duty_nudge", pa_index=3, is_duty=True),
    SpecKnowledge("Naphtha Prod Rate", "overhead", "reflux_or_oh_nudge", "Naphtha"),
    SpecKnowledge("Liquid Flow", "overhead", "reflux_or_oh_nudge"),
    SpecKnowledge("Kero Reb Duty", "side_stripper", "side_strip_steam_nudge", "Kerosene"),
    SpecKnowledge("Vap Prod Flow", "overhead", "reflux_or_oh_nudge"),
    SpecKnowledge("Reflux Ratio", "overhead", "reflux_or_oh_nudge", monitor_only=True),
)

_SYMPTOM_SUBSYSTEM: dict[str, str] = {
    "diesel_too_heavy": "diesel_section",
    "diesel_too_light": "diesel_section",
    "kerosene_off_spec": "kerosene_section",
    "naphtha_too_heavy": "overhead",
    "residue_too_light": "bottom_section",
    "yield_off": "bottom_section",
}

# When PA rate+duty both active, prefer duty knob (PE Specs Summary pattern on T-100)
_PREFER_DUTY_OVER_RATE = True


def knowledge_for_spec(spec_name: str) -> SpecKnowledge | None:
    for row in T100_SPEC_KNOWLEDGE:
        if row.name.lower() == spec_name.lower():
            return row
    lower = spec_name.lower()
    for row in T100_SPEC_KNOWLEDGE:
        key = row.name.lower().replace("(pa)", "").replace(" ", "")
        probe = lower.replace("(pa)", "").replace(" ", "")
        if key in probe or probe in key:
            return row
    return None


def subsystem_for_spec(spec_name: str, case: CduCaseConfig | None = None) -> str:
    kn = knowledge_for_spec(spec_name)
    if kn:
        return kn.subsystem
    lower = spec_name.lower()
    if "diesel" in lower:
        return "diesel_section"
    if "kero" in lower:
        return "kerosene_section"
    if "ago" in lower:
        return "ago_section"
    if "pa_" in lower or "(pa)" in lower:
        return "pumparound"
    if any(t in lower for t in ("naphtha", "liquid", "vap", "reflux")):
        return "overhead"
    if case:
        entry = case.spec_role_for(spec_name)
        if entry and entry.subsystem:
            return entry.subsystem
    return "main_fractionator"


def dominant_subsystem(state: ColumnState) -> str:
    """L2 — infer subsystem from largest active spec residual."""
    active = [s for s in state.active_specs() if s.score_error() > 0]
    if not active:
        active = list(state.active_specs())
    if not active:
        return "main_fractionator"
    top = max(active, key=lambda s: s.score_error())
    return subsystem_for_spec(top.name)


def _pa_duty_active(state: ColumnState, pa_index: int) -> bool:
    for spec in state.active_specs():
        kn = knowledge_for_spec(spec.name)
        if kn and kn.pa_index == pa_index and kn.is_duty:
            return True
    return False


def _spec_by_name(state: ColumnState, name: str) -> ColumnSpecState | None:
    for spec in state.specs:
        if spec.name.lower() == name.lower():
            return spec
    return None


def _direction_from_spec(spec: ColumnSpecState) -> float:
    err = spec.error
    if err is not None and abs(float(err)) >= 1e-12:
        return -1.0 if float(err) > 0 else 1.0
    cur, goal = spec.current_value, spec.goal_value
    if cur is not None and goal is not None and abs(float(goal)) > 1e-12:
        return 1.0 if float(cur) < float(goal) else -1.0
    return 1.0


def specs_for_strategy(
    state: ColumnState,
    strategy_id: str,
    *,
    subsystem: str = "",
    product_hint: str = "",
) -> list[ColumnSpecState]:
    """Active specs matching strategy + optional subsystem/product filter."""
    out: list[ColumnSpecState] = []
    product_l = product_hint.lower()
    for spec in state.active_specs():
        kn = knowledge_for_spec(spec.name)
        if not kn or kn.monitor_only:
            continue
        if kn.strategy_id != strategy_id and not (
            strategy_id == "side_draw_rate_nudge" and "prod flow" in spec.name.lower()
        ):
            continue
        if subsystem and kn.subsystem != subsystem:
            continue
        if product_l and kn.product.lower() != product_l and product_l not in spec.name.lower():
            continue
        if spec.goal_value is None:
            continue
        if _PREFER_DUTY_OVER_RATE and kn.is_rate and kn.pa_index and _pa_duty_active(
            state, kn.pa_index
        ):
            continue
        out.append(spec)
    return out


def validate_t100_specs_summary(state: ColumnState, case: CduCaseConfig | None = None) -> list[str]:
    """Checks from PE Specs Summary screen (Active/Current matrix)."""
    issues: list[str] = []
    case = case or load_case_config()
    rr = _spec_by_name(state, "Reflux Ratio")
    if rr is not None:
        role = case.spec_role_for(rr.name)
        if role and role.role == "monitor_only" and rr.is_active:
            issues.append(
                "Reflux Ratio must be Active OFF (monitor/estimate only) per T-100 spec philosophy"
            )
    active_count = len(state.active_specs())
    if state.degrees_of_freedom == 0 and active_count > 0:
        if rr and not rr.is_active:
            issues.append(
                f"Specs Summary OK pattern: {active_count} Active specs, Reflux off Active, DOF=0"
            )
    return issues


def infer_symptom_key(state: ColumnState, subsystem: str) -> str:
    """Guess routing key from subsystem when quality reads unavailable."""
    for key, sub in _SYMPTOM_SUBSYSTEM.items():
        if sub == subsystem:
            return key
    if subsystem == "pumparound":
        return "diesel_too_heavy"
    return "off_spec_or_high_residual"


@dataclass(slots=True)
class RoutedHypothesisSeed:
    rule_id: str
    subsystem: str
    symptom: str
    mechanism: str
    strategy_id: str
    spec_name: str
    direction: float
    confidence: float
    mv_family: str
    evidence: list[str] = field(default_factory=list)


def build_subsystem_routed_seeds(
    state: ColumnState,
    case: CduCaseConfig,
    limits: ConvergenceLimits,
    *,
    symptom_key: str | None = None,
    target_miss: bool = False,
) -> list[RoutedHypothesisSeed]:
    """
    L2→L4 routing: subsystem → MV preference → spec handle.
    Used when quality symptoms are not configured yet.
    """
    subsystem = dominant_subsystem(state)
    symptom_key = symptom_key or infer_symptom_key(state, subsystem)
    order = case.mv_preference.get(symptom_key, [])
    if not order:
        order = [
            "side_draw_rate_nudge",
            "pa_duty_nudge",
            "side_strip_steam_nudge",
            "reflux_or_oh_nudge",
        ]

    product_hint = ""
    if "diesel" in symptom_key:
        product_hint = "diesel"
    elif "kero" in symptom_key:
        product_hint = "kero"

    draw_subsystem = _SYMPTOM_SUBSYSTEM.get(symptom_key, subsystem)

    seeds: list[RoutedHypothesisSeed] = []
    for rank, strategy_id in enumerate(order):
        if strategy_id == "side_draw_rate_nudge":
            sub_filter = draw_subsystem
            ph = product_hint
        elif strategy_id == "side_strip_steam_nudge":
            sub_filter = draw_subsystem
            ph = product_hint
        elif strategy_id == "pa_duty_nudge":
            sub_filter = ""
            ph = ""
        elif strategy_id == "reflux_or_oh_nudge":
            sub_filter = "overhead"
            ph = ""
        else:
            sub_filter = subsystem
            ph = product_hint

        specs = specs_for_strategy(
            state,
            strategy_id,
            subsystem=sub_filter,
            product_hint=ph,
        )
        if strategy_id == "pa_duty_nudge" and draw_subsystem in {
            "diesel_section",
            "kerosene_section",
            "ago_section",
        }:
            # Prefer PA_2/PA_3 for middle cuts; PA_1 for overhead-heavy issues
            specs.sort(
                key=lambda s: (
                    0
                    if knowledge_for_spec(s.name)
                    and knowledge_for_spec(s.name).pa_index in (2, 3)
                    else 1
                )
            )
        for spec in specs[:1]:
            kn = knowledge_for_spec(spec.name)
            direction = _direction_from_spec(spec)
            if symptom_key == "diesel_too_heavy" and strategy_id == "side_draw_rate_nudge":
                direction = -1.0
            err_boost = min(spec.score_error() * 500, 0.25)
            conf = 0.72 - rank * 0.07 + err_boost
            if target_miss:
                conf += 0.03
            mv = (kn.subsystem if kn else subsystem).replace("_", " ").title()
            seeds.append(
                RoutedHypothesisSeed(
                    rule_id=f"RT-{symptom_key}-{strategy_id}-{spec.name[:12]}",
                    subsystem=kn.subsystem if kn else subsystem,
                    symptom=symptom_key,
                    mechanism=(
                        f"L2 subsystem={subsystem} → preferred MV #{rank + 1} "
                        f"({strategy_id}) on '{spec.name}'"
                    ),
                    strategy_id=strategy_id,
                    spec_name=spec.name,
                    direction=direction,
                    confidence=conf,
                    mv_family=mv,
                    evidence=[
                        f"dominant_subsystem={subsystem}",
                        f"spec_err={spec.error}",
                        f"routing={symptom_key}",
                    ],
                )
            )
            break

    if not seeds:
        top = max(state.active_specs(), key=lambda s: s.score_error(), default=None)
        if top and top.score_error() > limits.max_active_spec_error:
            kn = knowledge_for_spec(top.name)
            seeds.append(
                RoutedHypothesisSeed(
                    rule_id=f"RT-fallback-{top.name[:12]}",
                    subsystem=kn.subsystem if kn else subsystem,
                    symptom=symptom_key,
                    mechanism=f"Fallback: largest residual on '{top.name}'",
                    strategy_id=kn.strategy_id if kn else "side_draw_rate_nudge",
                    spec_name=top.name,
                    direction=_direction_from_spec(top),
                    confidence=0.55,
                    mv_family=subsystem,
                    evidence=[f"spec={top.name} err={top.error}"],
                )
            )
    return seeds[:6]


def format_subsystem_board(state: ColumnState, case: CduCaseConfig | None = None) -> str:
    case = case or load_case_config()
    sub = dominant_subsystem(state)
    lines = [
        "T-100 SUBSYSTEM ROUTING (L2)",
        f"  dominant_subsystem={sub}",
        f"  inferred_symptom={infer_symptom_key(state, sub)}",
    ]
    for issue in validate_t100_specs_summary(state, case):
        if "OK pattern" in issue:
            lines.append(f"  • {issue}")
        else:
            lines.append(f"  ⚠ {issue}")
    active = sorted(state.active_specs(), key=lambda s: s.score_error(), reverse=True)[:4]
    if active:
        lines.append("  top_active_residuals:")
        for spec in active:
            kn = knowledge_for_spec(spec.name)
            sub_name = kn.subsystem if kn else "?"
            lines.append(f"    {spec.name} err={spec.error} → {sub_name}")
    return "\n".join(lines)
