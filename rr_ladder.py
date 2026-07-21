"""RR ladder: hold Btms=12500, raise RR until NH3 <= plant target or weak response."""
from __future__ import annotations

from column_api import ColumnController
from column_engine import ConvergenceAssistant, format_pe_board
from column_models import ConvergenceLimits
from hysys_api import HysysController

COLUMN = "SW Stripper"
BTMS_KGMOLE_H = 12500.0
BTMS_SI = BTMS_KGMOLE_H / 3600.0
NH3_TARGET = 5e-5  # 50 ppmw plant-typical
# Ladder from current ~2.5
RR_STEPS = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 7.0, 8.0, 10.0, 12.0]
WEAK_REL = 0.05  # <5% NH3 improvement vs previous → weak


def main() -> int:
    c = HysysController()
    c.connect(None)
    api = ColumnController(c)
    assistant = ConvergenceAssistant(api, ConvergenceLimits())

    # Ensure Active pair stays RR + Btms
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", False)
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Btms Prod Rate", True)
    api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_SI)
    api.set_spec_goal(COLUMN, "NH3 Mass Frac (Reboiler)", NH3_TARGET)

    state0 = api.inspect(COLUMN)
    nh3_prev = state0.bottoms_nh3_mass_frac
    print(
        f"START  RR={state0.reflux_ratio}  Btms={state0.bottoms_molar_flow_kgmole_h}  "
        f"NH3={nh3_prev}  target={NH3_TARGET}"
    )
    print("-" * 72)

    met = False
    last_state = state0
    last_diag = None

    for rr in RR_STEPS:
        api.set_spec_goal(COLUMN, "Reflux Ratio", float(rr))
        api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_SI)
        api.run_column(COLUMN)
        state, diag = assistant.diagnose_column(COLUMN)
        last_state, last_diag = state, diag
        nh3 = state.bottoms_nh3_mass_frac
        btms = state.bottoms_molar_flow_kgmole_h
        ovhd = state.overhead_molar_flow_kgmole_h
        phys = state.physical_solution
        conv = state.appears_converged

        improve = None
        if nh3 is not None and nh3_prev is not None and nh3_prev > 0:
            improve = (nh3_prev - nh3) / nh3_prev

        flag = ""
        if nh3 is not None and nh3 <= NH3_TARGET:
            flag = "  *** TARGET MET ***"
            met = True
        elif improve is not None and improve < WEAK_REL:
            flag = "  (weak NH3 response)"

        print(
            f"RR={rr:<5g}  NH3={nh3}  Btms={btms}  Ovhd={ovhd}  "
            f"phys={phys} conv={conv}  dNH3_rel={improve}{flag}"
        )

        if met:
            break
        if not phys:
            print("  STOP: lost physical solution")
            break
        if btms is not None and btms < 1000:
            print("  STOP: bottoms collapsed — abort ladder")
            break
        if improve is not None and improve < WEAK_REL and rr >= 6.0:
            print("  STOP: weak response at elevated RR — likely need stages/steam rethink")
            break

        nh3_prev = nh3

    print("-" * 72)
    if last_diag is not None:
        print(format_pe_board(last_state, last_diag))
    print("-" * 72)
    if met:
        print("RESULT: NH3 FINAL_TARGET met with plant-like bottoms held.")
    else:
        print("RESULT: Ladder finished without meeting NH3 — State C/F review.")
    c.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
