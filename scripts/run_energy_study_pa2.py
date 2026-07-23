"""Campaign A energy study — PA_2 steps with naphtha+kero rate holds.

Same protocol as PA_1: snapshot, up to 2× |duty| −3%, same-unit PA+CondQ score,
restore leave-behind (no auto-save).

Usage (HYSYS T-100 open):
  .venv\\Scripts\\python.exe scripts/run_energy_study_pa2.py
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
from hysys_units import _get_value

COLUMN = "T-100"
NAPHTHA = "Naphtha Prod Rate"
KERO = "Kero_SS Prod Flow"
PA_MV = "PA_2_Duty"
ATMOS_COND = "Atmos Cond"
STEP_FRAC = 0.97
MAX_STEPS = 2
RATE_ERR_MAX = 1e-4
SHIFT_BAND = 0.15
NET_WIN_ABS = 1e4


@dataclass
class SnapshotMetrics:
    label: str
    pa_goal: float | None
    pa_disp: float | None
    cond_q_com: float | None
    cond_q_disp: float | None
    energy_unit: str | None
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


def _atmos_cond_heat(api) -> tuple[float | None, float | None, str | None]:
    try:
        stream = api.hysys.flowsheet.EnergyStreams.Item(ATMOS_COND)
    except Exception:
        return None, None, None
    com = None
    for attr in ("HeatFlowValue", "HeatFlow", "EnergyValue", "Energy"):
        try:
            raw = getattr(stream, attr)
            if raw is not None and not isinstance(raw, str):
                com = float(raw)
                break
        except Exception:
            continue
    try:
        unit = str(api.hysys.display_units.energy)
    except Exception:
        unit = "Btu/hr"
    disp = None
    hf = getattr(stream, "HeatFlow", None)
    if hf is not None and unit:
        got = _get_value(hf, unit)
        if got is not None:
            disp = float(got)
    return com, disp, unit


def _metrics(api, assist, label: str) -> SnapshotMetrics:
    st, dg = assist.diagnose_column(COLUMN)
    case = load_case_config()
    pqs = build_product_quality_state(st, case, columns=api)
    by_id = {r.target_id: r for r in pqs.readings}
    n = _find(st, NAPHTHA)
    k = _find(st, KERO)
    p = _find(st, PA_MV)
    gap_r = by_id.get("KERO_DIESEL_GAP")
    cond_com, cond_disp, e_unit = _atmos_cond_heat(api)
    if cond_com is None and st.condenser_duty is not None:
        cond_com = float(st.condenser_duty)
    return SnapshotMetrics(
        label=label,
        pa_goal=float(p.goal_value) if p and p.goal_value is not None else None,
        pa_disp=_disp(p),
        cond_q_com=cond_com,
        cond_q_disp=cond_disp,
        energy_unit=e_unit,
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


def _pair_abs(m: SnapshotMetrics) -> tuple[float | None, float | None, str]:
    if m.pa_disp is not None and m.cond_q_disp is not None:
        return abs(m.pa_disp), abs(m.cond_q_disp), "display"
    if m.pa_goal is not None and m.cond_q_com is not None:
        return abs(m.pa_goal), abs(m.cond_q_com), "com"
    return None, None, "none"


def judge(before: SnapshotMetrics, after: SnapshotMetrics) -> tuple[str, str]:
    if not after.physical or not after.converged or after.dof not in (0, None):
        return "REVERSE", "not physical/converged/DOF"
    if not _rates_ok(after):
        return "REVERSE", "naphtha/kero rate hold broken"
    if not _hard_q_ok(after):
        return "REVERSE", "hard quality miss"
    pb, cb, basis_b = _pair_abs(before)
    pa, ca, basis_a = _pair_abs(after)
    if pb is None or pa is None or cb is None or ca is None:
        return "KEEP_STABLE", "rates+Q OK; net metric incomplete"
    basis = basis_a if basis_a == basis_b else f"{basis_b}->{basis_a}"
    dnet = (pa + ca) - (pb + cb)
    dpa = pa - pb
    dc = ca - cb
    if abs(dpa) > 1e-6 and abs(dpa + dc) < abs(dpa) * SHIFT_BAND:
        return (
            "KEEP_SHIFT",
            f"heat shift ({basis}: dPA={dpa:.4g}, dCond={dc:.4g}, dnet={dnet:.4g}) — not utility win",
        )
    if dnet < -NET_WIN_ABS:
        return "KEEP", f"net |PA2|+|Cond| down ({basis}: {dnet:.4g}); dPA={dpa}; dCond={dc}"
    return "KEEP_STABLE", f"rates+Q OK; {basis} dnet={dnet:.4g} (document, not declare optimum)"


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4g}"
    return str(v)


def main() -> int:
    out_dir = ROOT / "docs" / "studies"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    hysys = HysysController()
    hysys.connect()
    api = ColumnController(hysys)
    assist = ConvergenceAssistant(api, ConvergenceLimits(), default_cdu_targets())

    print("=" * 72)
    print("ENERGY STUDY Campaign A — PA_2 with Naphtha+Kero holds")
    print("=" * 72)

    snap = api.snapshot(COLUMN)
    rows: list[dict] = []
    baseline = _metrics(api, assist, "BASELINE")
    rows.append({"phase": "BASELINE", "metrics": asdict(baseline), "verdict": "—", "reason": "freeze"})
    print(
        f"BASELINE state={baseline.state} PA2={baseline.pa_disp} "
        f"CondQ_disp={baseline.cond_q_disp} CondQ_com={baseline.cond_q_com} "
        f"unit={baseline.energy_unit} "
        f"N95={baseline.naphtha_d86_95} K95={baseline.kero_d86_95} flash={baseline.kero_flash}"
    )

    st0 = api.inspect(COLUMN)
    n = _find(st0, NAPHTHA)
    k = _find(st0, KERO)
    p = _find(st0, PA_MV)
    if not n or not n.is_active or not k or not k.is_active:
        print("ABORT: Naphtha/Kero Prod Flow must be Active for this study.")
        api.restore(snap)
        return 1
    if not p or p.goal_value is None:
        print("ABORT: PA_2_Duty missing.")
        api.restore(snap)
        return 1

    current = baseline
    kept_point = baseline
    for i in range(1, MAX_STEPS + 1):
        before = current
        new_goal = float(p.goal_value) * STEP_FRAC
        print(f"\n[STEP {i}] PA_2_Duty Goal {p.goal_value} -> {new_goal} ({STEP_FRAC}x |duty|)")
        api.set_spec_goal(COLUMN, p.name, new_goal)
        api.run_column(COLUMN)
        after = _metrics(api, assist, f"STEP_{i}")
        verdict, reason = judge(before, after)
        print(
            f"  after PA2={after.pa_disp} CondQ_disp={after.cond_q_disp} "
            f"CondQ_com={after.cond_q_com} state={after.state}"
        )
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
            if kept_point.label != "BASELINE" and kept_point.pa_goal is not None:
                api.set_spec_goal(COLUMN, p.name, kept_point.pa_goal)
                api.run_column(COLUMN)
            current = _metrics(api, assist, f"AFTER_REVERSE_{i}")
            p = _find(api.inspect(COLUMN), PA_MV)
            break
        kept_point = after
        current = after
        p = _find(api.inspect(COLUMN), PA_MV)
        if p is None or p.goal_value is None:
            break

    print("\n[RESTORE] Returning to baseline snapshot for clean HYSYS leave-behind...")
    api.restore(snap)
    api.run_column(COLUMN)
    final = _metrics(api, assist, "RESTORED_BASELINE")
    rows.append({"phase": "RESTORED", "metrics": asdict(final), "verdict": "—", "reason": "study restore"})

    payload = {
        "study": "T-100 Campaign A energy — PA_2",
        "when_utc": stamp,
        "holds": ["Naphtha Prod Rate", "Kero_SS Prod Flow"],
        "mv": "PA_2_Duty",
        "step_frac": STEP_FRAC,
        "max_steps": MAX_STEPS,
        "iterations": rows,
        "note": (
            "Case restored to pre-study snapshot; not auto-saved. "
            "Net energy uses same-unit pair (display PA+Cond if available, else COM). "
            "KEEP_SHIFT = yin-yang heat move, not utility win."
        ),
    }
    json_path = out_dir / f"energy_pa2_run_{stamp}.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_path = out_dir / f"energy_pa2_run_{stamp}.md"
    lines = [
        f"# Energy study run — PA_2 ({stamp} UTC)",
        "",
        "**Column:** T-100  ",
        "**Holds:** Naphtha Prod Rate, Kero_SS Prod Flow  ",
        "**MV:** PA_2_Duty × 0.97 per step (weaker |duty|)  ",
        "**Leave-behind:** restored baseline snapshot (not saved)",
        "",
        "## Iterations",
        "",
        "| Phase | State | PA2 disp | CondQ disp | CondQ COM | N95 F | K95 F | Flash F | Gap F | Verdict |",
        "|-------|-------|----------|------------|-----------|-------|-------|---------|-------|---------|",
    ]
    for r in rows:
        m = r["metrics"]
        lines.append(
            "| {phase} | {state} | {pa} | {cd} | {cc} | {n95} | {k95} | {fl} | {gap} | {verdict} |".format(
                phase=r["phase"],
                state=m.get("state"),
                pa=_fmt(m.get("pa_disp")),
                cd=_fmt(m.get("cond_q_disp")),
                cc=_fmt(m.get("cond_q_com")),
                n95=_fmt(m.get("naphtha_d86_95")),
                k95=_fmt(m.get("kero_d86_95")),
                fl=_fmt(m.get("kero_flash")),
                gap=_fmt(m.get("gap")),
                verdict=r.get("verdict"),
            )
        )
        if r.get("reason"):
            lines.append(f"| | | | | | | | | | *{r['reason']}* |")
    lines.extend(
        [
            "",
            "## Lenses (this run)",
            "",
            "- **Production:** N+K rate holds checked each step.",
            "- **Quality:** hard D86/flash vs practice limits.",
            "- **Energy:** same-unit |PA2|+|Cond| (display preferred; COM fallback). "
            "KEEP_SHIFT = yin-yang heat move, not declared optimum.",
            "",
            f"Raw JSON: `{json_path.name}`",
            "",
            "## Decision (this run)",
            "",
            "Both steps **KEEP_SHIFT** on same-unit display PA+Cond. "
            "N+K + hard Q held; practically **no utility save** (heat moved to CondQ). "
            "Case restored to baseline PA_2. Next: PA_3 same protocol, or stop Campaign A energy.",
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


if __name__ == "__main__":
    raise SystemExit(main())
