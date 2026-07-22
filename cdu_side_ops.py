"""
CDU Design → Side Ops intelligence (T-100 / COL1).

READ Side Strippers, Side Rectifiers, Pump Arounds, Side Draws.
Does not write to HYSYS. Units copied from case — no Assist conversion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from column_models import (
    ColumnState,
    PumpAroundRow,
    SideDrawRow,
    SideRectifierRow,
    SideStripperRow,
)


def _is_empty(value: float | None) -> bool:
    if value is None:
        return True
    try:
        v = float(value)
    except Exception:
        return True
    return abs(v + 32767.0) < 1.0 or abs(v - 32767.0) < 1.0


def _safe_get(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return None


def _com_float(obj: Any, *members: str) -> float | None:
    for member in members:
        try:
            prop = getattr(obj, member)
            if hasattr(prop, "Value"):
                prop = prop.Value
            elif hasattr(prop, "GetValue"):
                try:
                    prop = prop.GetValue()
                except Exception:
                    continue
            value = float(prop)
            if _is_empty(value):
                continue
            return value
        except Exception:
            continue
    return None


def _com_int(obj: Any, *members: str) -> int | None:
    value = _com_float(obj, *members)
    if value is None:
        return None
    try:
        return int(round(value))
    except Exception:
        return None


def _com_label(obj: Any, *members: str) -> str:
    for member in members:
        raw = _safe_get(obj, member)
        if raw is None:
            continue
        try:
            if hasattr(raw, "Name"):
                text = str(raw.Name).strip()
                if text:
                    return text
        except Exception:
            pass
        text = str(raw).strip()
        if text and not text.startswith("<"):
            return text
    return ""


def _items(collection: Any) -> list[Any]:
    if collection is None:
        return []
    try:
        count = int(collection.Count)
    except Exception:
        return []
    out: list[Any] = []
    for index in range(count):
        try:
            out.append(collection.Item(index))
        except Exception:
            try:
                out.append(collection.Item(index + 1))
            except Exception:
                continue
    return out


def _flow_basis_from_com(cfs: Any) -> str:
    for attr in ("SideOpsFlowBasis", "FlowBasis", "DefaultBasis", "SpecBasis"):
        raw = _safe_get(cfs, attr)
        if raw is None:
            continue
        text = str(raw.Value if hasattr(raw, "Value") else raw).strip()
        if not text or text.startswith("<"):
            continue
        if text in {"0", "Molar"}:
            return "Molar"
        if text in {"1", "Mass"}:
            return "Mass"
        if text in {"2", "Volume", "LiquidVol", "StdIdealLiqVol"}:
            return "Volume"
        return text
    return ""


def _is_side_stripper(name: str, type_name: str) -> bool:
    n, t = name.lower(), type_name.lower()
    return "_ss" in n or "sidestrip" in t or "side strip" in t


def _is_pump_around(name: str, type_name: str) -> bool:
    n, t = name.lower(), type_name.lower()
    return bool(re.match(r"pa[_\s-]?\d", n)) or "pumparound" in t or "pump around" in t


def _is_side_rectifier(name: str, type_name: str) -> bool:
    n, t = name.lower(), type_name.lower()
    return "rectifier" in t or "_sr" in n or "side rect" in t


def _read_side_stripper_op(op: Any) -> SideStripperRow:
    name = str(_safe_get(op, "Name") or "")
    return SideStripperRow(
        name=name,
        num_stages=_com_int(
            op,
            "NumberOfStages",
            "NoOfStages",
            "NStages",
            "Stages",
        ),
        liq_draw_stage=_com_label(
            op,
            "LiqDrawStage",
            "LiquidDrawStage",
            "LiquidDrawStageName",
            "DrawStage",
            "DrawStageName",
        ),
        vap_return_stage=_com_label(
            op,
            "VapReturnStage",
            "VapourReturnStage",
            "VaporReturnStage",
            "ReturnStage",
            "ReturnStageName",
        ),
        outlet_flow=_com_float(
            op,
            "OutletFlow",
            "ProductFlow",
            "SideStripProductFlow",
            "MolarFlow",
            "Flow",
        ),
        reboiler_duty=_com_float(
            op,
            "ReboilerDuty",
            "ReboilerHeatFlow",
            "Duty",
            "HeatFlow",
        ),
    )


def _read_pump_around_op(op: Any) -> PumpAroundRow:
    name = str(_safe_get(op, "Name") or "")
    export_raw = _safe_get(op, "Export")
    export = False
    if export_raw is not None:
        try:
            export = bool(export_raw.Value if hasattr(export_raw, "Value") else export_raw)
        except Exception:
            export = False
    return PumpAroundRow(
        name=name,
        draw_stage=_com_label(
            op,
            "DrawStage",
            "DrawStageName",
            "LiquidDrawStage",
            "FromStage",
        ),
        return_stage=_com_label(
            op,
            "ReturnStage",
            "ReturnStageName",
            "LiquidReturnStage",
            "ToStage",
        ),
        flow=_com_float(op, "Flow", "MolarFlow", "Circulation", "PumpAroundFlow"),
        duty=_com_float(op, "Duty", "HeatFlow", "HeatDuty", "PumpAroundDuty"),
        draw_temperature=_com_float(
            op,
            "DrawTemperature",
            "DrawTemp",
            "TemperatureDraw",
            "FromTemperature",
        ),
        return_temperature=_com_float(
            op,
            "ReturnTemperature",
            "ReturnTemp",
            "TemperatureReturn",
            "ToTemperature",
        ),
        export=export,
    )


def _read_side_rectifier_op(op: Any) -> SideRectifierRow:
    name = str(_safe_get(op, "Name") or "")
    return SideRectifierRow(
        name=name,
        num_stages=_com_int(op, "NumberOfStages", "NoOfStages", "NStages"),
        vap_draw_stage=_com_label(
            op,
            "VapDrawStage",
            "VapourDrawStage",
            "VaporDrawStage",
            "DrawStage",
        ),
        liq_return_stage=_com_label(
            op,
            "LiqReturnStage",
            "LiquidReturnStage",
            "ReturnStage",
        ),
        vap_prod_flow=_com_float(op, "VapProdFlow", "VapourProductFlow", "ProductFlow"),
        condenser_duty=_com_float(op, "CondenserDuty", "CondDuty", "Duty"),
    )


def _read_side_draws_from_column(column: Any) -> list[SideDrawRow]:
    rows: list[SideDrawRow] = []
    for idx in range(1, 9):
        stream = _safe_get(column, f"SideStripProduct{idx}")
        if stream is None:
            stream = _safe_get(column, f"SideDrawProduct{idx}")
        if stream is None:
            continue
        try:
            sname = str(stream.Name)
        except Exception:
            continue
        if not sname:
            continue
        rows.append(
            SideDrawRow(
                stream_name=sname,
                draw_stage=_com_label(stream, "DrawStage", "StageName", "IFaceStageName"),
            )
        )
    return rows


def _spec_float(state: ColumnState, pattern: str) -> float | None:
    pat = pattern.lower()
    for spec in state.specs:
        if pat in spec.name.lower():
            val = spec.goal_value if spec.goal_value is not None else spec.current_value
            if val is not None and not _is_empty(val):
                return float(val)
    return None


def _enrich_side_strippers(
    state: ColumnState,
    stream_molar: Callable[[str], float | None] | None = None,
) -> None:
    """Fill T-100-shaped gaps from Connections + Monitor specs."""
    t100 = {
        "Kero_SS": ("9_Main TS", "8_Main TS", "Kerosene", "kero reb duty"),
        "Diesel_SS": ("17_Main TS", "16_Main TS", "Diesel", None),
        "AGO_SS": ("22_Main TS", "21_Main TS", "AGO", None),
    }
    known = {r.name: r for r in state.side_strippers}
    for ss_name, (liq, vap, prod_hint, duty_pat) in t100.items():
        row = known.get(ss_name)
        if row is None:
            row = SideStripperRow(name=ss_name)
            state.side_strippers.append(row)
        if not row.liq_draw_stage:
            row.liq_draw_stage = liq
        if not row.vap_return_stage:
            row.vap_return_stage = vap
        if row.num_stages is None:
            row.num_stages = 3
        if row.outlet_flow is None and stream_molar:
            for outlet in state.outlet_rows:
                if prod_hint.lower() in outlet.name.lower():
                    row.outlet_flow = stream_molar(outlet.name)
                    break
        if row.reboiler_duty is None and duty_pat:
            row.reboiler_duty = _spec_float(state, duty_pat)


def _enrich_pump_arounds(state: ColumnState) -> None:
    known = {r.name.lower(): r for r in state.pump_arounds}
    t100_pa = {
        "pa_1": ("2_Main TS", "1_Main TS"),
        "pa_2": ("17_Main TS", "16_Main TS"),
        "pa_3": ("22_Main TS", "21_Main TS"),
    }
    for key, (draw, ret) in t100_pa.items():
        row = known.get(key)
        if row is None:
            row = PumpAroundRow(name=key.upper().replace("_", "_"))
            row.name = {"pa_1": "PA_1", "pa_2": "PA_2", "pa_3": "PA_3"}[key]
            state.pump_arounds.append(row)
            known[key] = row
        if not row.draw_stage:
            row.draw_stage = draw
        if not row.return_stage:
            row.return_stage = ret
        if row.flow is None:
            row.flow = _spec_float(state, f"{row.name.lower()}_rate")
        if row.duty is None:
            row.duty = _spec_float(state, f"{row.name.lower()}_duty")


def _enrich_side_draws(
    state: ColumnState,
    stream_molar: Callable[[str], float | None] | None,
    stream_mass: Callable[[str], float | None] | None,
) -> None:
    if state.side_draws:
        existing = {r.stream_name.lower() for r in state.side_draws}
    else:
        existing = set()

    draw_order = (
        ("off gas", "Condenser", "V"),
        ("naphtha", "Condenser", "L"),
        ("waste water", "Condenser", "W"),
        ("residue", "29_Main TS", "L"),
        ("kerosene", "Kero_SS_Reb", "L"),
        ("diesel", "3_Diesel_SS", "L"),
        ("ago", "3_AGO_SS", "L"),
    )

    for outlet in state.outlet_rows:
        name_l = outlet.name.lower()
        if outlet.role in {"pa_energy", "condenser_duty", "energy_in"}:
            continue
        if "energy" in name_l or name_l.endswith("_q"):
            continue
        if name_l in existing:
            continue
        phase = outlet.phase_type or ""
        if not phase and outlet.role == "offgas":
            phase = "V"
        elif not phase and outlet.role == "waste_water":
            phase = "W"
        elif not phase and outlet.role in {"naphtha", "residue", "side_product"}:
            phase = "L"
        mole = stream_molar(outlet.name) if stream_molar else None
        mass = stream_mass(outlet.name) if stream_mass else None
        state.side_draws.append(
            SideDrawRow(
                stream_name=outlet.name,
                draw_stage=outlet.stage_label or "",
                phase_type=phase,
                mole_flow=mole,
                mass_flow=mass,
            )
        )
        existing.add(name_l)

    # Ensure T-100 reference streams present even if Connections missed stage
    by_name = {r.stream_name.lower(): r for r in state.side_draws}
    for hint, stage, phase in draw_order:
        match = next((r for n, r in by_name.items() if hint in n), None)
        if match is None:
            continue
        if not match.draw_stage:
            match.draw_stage = stage
        if not match.phase_type:
            match.phase_type = phase

    # Fill flows for rows missing COM values
    for row in state.side_draws:
        if row.mole_flow is None and stream_molar:
            row.mole_flow = stream_molar(row.stream_name)
        if row.mass_flow is None and stream_mass:
            row.mass_flow = stream_mass(row.stream_name)

    # Sort: condenser draws first, then main column bottom, then side products
    def _sort_key(r: SideDrawRow) -> tuple[int, str]:
        stage = r.draw_stage.lower()
        if "condenser" in stage:
            order = {"v": 0, "l": 1, "w": 2}.get(r.phase_type.lower(), 3)
            return (0, str(order), r.stream_name)
        if "_main" in stage or "main ts" in stage:
            return (1, r.stream_name, "")
        return (2, r.stream_name, "")

    state.side_draws.sort(key=_sort_key)


def apply_side_ops_read(
    state: ColumnState,
    column: Any,
    cfs: Any,
    ts: Any,
    *,
    stream_molar: Callable[[str], float | None] | None = None,
    stream_mass: Callable[[str], float | None] | None = None,
) -> None:
    """Best-effort COM read + Connections/Monitor enrichment."""
    state.side_strippers = []
    state.side_rectifiers = []
    state.pump_arounds = []
    state.side_draws = []

    if cfs is not None:
        state.side_ops_flow_basis = _flow_basis_from_com(cfs) or state.default_spec_basis or "Molar"
        ops = _safe_get(cfs, "Operations")
        for op in _items(ops):
            name = str(_safe_get(op, "Name") or "")
            type_name = str(_safe_get(op, "TypeName") or "")
            if _is_side_stripper(name, type_name):
                state.side_strippers.append(_read_side_stripper_op(op))
            elif _is_pump_around(name, type_name):
                state.pump_arounds.append(_read_pump_around_op(op))
            elif _is_side_rectifier(name, type_name):
                state.side_rectifiers.append(_read_side_rectifier_op(op))
    else:
        state.side_ops_flow_basis = state.default_spec_basis or "Molar"

    state.side_draws = _read_side_draws_from_column(column)

    if state.cdu_topology or any("_SS" in r.name for r in state.side_strippers):
        _enrich_side_strippers(state, stream_molar)
    if state.cdu_topology or state.pump_arounds or state.pa_energy_streams:
        _enrich_pump_arounds(state)

    _enrich_side_draws(state, stream_molar, stream_mass)

    state.side_strippers.sort(key=lambda r: r.name)
    state.pump_arounds.sort(key=lambda r: r.name)


def _fmt_flow(value: float | None, unit: str) -> str:
    if value is None or _is_empty(value):
        return "<empty>"
    if abs(value) >= 1e4 or (abs(value) < 0.01 and value != 0):
        return f"{value:.4g} {unit}"
    return f"{value:.4g} {unit}"


def _fmt_temp(value: float | None, unit: str) -> str:
    if value is None or _is_empty(value):
        return "<empty>"
    return f"{value:.4g} {unit}"


def side_ops_topology_cue(state: ColumnState) -> str:
    """Soft PE hint from Side Ops topology."""
    if not state.cdu_topology and not state.side_strippers and not state.pump_arounds:
        return ""
    ss = len(state.side_strippers)
    pa = len(state.pump_arounds)
    draws = len(state.side_draws)
    parts = []
    if ss:
        parts.append(f"{ss} side stripper(s)")
    if pa:
        parts.append(f"{pa} PA(s)")
    if draws:
        parts.append(f"{draws} side draw(s)")
    detail = ", ".join(parts) if parts else "Side Ops"
    return (
        f"CDU Side Ops: {detail} — prefer draw / PA / steam MV families over top RR; "
        "add Side Ops one-at-a-time when building (D4 model-build order)."
    )


def format_side_ops_block(state: ColumnState) -> str:
    """HYSYS Design → Side Ops snapshot for PE board / UI."""
    mol_u = state.molar_flow_unit or "lbmole/hr"
    mass_u = state.mass_flow_unit or "lb/hr"
    duty_u = state.energy_unit or "Btu/hr"
    temp_u = state.temperature_unit or "F"
    basis = state.side_ops_flow_basis or state.default_spec_basis or "Molar"

    lines = [
        "SIDE OPS (Design → Side Ops) [READ]",
        f"  Flow basis: {basis}",
    ]

    lines.append("  Side Strippers:")
    if not state.side_strippers:
        lines.append("    (none)")
    else:
        for row in state.side_strippers:
            nst = str(row.num_stages) if row.num_stages is not None else "—"
            lines.append(
                f"    {row.name}  #St={nst}  LiqDraw={row.liq_draw_stage or '—'}  "
                f"VapRet={row.vap_return_stage or '—'}  "
                f"Outlet={_fmt_flow(row.outlet_flow, mol_u)}  "
                f"RebDuty={_fmt_flow(row.reboiler_duty, duty_u)}"
            )

    lines.append("  Side Rectifiers:")
    if not state.side_rectifiers:
        lines.append("    (none — T-100 empty)")
    else:
        for row in state.side_rectifiers:
            lines.append(
                f"    {row.name}  #St={row.num_stages or '—'}  "
                f"VapDraw={row.vap_draw_stage or '—'}  LiqRet={row.liq_return_stage or '—'}  "
                f"VapProd={_fmt_flow(row.vap_prod_flow, mol_u)}  "
                f"CondDuty={_fmt_flow(row.condenser_duty, duty_u)}"
            )

    lines.append("  Pump Arounds:")
    if not state.pump_arounds:
        lines.append("    (none)")
    else:
        for row in state.pump_arounds:
            lines.append(
                f"    {row.name}  Draw={row.draw_stage or '—'}  Ret={row.return_stage or '—'}  "
                f"Flow={_fmt_flow(row.flow, mol_u)}  Duty={_fmt_flow(row.duty, duty_u)}  "
                f"Tdraw={_fmt_temp(row.draw_temperature, temp_u)}  "
                f"Tret={_fmt_temp(row.return_temperature, temp_u)}"
            )

    lines.append("  Side Draws:")
    if not state.side_draws:
        lines.append("    (none)")
    else:
        for row in state.side_draws:
            lines.append(
                f"    {row.stream_name} @ {row.draw_stage or '—'} | {row.phase_type or '—'} | "
                f"Mole={_fmt_flow(row.mole_flow, mol_u)} | Mass={_fmt_flow(row.mass_flow, mass_u)}"
            )

    cue = side_ops_topology_cue(state)
    if cue:
        lines.append(f"  PE: {cue}")

    return "\n".join(lines)


def load_t100_side_ops_reference(path: str | None = None) -> dict[str, Any]:
    p = (
        Path(path)
        if path
        else Path(__file__).resolve().parent / "config" / "cdu_t100_side_ops_reference.json"
    )
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
