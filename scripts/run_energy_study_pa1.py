"""Campaign A energy study — PA_1 steps with naphtha+kero rate holds.

Snapshots, runs up to 2× PA_1 |duty| −3% steps, scores rates/quality/CondQ,
writes docs/studies/ iteration log, restores snapshot (no auto-save).

Usage (HYSYS T-100 open):
  .venv\\Scripts\\python.exe scripts/run_energy_study_pa1.py
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cdu_case_config import load_case_config
from cdu_quality_engine import _d86_at_percent, _flash_point_display, build_product_quality_state
from column_api import ColumnController
from column_engine import ConvergenceAssistant
from column_models import ConvergenceLimits, default_cdu_targets
from hysys_api import HysysController

COLUMN = "T-100"
NAPHTHA = "Naphtha Prod Rate"
KERO = "Kero_SS Prod Flow"
PA1 = "PA_1_Duty"
STEP_FRAC = 0.97  # reduce |PA duty| by 3% (weaker cooling)
MAX_STEPS = 2
RATE_ERR_MAX = 1e-4


@dataclass
class SnapshotMetrics:
    label: str
    pa1_goal: float | None
    pa1_disp: float | None
    cond_q: float | None
    naphtha_err: float | None
    kero_err: float | None
    naphtha_d86_95: float | None
    kero_d86_95: float | None
    kero_flash: float | None
    gap: float | None
    dof: int | None
    physical: bool
    converged: bool
    state: str


def _find(state, needle: str):
    for s in state.specs:
        if needle.lower() in s.name.lower():
            return s
    return None


def _disp(spec):
    if spec is None:
        return None
    if spec.goal_display is not None:
        return float(spec.goal_display)
    if spec.goal_value is not None:
        return float(spec.goal_value)
    return None


def _metrics(api, assist, label: str) -> SnapshotMetrics:
    st, dg = assist.diagnose_column(COLUMN)
    case = load_case_config()
    pqs = build_product_quality_state(st, case, columns=api)
    by_id = {r.target_id: r for r in pqs.readings}
    n = _find(st, NAPHTHA)
    k = _find(st, KERO)
    p = _find(st, PA1)
    gap_r = by_id.get("KERO_DIESEL_GAP")
    return SnapshotMetrics(
        label=label,
        pa1_goal=float(p.goal_value) if p and p.goal_value is not None else None,
        pa1_disp=_disp(p),
        cond_q=float(st.condenser_duty) if st.condenser_duty is not None else None,
        naphtha_err=float(n.error) if n and n.error is not None else None,
        kero_err=float(k.error) if k and k.error is not None else None,
        naphtha_d86_95=_d86_at_percent(api, "Naphtha", 95.0),
        kero_d86_95=_d86_at_percent(api, "Kerosene", 95.0),
        kero_flash=_flash_point_display(api, "Kerosene"),
        gap=float(gap_r.value) if gap_r and gap_r.value is not None else None,
        dof=st.degrees_of_freedom,
        physical=bool(st.physical_solution),
        converged=bool(st.appears_converged),
        state=dg.engineering_state.value,
    )


def _rates_ok(m: SnapshotMetrics) -> bool:
    if m.naphtha_err is None or m.kero_err is None:
        return False
    return abs(m.naphtha_err) < RATE_ERR_MAX and abs(m.kero_err) < RATE_ERR_MAX


def _hard_q_ok(m: SnapshotMetrics) -> bool:
    if m.naphtha_d86_95 is None or m.kero_d86_95 is None or m.kero_flash is None:
        return False
    return m.naphtha_d86_95 <= 356.0 + 2 and m.kero_d86_95 <= 518.0 + 2 and m.kero_flash >= 100.0 - 2


def _net_abs(m: SnapshotMetrics) -> float | None:
    if m.pa1_disp is None or m.cond_q is None:
        return None
    return abs(m.pa1_disp) + abs(m.cond_q)


def judge(before: SnapshotMetrics, after: SnapshotMetrics) -> tuple[str, str]:
    if not after.physical or not after.converged or after.dof not in (0, None):
        return "REVERSE", "not physical/converged/DOF"
    if not _rates_ok(after):
        return "REVERSE", "naphtha/kero rate hold broken"
    if not _hard_q_ok(after):
        return "REVERSE", "hard quality miss"
    nb, na = _net_abs(before), _net_abs(after)
    if nb is not None and na is not None:
        dnet = na - nb
        dpa = (abs(after.pa1_disp) - abs(before.pa1_disp)) if after.pa1_disp and before.pa1_disp else None
        dc = (abs(after.cond_q) - abs(before.cond_q)) if after.cond_q and before.cond_q else None
        if dnet < -1e3:
            return "KEEP", f"net |PA1|+|Cond| down ({dnet:.4g}); dPA={dpa}; dCond={dc}"
        if dpa is not None and dc is not None and abs(dpa + dc) < abs(dpa) * 0.15:
            return "KEEP_SHIFT", f"heat shift (dPA={dpa:.4g}, dCond={dc:.4g}, dnet={dnet:.4g}) — not clear utility win"
        return "KEEP_STABLE", f"rates+Q OK; dnet={dnet:.4g} (document, not declare optimum)"
    return "KEEP_STABLE", "rates+Q OK; net metric incomplete"


def main() -> int:
    out_dir = ROOT / "docs" / "studies"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    hysys = HysysController()
    hysys.connect()
    api = ColumnController(hysys)
    assist = ConvergenceAssistant(api, ConvergenceLimits(), default_cdu_targets())

    print("=" * 72)
    print("ENERGY STUDY Campaign A — PA_1 with Naphtha+Kero holds")
    print("=" * 72)

    snap = api.snapshot(COLUMN)
    rows: list[dict] = []
    baseline = _metrics(api, assist, "BASELINE")
    rows.append({"phase": "BASELINE", "metrics": asdict(baseline), "verdict": "—", "reason": "freeze"})
    print(
        f"BASELINE state={baseline.state} PA1={baseline.pa1_disp} CondQ={baseline.cond_q} "
        f"N95={baseline.naphtha_d86_95} K95={baseline.kero_d86_95} flash={baseline.kero_flash}"
    )

    st0 = api.inspect(COLUMN)
    n = _find(st0, NAPHTHA)
    k = _find(st0, KERO)
    p = _find(st0, PA1)
    if not n or not n.is_active or not k or not k.is_active:
        print("ABORT: Naphtha/Kero Prod Flow must be Active for this study.")
        api.restore(snap)
        return 1
    if not p or p.goal_value is None:
        print("ABORT: PA_1_Duty missing.")
        api.restore(snap)
        return 1

    current = baseline
    kept_point = baseline
    for i in range(1, MAX_STEPS + 1):
        before = current
        new_goal = float(p.goal_value) * STEP_FRAC
        print(f"\n[STEP {i}] PA_1_Duty Goal {p.goal_value} -> {new_goal} ({STEP_FRAC}× |duty|)")
        api.set_spec_goal(COLUMN, p.name, new_goal)
        api.run_column(COLUMN)
        after = _metrics(api, assist, f"STEP_{i}")
        verdict, reason = judge(before, after)
        print(f"  after PA1={after.pa1_disp} CondQ={after.cond_q} state={after.state}")
        print(f"  rates ok={_rates_ok(after)} hardQ ok={_hard_q_ok(after)} -> {verdict}: {reason}")
        rows.append(
            {
                "phase": f"STEP_{i}",
                "metrics": asdict(after),
                "verdict": verdict,
                "reason": reason,
                "goal_written": new_goal,
            }
        )
        if verdict.startswith("REVERSE"):
            print("  Restoring previous kept point...")
            api.restore(snap)
            # re-apply kept_point goal if we had kept steps inside snap... snap is baseline
            # For multi-step: restore snap then re-apply last kept goal
            if kept_point.label != "BASELINE" and kept_point.pa1_goal is not None:
                api.set_spec_goal(COLUMN, p.name, kept_point.pa1_goal)
                api.run_column(COLUMN)
            current = _metrics(api, assist, f"AFTER_REVERSE_{i}")
            p = _find(api.inspect(COLUMN), PA1)
            break
        kept_point = after
        current = after
        p = _find(api.inspect(COLUMN), PA1)
        if p is None or p.goal_value is None:
            break

    print("\n[RESTORE] Returning to baseline snapshot for clean HYSYS leave-behind...")
    api.restore(snap)
    api.run_column(COLUMN)
    final = _metrics(api, assist, "RESTORED_BASELINE")
    rows.append({"phase": "RESTORED", "metrics": asdict(final), "verdict": "—", "reason": "study restore"})

    payload = {
        "study": "T-100 Campaign A energy — PA_1",
        "when_utc": stamp,
        "holds": ["Naphtha Prod Rate", "Kero_SS Prod Flow"],
        "mv": "PA_1_Duty",
        "step_frac": STEP_FRAC,
        "max_steps": MAX_STEPS,
        "iterations": rows,
        "note": "Case restored to pre-study snapshot; not auto-saved. Heat-shift KEEP ≠ net utility win.",
    }
    json_path = out_dir / f"energy_pa1_run_{stamp}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_path = out_dir / f"energy_pa1_run_{stamp}.md"
    lines = [
        f"# Energy study run — PA_1 ({stamp} UTC)",
        "",
        "**Column:** T-100  ",
        "**Holds:** Naphtha Prod Rate, Kero_SS Prod Flow  ",
        "**MV:** PA_1_Duty × 0.97 per step (weaker |duty|)  ",
        "**Leave-behind:** restored baseline snapshot (not saved)",
        "",
        "## Iterations",
        "",
        "| Phase | State | PA1 disp | CondQ | N95 F | K95 F | Flash F | Gap F | Verdict |",
        "|-------|-------|----------|-------|-------|-------|---------|-------|---------|",
    ]
    for r in rows:
        m = r["metrics"]
        lines.append(
            "| {phase} | {state} | {pa1} | {cond} | {n95} | {k95} | {fl} | {gap} | {verdict} |".format(
                phase=r["phase"],
                state=m.get("state"),
                pa1=_fmt(m.get("pa1_disp")),
                cond=_fmt(m.get("cond_q")),
                n95=_fmt(m.get("naphtha_d86_95")),
                k95=_fmt(m.get("kero_d86_95")),
                fl=_fmt(m.get("kero_flash")),
                gap=_fmt(m.get("gap")),
                verdict=r.get("verdict"),
            )
        )
        if r.get("reason"):
            lines.append(f"| | | | | | | | | *{r['reason']}* |")
    lines.extend(
        [
            "",
            "## Lenses (this run)",
            "",
            "- **Production:** N+K rate holds checked each step.",
            "- **Quality:** hard D86/flash vs practice limits.",
            "- **Energy:** |PA1|+|Cond|; KEEP_SHIFT = yin–yang heat move, not declared optimum.",
            "",
            f"Raw JSON: `{json_path.name}`",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote {md_path.relative_to(ROOT)}")
    print(f"Wrote {json_path.relative_to(ROOT)}")

    try:
        hysys.disconnect()
    except Exception:
        pass
    return 0


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


if __name__ == "__main__":
    raise SystemExit(main())
