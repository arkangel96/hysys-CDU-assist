"""DEPRECATED — Simple Column / SW Stripper helper. Not used by CDU Assist.

Transfer PE pre-estimates into a stripper case (feed unchanged).
Kept only as platform-history reference. Prefer CDU-specific helpers after Phase 1.
"""
from __future__ import annotations

from column_api import ColumnController
from column_engine import ConvergenceAssistant, format_pe_board
from column_models import ConvergenceLimits
from hysys_api import HysysController

# Manual PE pre-estimates (stripper reference only)
RR_GOAL = 2.5
BTMS_KGMOLE_H = 12500.0
BTMS_GOAL_SI = BTMS_KGMOLE_H / 3600.0  # COM molar rate often kgmole/s
NH3_GOAL = 5e-5  # 50 ppmw — plant-typical SWS bottoms
COLUMN = "SW Stripper"  # reference case name — not a CDU default



def main() -> int:
    c = HysysController()
    c.connect(None)
    api = ColumnController(c)

    print("=== BEFORE ===")
    before = api.inspect(COLUMN)
    for s in before.specs:
        print(
            f"  {s.name}: Active={s.is_active} "
            f"goal={s.goal_display or s.goal_value} "
            f"cur={s.current_display or s.current_value}"
        )
    print(
        f"  Btms={before.bottoms_molar_flow_kgmole_h} "
        f"Ovhd={before.overhead_molar_flow_kgmole_h} "
        f"NH3={before.bottoms_nh3_mass_frac}"
    )

    print("\n=== SNAPSHOT (for restore if needed) ===")
    api.snapshot(COLUMN)
    print("  OK")

    print("\n=== APPLY PRE-ESTIMATES (feed constant) ===")
    api.set_spec_goal(COLUMN, "Reflux Ratio", RR_GOAL)
    print(f"  RR Goal -> {RR_GOAL}")

    try:
        api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_GOAL_SI)
        print(f"  Btms Goal -> {BTMS_KGMOLE_H:g} kgmole/h ({BTMS_GOAL_SI:.6g} SI)")
    except Exception as exc:
        print(f"  Btms Goal before activate: {exc}")

    api.set_spec_goal(COLUMN, "NH3 Mass Frac (Reboiler)", NH3_GOAL)
    print(f"  NH3 Goal -> {NH3_GOAL} (stay inactive)")

    api.set_spec_active(COLUMN, "Ovhd Vap Rate", False)
    print("  Ovhd Active -> OFF")
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    print("  NH3 Active -> OFF")
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    print("  RR Active -> ON")
    api.set_spec_active(COLUMN, "Btms Prod Rate", True)
    print("  Btms Active -> ON")

    try:
        api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_GOAL_SI)
        print(f"  Btms Goal confirmed {BTMS_KGMOLE_H:g} kgmole/h")
    except Exception as exc:
        print(f"  Btms Goal after activate: {exc}")

    for sp in ("Ovhd Vap Rate", "NH3 Mass Frac (Reboiler)", "Reflux Rate"):
        try:
            api.set_spec_estimate(COLUMN, sp, True)
        except Exception:
            pass

    print("\n=== RUN COLUMN ===")
    api.run_column(COLUMN)
    print("  done")

    print("\n=== AFTER ===")
    assistant = ConvergenceAssistant(api, ConvergenceLimits())
    state, diagnosis = assistant.diagnose_column(COLUMN)
    for s in state.specs:
        print(
            f"  {s.name}: Active={s.is_active} "
            f"goal={s.goal_display or s.goal_value} "
            f"cur={s.current_display or s.current_value} err={s.error}"
        )
    print(
        f"  DOF={state.degrees_of_freedom} converged={state.appears_converged} "
        f"physical={state.physical_solution}"
    )
    print(
        f"  Btms={state.bottoms_molar_flow_kgmole_h} "
        f"Ovhd={state.overhead_molar_flow_kgmole_h}"
    )
    print(
        f"  NH3 stream={state.bottoms_nh3_mass_frac} RR={state.reflux_ratio}"
    )
    print(f"  CondQ={state.condenser_duty} RebQ={state.reboiler_duty}")
    print()
    print(format_pe_board(state, diagnosis))
    c.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
