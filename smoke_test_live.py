"""Quick smoke test: connect → columns → inspect → diagnose → PE board."""
from __future__ import annotations

import sys

from column_engine import ConvergenceAssistant, format_pe_board
from column_models import ConvergenceLimits
from column_api import ColumnController
from hysys_api import HysysController, HysysError


def main() -> int:
    print("=" * 60)
    print("HYSYS Studio — live smoke test")
    print("=" * 60)

    controller = HysysController()
    try:
        print("\n[1] Connect")
        controller.connect(None)
        print("    OK")
    except HysysError as exc:
        print(f"    FAIL: {exc}")
        print("    Open a HYSYS case first, then rerun.")
        return 1

    column_api = ColumnController(controller)
    assistant = ConvergenceAssistant(column_api, ConvergenceLimits())

    try:
        print("\n[2] List columns")
        columns = column_api.list_columns()
        print(f"    {columns}")
        if not columns:
            print("    FAIL: no columns in case")
            return 1
        name = "SW Stripper" if "SW Stripper" in columns else columns[0]
        print(f"    Using: {name}")

        print("\n[3] Inspect")
        state = assistant.inspect(name)
        print(
            f"    DOF={state.degrees_of_freedom}  "
            f"converged={state.appears_converged}  "
            f"specs={len(state.specs)}  "
            f"stages={state.number_of_stages}"
        )
        for spec in state.specs[:8]:
            kind = "ACTIVE" if spec.is_active else "est"
            print(
                f"      [{kind}] {spec.name}: "
                f"goal={spec.goal_value} current={spec.current_value} err={spec.error}"
            )

        print("\n[4] Diagnose + PE board")
        state, diagnosis = assistant.diagnose_column(name)
        print(f"    severity={diagnosis.severity}")
        print(f"    engineering_state={diagnosis.engineering_state}")
        print()
        print(format_pe_board(state, diagnosis))

        print("\n[5] FINAL_TARGET snapshot")
        from column_models import default_sw_stripper_targets
        from column_engine import evaluate_final_targets

        for status in evaluate_final_targets(state, default_sw_stripper_targets()):
            print(f"    {status}")

        print("\n" + "=" * 60)
        print("SMOKE TEST PASS")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"\nFAIL: {type(exc).__name__}: {exc}")
        return 1
    finally:
        try:
            controller.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
