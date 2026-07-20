"""Live smoke test for the column convergence assistant (read + dry-run)."""
from __future__ import annotations

import sys

from column_api import ColumnController
from column_engine import ConvergenceAssistant, diagnose, score_state
from column_models import ConvergenceLimits
from hysys_api import HysysController


def main() -> int:
    column_name = sys.argv[1] if len(sys.argv) > 1 else "SW Stripper"
    hysys = HysysController()
    hysys.connect()
    columns = ColumnController(hysys)
    assistant = ConvergenceAssistant(columns, ConvergenceLimits())

    print("Columns:", columns.list_columns())
    state, diagnosis = assistant.diagnose_column(column_name)
    print(f"\nInspect: {state.name} / {state.flowsheet_tag}")
    print(f"  stages={state.number_of_stages} feed_stage={state.feed_stage}")
    print(f"  DOF={state.degrees_of_freedom} reflux={state.reflux_ratio}")
    print(f"  max_active_err={state.max_active_spec_error:.4g} score={score_state(state):.4g}")
    print(f"  appears_converged={state.appears_converged}")
    print(f"  Cond Q={state.condenser_duty}  Reb Q={state.reboiler_duty}")
    print(f"  Off-gas F={state.overhead_molar_flow}  Bottoms F={state.bottoms_molar_flow}")
    print("\nSpecs:")
    for spec in state.specs:
        print(
            f"  - {spec.name}: active={spec.is_active} goal={spec.goal_value} "
            f"current={spec.current_value} err={spec.error} role={spec.role.value}"
        )
    print(f"\nDiagnosis: {diagnosis.severity} / {diagnosis.recommended_strategy}")
    print(f"  {diagnosis.summary}")
    for detail in diagnosis.details:
        print(f"  - {detail}")

    trial = assistant.run_one_trial(column_name, dry_run=True)
    print(f"\nDry-run trial: {trial.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
