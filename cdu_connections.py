"""
CDU Design → Connections role map (T-100 / COL1 reference topology).

Classifies inlet/outlet rows for PE board and soft family hints.
Does not write to HYSYS.
"""
from __future__ import annotations

import re
from typing import Any

from column_models import ColumnState, ConnectionStreamRow


def classify_connection_role(
    name: str,
    *,
    direction: str,
    phase_type: str = "",
    stage_label: str = "",
) -> str:
    """Map a Connections stream name to a CDU role (T-100 heuristics)."""
    n = (name or "").strip().lower()
    stage = (stage_label or "").strip().lower()
    phase = (phase_type or "").strip().upper()

    if direction == "inlet":
        if phase == "Q" or "energy" in n or n.endswith("_q") or n.startswith("q-") or n.startswith("q_"):
            if "pa" in n or "pump" in n:
                return "pa_energy"
            return "energy_in"
        if "steam" in n:
            return "stripping_steam"
        if "atm" in n and "feed" in n:
            return "crude_feed"
        if "feed" in n and "steam" not in n:
            return "crude_feed"
        if "pa" in n and ("q" in n or "duty" in n or "energy" in n):
            return "pa_energy"
        return "unknown"

    # outlets
    if phase == "Q" or n.endswith("_q") or "cond" in n and ("q" in n or "duty" in n or "energy" in n):
        if re.search(r"\bpa[_\s-]?\d", n) or n.startswith("pa_") or "pump around" in n:
            return "pa_energy"
        if "cond" in n:
            return "condenser_duty"
        return "pa_energy" if "pa" in n else "condenser_duty"

    if "residue" in n or "resid" in n or n in {"btms", "bottoms"}:
        return "residue"
    if "naphtha" in n or "ovhd liq" in n or "distillate" in n:
        return "naphtha"
    if "off gas" in n or "offgas" in n or "fuel gas" in n:
        return "offgas"
    if "waste water" in n or "wastewater" in n or phase == "W":
        return "waste_water"
    if any(t in n for t in ("kero", "diesel", "ago", "lgo", "hgo", "gas oil", "jet")):
        return "side_product"
    if "_ss" in stage or "stripper" in stage:
        return "side_product"
    if phase == "V":
        return "offgas"
    if phase == "L" and "condenser" in stage:
        return "naphtha"
    return "unknown"


def infer_phase_type(
    *,
    name: str,
    is_energy: bool,
    type_name: str = "",
    vapor_frac: float | None = None,
    water_draw: bool = False,
) -> str:
    """HYSYS Connections Type column: L / V / W / Q."""
    if is_energy:
        return "Q"
    n = (name or "").lower()
    tn = (type_name or "").lower()
    if water_draw or "waste water" in n or "wastewater" in n or "water" in tn and "waste" in n:
        return "W"
    if vapor_frac is not None:
        try:
            vf = float(vapor_frac)
            if vf >= 0.95:
                return "V"
            if vf <= 0.05:
                return "L"
        except Exception:
            pass
    if "vap" in tn or "vapor" in tn or "vapour" in tn:
        return "V"
    if "liquid" in tn or "liq" in tn:
        return "L"
    if "off gas" in n or "offgas" in n:
        return "V"
    if any(t in n for t in ("naphtha", "residue", "kero", "diesel", "ago", "btms", "bottoms")):
        return "L"
    return ""


def _stage_num_from_label(label: str) -> int | None:
    if not label:
        return None
    m = re.match(r"^(\d+)", label.strip())
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


def apply_connection_roles(state: ColumnState) -> None:
    """
    Fill convenience lists, prefer CDU product/feed names, set cdu_topology.
    Mutates state in place.
    """
    for row in state.inlet_rows:
        if not row.role or row.role == "unknown":
            row.role = classify_connection_role(
                row.name,
                direction="inlet",
                phase_type=row.phase_type,
                stage_label=row.stage_label,
            )
    for row in state.outlet_rows:
        if not row.role or row.role == "unknown":
            row.role = classify_connection_role(
                row.name,
                direction="outlet",
                phase_type=row.phase_type,
                stage_label=row.stage_label,
            )

    state.steam_streams = [
        r.name for r in state.inlet_rows if r.role == "stripping_steam"
    ]
    state.side_products = [
        r.name for r in state.outlet_rows if r.role == "side_product"
    ]
    state.pa_energy_streams = [
        r.name
        for r in (*state.inlet_rows, *state.outlet_rows)
        if r.role == "pa_energy"
    ]
    # Deduplicate PA names preserving order
    seen: set[str] = set()
    pa_unique: list[str] = []
    for n in state.pa_energy_streams:
        if n not in seen:
            seen.add(n)
            pa_unique.append(n)
    state.pa_energy_streams = pa_unique

    crude = next((r for r in state.inlet_rows if r.role == "crude_feed"), None)
    if crude is not None:
        num = _stage_num_from_label(crude.stage_label)
        if num is not None:
            state.feed_stage = num
        if crude.stage_label:
            state.feed_stage_label = crude.stage_label

    residue = next((r for r in state.outlet_rows if r.role == "residue"), None)
    if residue is not None:
        state.bottoms_liquid_product = residue.name

    offgas = next((r for r in state.outlet_rows if r.role == "offgas"), None)
    if offgas is not None:
        state.top_vapour_product = offgas.name

    naphtha = next((r for r in state.outlet_rows if r.role == "naphtha"), None)
    if naphtha is not None:
        state.overhead_liquid_product = naphtha.name

    # Fill missing stage labels for known overhead / bottoms roles
    for row in state.outlet_rows:
        if row.stage_label:
            continue
        if row.role in {"offgas", "naphtha", "waste_water", "condenser_duty"}:
            row.stage_label = "Condenser"
        elif row.role == "residue" and state.feed_stage_label:
            # Often same tray section bottom as main steam / residue draw
            bot = state.feed_stage_label
            if "Main" in bot or bot[:1].isdigit():
                # Prefer highest Main TS stage if we saw steam at bottom
                steam_bot = next(
                    (
                        r.stage_label
                        for r in state.inlet_rows
                        if r.role == "stripping_steam" and "Main" in (r.stage_label or "")
                    ),
                    "",
                )
                row.stage_label = steam_bot or bot

    state.cdu_topology = (
        len(state.side_products) >= 2
        or (
            len(state.pa_energy_streams) >= 1
            and any(r.role == "crude_feed" for r in state.inlet_rows)
        )
        or (
            any(r.role == "crude_feed" for r in state.inlet_rows)
            and any(r.role == "residue" for r in state.outlet_rows)
            and any(r.role in {"naphtha", "offgas"} for r in state.outlet_rows)
        )
    )


def connections_topology_cue(state: ColumnState) -> str:
    """Soft PE-board cue when CDU Connections topology is detected."""
    if not state.cdu_topology:
        return ""
    parts = []
    if state.side_products:
        parts.append(f"side products={', '.join(state.side_products)}")
    if state.pa_energy_streams:
        parts.append(f"PAs={', '.join(state.pa_energy_streams)}")
    if state.steam_streams:
        parts.append(f"steam={', '.join(state.steam_streams)}")
    detail = "; ".join(parts) if parts else "multi-product tower"
    return (
        f"CDU Connections: side strippers + PAs present ({detail}) — "
        "prefer draw/PA/steam families over top RR."
    )


def load_t100_reference(path: str | None = None) -> dict[str, Any]:
    """Load offline T-100 Connections reference fixture."""
    from pathlib import Path
    import json

    p = Path(path) if path else Path(__file__).resolve().parent / "config" / "cdu_t100_connections_reference.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
