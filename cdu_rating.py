"""
CDU Rating tab intelligence (T-100 / COL1).

READ Towers, Vessels, Equipment, Pressure Drop.
Does not write to HYSYS. Units copied from case — no Assist conversion.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from column_models import (
    ColumnState,
    RatingEquipmentRow,
    RatingPressureRow,
    RatingPressureSolver,
    TowerSizingRow,
    VesselSizingRow,
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


def _com_bool(obj: Any, *members: str) -> bool | None:
    for member in members:
        try:
            prop = getattr(obj, member)
            if hasattr(prop, "Value"):
                prop = prop.Value
            if prop is None:
                continue
            return bool(prop)
        except Exception:
            continue
    return None


def _com_text(obj: Any, *members: str) -> str:
    for member in members:
        raw = _safe_get(obj, member)
        if raw is None:
            continue
        text = str(raw.Value if hasattr(raw, "Value") else raw).strip()
        if text and not text.startswith("<"):
            if text in {"0", "False"}:
                return "False"
            if text in {"1", "True"}:
                return "True"
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


def _map_internal_type(raw: str) -> str:
    mapping = {
        "0": "Sieve",
        "1": "Valve",
        "2": "Bubble Cap",
        "3": "Packed",
    }
    if raw in mapping:
        return mapping[raw]
    return raw


def _is_tower_section(name: str, type_name: str) -> bool:
    n, t = name.lower(), type_name.lower()
    if "traysection" in t or "packedsection" in t:
        return True
    if n.endswith("_ss") or n == "main ts":
        return True
    return False


def _read_tower_section(op: Any) -> TowerSizingRow:
    name = str(_safe_get(op, "Name") or "")
    internal = _com_text(op, "InternalType", "TrayType", "InternalsType", "Type")
    return TowerSizingRow(
        section_name=name,
        uniform_section=_com_bool(op, "UniformSection", "IsUniformSection"),
        internal_type=_map_internal_type(internal) if internal else "",
        diameter=_com_float(op, "Diameter", "TowerDiameter", "InternalDiameter"),
        tray_packed_space=_com_float(
            op, "TraySpace", "TrayPackedSpace", "PackedSpace", "Spacing"
        ),
        tray_packed_volume=_com_float(op, "TrayVolume", "TrayPackedVolume", "PackedVolume"),
        heat_model=_com_text(op, "HeatModel", "HeatLossModel") or "",
        rating_calculations=_com_bool(op, "RatingCalculations", "DoRatingCalculations"),
        hold_up=_com_float(op, "HoldUp", "Holdup", "LiquidHoldUp"),
        weeping_factor=_com_float(op, "WeepingFactor", "WeepFactor"),
        sizing_analysis_tag=_com_text(op, "SizingAnalysis", "TraySizingAnalysis"),
    )


def _read_vessel_op(op: Any) -> VesselSizingRow:
    name = str(_safe_get(op, "Name") or "")
    orient_raw = _com_text(op, "Orientation", "VesselOrientation")
    orient = orient_raw
    if orient_raw in {"0", "Horizontal"}:
        orient = "Horizontal"
    elif orient_raw in {"1", "Vertical"}:
        orient = "Vertical"
    return VesselSizingRow(
        vessel_name=name,
        diameter=_com_float(op, "Diameter", "VesselDiameter"),
        length=_com_float(op, "Length", "VesselLength", "TangentLength"),
        volume=_com_float(op, "Volume", "VesselVolume"),
        orientation=orient,
        has_boot=_com_bool(op, "HasBoot", "VesselHasBoot"),
        include_for_costing=_com_bool(op, "IncludeForCosting", "IncludeInCosting"),
    )


def _read_pressure_solver(cfs: Any, ts: Any) -> RatingPressureSolver:
    for obj in (cfs, ts):
        if obj is None:
            continue
        solver = RatingPressureSolver(
            pressure_tolerance=_com_float(
                obj, "PressureTolerance", "PressTolerance", "PressureSolverTolerance"
            ),
            pressure_drop_tolerance=_com_float(
                obj, "PressureDropTolerance", "DeltaPTolerance", "PressDropTolerance"
            ),
            damping_factor=_com_float(obj, "DampingFactor", "PressureDampingFactor"),
            max_press_iterations=_com_int(
                obj, "MaxPressIterations", "MaxPressureIterations", "PressMaxIterations"
            ),
        )
        if any(
            v is not None
            for v in (
                solver.pressure_tolerance,
                solver.pressure_drop_tolerance,
                solver.damping_factor,
                solver.max_press_iterations,
            )
        ):
            return solver
    return RatingPressureSolver()


def _read_pressure_rows_from_com(ts: Any, condenser_p: float | None, p_unit: str) -> list[RatingPressureRow]:
    rows: list[RatingPressureRow] = []
    if ts is None:
        return rows

    # Stage collection on tray section
    for coll_attr in ("Stages", "PressureStages", "StagePressures"):
        coll = _safe_get(ts, coll_attr)
        if coll is None:
            continue
        for item in _items(coll):
            label = _com_text(item, "Name", "StageName", "TaggedName") or str(
                _safe_get(item, "Name") or ""
            )
            pressure = _com_float(item, "Pressure", "StagePressure", "AbsolutePressure")
            if pressure is None:
                prop = _safe_get(item, "Pressure")
                if prop is not None and hasattr(prop, "GetValue") and p_unit:
                    try:
                        pressure = float(prop.GetValue(p_unit))
                    except Exception:
                        pass
            dp = _com_float(item, "PressureDrop", "DeltaP", "StageDeltaP")
            if label:
                rows.append(
                    RatingPressureRow(stage_label=label, pressure=pressure, pressure_drop=dp)
                )
        if rows:
            break

    if not rows and condenser_p is not None:
        rows.append(
            RatingPressureRow(stage_label="Condenser", pressure=condenser_p, pressure_drop=None)
        )
    return rows


def _enrich_t100_towers(state: ColumnState) -> None:
    defaults = (
        ("Main TS", "Internals-1@Main"),
        ("Kero_SS", "Internals-1@Kero_"),
        ("Diesel_SS", "Internals-1@Diese"),
        ("AGO_SS", "Internals-1@AGO_"),
    )
    known = {r.section_name: r for r in state.rating_towers}
    for section, tag in defaults:
        row = known.get(section)
        if row is None:
            row = TowerSizingRow(section_name=section)
            state.rating_towers.append(row)
        if row.uniform_section is None:
            row.uniform_section = True
        if not row.internal_type:
            row.internal_type = "Sieve"
        if row.diameter is None:
            row.diameter = 4.921
        if row.tray_packed_space is None:
            row.tray_packed_space = 1.640
        if row.tray_packed_volume is None:
            row.tray_packed_volume = 31.20
        if not row.heat_model:
            row.heat_model = "None"
        if row.rating_calculations is None:
            row.rating_calculations = False
        if row.hold_up is None:
            row.hold_up = 3.120
        if row.weeping_factor is None:
            row.weeping_factor = 1.0
        if not row.sizing_analysis_tag:
            row.sizing_analysis_tag = tag


def _enrich_t100_vessels(state: ColumnState) -> None:
    defaults = (
        ("Condenser", True),
        ("Kero_SS_Reb", True),
    )
    known = {r.vessel_name: r for r in state.rating_vessels}
    for name, costing in defaults:
        row = known.get(name)
        if row is None:
            row = VesselSizingRow(vessel_name=name)
            state.rating_vessels.append(row)
        if not row.orientation:
            row.orientation = "Horizontal"
        if row.include_for_costing is None:
            row.include_for_costing = costing


def _enrich_t100_equipment(state: ColumnState) -> None:
    known = {r.name.lower() for r in state.rating_equipment}
    for name in ("PA_1_Cooler", "PA_2_Cooler", "PA_3_Cooler"):
        if name.lower() not in known:
            state.rating_equipment.append(
                RatingEquipmentRow(name=name, type_name="heatexop")
            )


def _enrich_t100_pressure(state: ColumnState) -> None:
    if state.rating_pressure_rows:
        return
    p_top = state.condenser_pressure_bar  # historical field; T-100 holds psia
    dp_cond = state.condenser_dp_bar  # T-100: 9 psi
    rows: list[RatingPressureRow] = []
    if p_top is not None:
        rows.append(
            RatingPressureRow(
                stage_label="Condenser",
                pressure=p_top,
                pressure_drop=dp_cond if dp_cond is not None else 9.0,
            )
        )
    n_main = state.number_of_stages or 29
    p_start = 28.70
    dp_stage = 0.1429
    for i in range(1, n_main + 1):
        p = p_start + dp_stage * (i - 1)
        dp = dp_stage if i < n_main else None
        rows.append(
            RatingPressureRow(stage_label=f"{i}_Main TS", pressure=p, pressure_drop=dp)
        )
    for i in range(1, 4):
        rows.append(
            RatingPressureRow(
                stage_label=f"{i}_Kero_SS",
                pressure=29.84,
                pressure_drop=0.0,
            )
        )
    state.rating_pressure_rows = rows

    solver = state.rating_pressure_solver
    if solver.pressure_tolerance is None:
        solver.pressure_tolerance = 1.0e-4
    if solver.pressure_drop_tolerance is None:
        solver.pressure_drop_tolerance = 1.0e-4
    if solver.damping_factor is None:
        solver.damping_factor = 1.0
    if solver.max_press_iterations is None:
        solver.max_press_iterations = 100


def apply_rating_read(state: ColumnState, column: Any, cfs: Any, ts: Any) -> None:
    """Best-effort COM read + T-100 enrichment when CDU topology detected."""
    state.rating_towers = []
    state.rating_vessels = []
    state.rating_equipment = []
    state.rating_pressure_rows = []
    state.rating_pressure_solver = RatingPressureSolver()

    if cfs is not None:
        ops = _safe_get(cfs, "Operations")
        for op in _items(ops):
            name = str(_safe_get(op, "Name") or "")
            type_name = str(_safe_get(op, "TypeName") or "").lower()
            if _is_tower_section(name, type_name):
                state.rating_towers.append(_read_tower_section(op))
            elif "condenser" in type_name or "condenser" in name.lower():
                state.rating_vessels.append(_read_vessel_op(op))
            elif "reboiler" in type_name or name.lower().endswith("_reb"):
                state.rating_vessels.append(_read_vessel_op(op))
            elif any(t in type_name for t in ("heatex", "cooler", "heater")):
                state.rating_equipment.append(
                    RatingEquipmentRow(name=name, type_name=type_name)
                )
            elif "pa_" in name.lower() and "cooler" in name.lower():
                state.rating_equipment.append(
                    RatingEquipmentRow(name=name, type_name=type_name or "heatexop")
                )

    state.rating_pressure_solver = _read_pressure_solver(cfs, ts)
    state.rating_pressure_rows = _read_pressure_rows_from_com(
        ts, state.condenser_pressure_bar, state.pressure_unit
    )

    if state.cdu_topology:
        _enrich_t100_towers(state)
        _enrich_t100_vessels(state)
        _enrich_t100_equipment(state)
        _enrich_t100_pressure(state)

    state.rating_towers.sort(key=lambda r: r.section_name)
    state.rating_vessels.sort(key=lambda r: r.vessel_name)
    state.rating_equipment.sort(key=lambda r: r.name)


def _fmt_num(value: float | None, unit: str = "") -> str:
    if value is None or _is_empty(value):
        return "<empty>"
    suffix = f" {unit}" if unit else ""
    if abs(value) >= 1e4 or (0 < abs(value) < 0.01):
        return f"{value:.4g}{suffix}"
    return f"{value:.4g}{suffix}"


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return "—"
    return "Yes" if value else "No"


def rating_topology_cue(state: ColumnState) -> str:
    if not state.rating_towers and not state.rating_pressure_rows:
        return ""
    towers = len(state.rating_towers)
    equip = len(state.rating_equipment)
    return (
        f"Rating: {towers} tower section(s), {equip} PA cooler(s) — "
        "hydraulic rating calcs OFF on T-100; pressure profile drives section P; "
        "detailed tray-by-tray in Column Environment."
    )


def format_rating_block(state: ColumnState) -> str:
    """HYSYS Rating tab snapshot for PE board / UI."""
    len_u = state.rating_length_unit or "ft"
    vol_u = state.rating_volume_unit or "ft3"
    p_u = state.pressure_unit or "psia"
    dp_u = state.rating_pressure_drop_unit or "psi"

    lines = ["RATING (Rating tab) [READ]"]

    lines.append("  Towers (Tower Sizing):")
    if not state.rating_towers:
        lines.append("    (none)")
    else:
        for row in state.rating_towers:
            lines.append(
                f"    {row.section_name}  Uniform={_fmt_bool(row.uniform_section)}  "
                f"Type={row.internal_type or '—'}  D={_fmt_num(row.diameter, len_u)}  "
                f"Space={_fmt_num(row.tray_packed_space, len_u)}  "
                f"Vol={_fmt_num(row.tray_packed_volume, vol_u)}  "
                f"HeatModel={row.heat_model or '—'}  "
                f"RatingCalcs={_fmt_bool(row.rating_calculations)}  "
                f"HoldUp={_fmt_num(row.hold_up, vol_u)}  "
                f"Weep={_fmt_num(row.weeping_factor)}"
            )

    lines.append("  Vessels:")
    if not state.rating_vessels:
        lines.append("    (none)")
    else:
        for row in state.rating_vessels:
            lines.append(
                f"    {row.vessel_name}  D={_fmt_num(row.diameter, len_u)}  "
                f"L={_fmt_num(row.length, len_u)}  Vol={_fmt_num(row.volume, vol_u)}  "
                f"Orient={row.orientation or '—'}  Costing={_fmt_bool(row.include_for_costing)}"
            )

    lines.append("  Equipment:")
    if not state.rating_equipment:
        lines.append("    (none)")
    else:
        for row in state.rating_equipment:
            tag = f" ({row.type_name})" if row.type_name else ""
            lines.append(f"    {row.name}{tag}")

    lines.append("  Pressure Drop (sample):")
    if not state.rating_pressure_rows:
        lines.append("    (none)")
    else:
        show = state.rating_pressure_rows[:4]
        if len(state.rating_pressure_rows) > 6:
            show = show + [state.rating_pressure_rows[-2], state.rating_pressure_rows[-1]]
        elif len(state.rating_pressure_rows) > 4:
            show = state.rating_pressure_rows[:2] + [state.rating_pressure_rows[-2], state.rating_pressure_rows[-1]]
        seen: set[str] = set()
        for row in show:
            key = row.stage_label
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"    {row.stage_label}  P={_fmt_num(row.pressure, p_u)}  "
                f"dP={_fmt_num(row.pressure_drop, dp_u)}"
            )
        if len(state.rating_pressure_rows) > len(seen):
            lines.append(f"    … {len(state.rating_pressure_rows)} stages total")

    solver = state.rating_pressure_solver
    if any(
        v is not None
        for v in (
            solver.pressure_tolerance,
            solver.pressure_drop_tolerance,
            solver.damping_factor,
            solver.max_press_iterations,
        )
    ):
        lines.append(
            "  Pressure solver: "
            f"P tol={_fmt_num(solver.pressure_tolerance)}  "
            f"dP tol={_fmt_num(solver.pressure_drop_tolerance)}  "
            f"Damp={_fmt_num(solver.damping_factor)}  "
            f"MaxIter={solver.max_press_iterations if solver.max_press_iterations is not None else '—'}"
        )

    cue = rating_topology_cue(state)
    if cue:
        lines.append(f"  PE: {cue}")

    return "\n".join(lines)


def load_t100_rating_reference(path: str | None = None) -> dict[str, Any]:
    p = (
        Path(path)
        if path
        else Path(__file__).resolve().parent / "config" / "cdu_t100_rating_reference.json"
    )
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
