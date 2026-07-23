"""Live T-100: hold naphtha+kero rates, read qualities vs Assist targets + typical standards.

Usage (HYSYS open):
  .venv\\Scripts\\python.exe scripts/live_naphtha_kero_quality.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cdu_case_config import load_case_config
from cdu_quality_engine import build_product_quality_state, format_quality_board
from column_api import ColumnController
from column_engine import ConvergenceAssistant
from column_models import ConvergenceLimits, default_cdu_targets
from hysys_api import HysysController

COLUMN = "T-100"
HOLD_SPECS = ("Naphtha Prod Rate", "Kero_SS Prod Flow")


def _spec(state, needle: str):
    for s in state.specs:
        if needle.lower() in s.name.lower():
            return s
    return None


def _d86_points(columns: ColumnController, stream: str, pcts=(5, 10, 50, 90, 95)) -> dict:
    from cdu_quality_engine import _d86_at_percent

    out = {}
    for p in pcts:
        out[p] = _d86_at_percent(columns, stream, float(p))
    return out


def main() -> int:
    hysys = HysysController()
    hysys.connect()
    api = ColumnController(hysys)
    limits = ConvergenceLimits()
    targets = default_cdu_targets()
    case = load_case_config()

    assist = ConvergenceAssistant(api, limits, targets)
    st, dg = assist.diagnose_column(COLUMN)

    print("=" * 72)
    print("T-100 live — Naphtha + Kerosene rates + quality vs standards")
    print("=" * 72)
    print(f"State={dg.engineering_state.value}  DOF={st.degrees_of_freedom}  "
          f"phys={st.physical_solution}  conv={st.appears_converged}")

    print("\n--- RATE HOLDS (primary production) ---")
    for name in HOLD_SPECS:
        sp = _spec(st, name)
        if sp is None:
            print(f"  MISSING spec matching '{name}'")
            continue
        g = sp.goal_display if sp.goal_display is not None else sp.goal_value
        c = sp.current_display if sp.current_display is not None else sp.current_value
        u = sp.display_unit or ""
        print(
            f"  {sp.name}: Active={sp.is_active}  Goal={g}  Current={c}  {u}  "
            f"err={sp.error}"
        )
        if not sp.is_active:
            print("    WARNING: not Active — rate hold not enforced by solver")

    print("\n--- HYSYS D86 (display F) Boiling Point Curves ---")
    for stream in ("Naphtha", "Kerosene"):
        pts = _d86_points(api, stream)
        bits = "  ".join(
            f"D86_{p}%={v:.1f}" if v is not None else f"D86_{p}%=—"
            for p, v in pts.items()
        )
        print(f"  {stream}: {bits}")

    pqs = build_product_quality_state(st, case, columns=api)
    print("\n--- ASSIST QUALITY BOARD (configured targets) ---")
    print(format_quality_board(pqs))

    print("\n--- COMPARE: Assist FINAL_TARGET / case vs HYSYS now ---")
    # Typical industry / practice notes (Field) — PE reference, not legal specs
    standards = [
        ("Naphtha D86 95% max", 356.0, "F", "Assist hard; ~180 C full-range / heavy naphtha EP style"),
        ("Kero flash min", 100.0, "F", "Assist hard; Jet A-style flash ~38 C (ASTM D56 class)"),
        ("Kero D86 95% max", 518.0, "F", "Assist hard; ~270 C kerosene cut EP style"),
        ("Kero–diesel gap soft", 27.0, "F", "Assist soft; ~15 C Diesel D86 5% − Kero D86 95%"),
    ]
    print("  Reference (Assist practice targets — not a particular plant contract):")
    for name, val, unit, note in standards:
        print(f"    {name}: {val} {unit} — {note}")

    print("\n  Readings vs Assist:")
    for r in pqs.readings:
        if r.product.lower() not in {"naphtha", "kerosene", "spec"}:
            continue
        if "diesel" in r.target_id.lower() and "gap" not in r.property.lower():
            continue
        meas = f"{r.value:.2f}" if r.value is not None else "UNAVAILABLE"
        tgt = f"{r.target_value}" if r.target_value is not None else "—"
        flag = "OK" if r.status.value == "on_spec" else r.status.value.upper()
        print(
            f"    {r.target_id}: measured={meas} {r.unit}  target={tgt}  "
            f"[{flag}]  ({r.read_method})"
        )

    print("\nDone. Rates left as-is (no Goal edits). Case not saved.")
    try:
        hysys.disconnect()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
