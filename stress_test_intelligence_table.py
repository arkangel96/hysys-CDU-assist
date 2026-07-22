"""Tabulated multi-parameter intelligence stress tests (RR held where noted).

Prints Action | Result rows for tracking. Restores baseline; never auto-saves.
"""
from __future__ import annotations

from column_api import ColumnController
from column_engine import ConvergenceAssistant, propose_action
from column_models import ConvergenceLimits, FinalTarget, default_sw_stripper_targets
from hysys_api import HysysController

COLUMN = "SW Stripper"
BTMS_SI = 12500.0 / 3600.0
RR_GOOD = 2.5


def _ascii(text: object) -> str:
    return str(text or "-").encode("ascii", "replace").decode()


def restore_good(api: ColumnController, snap) -> None:
    api.restore(snap)
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Btms Prod Rate", True)
    api.set_spec_goal(COLUMN, "Reflux Ratio", RR_GOOD)
    api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_SI)
    api.run_column(COLUMN)


def row(
    case: str,
    action: str,
    state: str,
    family: str,
    propose: str,
    key_result: str,
    trial: str = "-",
) -> dict:
    return {
        "case": case,
        "action": action,
        "state": state,
        "family": family or "-",
        "propose": propose,
        "key_result": key_result,
        "trial": trial,
    }


def diagnose_pack(api: ColumnController, limits: ConvergenceLimits, targets):
    assist = ConvergenceAssistant(api, limits, targets)
    st, dg = assist.diagnose_column(COLUMN)
    act = propose_action(st, limits, dg, targets)
    return assist, st, dg, act


def propose_text(act) -> str:
    if act is None:
        return "none"
    sid = act.payload.get("strategy_id", act.kind)
    fam = act.payload.get("family", "")
    spec = act.payload.get("spec_name", "")
    bits = [str(sid)]
    if fam:
        bits.append(str(fam))
    if spec:
        bits.append(str(spec))
    return " | ".join(bits)


def main() -> int:
    hysys = HysysController()
    hysys.connect(None)
    api = ColumnController(hysys)
    snap = api.snapshot(COLUMN)

    rows: list[dict] = []
    plant_targets = default_sw_stripper_targets()
    # Harder plant gate for split stress (this case design Btms ~12500)
    strict_limits = ConvergenceLimits(min_bottoms_flow_kgmole_h=5000.0)
    # Harder product target to force State C without touching RR first
    tight_targets = [
        FinalTarget(
            id="NH3_BOTTOMS",
            description="Tight stress FINAL_TARGET 1 ppmw",
            spec_name_contains="nh3",
            component_name_contains=("ammonia", "nh3"),
            stream="bottoms",
            relationship="less_or_equal",
            target_value=1e-6,  # 1 ppmw
            tolerance=0.0,
            locked=True,
            hard=True,
        )
    ]

    # ----- 0 Baseline -----
    limits = ConvergenceLimits()
    assist, st, dg, act = diagnose_pack(api, limits, plant_targets)
    rows.append(
        row(
            "0_BASELINE",
            "Inspect only (RR=2.5, Btms=12500 Active)",
            dg.engineering_state.value,
            dg.preferred_family,
            propose_text(act),
            f"NH3={(st.bottoms_nh3_mass_frac or 0)*1e6:.3g} ppmw; Btms={st.bottoms_molar_flow_kgmole_h:.4g}",
        )
    )

    # ----- 1 Split stress: RR fixed, high Ovhd, strict operability -----
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Btms Prod Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", True)
    api.set_spec_goal(COLUMN, "Reflux Ratio", RR_GOOD)  # RR held
    api.set_spec_goal(COLUMN, "Ovhd Vap Rate", 16000.0 / 3600.0)
    api.run_column(COLUMN)
    assist, st, dg, act = diagnose_pack(api, strict_limits, plant_targets)
    trial_txt = "-"
    if act is not None and act.kind in {"set_goal", "refresh_estimates", "baseline_swap"}:
        # Prefer skipping RR if possible: if propose is RR, note it; still run once
        tr = assist.run_one_trial(COLUMN, dry_run=False)
        trial_txt = (
            f"{'KEPT' if tr.kept else 'REVERSED'} "
            f"{tr.action.payload.get('strategy_id')} "
            f"{tr.action.payload.get('spec_name','')}"
        )
        st2, dg2 = assist.diagnose_column(COLUMN)
        key = (
            f"Btms={st.bottoms_molar_flow_kgmole_h:.4g}->{st2.bottoms_molar_flow_kgmole_h:.4g}; "
            f"Ovhd={st.overhead_molar_flow_kgmole_h:.4g}->{st2.overhead_molar_flow_kgmole_h:.4g}; "
            f"after_state={dg2.engineering_state.value}"
        )
    else:
        key = (
            f"Btms={st.bottoms_molar_flow_kgmole_h:.4g}; "
            f"Ovhd={st.overhead_molar_flow_kgmole_h:.4g}; RR held={st.reflux_ratio:.4g}"
        )
    rows.append(
        row(
            "1_SPLIT_high_Ovhd_RR_held",
            "RR Goal fixed 2.5; Ovhd Active Goal=16000 kgmole/h; Btms inactive; "
            "operability gate Btms>=5000",
            dg.engineering_state.value,
            dg.preferred_family,
            propose_text(act),
            key,
            trial_txt,
        )
    )
    restore_good(api, snap)

    # ----- 2 Split via low Btms Active (RR held) -----
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Btms Prod Rate", True)
    api.set_spec_goal(COLUMN, "Reflux Ratio", RR_GOOD)
    api.set_spec_goal(COLUMN, "Btms Prod Rate", 500.0 / 3600.0)  # very low bottoms
    api.run_column(COLUMN)
    assist, st, dg, act = diagnose_pack(api, strict_limits, plant_targets)
    trial_txt = "-"
    if act is not None and act.kind in {"set_goal", "refresh_estimates", "baseline_swap"}:
        tr = assist.run_one_trial(COLUMN, dry_run=False)
        trial_txt = (
            f"{'KEPT' if tr.kept else 'REVERSED'} "
            f"{tr.action.payload.get('strategy_id')} "
            f"{tr.action.payload.get('spec_name','')}"
        )
        st2, dg2 = assist.diagnose_column(COLUMN)
        key = (
            f"Btms={st.bottoms_molar_flow_kgmole_h:.4g}->{st2.bottoms_molar_flow_kgmole_h:.4g}; "
            f"after_state={dg2.engineering_state.value}"
        )
    else:
        key = f"Btms={st.bottoms_molar_flow_kgmole_h:.4g}; RR={st.reflux_ratio:.4g}"
    rows.append(
        row(
            "2_SPLIT_low_Btms_RR_held",
            "RR fixed 2.5; Btms Active Goal=500 kgmole/h; gate Btms>=5000",
            dg.engineering_state.value,
            dg.preferred_family,
            propose_text(act),
            key,
            trial_txt,
        )
    )
    restore_good(api, snap)

    # ----- 3 Tight NH3 target + low RR (energy) — for comparison -----
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Btms Prod Rate", True)
    api.set_spec_goal(COLUMN, "Btms Prod Rate", BTMS_SI)
    api.set_spec_goal(COLUMN, "Reflux Ratio", 0.8)
    api.run_column(COLUMN)
    assist, st, dg, act = diagnose_pack(api, limits, tight_targets)
    trial_txt = "-"
    if act is not None and act.kind == "set_goal":
        tr = assist.run_one_trial(COLUMN, dry_run=False)
        trial_txt = (
            f"{'KEPT' if tr.kept else 'REVERSED'} "
            f"{tr.action.payload.get('strategy_id')} "
            f"{tr.action.payload.get('spec_name','')}"
        )
        st2, dg2 = assist.diagnose_column(COLUMN)
        key = (
            f"NH3={(st.bottoms_nh3_mass_frac or 0)*1e6:.3g}->{(st2.bottoms_nh3_mass_frac or 0)*1e6:.3g} ppmw; "
            f"RR={st.reflux_ratio:.4g}->{st2.reflux_ratio:.4g}; after={dg2.engineering_state.value}"
        )
    else:
        key = (
            f"NH3={(st.bottoms_nh3_mass_frac or 0)*1e6:.3g} ppmw vs 1 ppmw; RR={st.reflux_ratio:.4g}"
        )
    rows.append(
        row(
            "3_ENERGY_low_RR_tight_NH3",
            "RR Goal=0.8; Assist FINAL_TARGET temporary 1 ppmw (locked); Btms=12500",
            dg.engineering_state.value,
            dg.preferred_family,
            propose_text(act),
            key,
            trial_txt,
        )
    )
    restore_good(api, snap)

    # ----- 4 Init path: refresh estimates when physical but ask numerical_recovery style -----
    # Force State B-ish if possible by wild Ovhd then estimates; else document refresh proposal unused
    api.set_spec_active(COLUMN, "NH3 Mass Frac (Reboiler)", False)
    api.set_spec_active(COLUMN, "Btms Prod Rate", False)
    api.set_spec_active(COLUMN, "Reflux Ratio", True)
    api.set_spec_active(COLUMN, "Ovhd Vap Rate", True)
    api.set_spec_goal(COLUMN, "Reflux Ratio", RR_GOOD)
    api.set_spec_goal(COLUMN, "Ovhd Vap Rate", 50000.0 / 3600.0)  # extreme
    api.run_column(COLUMN)
    assist, st, dg, act = diagnose_pack(api, strict_limits, plant_targets)
    trial_txt = "-"
    if act is not None and act.kind in {"set_goal", "refresh_estimates", "baseline_swap"}:
        tr = assist.run_one_trial(COLUMN, dry_run=False)
        trial_txt = (
            f"{'KEPT' if tr.kept else 'REVERSED'} "
            f"{tr.action.payload.get('strategy_id')} "
            f"{tr.action.payload.get('spec_name','')}"
        )
        st2, dg2 = assist.diagnose_column(COLUMN)
        key = (
            f"physical={st.physical_solution}->{st2.physical_solution}; "
            f"Btms={st.bottoms_molar_flow_kgmole_h}->{st2.bottoms_molar_flow_kgmole_h}; "
            f"after={dg2.engineering_state.value}"
        )
    else:
        key = (
            f"physical={st.physical_solution}; Btms={st.bottoms_molar_flow_kgmole_h}; "
            f"Ovhd={st.overhead_molar_flow_kgmole_h}"
        )
    rows.append(
        row(
            "4_EXTREME_Ovhd_or_init",
            "RR held 2.5; Ovhd Active Goal=50000 kgmole/h (extreme split/init)",
            dg.engineering_state.value,
            dg.preferred_family,
            propose_text(act),
            key,
            trial_txt,
        )
    )

    restore_good(api, snap)
    _, stf, dgf, _ = diagnose_pack(api, limits, plant_targets)
    rows.append(
        row(
            "9_RESTORE",
            "Restore snapshot + RR=2.5 + Btms=12500 Active",
            dgf.engineering_state.value,
            dgf.preferred_family,
            "none",
            f"NH3={(stf.bottoms_nh3_mass_frac or 0)*1e6:.3g} ppmw; Btms={stf.bottoms_molar_flow_kgmole_h:.4g}",
        )
    )

    # Print tracking table
    print()
    print("INTELLIGENCE STRESS TRACKING TABLE")
    print("=" * 120)
    hdr = (
        f"{'CASE':<28} | {'STATE':<22} | {'FAMILY':<10} | {'PROPOSE':<40} | {'TRIAL':<36}"
    )
    print(hdr)
    print("-" * 120)
    for r in rows:
        print(
            f"{r['case']:<28} | {r['state']:<22} | {r['family']:<10} | "
            f"{r['propose']:<40} | {r['trial']:<36}"
        )
    print("-" * 120)
    print()
    print("ACTION DETAIL")
    print("=" * 120)
    for r in rows:
        print(f"CASE:    {r['case']}")
        print(f"ACTION:  {r['action']}")
        print(f"RESULT:  state={r['state']}  family={r['family']}  propose={r['propose']}")
        print(f"         key={r['key_result']}")
        print(f"         trial={r['trial']}")
        print()

    # Markdown file for user tracking
    md_path = "docs/STRESS_TEST_RESULTS.md"
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("# Intelligence Stress Test Results\n\n")
        fh.write("Live HYSYS SW Stripper — multi-parameter tests. Case restored; not auto-saved.\n\n")
        fh.write("| Case | Action | State | Family | Propose | Trial | Key result |\n")
        fh.write("|------|--------|-------|--------|---------|-------|------------|\n")
        for r in rows:
            fh.write(
                f"| `{r['case']}` | {r['action']} | `{r['state']}` | `{r['family']}` | "
                f"`{r['propose']}` | `{r['trial']}` | {r['key_result']} |\n"
            )
        fh.write("\n*Generated by stress_test_intelligence_table.py*\n")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
