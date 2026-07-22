"""
CDU Design → Monitor specs intelligence (T-100 / COL1 reference).

Classifies Active/Estimate specs into MV families and preferred worksheet units.
Does not write to HYSYS. Units are copied from HYSYS labels / GetValue — no Assist conversion.
"""
from __future__ import annotations

from typing import Any

from column_models import ColumnSpecState, ColumnState


# Preferred unit candidates by family (HYSYS GetValue strings; first match wins).
_VOLUME_UNITS = ("USGPM", "USgal/min", "gpm", "barrel/day", "m3/h", "m3/s", "L/min")
_DUTY_UNITS = ("Btu/hr", "Btu/h", "MMBtu/hr", "kJ/h", "kW", "MJ/h", "kcal/h")
_MOLAR_UNITS = ("lbmole/hr", "lbmol/h", "lbmole/h", "kgmole/h", "kmole/h", "mol/h", "mol/s")


def classify_monitor_spec(name: str, type_name: str = "") -> tuple[str, tuple[str, ...]]:
    """
    Return (mv_family, preferred_unit_candidates).

    Families align with Trial Map / Connections roles:
      side_draw | pa_rate | pa_duty | top_product | vapor_prod |
      ss_reb_duty | reflux | liquid_flow | unknown
    """
    n = f"{name} {type_name}".strip().lower()

    if "reflux ratio" in n or n.strip() == "rr" or "reflux ratio" in name.lower():
        return "reflux", ()

    if "pa_" in n or "pump around" in n or "pumparound" in n:
        if "duty" in n or "heat" in n or "energy" in n:
            return "pa_duty", _DUTY_UNITS
        return "pa_rate", _VOLUME_UNITS

    if "reb" in n and "duty" in n:
        return "ss_reb_duty", _DUTY_UNITS

    if "vap prod" in n or "vapour prod" in n or "vapor prod" in n:
        return "vapor_prod", _MOLAR_UNITS

    if "naphtha" in n and ("prod" in n or "rate" in n or "flow" in n):
        return "top_product", _VOLUME_UNITS

    if any(t in n for t in ("kero_ss", "diesel_ss", "ago_ss")) and (
        "prod" in n or "flow" in n or "rate" in n
    ):
        return "side_draw", _VOLUME_UNITS

    if any(t in n for t in ("kero", "diesel", "ago", "lgo", "hgo")) and (
        "prod" in n or "draw" in n or "flow" in n or "rate" in n
    ):
        return "side_draw", _VOLUME_UNITS

    if n.strip() == "liquid flow" or (
        "liquid flow" in n and "pa" not in n and "prod" not in n
    ):
        return "liquid_flow", _VOLUME_UNITS

    if "duty" in n or "heat flow" in n:
        return "pa_duty", _DUTY_UNITS

    if any(t in n for t in ("prod flow", "prod rate", "draw")):
        return "side_draw", _VOLUME_UNITS

    return "unknown", ()


def default_unit_for_family(family: str, display_units: Any = None) -> str:
    """Worksheet unit label to show when COM Units string is unavailable."""
    if family in {"side_draw", "pa_rate", "top_product", "liquid_flow"}:
        return getattr(display_units, "volume_flow", None) or "USGPM"
    if family in {"pa_duty", "ss_reb_duty"}:
        return getattr(display_units, "energy", None) or "Btu/hr"
    if family == "vapor_prod":
        return getattr(display_units, "molar_flow", None) or "lbmole/hr"
    return ""


def apply_monitor_spec_roles(
    state: ColumnState,
    *,
    display_units: Any = None,
) -> None:
    """Stamp mv_family + fallback display_unit on each spec; fill Active family lists."""
    side_draws: list[str] = []
    pa_rates: list[str] = []
    pa_duties: list[str] = []
    for spec in state.specs:
        family, _cands = classify_monitor_spec(spec.name, spec.type_name)
        spec.mv_family = family
        if not spec.display_unit:
            unit = default_unit_for_family(family, display_units)
            if unit:
                spec.display_unit = unit
        if family == "side_draw" and spec.is_active:
            side_draws.append(spec.name)
        elif family == "pa_rate" and spec.is_active:
            pa_rates.append(spec.name)
        elif family == "pa_duty" and spec.is_active:
            pa_duties.append(spec.name)

    state.active_side_draw_specs = side_draws
    state.active_pa_rate_specs = pa_rates
    state.active_pa_duty_specs = pa_duties

    # CDU topology also from Monitor Active set
    if len(side_draws) >= 2 or (pa_rates and pa_duties):
        state.cdu_topology = True


def format_monitor_block(state: ColumnState) -> str:
    """HYSYS Design → Monitor specifications snapshot."""
    lines = [
        "MONITOR (Design → Monitor) [READ]",
        f"  DOF={state.degrees_of_freedom}  Active={sum(1 for s in state.specs if s.is_active)}  "
        f"Estimate-only={sum(1 for s in state.specs if not s.is_active and s.use_as_estimate)}",
    ]
    order = (
        "side_draw",
        "top_product",
        "pa_rate",
        "pa_duty",
        "ss_reb_duty",
        "vapor_prod",
        "liquid_flow",
        "reflux",
        "unknown",
    )
    by_fam: dict[str, list[ColumnSpecState]] = {k: [] for k in order}
    for sp in state.specs:
        fam = sp.mv_family or "unknown"
        by_fam.setdefault(fam, []).append(sp)

    labels = {
        "side_draw": "Side-stripper / draw rates",
        "top_product": "Overhead liquid product",
        "pa_rate": "Pumparound rates",
        "pa_duty": "Pumparound duties",
        "ss_reb_duty": "Side-stripper reboiler",
        "vapor_prod": "Overhead vapor product",
        "liquid_flow": "Other liquid flow",
        "reflux": "Reflux (often Estimate)",
        "unknown": "Other",
    }
    for fam in order:
        group = by_fam.get(fam) or []
        if not group:
            continue
        lines.append(f"  {labels.get(fam, fam)}:")
        for sp in group:
            goal = sp.goal_display if sp.goal_display is not None else sp.goal_value
            cur = sp.current_display if sp.current_display is not None else sp.current_value
            unit = f" {sp.display_unit}" if sp.display_unit else ""
            flags = []
            if sp.is_active:
                flags.append("Active")
            if sp.use_as_estimate:
                flags.append("Est")
            if sp.summary_current or sp.use_as_current:
                flags.append("Cur")
            flag_s = ",".join(flags) if flags else "—"
            gtxt = f"{goal:.4g}" if isinstance(goal, (int, float)) else goal
            ctxt = f"{cur:.4g}" if isinstance(cur, (int, float)) else cur
            lines.append(
                f"    {sp.name}: spec={gtxt}{unit}  current={ctxt}{unit}  "
                f"err={sp.error}  [{flag_s}]"
            )

    if state.active_side_draw_specs or state.active_pa_rate_specs:
        lines.append(
            "  MV cue: Active draws/PAs present — prefer C_split / B_energy before top RR."
        )
    return "\n".join(lines)


def load_t100_monitor_reference(path: str | None = None) -> dict[str, Any]:
    from pathlib import Path
    import json

    p = (
        Path(path)
        if path
        else Path(__file__).resolve().parent / "config" / "cdu_t100_monitor_reference.json"
    )
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
