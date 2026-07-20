"""Quick live integration test against a running/open HYSYS case."""
from __future__ import annotations

import sys
from pathlib import Path

from hysys_api import HysysController, HysysError


def main() -> int:
    controller = HysysController()
    case_path = sys.argv[1] if len(sys.argv) > 1 else None

    print("=" * 60)
    print("HYSYS Automation Studio — Live Integration Test")
    print("=" * 60)

    try:
        print("\n[1/6] Connecting to HYSYS...")
        controller.connect(case_path)
        print("      Connected successfully.")
        if case_path:
            print(f"      Opened case: {case_path}")
    except HysysError as exc:
        print(f"      FAILED: {exc}")
        print("\nTip: Open a case in HYSYS first, or pass a .hsc path:")
        print("  python test_hysys_live.py C:\\path\\to\\case.hsc")
        return 1

    try:
        print("\n[2/6] Reading components...")
        components = controller.get_component_names()
        print(f"      Found {len(components)} components: {', '.join(components[:8])}")
        if len(components) > 8:
            print(f"      ... and {len(components) - 8} more")

        print("\n[3/6] Reading material streams...")
        streams = controller.get_stream_objects()
        print(f"      Found {len(streams)} streams: {', '.join(sorted(streams)[:10])}")
        if len(streams) > 10:
            print(f"      ... and {len(streams) - 10} more")

        print("\n[4/6] Reading stream data (first 3 streams)...")
        for name in sorted(streams)[:3]:
            data = controller.get_stream_data(streams[name])
            comp_preview = ", ".join(
                f"{k}={v:.4g}" for k, v in list(data.composition.items())[:3]
            )
            print(
                f"      {data.name}: T={data.temperature}, P={data.pressure}, "
                f"F={data.molar_flow}, comp=[{comp_preview}]"
            )

        print("\n[5/6] Reading operations...")
        operations = controller.get_operations()
        print(f"      Found {len(operations)} operations")
        for op in operations[:5]:
            solved = "?" if op.is_solved is None else op.is_solved
            print(f"      - {op.name} ({op.operation_type}) solved={solved}")
        if len(operations) > 5:
            print(f"      ... and {len(operations) - 5} more")

        print("\n[6/6] Exporting to test export...")
        from exporter import export_workbook

        out = Path(__file__).resolve().parent / "HYSYS_Live_Test_Export.xlsx"
        stream_data = [controller.get_stream_data(s) for s in streams.values()]
        export_workbook(str(out), stream_data, operations)
        print(f"      Exported to: {out}")

        print("\n" + "=" * 60)
        print("ALL LIVE TESTS PASSED")
        print("=" * 60)
        return 0

    except Exception as exc:
        print(f"\nFAILED during data read: {exc}")
        return 1
    finally:
        controller.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
