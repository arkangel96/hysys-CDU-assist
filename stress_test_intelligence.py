"""Controlled stress test of multi-variable Column Assist intelligence.

Snapshots the live HYSYS case, applies two stresses, diagnoses/proposes,
optionally runs one trial each, then restores the baseline Active set.
Never auto-saves the .hsc.
"""
from __future__ import annotations

from column_api import ColumnController
from column_engine import ConvergenceAssistant, propose_action
from column_models import ConvergenceLimits
from hysys_api import HysysController

COLUMN = "SW Stripper"
BTMS_SI = 12500.0 / 3600.0
RR_GOOD = 2.5


def _ascii(text: object) -> str:
    return str(text or "-").encode("ascii", "replace").decode()


def show(title: str, state, diag, act) -> None:
    nh3 = state.bottoms_nh3_mass_frac
    ppm = (nh3 or 0.0) * 1e6
    print("=" * 60)
    print(title)
    print("=" * 60)
    print(
        f"State={diag.engineering_state.value}  family={diag.preferred_family}  "
        f"physical={state.physical_solution}  conv={state.appears_converged}"
    )
    print(f"Hypothesis: {_ascii(diag.pe_hypothesis)}")
    print(
        f"RR={state.reflux_ratio}  Btms={state.bottoms_molar_flow_kgmole_h}  "
        f"Ovhd={state.overhead_molar_flow_kgmole_h}"
    )
    met = diag.final_target_status.get("NH3_BOTTOMS", {}).get("met")
    print(f"NH3 stream={nh3} ({ppm:.4g} ppmw)  target=50 ppmw  met={met}")
    print(f"max_active_err={state.max_active_spec_error}")
    for spec in state.active_specs():
        goal = spec.goal_display if spec.goal_display is not None else spec.goal_value
        cur = spec.current_display if spec.current_display is not None else spec.current_value
        print(f"  ACTIVE {spec.name}: goal={goal} current={cur} err={spec.error}")
    if act is None:
        print("PROPOSE: none")
    else:
        print(f"PROPOSE: {act.kind} {_ascii(act.description)}")
        print(
            f"  strategy={act.payload.get('strategy_id')} family={act.payload.get('family')}"
        )
    print()


def restore_good(api: ColumnController, snap) -> None:
    api.restore(snap)
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Btms Prod Rate", True)
    api.set_spec_goal(COLUMN, "Reflux Ratio", RR_GOOD)
    api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_SI)
    api.run_column(COLUMN)


def main() -> int:
    hysys = HysysController()
    hysys.connect(None)
    api = ColumnController(hysys)
    limits = ConvergenceLimits()

    snap = api.snapshot(COLUMN)
    assist0 = ConvergenceAssistant(api, limits)
    base_state, base_diag = assist0.diagnose_column(COLUMN)
    show(
        "BASELINE (before stress)",
        base_state,
        base_diag,
        propose_action(base_state, limits, base_diag, assist0.targets),
    )

    summary: list[tuple] = []

    # ----- Stress 1: underpowered energy -----
    print("Applying STRESS 1: RR Goal -> 0.8 ...")
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Btms Prod Rate", True)
    api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_SI)
    api.set_spec_goal(COLUMN, "Reflux Ratio", 0.8)
    api.run_column(COLUMN)

    assist1 = ConvergenceAssistant(api, limits)
    st, dg = assist1.diagnose_column(COLUMN)
    act = propose_action(st, limits, dg, assist1.targets)
    show("STRESS 1 RESULT (low RR=0.8)", st, dg, act)
    summary.append(
        (
            "stress1_low_RR",
            dg.engineering_state.value,
            dg.preferred_family,
            None if act is None else act.payload.get("strategy_id"),
            st.bottoms_nh3_mass_frac,
            st.reflux_ratio,
        )
    )

    if act is not None and act.kind == "set_goal":
        print("Running ONE live trial under stress 1...")
        trial = assist1.run_one_trial(COLUMN, dry_run=False)
        print(
            f"TRIAL: {'KEPT' if trial.kept else 'REVERSED'}  "
            f"{_ascii(trial.action.description)}  response={trial.response_class}"
        )
        st2, dg2 = assist1.diagnose_column(COLUMN)
        print(
            f"After trial: State={dg2.engineering_state.value} "
            f"family={dg2.preferred_family} "
            f"NH3={(st2.bottoms_nh3_mass_frac or 0)*1e6:.4g} ppmw RR={st2.reflux_ratio}"
        )
        print()

    restore_good(api, snap)
    print("Restored baseline after stress 1.\n")

    # ----- Stress 2: split / dry-bottoms style -----
    print("Applying STRESS 2: high Ovhd Active, Btms inactive ...")
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Btms Prod Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", True)
    api.set_spec_goal(COLUMN, "Reflux Ratio", RR_GOOD)
    api.set_spec_goal(COLUMN, "Ovhd Vap Rate", 15000.0 / 3600.0)
    api.run_column(COLUMN)

    assist2 = ConvergenceAssistant(api, limits)
    st, dg = assist2.diagnose_column(COLUMN)
    act = propose_action(st, limits, dg, assist2.targets)
    show("STRESS 2 RESULT (high Ovhd Active)", st, dg, act)
    summary.append(
        (
            "stress2_high_Ovhd",
            dg.engineering_state.value,
            dg.preferred_family,
            None if act is None else act.payload.get("strategy_id"),
            st.bottoms_molar_flow_kgmole_h,
            st.overhead_molar_flow_kgmole_h,
        )
    )

    if act is not None and act.kind in {"set_goal", "refresh_estimates", "baseline_swap"}:
        print("Running ONE live trial under stress 2...")
        trial = assist2.run_one_trial(COLUMN, dry_run=False)
        print(
            f"TRIAL: {'KEPT' if trial.kept else 'REVERSED'}  "
            f"{_ascii(trial.action.description)}  response={trial.response_class}"
        )
        st2, dg2 = assist2.diagnose_column(COLUMN)
        print(
            f"After trial: State={dg2.engineering_state.value} "
            f"family={dg2.preferred_family} "
            f"Btms={st2.bottoms_molar_flow_kgmole_h} Ovhd={st2.overhead_molar_flow_kgmole_h}"
        )
        print()

    restore_good(api, snap)
    stf, dgf = ConvergenceAssistant(api, limits).diagnose_column(COLUMN)
    show("FINAL RESTORE", stf, dgf, None)

    print("SUMMARY")
    for row in summary:
        print(row)
    print("Done. Case restored (not auto-saved). Review numbers in HYSYS if needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
