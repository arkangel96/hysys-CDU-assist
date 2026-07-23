"""PreFlash + Crude Heater intelligence (PFH) — observe + PE board propose-only.

Complementary to CDU Assist v1. Does NOT auto-write heater GoalValues.
Playbook: new_intelligence/CDU_PreFlash_Crude_Heater_Intelligence_v0.1.md
Inventory: CDU-PFH-T100 (DOCS + PARTIAL board).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cdu_case_config import (
    CduCaseConfig,
    UpstreamObjectsConfig,
    load_case_config,
)
from column_api import is_sentinel
from column_models import ColumnState, EngineeringState
from hysys_units import _get_value


@dataclass(slots=True)
class PreFlashSnapshot:
    name: str
    temperature: float | None = None
    temperature_unit: str = ""
    pressure: float | None = None
    pressure_unit: str = ""
    vapour_fraction: float | None = None
    vapour_flow: float | None = None
    liquid_flow: float | None = None
    flow_unit: str = ""
    ok: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class HeaterSnapshot:
    name: str
    duty: float | None = None
    duty_unit: str = ""
    duty_energy_stream: str = ""
    cot: float | None = None
    cot_unit: str = ""
    ok: bool = True
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class OverflashSnapshot:
    definition: str
    value_pct_feed: float | None = None
    band_min: float | None = None
    band_max: float | None = None
    band_configured: bool = False
    status: str = "unavailable"  # unavailable | unknown | in_band | above | below
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PfhRecommendation:
    rule_id: str
    action: str
    reason: str


@dataclass(slots=True)
class PfhDiagnosis:
    preflash: PreFlashSnapshot
    heater: HeaterSnapshot
    overflash: OverflashSnapshot
    primary_mv: str
    secondary_mv: str
    recommendations: list[PfhRecommendation] = field(default_factory=list)
    stop_optimization: bool = False
    propose_only_notice: str = (
        "Await PE approval — Assist will not auto-execute heater changes in v0.1."
    )


def _display_units(hysys: Any) -> tuple[str, str, str, str]:
    try:
        du = hysys.display_units
        return (
            str(getattr(du, "temperature", "F")),
            str(getattr(du, "pressure", "psia")),
            str(getattr(du, "molar_flow", "lbmole/hr")),
            str(getattr(du, "energy", "Btu/hr")),
        )
    except Exception:
        return "F", "psia", "lbmole/hr", "Btu/hr"


def _prop_display(obj: Any, prop_names: tuple[str, ...], unit: str | None) -> float | None:
    for pname in prop_names:
        try:
            prop = getattr(obj, pname, None)
        except Exception:
            prop = None
        if prop is None:
            continue
        if unit:
            got = _get_value(prop, unit)
            if got is not None and not is_sentinel(got):
                return float(got)
        for attr in ("Value", "GetValue"):
            try:
                if attr == "GetValue":
                    raw = prop.GetValue()
                else:
                    raw = getattr(prop, attr)
                if raw is not None and not is_sentinel(raw):
                    return float(raw)
            except Exception:
                continue
    return None


def _op_item(fs: Any, name: str) -> Any | None:
    try:
        return fs.Operations.Item(name)
    except Exception:
        return None


def _energy_item(fs: Any, name: str) -> Any | None:
    try:
        return fs.EnergyStreams.Item(name)
    except Exception:
        return None


def _material_item(fs: Any, name: str) -> Any | None:
    try:
        return fs.MaterialStreams.Item(name)
    except Exception:
        return None


def _hysys_from_columns(columns: Any) -> Any | None:
    if columns is None:
        return None
    hysys = getattr(columns, "hysys", None)
    if hysys is None:
        return None
    if hasattr(hysys, "connected") and not hysys.connected:
        return None
    return hysys


def read_preflash(hysys: Any, name: str) -> PreFlashSnapshot:
    t_u, p_u, f_u, _ = _display_units(hysys)
    snap = PreFlashSnapshot(name=name, temperature_unit=t_u, pressure_unit=p_u, flow_unit=f_u)
    op = _op_item(hysys.flowsheet, name)
    if op is None:
        snap.ok = False
        snap.notes.append(f"PreFlash op '{name}' not found")
        return snap
    snap.temperature = _prop_display(op, ("Temperature", "VesselTemperature"), t_u)
    snap.pressure = _prop_display(op, ("Pressure", "VesselPressure"), p_u)
    snap.vapour_fraction = _prop_display(
        op, ("VapourFraction", "VaporFraction", "VF"), None
    )
    # Vessel may expose product streams; best-effort from attached feeds/products
    for coll_attr, flow_attr in (
        ("VapourProduct", "vapour_flow"),
        ("VaporProduct", "vapour_flow"),
        ("LiquidProduct", "liquid_flow"),
    ):
        try:
            stream = getattr(op, coll_attr, None)
            if stream is None:
                continue
            flow = _prop_display(
                stream, ("MolarFlow", "MassFlow", "StdIdealLiqVolFlow"), f_u
            )
            setattr(snap, flow_attr, flow)
        except Exception:
            continue
    if snap.temperature is None and snap.pressure is None and snap.vapour_fraction is None:
        snap.ok = False
        snap.notes.append("PreFlash properties unreadable")
    if snap.vapour_fraction is not None and (
        snap.vapour_fraction < -0.01 or snap.vapour_fraction > 1.01
    ):
        snap.ok = False
        snap.notes.append(f"Invalid vapour fraction {snap.vapour_fraction}")
    if snap.pressure is not None and snap.pressure <= 0:
        snap.ok = False
        snap.notes.append(f"Invalid PreFlash pressure {snap.pressure}")
    return snap


def read_heater(hysys: Any, heater_name: str, duty_energy: str) -> HeaterSnapshot:
    t_u, _, _, e_u = _display_units(hysys)
    snap = HeaterSnapshot(
        name=heater_name,
        duty_unit=e_u,
        cot_unit=t_u,
        duty_energy_stream=duty_energy,
    )
    op = _op_item(hysys.flowsheet, heater_name)
    if op is None:
        snap.ok = False
        snap.notes.append(f"Heater op '{heater_name}' not found")
        return snap
    # Prefer energy stream Crude Duty (display), fallback heater Duty
    energy = _energy_item(hysys.flowsheet, duty_energy)
    if energy is not None:
        snap.duty = _prop_display(energy, ("HeatFlow", "Energy"), e_u)
        if snap.duty is None:
            try:
                raw = getattr(energy, "HeatFlowValue", None)
                if raw is not None and not is_sentinel(raw):
                    snap.duty = float(raw)
                    snap.notes.append("duty from HeatFlowValue (COM); display GetValue failed")
            except Exception:
                pass
    if snap.duty is None:
        snap.duty = _prop_display(op, ("Duty", "HeatFlow", "Energy"), e_u)
    # COT — outlet stream temperature
    for attr in ("Product", "Outlet", "To", "ProductStream"):
        try:
            outlet = getattr(op, attr, None)
            if outlet is None:
                continue
            if hasattr(outlet, "Count"):
                try:
                    outlet = outlet.Item(0) if outlet.Count else None
                except Exception:
                    try:
                        outlet = outlet.Item(1)
                    except Exception:
                        outlet = None
            if outlet is None:
                continue
            snap.cot = _prop_display(outlet, ("Temperature",), t_u)
            if snap.cot is not None:
                break
        except Exception:
            continue
    if snap.duty is None and snap.cot is None:
        snap.ok = False
        snap.notes.append("Heater duty and COT unreadable")
    return snap


def read_overflash(hysys: Any, upstream: UpstreamObjectsConfig) -> OverflashSnapshot:
    of = upstream.overflash
    snap = OverflashSnapshot(
        definition=of.definition,
        band_min=of.band_min,
        band_max=of.band_max,
        band_configured=of.band_min is not None and of.band_max is not None,
    )
    snap.notes.append(of.notes or "definition: liquid below flash as % fresh crude feed")
    if not of.liquid_flow_stream or not of.feed_flow_stream:
        snap.status = "unavailable"
        snap.notes.append(
            "overflash % unavailable — set liquid_flow_stream and feed_flow_stream in config"
        )
        return snap
    _, _, f_u, _ = _display_units(hysys)
    liq = _material_item(hysys.flowsheet, of.liquid_flow_stream)
    feed = _material_item(hysys.flowsheet, of.feed_flow_stream)
    if liq is None or feed is None:
        snap.status = "unavailable"
        snap.notes.append("configured overflash streams not found on flowsheet")
        return snap
    # Prefer mass or std liq vol — same basis for both
    liq_f = _prop_display(liq, ("MassFlow", "StdIdealLiqVolFlow", "MolarFlow"), None)
    feed_f = _prop_display(feed, ("MassFlow", "StdIdealLiqVolFlow", "MolarFlow"), None)
    # Retry with display unit if needed
    if liq_f is None:
        liq_f = _prop_display(liq, ("MassFlow", "StdIdealLiqVolFlow", "MolarFlow"), f_u)
    if feed_f is None:
        feed_f = _prop_display(feed, ("MassFlow", "StdIdealLiqVolFlow", "MolarFlow"), f_u)
    if liq_f is None or feed_f is None or abs(feed_f) < 1e-12:
        snap.status = "unavailable"
        snap.notes.append("could not compute overflash % from configured streams")
        return snap
    pct = 100.0 * abs(liq_f) / abs(feed_f)
    snap.value_pct_feed = pct
    if not snap.band_configured:
        snap.status = "unknown"
        snap.notes.append("band_min/band_max unset — no in/out-of-band claim")
        return snap
    assert of.band_min is not None and of.band_max is not None
    if pct > of.band_max:
        snap.status = "above"
    elif pct < of.band_min:
        snap.status = "below"
    else:
        snap.status = "in_band"
    return snap


def diagnose_pfh(
    preflash: PreFlashSnapshot,
    heater: HeaterSnapshot,
    overflash: OverflashSnapshot,
    state: ColumnState | None,
    upstream: UpstreamObjectsConfig,
) -> PfhDiagnosis:
    diag = PfhDiagnosis(
        preflash=preflash,
        heater=heater,
        overflash=overflash,
        primary_mv=upstream.primary_mv,
        secondary_mv=upstream.secondary_mv,
    )
    # PFH-003 — stop on abnormal PreFlash
    if not preflash.ok:
        diag.stop_optimization = True
        diag.recommendations.append(
            PfhRecommendation(
                rule_id="PFH-003",
                action="Stop heater optimization; require engineer intervention",
                reason="; ".join(preflash.notes) or "PreFlash abnormal",
            )
        )
        return diag

    tower_ok = True
    if state is not None:
        if state.degrees_of_freedom not in (0, None):
            tower_ok = False
        if not state.appears_converged or not state.physical_solution:
            tower_ok = False

    mv_label = "Crude Heater Duty" if upstream.primary_mv == "heater_duty" else "COT"
    if overflash.status == "above" and tower_ok:
        diag.recommendations.append(
            PfhRecommendation(
                rule_id="PFH-001",
                action=f"Propose: reduce {mv_label} by one bounded step (PE approval required)",
                reason="Overflash above configured band; quality/recovery assumed held until trial",
            )
        )
    elif overflash.status == "below" and tower_ok:
        diag.recommendations.append(
            PfhRecommendation(
                rule_id="PFH-002",
                action=f"Propose: increase {mv_label} by one bounded step (PE approval required)",
                reason="Overflash below configured band or recovery concern; heater within observe limits",
            )
        )
    elif overflash.status in {"unavailable", "unknown"} and tower_ok and heater.ok:
        diag.recommendations.append(
            PfhRecommendation(
                rule_id="PFH-observe",
                action=(
                    f"Propose direction only: prefer lowering {mv_label} for energy "
                    "if overflash/recovery still acceptable after PE review"
                ),
                reason=(
                    "Overflash band not configured or % unavailable — "
                    "no in/out-of-band verdict (v0.1)"
                ),
            )
        )
    elif not tower_ok:
        diag.recommendations.append(
            PfhRecommendation(
                rule_id="PFH-gate",
                action="Do not change heater until CDU converged / DOF=0 / physical",
                reason="Tower hard gate not satisfied",
            )
        )

    diag.recommendations.append(
        PfhRecommendation(
            rule_id="PFH-004",
            action=(
                "Accept heater change only if: converged, duty improved, "
                "overflash in band (when set), N+K recovery + hard Q held; else restore"
            ),
            reason="Keep/restore gate for any future approved trial (v0.2 study runner)",
        )
    )
    return diag


def build_pfh_diagnosis(
    columns: Any | None,
    state: ColumnState | None = None,
    case: CduCaseConfig | None = None,
) -> PfhDiagnosis | None:
    hysys = _hysys_from_columns(columns)
    if hysys is None:
        return None
    case = case or load_case_config()
    up = case.upstream_objects
    preflash = read_preflash(hysys, up.preflash)
    heater = read_heater(hysys, up.crude_heater, up.crude_duty_energy)
    overflash = read_overflash(hysys, up)
    return diagnose_pfh(preflash, heater, overflash, state, up)


def _fmt(v: float | None, digits: int = 4) -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}g}"


def format_pfh_board_section(
    columns: Any | None = None,
    state: ColumnState | None = None,
    case: CduCaseConfig | None = None,
) -> str:
    """PE board block — propose only; never executes heater changes."""
    lines = [
        "PREFLASH + CRUDE HEATER [PFH v0.1 — PROPOSE ONLY]",
        "  Await PE approval — Assist will not auto-execute heater changes in v0.1.",
    ]
    diag = build_pfh_diagnosis(columns, state=state, case=case)
    if diag is None:
        lines.append("  (upstream read unavailable — connect HYSYS / pass columns)")
        return "\n".join(lines)

    pf = diag.preflash
    ht = diag.heater
    of = diag.overflash
    lines.append(
        f"  PreFlash '{pf.name}': T={_fmt(pf.temperature)} {pf.temperature_unit} | "
        f"P={_fmt(pf.pressure)} {pf.pressure_unit} | VF={_fmt(pf.vapour_fraction)} | "
        f"ok={pf.ok}"
    )
    if pf.notes:
        for n in pf.notes:
            lines.append(f"    note: {n}")
    lines.append(
        f"  Heater '{ht.name}': duty={_fmt(ht.duty)} {ht.duty_unit} "
        f"(stream={ht.duty_energy_stream or '—'}) | "
        f"COT={_fmt(ht.cot)} {ht.cot_unit} | ok={ht.ok}"
    )
    if ht.notes:
        for n in ht.notes:
            lines.append(f"    note: {n}")
    band = (
        f"{_fmt(of.band_min)}..{_fmt(of.band_max)}"
        if of.band_configured
        else "unset (no in/out-of-band claim)"
    )
    lines.append(
        f"  Overflash: def={of.definition} | value%={_fmt(of.value_pct_feed)} | "
        f"band={band} | status={of.status}"
    )
    for n in of.notes:
        lines.append(f"    note: {n}")
    lines.append(f"  Primary MV={diag.primary_mv} | Secondary MV={diag.secondary_mv}")
    if state is not None:
        eng = getattr(state, "engineering_state", None)
        # state may not carry eng; board uses tower flags
        lines.append(
            f"  Tower gates: DOF={state.degrees_of_freedom} "
            f"physical={state.physical_solution} converged={state.appears_converged}"
        )
        if isinstance(eng, EngineeringState):
            lines.append(f"  Tower state: {eng.value}")
    if diag.stop_optimization:
        lines.append("  STOP: PreFlash abnormal — heater optimize blocked (PFH-003).")
    lines.append("  Recommendations:")
    for rec in diag.recommendations:
        lines.append(f"    [{rec.rule_id}] {rec.action}")
        lines.append(f"      why: {rec.reason}")
    return "\n".join(lines)
