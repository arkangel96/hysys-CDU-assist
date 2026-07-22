"""CDU T-100 live intelligence stress test.

Snapshots the open HYSYS case, applies CDU MV stresses (draw / PA / wrong RR Active),
diagnoses + proposes, restores baseline. Never auto-saves the .hsc.

Usage (HYSYS T-100 open first):
  .venv\\Scripts\\python.exe stress_test_cdu_t100.py
"""
from __future__ import annotations

from column_api import ColumnController
from column_engine import ConvergenceAssistant, propose_action
from column_models import ConvergenceLimits, default_cdu_targets
from hysys_api import HysysController

COLUMN = "T-100"


def _ascii(text: object) -> str:
    return str(text or "-").encode("ascii", "replace").decode()


def _spec(state, name_part: str):
    for s in state.specs:
        if name_part.lower() in s.name.lower():
            return s
    return None


def _disp(spec) -> str:
    if spec is None:
        return "-"
    g = spec.goal_display if spec.goal_display is not None else spec.goal_value
    u = spec.display_unit or ""
    return f"{g} {u}".strip()


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


def diagnose_pack(api: ColumnController, limits: ConvergenceLimits, targets):
    assist = ConvergenceAssistant(api, limits, targets)
    st, dg = assist.diagnose_column(COLUMN)
    act = propose_action(st, limits, dg, targets)
    return assist, st, dg, act


def print_table(rows: list[dict]) -> None:
    headers = ("case", "action", "state", "family", "propose", "trial", "key_result")
    widths = {h: max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in headers}
    # Cap wide columns for readability
    for h in ("action", "propose", "key_result"):
        widths[h] = min(widths[h], 72)

    def fmt(r: dict) -> str:
        parts = []
        for h in headers:
            text = str(r.get(h, ""))[: widths[h]]
            parts.append(text.ljust(widths[h]))
        return " | ".join(parts)

    print(fmt({h: h for h in headers}))
    print("-+-".join("-" * widths[h] for h in headers))
    for r in rows:
        print(fmt(r))


def main() -> int:
    print("=" * 72)
    print("CDU Assist — T-100 live stress test")
    print("Snapshot → stress → diagnose → restore (no auto-save)")
    print("=" * 72)

    hysys = HysysController()
    hysys.connect(None)
    api = ColumnController(hysys)
    limits = ConvergenceLimits()
    targets = default_cdu_targets()
    rows: list[dict] = []

    print("\n[0] Snapshot baseline Active/Goal set...")
    snap = api.snapshot(COLUMN)

    try:
        # ----- 0 Baseline -----
        assist, st, dg, act = diagnose_pack(api, limits, targets)
        kero = _spec(st, "Kero_SS Prod Flow")
        pa1d = _spec(st, "PA_1_Duty")
        pa1r = _spec(st, "PA_1_Rate")
        rr = _spec(st, "Reflux Ratio")
        rows.append(
            row(
                "0_BASELINE",
                "Inspect only (T-100 converged)",
                dg.engineering_state.value,
                dg.preferred_family,
                propose_text(act),
                (
                    f"phys={st.physical_solution}; Active={sum(1 for s in st.specs if s.is_active)}; "
                    f"Kero={_disp(kero)}; PA1Duty={_disp(pa1d)}; RR_act={rr.is_active if rr else '-'}"
                ),
            )
        )
        print(
            f"    State={dg.engineering_state.value} physical={st.physical_solution} "
            f"Active={sum(1 for s in st.specs if s.is_active)}"
        )

        if not st.appears_converged or not st.physical_solution:
            print("BASELINE not healthy — abort stress (restore still applied).")
            return 1

        # ----- 1 PA duty stress (weaker cooling) -----
        print("\n[1] STRESS PA_1_Duty → 70% of Goal (weaker section cooling)...")
        if pa1d is None or pa1d.goal_value is None:
            rows.append(
                row("1_PA_DUTY", "SKIP — PA_1_Duty missing", "-", "-", "none", "skip")
            )
        else:
            new_duty = float(pa1d.goal_value) * 0.70
            api.set_spec_goal(COLUMN, pa1d.name, new_duty)
            api.run_column(COLUMN)
            assist, st, dg, act = diagnose_pack(api, limits, targets)
            trial_txt = "-"
            if act is not None and act.kind in {"set_goal", "refresh_estimates", "baseline_swap"}:
                print("    Running ONE Assist trial...")
                trial = assist.run_one_trial(COLUMN, dry_run=False)
                trial_txt = (
                    f"{'KEPT' if trial.kept else 'REVERSED'} "
                    f"{_ascii(trial.action.description)}"
                )
                st2, dg2 = assist.diagnose_column(COLUMN)
                key = (
                    f"before_state={dg.engineering_state.value}; after={dg2.engineering_state.value}; "
                    f"PA1Duty={_disp(_spec(st2, 'PA_1_Duty'))}; family={dg2.preferred_family}"
                )
                rows.append(
                    row(
                        "1_PA_DUTY_weak",
                        f"PA_1_Duty Goal *= 0.70 ({new_duty:.4g} SI)",
                        dg.engineering_state.value,
                        dg.preferred_family,
                        propose_text(act),
                        key,
                        trial_txt,
                    )
                )
            else:
                rows.append(
                    row(
                        "1_PA_DUTY_weak",
                        f"PA_1_Duty Goal *= 0.70 ({new_duty:.4g} SI)",
                        dg.engineering_state.value,
                        dg.preferred_family,
                        propose_text(act),
                        f"PA1Duty={_disp(_spec(st, 'PA_1_Duty'))}; max_err={st.max_active_spec_error:.3g}",
                    )
                )
            api.restore(snap)
            api.run_column(COLUMN)

        # ----- 2 Side-draw stress (cut Kero rate) -----
        print("\n[2] STRESS Kero_SS Prod Flow → 50% of Goal...")
        assist, st, dg, act = diagnose_pack(api, limits, targets)
        kero = _spec(st, "Kero_SS Prod Flow")
        if kero is None or kero.goal_value is None:
            rows.append(
                row("2_KERO_DRAW", "SKIP — Kero_SS Prod Flow missing", "-", "-", "none", "skip")
            )
        else:
            new_kero = float(kero.goal_value) * 0.50
            api.set_spec_goal(COLUMN, kero.name, new_kero)
            api.run_column(COLUMN)
            assist, st, dg, act = diagnose_pack(api, limits, targets)
            trial_txt = "-"
            if act is not None and act.kind in {"set_goal", "refresh_estimates", "baseline_swap"}:
                print("    Running ONE Assist trial...")
                trial = assist.run_one_trial(COLUMN, dry_run=False)
                trial_txt = (
                    f"{'KEPT' if trial.kept else 'REVERSED'} "
                    f"{_ascii(trial.action.description)}"
                )
                st2, dg2 = assist.diagnose_column(COLUMN)
                key = (
                    f"before={dg.engineering_state.value}; after={dg2.engineering_state.value}; "
                    f"Kero={_disp(_spec(st2, 'Kero_SS Prod Flow'))}; family={dg2.preferred_family}"
                )
            else:
                key = (
                    f"Kero={_disp(_spec(st, 'Kero_SS Prod Flow'))}; "
                    f"max_err={st.max_active_spec_error:.3g}; phys={st.physical_solution}"
                )
            rows.append(
                row(
                    "2_KERO_DRAW_half",
                    f"Kero_SS Prod Flow Goal *= 0.50 ({new_kero:.4g} SI)",
                    dg.engineering_state.value,
                    dg.preferred_family,
                    propose_text(act),
                    key,
                    trial_txt,
                )
            )
            api.restore(snap)
            api.run_column(COLUMN)

        # ----- 3 Wrong Active: RR ON, one PA rate OFF (DOF stay 0) -----
        print("\n[3] STRESS wrong Active — deactivate PA_1_Rate, activate Reflux Ratio...")
        assist, st, dg, act = diagnose_pack(api, limits, targets)
        pa1r = _spec(st, "PA_1_Rate")
        rr = _spec(st, "Reflux Ratio")
        if pa1r is None or rr is None:
            rows.append(
                row("3_RR_WRONG_ACTIVE", "SKIP — PA_1_Rate or RR missing", "-", "-", "none", "skip")
            )
        else:
            api.set_spec_active(COLUMN, pa1r.name, False)
            api.set_spec_active(COLUMN, rr.name, True)
            api.run_column(COLUMN)
            assist, st, dg, act = diagnose_pack(api, limits, targets)
            # Expect Assist to prefer draw/PA and/or recommend unchecking RR
            clicks = " | ".join(dg.specs_summary_clicks[:2]) if dg.specs_summary_clicks else "-"
            rows.append(
                row(
                    "3_RR_WRONG_ACTIVE",
                    "PA_1_Rate Active OFF; Reflux Ratio Active ON",
                    dg.engineering_state.value,
                    dg.preferred_family,
                    propose_text(act),
                    (
                        f"RR_act={_spec(st, 'Reflux Ratio').is_active}; "
                        f"PA1R_act={_spec(st, 'PA_1_Rate').is_active}; "
                        f"clicks={_ascii(clicks)}"
                    ),
                )
            )
            api.restore(snap)
            api.run_column(COLUMN)

        # ----- 9 Final restore verify -----
        print("\n[9] Restore snapshot + verify baseline...")
        api.restore(snap)
        api.run_column(COLUMN)
        _, stf, dgf, actf = diagnose_pack(api, limits, targets)
        rows.append(
            row(
                "9_RESTORE",
                "Restore snapshot Active/Goal",
                dgf.engineering_state.value,
                dgf.preferred_family,
                propose_text(actf),
                (
                    f"phys={stf.physical_solution}; conv={stf.appears_converged}; "
                    f"Active={sum(1 for s in stf.specs if s.is_active)}; "
                    f"Kero={_disp(_spec(stf, 'Kero_SS Prod Flow'))}; "
                    f"PA1Duty={_disp(_spec(stf, 'PA_1_Duty'))}"
                ),
            )
        )

    except Exception as exc:
        print(f"\nERROR during stress: {type(exc).__name__}: {exc}")
        print("Attempting restore...")
        try:
            api.restore(snap)
            api.run_column(COLUMN)
            print("Restore OK")
        except Exception as rex:
            print(f"Restore FAILED: {rex}")
        return 1
    finally:
        try:
            hysys.disconnect()
        except Exception:
            pass

    print("\n" + "=" * 72)
    print("RESULTS TABLE")
    print("=" * 72)
    print_table(rows)
    print("\nDone. Case restored (not auto-saved). Check HYSYS Status = Converged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
