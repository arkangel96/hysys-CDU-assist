"""Run live column assist loop from CLI (same engine as GUI Assist Loop)."""
from __future__ import annotations

import sys

from column_api import ColumnController
from column_engine import ConvergenceAssistant, score_state
from column_models import ConvergenceLimits
from hysys_api import HysysController


def main() -> int:
    column_name = sys.argv[1] if len(sys.argv) > 1 else "SW Stripper"
    max_iter = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    hysys = HysysController()
    hysys.connect()
    columns = ColumnController(hysys)
    limits = ConvergenceLimits(max_iterations=max_iter)
    assistant = ConvergenceAssistant(columns, limits)

    state, diagnosis = assistant.diagnose_column(column_name)
    print(f"BEFORE: DOF={state.degrees_of_freedom} max_err={state.max_active_spec_error:.4g} "
          f"score={score_state(state):.4g} converged={state.appears_converged}")
    print(f"  RR goal={state.specs[0].goal_value if state.specs else '?'} reflux={state.reflux_ratio}")
    print(f"  Diagnosis: {diagnosis.recommended_strategy} - {diagnosis.summary}")
    print(f"\nRunning Assist Loop (max {max_iter} trials)...\n")

    results = assistant.assist(column_name, max_iterations=max_iter, dry_run=False)
    for i, result in enumerate(results, 1):
        print(f"[{i}] {result.message}")

    state, diagnosis = assistant.diagnose_column(column_name)
    print(f"\nAFTER: DOF={state.degrees_of_freedom} max_err={state.max_active_spec_error:.4g} "
          f"score={score_state(state):.4g} converged={state.appears_converged}")
    print(f"  RR goal=", end="")
    for spec in state.specs:
        if "reflux ratio" in spec.name.lower() and spec.is_active:
            print(f"{spec.goal_value} current={spec.current_value} err={spec.error}")
            break
    for spec in state.specs:
        if spec.is_active and ("nh3" in spec.name.lower() or "ammonia" in spec.name.lower()):
            print(f"  NH3 goal={spec.goal_value} current={spec.current_value} err={spec.error}")
    print(f"  Cond Q={state.condenser_duty}  Reb Q={state.reboiler_duty}")
    return 0 if state.appears_converged else 1


if __name__ == "__main__":
    raise SystemExit(main())
