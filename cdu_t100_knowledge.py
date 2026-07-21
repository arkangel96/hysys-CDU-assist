"""T-100 UI / PE knowledge → expert routing (L2–L4).

Source: docs/expert/T100_HYSYS_UI_Click_Map.md + config/cdu_t100_case.json
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from cdu_case_config import CduCaseConfig, load_case_config
from column_models import ColumnSpecState, ColumnState, ConvergenceLimits

ROOT = Path(__file__).resolve().parent
SIDE_OPS_PATH = ROOT / "config" / "cdu_t100_side_ops.json"


@dataclass(frozen=True, slots=True)
class SideStripperKnowledge:
    name: str
    stages: int
    liq_draw_stage: str
    vap_return_stage: str
    product_stream: str
    prod_flow_spec: str
    subsystem: str
    reb_duty_spec: str = ""
    steam_feed: str = ""


@dataclass(frozen=True, slots=True)
class PumpAroundKnowledge:
    name: str
    draw_stage: str
    return_stage: str
    rate_spec: str
    duty_spec: str
    subsystem: str
    pa_index: int
    duty_btuh: float | None = None
    draw_temp_f: float | None = None
    serves: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SideDrawKnowledge:
    stream: str
    draw_stage: str
    stream_type: str
    subsystem: str
    rate_spec: str = ""


@dataclass(slots=True)
class SideOpsKnowledge:
    side_strippers: tuple[SideStripperKnowledge, ...] = ()
    pump_arounds: tuple[PumpAroundKnowledge, ...] = ()
    side_draws: tuple[SideDrawKnowledge, ...] = ()


def _load_side_ops_json() -> SideOpsKnowledge:
    if not SIDE_OPS_PATH.is_file():
        return default_side_ops_knowledge()
    data = json.loads(SIDE_OPS_PATH.read_text(encoding="utf-8"))
    strippers = tuple(
        SideStripperKnowledge(
            name=str(s["name"]),
            stages=int(s.get("stages", 3)),
            liq_draw_stage=str(s["liq_draw_stage"]),
            vap_return_stage=str(s["vap_return_stage"]),
            product_stream=str(s.get("product_stream", "")),
            prod_flow_spec=str(s.get("prod_flow_spec", "")),
            subsystem=str(s.get("subsystem", "")),
            reb_duty_spec=str(s.get("reb_duty_spec", "")),
            steam_feed=str(s.get("steam_feed", "")),
        )
        for s in data.get("side_strippers", [])
    )
    pas = tuple(
        PumpAroundKnowledge(
            name=str(p["name"]),
            draw_stage=str(p["draw_stage"]),
            return_stage=str(p["return_stage"]),
            rate_spec=str(p["rate_spec"]),
            duty_spec=str(p["duty_spec"]),
            subsystem=str(p.get("subsystem", "")),
            pa_index=int(p["name"].replace("PA_", "")),
            duty_btuh=p.get("duty_btuh"),
            draw_temp_f=p.get("draw_temp_f"),
            serves=tuple(p.get("serves", [])),
        )
        for p in data.get("pump_arounds", [])
    )
    draws = tuple(
        SideDrawKnowledge(
            stream=str(d["stream"]),
            draw_stage=str(d["draw_stage"]),
            stream_type=str(d.get("type", "L")),
            subsystem=str(d.get("subsystem", "")),
            rate_spec=str(d.get("rate_spec", "")),
        )
        for d in data.get("side_draws", [])
    )
    return SideOpsKnowledge(strippers, pas, draws)


def default_side_ops_knowledge() -> SideOpsKnowledge:
    """PE-confirmed T-100 Side Ops (fallback if JSON missing)."""
    return SideOpsKnowledge(
        side_strippers=(
            SideStripperKnowledge(
                "Kero_SS", 3, "9_Main TS", "8_Main TS", "Kerosene",
                "Kero_SS Prod Flow", "kerosene_section", "Kero Reb Duty",
            ),
            SideStripperKnowledge(
                "Diesel_SS", 3, "17_Main TS", "16_Main TS", "Diesel",
                "Diesel_SS Prod Flow", "diesel_section", steam_feed="Diesel Steam",
            ),
            SideStripperKnowledge(
                "AGO_SS", 3, "22_Main TS", "21_Main TS", "AGO",
                "AGO_SS Prod Flow", "ago_section", steam_feed="AGO Steam",
            ),
        ),
        pump_arounds=(
            PumpAroundKnowledge(
                "PA_1", "2_Main TS", "1_Main TS", "PA_1_Rate(Pa)", "PA_1_Duty(Pa)",
                "overhead", 1, draw_temp_f=262.5,
            ),
            PumpAroundKnowledge(
                "PA_2", "17_Main TS", "16_Main TS", "PA_2_Rate(Pa)", "PA_2_Duty(Pa)",
                "diesel_section", 2, draw_temp_f=450.0,
            ),
            PumpAroundKnowledge(
                "PA_3", "22_Main TS", "21_Main TS", "PA_3_Rate(Pa)", "PA_3_Duty(Pa)",
                "ago_section", 3, draw_temp_f=512.5,
            ),
        ),
        side_draws=(
            SideDrawKnowledge("Off Gas", "Condenser", "V", "overhead"),
            SideDrawKnowledge("Naphtha", "Condenser", "L", "overhead", "Naphtha Prod Rate"),
            SideDrawKnowledge("Waste Water", "Condenser", "W", "overhead"),
            SideDrawKnowledge("Residue", "29_Main TS", "L", "bottom_section"),
            SideDrawKnowledge("Kerosene", "Kero_SS_Reb", "L", "kerosene_section"),
            SideDrawKnowledge("Diesel", "3_Diesel_SS", "L", "diesel_section"),
        ),
    )


_SIDE_OPS_CACHE: SideOpsKnowledge | None = None


def load_side_ops_knowledge() -> SideOpsKnowledge:
    global _SIDE_OPS_CACHE
    if _SIDE_OPS_CACHE is None:
        _SIDE_OPS_CACHE = _load_side_ops_json()
    return _SIDE_OPS_CACHE


# Subsystem → PA index (Side Ops tray alignment)
SUBSYSTEM_PA_INDEX: dict[str, int] = {
    "overhead": 1,
    "kerosene_section": 1,
    "diesel_section": 2,
    "ago_section": 3,
    "bottom_section": 3,
}


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
    "ago_off_spec": "ago_section",
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


def stripper_for_subsystem(subsystem: str) -> SideStripperKnowledge | None:
    for ss in load_side_ops_knowledge().side_strippers:
        if ss.subsystem == subsystem:
            return ss
    return None


def pa_for_subsystem(subsystem: str) -> PumpAroundKnowledge | None:
    idx = SUBSYSTEM_PA_INDEX.get(subsystem)
    if idx is None:
        return None
    for pa in load_side_ops_knowledge().pump_arounds:
        if pa.pa_index == idx:
            return pa
    return None


def side_ops_mechanism_hint(symptom_key: str, strategy_id: str) -> str:
    """L3 mechanism text from Side Ops tray map."""
    sub = _SYMPTOM_SUBSYSTEM.get(symptom_key, "")
    ops = load_side_ops_knowledge()
    ss = stripper_for_subsystem(sub)
    pa = pa_for_subsystem(sub)
    parts: list[str] = []
    if strategy_id == "side_draw_rate_nudge" and ss:
        parts.append(
            f"Side stripper {ss.name} draw @ {ss.liq_draw_stage} → product {ss.product_stream}"
        )
    elif strategy_id == "side_strip_steam_nudge" and ss:
        steam = ss.steam_feed or ss.reb_duty_spec or "strip energy"
        parts.append(f"Side stripper {ss.name} energy via {steam}")
    elif strategy_id == "pa_duty_nudge" and pa:
        parts.append(
            f"PA_{pa.pa_index} heat removal @ {pa.draw_stage}→{pa.return_stage} "
            f"(aligned with {sub})"
        )
    elif strategy_id == "reflux_or_oh_nudge":
        parts.append("Overhead / naphtha section @ Condenser")
    return " | ".join(parts) if parts else ""


def _sort_pa_specs_for_subsystem(
    specs: list[ColumnSpecState], draw_subsystem: str
) -> list[ColumnSpecState]:
    preferred = SUBSYSTEM_PA_INDEX.get(draw_subsystem, 0)

    def key(spec: ColumnSpecState) -> tuple[int, int]:
        kn = knowledge_for_spec(spec.name)
        if not kn or not kn.pa_index:
            return (99, 99)
        return (0 if kn.pa_index == preferred else 1, kn.pa_index)

    return sorted(specs, key=key)


def infer_symptom_key(state: ColumnState, subsystem: str) -> str:
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
        if strategy_id == "pa_duty_nudge" and draw_subsystem:
            specs = _sort_pa_specs_for_subsystem(specs, draw_subsystem)
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
            mech_hint = side_ops_mechanism_hint(symptom_key, strategy_id)
            mechanism = (
                f"L2 subsystem={subsystem} → preferred MV #{rank + 1} "
                f"({strategy_id}) on '{spec.name}'"
            )
            if mech_hint:
                mechanism += f" — {mech_hint}"
            seeds.append(
                RoutedHypothesisSeed(
                    rule_id=f"RT-{symptom_key}-{strategy_id}-{spec.name[:12]}",
                    subsystem=kn.subsystem if kn else subsystem,
                    symptom=symptom_key,
                    mechanism=mechanism,
                    strategy_id=strategy_id,
                    spec_name=spec.name,
                    direction=direction,
                    confidence=conf,
                    mv_family=mv,
                    evidence=[
                        f"dominant_subsystem={subsystem}",
                        f"spec_err={spec.error}",
                        f"routing={symptom_key}",
                    ]
                    + ([mech_hint] if mech_hint else []),
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


def format_side_ops_board() -> str:
    """Side Ops tray map for PE board (from PE screenshots)."""
    ops = load_side_ops_knowledge()
    lines = [
        "T-100 SIDE OPS (L3 equipment map)",
        "  Side Strippers:",
    ]
    for ss in ops.side_strippers:
        energy = ss.reb_duty_spec or ss.steam_feed or "—"
        lines.append(
            f"    {ss.name}: draw {ss.liq_draw_stage} → return {ss.vap_return_stage} "
            f"| product {ss.product_stream} | spec {ss.prod_flow_spec} | energy {energy}"
        )
    lines.append("  Pump Arounds:")
    for pa in ops.pump_arounds:
        temp = f"{pa.draw_temp_f} F" if pa.draw_temp_f else "—"
        lines.append(
            f"    {pa.name}: {pa.draw_stage}→{pa.return_stage} "
            f"| duty spec {pa.duty_spec} | draw T {temp}"
        )
    lines.append("  Side Draws (products):")
    for sd in ops.side_draws:
        spec = sd.rate_spec or "—"
        lines.append(f"    {sd.stream} @ {sd.draw_stage} ({sd.stream_type}) spec={spec}")
    lines.append("  Side Rectifiers: none | Vap Bypasses: none")
    return "\n".join(lines)
