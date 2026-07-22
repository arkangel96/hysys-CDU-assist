"""
CDU Design → Subcooling page intelligence (T-100 / COL1).

READ Condenser Subcooling: Degrees of Subcool, Subcool To.
Does not write to HYSYS.
"""
from __future__ import annotations

from typing import Any

from column_models import ColumnState


def format_subcooling_block(state: ColumnState) -> str:
    """HYSYS Design → Subcooling snapshot for PE board / UI."""
    t_u = state.temperature_unit or "F"
    deg = state.condenser_subcool_degrees
    sub_to = state.condenser_subcool_to
    mode = state.condenser_subcool_to_mode or "—"
    lines = [
        "SUBCOOLING (Design → Subcooling) [READ]",
        "  Condenser Subcooling:",
    ]
    if deg is None and sub_to is None:
        lines.append(f"    Degrees of Subcool=<empty>  Subcool To=<empty> ({mode})")
        lines.append(
            "  PE: no condenser subcool set (T-100 default) — naphtha/overhead "
            "cold props handled elsewhere unless you specify subcool here."
        )
    else:
        deg_s = f"{deg:.4g} {t_u}" if deg is not None else "<empty>"
        to_s = f"{sub_to:.4g} {t_u}" if sub_to is not None else "<empty>"
        lines.append(f"    Degrees of Subcool={deg_s}  Subcool To={to_s} ({mode})")
    return "\n".join(lines)


def read_subcooling_from_com(column: Any, cfs: Any, ts: Any) -> dict[str, Any]:
    """
    Best-effort COM read for Subcooling page fields.
    Returns dict with keys: degrees, subcool_to, subcool_to_mode.
    """
    out: dict[str, Any] = {
        "degrees": None,
        "subcool_to": None,
        "subcool_to_mode": "",
    }
    candidates = (column, cfs, ts)
    for obj in candidates:
        if obj is None:
            continue
        for deg_attr in (
            "DegreesOfSubcool",
            "SubcoolDegrees",
            "CondenserSubcoolDegrees",
            "SubcoolingDegrees",
        ):
            try:
                prop = getattr(obj, deg_attr, None)
                if prop is None:
                    continue
                val = float(prop.Value if hasattr(prop, "Value") else prop)
                if abs(val + 32767.0) > 1.0:
                    out["degrees"] = val
                    break
            except Exception:
                continue
        for to_attr in (
            "SubcoolTo",
            "SubcoolToTemperature",
            "CondenserSubcoolTo",
            "SubcoolingTo",
        ):
            try:
                prop = getattr(obj, to_attr, None)
                if prop is None:
                    continue
                val = float(prop.Value if hasattr(prop, "Value") else prop)
                if abs(val + 32767.0) > 1.0:
                    out["subcool_to"] = val
                    break
            except Exception:
                continue
        for mode_attr in ("SubcoolToType", "SubcoolToMode", "SubcoolBasis"):
            try:
                raw = getattr(obj, mode_attr, None)
                if raw is not None:
                    text = str(raw.Value if hasattr(raw, "Value") else raw).strip()
                    if text and not text.startswith("<"):
                        out["subcool_to_mode"] = text
            except Exception:
                continue
    return out


def load_t100_subcooling_reference(path: str | None = None) -> dict[str, Any]:
    from pathlib import Path
    import json

    p = (
        Path(path)
        if path
        else Path(__file__).resolve().parent / "config" / "cdu_t100_subcooling_reference.json"
    )
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
