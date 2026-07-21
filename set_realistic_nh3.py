"""Set plant-realistic NH3 FINAL_TARGET (50 ppmw) in HYSYS; restore sensible RR."""
from __future__ import annotations

from column_api import ColumnController
from column_engine import ConvergenceAssistant, format_pe_board
from column_models import ConvergenceLimits, default_sw_stripper_targets
from hysys_api import HysysController

COLUMN = "SW Stripper"
NH3_GOAL = 5e-5  # 50 ppmw
RR_GOAL = 2.5  # plant-sensible energy after ladder
BTMS_SI = 12500.0 / 3600.0


def main() -> int:
    target = default_sw_stripper_targets()[0]
    print(f"Studio FINAL_TARGET: {target.id} = {target.target_value:g} ({target.target_value*1e6:g} ppmw)")

    c = HysysController()
    c.connect(None)
    api = ColumnController(c)

    api.set_spec_goal(COLUMN, "NH3 Mass Frac (Reboiler)", NH3_GOAL)
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Btms Prod Rate", True)
    api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_SI)
    api.set_spec_goal(COLUMN, "Reflux Ratio", RR_GOAL)
    print(f"HYSYS NH3 Goal -> {NH3_GOAL:g} (Active OFF)")
    print(f"HYSYS RR Goal -> {RR_GOAL} | Btms -> 12500 kgmole/h (Active ON)")

    api.run_column(COLUMN)
    assistant = ConvergenceAssistant(api, ConvergenceLimits())
    state, diagnosis = assistant.diagnose_column(COLUMN)
    print(
        f"NH3 stream={state.bottoms_nh3_mass_frac} "
        f"({(state.bottoms_nh3_mass_frac or 0)*1e6:.4g} ppmw)  "
        f"target={NH3_GOAL:g} ({NH3_GOAL*1e6:g} ppmw)"
    )
    print(f"Btms={state.bottoms_molar_flow_kgmole_h} RR={state.reflux_ratio}")
    print()
    print(format_pe_board(state, diagnosis))
    c.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
