"""
CDU Design → Specs page intelligence (T-100 / COL1).

Maps HYSYS Specs list + Specification Details pane (Active / Estimate / Current,
Fixed/Ranged, Primary/Alternate, Spec Value, tolerances).
Does not auto-Add specs.
"""
from __future__ import annotations

from typing import Any

from column_models import ColumnSpecState, ColumnState


def _map_fixed_ranged(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bool):
        return "Fixed" if raw else "Ranged"
    text = str(raw).strip()
    lower = text.lower()
    if lower in {"0", "fixed", "fix"}:
        return "Fixed"
    if lower in {"1", "ranged", "range", "true"} and "fix" not in lower:
        if lower in {"1", "ranged", "range"}:
            return "Ranged"
    if "fix" in lower:
        return "Fixed"
    if "range" in lower:
        return "Ranged"
    return text


def _map_primary_alternate(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, bool):
        return "Primary" if raw else "Alternate"
    text = str(raw).strip()
    lower = text.lower()
    if lower in {"0", "primary", "pri"}:
        return "Primary"
    if lower in {"1", "alternate", "alt"}:
        return "Alternate"
    if "prim" in lower:
        return "Primary"
    if "alt" in lower:
        return "Alternate"
    return text


def format_specs_summary_block(state: ColumnState) -> str:
    """HYSYS Design → Specs Summary table snapshot (T-100 shape)."""
    lines = [
        "SPECS SUMMARY (Design → Specs Summary) [READ]",
        "  Columns: Specified | Active | Current | Fixed/Range | Prim/Alt | Lower | Upper",
        f"  Active={sum(1 for s in state.specs if s.is_active)} / {len(state.specs)}  "
        f"DOF={state.degrees_of_freedom}",
    ]
    for sp in state.specs:
        goal = sp.goal_display if sp.goal_display is not None else sp.goal_value
        unit = f" {sp.display_unit}" if sp.display_unit else ""
        gtxt = f"{goal:.4g}" if isinstance(goal, (int, float)) else str(goal)
        act = "Y" if sp.is_active else "n"
        cur = "Y" if (sp.summary_current or sp.use_as_current) else "n"
        fixed = sp.fixed_or_ranged or ("Fixed" if sp.is_active else "—")
        prim = sp.primary_or_alternate or ("Primary" if sp.is_active else "—")
        lo = sp.lower_bound if sp.lower_bound is not None else "<empty>"
        hi = sp.upper_bound if sp.upper_bound is not None else "<empty>"
        lines.append(
            f"  {sp.name}: {gtxt}{unit}  Act={act} Cur={cur}  "
            f"{fixed}/{prim}  L={lo} U={hi}"
        )
    rr = next((s for s in state.specs if "reflux ratio" in s.name.lower()), None)
    if rr is not None and not rr.is_active:
        lines.append(
            "  PE: Reflux Ratio Active OFF / Current OFF (T-100) — "
            "prefer draw/PA GoalValue; do not Activate RR first."
        )
    return "\n".join(lines)


def format_specs_page_block(state: ColumnState) -> str:
    """HYSYS Design → Specs (list + detail semantics) for PE board / UI."""
    basis = state.default_spec_basis or "—"
    lines = [
        "SPECS (Design → Specs) [READ]",
        f"  Default Basis={basis}  DOF={state.degrees_of_freedom}  "
        f"Count={len(state.specs)}",
        "  Detail pane fields: Active | Use As Estimate | Current | Dry Flow Basis |",
        "    Fixed/Ranged | Primary/Alternate | Spec Value | Current Calc | Wt/Abs Tol/Err",
        "  Actions in HYSYS: View… / Add… / Delete / Update Specs from Dynamics / "
        "Switch To Alternate Specs",
    ]
    if not state.specs:
        lines.append("  (no specifications)")
        return "\n".join(lines)

    lines.append("  Column Specifications:")
    for sp in state.specs:
        flags = []
        if sp.is_active:
            flags.append("Active")
        if sp.use_as_estimate:
            flags.append("Est")
        if sp.summary_current or sp.use_as_current:
            flags.append("Cur")
        if sp.dry_flow_basis:
            flags.append("Dry")
        flag_s = ",".join(flags) if flags else "—"
        goal = sp.goal_display if sp.goal_display is not None else sp.goal_value
        unit = f" {sp.display_unit}" if sp.display_unit else ""
        gtxt = f"{goal:.4g}" if isinstance(goal, (int, float)) else str(goal)
        type_bits = []
        if sp.fixed_or_ranged:
            type_bits.append(sp.fixed_or_ranged)
        if sp.primary_or_alternate:
            type_bits.append(sp.primary_or_alternate)
        type_s = "/".join(type_bits) if type_bits else "—"
        fam = sp.mv_family or "—"
        conv = ""
        if sp.spec_converged is True:
            conv = " ok"
        elif sp.spec_converged is False:
            conv = " !!"
        lines.append(
            f"    {sp.name}: spec={gtxt}{unit}  [{flag_s}]  "
            f"type={type_s}  fam={fam}{conv}"
        )
        if sp.weighted_tolerance is not None or sp.absolute_tolerance is not None:
            lines.append(
                f"      tol wt={sp.weighted_tolerance} abs={sp.absolute_tolerance}  "
                f"err wt={sp.error} abs={sp.absolute_error}"
            )

    lines.append(
        "  PE: edit Spec Value / Active / Estimate here or on Specs Summary; "
        "Add… opens type catalog (recommend only — no auto Add)."
    )
    return "\n".join(lines)


def load_t100_specs_page_reference(path: str | None = None) -> dict[str, Any]:
    from pathlib import Path
    import json

    p = (
        Path(path)
        if path
        else Path(__file__).resolve().parent / "config" / "cdu_t100_specs_page_reference.json"
    )
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
