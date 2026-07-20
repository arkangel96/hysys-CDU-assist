"""
COM discovery for a HYSYS column / stripper operation.

Goal: map what the external convergence assistant can actually read/write
on the installed HYSYS version before building the distillation module.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

OUTPUT = Path(__file__).resolve().parent / "column_com_discovery.json"


def safe_getattr(obj: Any, name: str) -> tuple[bool, Any, str]:
    try:
        value = getattr(obj, name)
        return True, value, ""
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def describe_value(value: Any) -> dict[str, Any]:
    info: dict[str, Any] = {"python_type": type(value).__name__}
    try:
        if hasattr(value, "Count") and not isinstance(value, (str, bytes)):
            info["count"] = int(value.Count)
        if hasattr(value, "Value"):
            try:
                info["value"] = value.Value
            except Exception as exc:
                info["value_error"] = str(exc)
        if hasattr(value, "Name"):
            try:
                info["name"] = str(value.Name)
            except Exception:
                pass
        # Scalars / strings
        if isinstance(value, (bool, int, float, str)):
            info["repr"] = value
        elif value is None:
            info["repr"] = None
        else:
            text = str(value)
            if len(text) < 120 and not text.startswith("<"):
                info["repr"] = text
    except Exception as exc:
        info["describe_error"] = str(exc)
    return info


def probe_members(obj: Any, label: str, member_names: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {"object": label, "members": {}}
    for name in member_names:
        ok, value, err = safe_getattr(obj, name)
        if not ok:
            result["members"][name] = {"available": False, "error": err}
            continue
        entry: dict[str, Any] = {"available": True, **describe_value(value)}
        # If it looks like a collection, list first few item names/types
        if "count" in entry:
            items = []
            count = int(entry["count"])
            for i in range(min(count, 25)):
                item = None
                item_err = ""
                for index in (i, i + 1):
                    try:
                        item = value.Item(index)
                        break
                    except Exception as exc:
                        item_err = str(exc)
                if item is None:
                    items.append({"index": i, "error": item_err})
                    continue
                item_info: dict[str, Any] = {"index": i, "type": type(item).__name__}
                for attr in (
                    "Name", "TypeName", "OperType", "Active", "IsActive",
                    "Specified", "IsSpecified", "Estimate", "IsEstimate",
                    "CurrentValue", "SpecifiedValue", "Value", "Target",
                    "Status", "WeightedError", "Error", "Tolerance",
                ):
                    ok2, val2, _ = safe_getattr(item, attr)
                    if ok2:
                        try:
                            if hasattr(val2, "Value"):
                                val2 = val2.Value
                            item_info[attr] = val2 if not hasattr(val2, "__call__") else str(val2)
                        except Exception as exc:
                            item_info[attr] = f"<error {exc}>"
                items.append(item_info)
            entry["items_preview"] = items
        result["members"][name] = entry
    return result


COLUMN_CANDIDATES = [
    # Identity / structure
    "Name", "TypeName", "OperType", "TaggedName",
    "NumberOfStages", "NoOfStages", "NStages", "Stages",
    "FeedStage", "FeedStages", "FeedLocation", "Feeds",
    "ProductStages", "Products",
    "CondenserType", "Condenser", "Reboiler", "ReboilerType",
    "PressureProfile", "TemperatureProfile",
    # Connections
    "AttachedFeeds", "AttachedProducts", "FeedStreams", "ProductStreams",
    "Inlet", "Outlet", "Feed", "OvhdVapour", "OvhdLiquid", "BottomsLiquid",
    "CondenserDuty", "ReboilerDuty",
    # Specs / DOF / convergence
    "Specifications", "ColumnSpecifications", "Specs",
    "ActiveSpecs", "DegreesOfFreedom", "DOF", "DOFAvailable",
    "IsConverged", "Converged", "Convergence", "Status", "SolveStatus",
    "Residual", "Residuals", "Error", "MaxError", "WeightedError",
    "Tolerance", "Tolerances",
    # Profiles / internals
    "StageTemperature", "StagePressure", "StageNetLiquidFlow", "StageNetVapourFlow",
    "StageLiquidFlow", "StageVapourFlow", "StageFeedFlow",
    "Temperature", "Pressure", "LiquidFlow", "VapourFlow",
    "ColumnFlowsheet", "Flowsheet", "SubFlowsheet",
    # Solver / estimates
    "Solver", "Estimate", "Estimates", "InitialEstimates",
    "CanSolve", "Solving",
    # Common stripper / column UI fields
    "RefluxRatio", "RefluxRate", "BoilupRatio", "BoilupRate",
    "DistillateRate", "BottomsRate", "OverheadRate",
    "CondenserPressure", "ReboilerPressure",
    "TopPressure", "BottomPressure",
]


SPEC_ITEM_CANDIDATES = [
    "Name", "Type", "TypeName", "Active", "IsActive", "Specified", "IsSpecified",
    "Estimate", "IsEstimate", "CurrentValue", "SpecifiedValue", "Value",
    "Target", "Goal", "Status", "WeightedError", "Error", "Tolerance",
    "LowerBound", "UpperBound", "Unit", "Units",
]


STAGE_PROFILE_CANDIDATES = [
    "Temperature", "Pressure", "NetLiqFlow", "NetVapFlow",
    "LiquidFlow", "VapourFlow", "FeedFlow", "Duty",
]


def get_operation(flowsheet: Any, wanted: str) -> Any:
    ops = flowsheet.Operations
    for i in range(int(ops.Count)):
        for index in (i, i + 1):
            try:
                op = ops.Item(index)
                if str(op.Name).strip().lower() == wanted.strip().lower():
                    return op
            except Exception:
                continue
    raise RuntimeError(f"Operation not found: {wanted}")


def try_dir_com(obj: Any) -> list[str]:
    """Best-effort member listing; COM often has no useful __dir__."""
    names: set[str] = set()
    try:
        for name in dir(obj):
            if not name.startswith("_"):
                names.add(name)
    except Exception:
        pass
    return sorted(names)


def main() -> int:
    column_name = sys.argv[1] if len(sys.argv) > 1 else "SW Stripper"
    report: dict[str, Any] = {
        "column_name": column_name,
        "notes": [
            "This is a live COM probe against the open HYSYS case.",
            "Use available=true members as the basis for the column module.",
            "Degrees of freedom must stay zero when the active spec set is already complete.",
        ],
    }

    try:
        import pythoncom
        import win32com.client
    except ImportError as exc:
        print("pywin32 required:", exc)
        return 1

    pythoncom.CoInitialize()
    app = None
    for prog_id in ("HYSYS.Application", "HYSYS.Application.V15"):
        try:
            app = win32com.client.GetActiveObject(prog_id)
            break
        except Exception:
            continue
    if app is None:
        print("HYSYS is not running / no active COM instance.")
        return 1

    case = None
    for getter in (lambda: app.ActiveDocument, lambda: app.SimulationCases.Item(0)):
        try:
            case = getter()
            if case is not None:
                break
        except Exception:
            continue
    if case is None:
        print("No open HYSYS case.")
        return 1

    report["case_name"] = str(getattr(case, "Name", ""))
    flowsheet = case.Flowsheet
    column = get_operation(flowsheet, column_name)
    report["column_com_type"] = type(column).__name__
    report["dir_members"] = try_dir_com(column)
    report["column_probe"] = probe_members(column, column_name, COLUMN_CANDIDATES)

    # Deeper: ColumnFlowsheet / SubFlowsheet if present
    for nested_name in ("ColumnFlowsheet", "Flowsheet", "SubFlowsheet"):
        ok, nested, err = safe_getattr(column, nested_name)
        if not ok or nested is None:
            continue
        nested_probe = probe_members(
            nested,
            f"{column_name}.{nested_name}",
            [
                "Operations", "MaterialStreams", "EnergyStreams",
                "Specifications", "Solver", "DegreesOfFreedom",
            ] + COLUMN_CANDIDATES,
        )
        report[f"nested_{nested_name}"] = nested_probe

        # Look for SpecOp / ColumnOp inside subflowsheet
        ok_ops, ops, _ = safe_getattr(nested, "Operations")
        if ok_ops:
            op_names = []
            for i in range(int(ops.Count)):
                for index in (i, i + 1):
                    try:
                        op = ops.Item(index)
                        op_names.append(str(op.Name))
                        # Probe likely solver / spec containers
                        if any(k in str(op.Name).lower() for k in ("spec", "column", "main", "tower")):
                            report[f"sub_op_{op.Name}"] = probe_members(
                                op,
                                f"{nested_name}/{op.Name}",
                                COLUMN_CANDIDATES + SPEC_ITEM_CANDIDATES,
                            )
                        break
                    except Exception:
                        continue
            report[f"{nested_name}_operation_names"] = op_names

    # Direct Specifications collection deep dive
    for spec_attr in ("Specifications", "ColumnSpecifications", "Specs"):
        ok, specs, _ = safe_getattr(column, spec_attr)
        if not ok or specs is None:
            continue
        deep = {"attr": spec_attr, "items": []}
        try:
            count = int(specs.Count)
        except Exception:
            continue
        for i in range(count):
            item = None
            for index in (i, i + 1):
                try:
                    item = specs.Item(index)
                    break
                except Exception:
                    continue
            if item is None:
                continue
            deep["items"].append(probe_members(item, f"{spec_attr}[{i}]", SPEC_ITEM_CANDIDATES)["members"])
        report[f"specs_deep_{spec_attr}"] = deep

    OUTPUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUTPUT}")

    # Human summary
    available = [
        name
        for name, meta in report["column_probe"]["members"].items()
        if meta.get("available")
    ]
    missing = [
        name
        for name, meta in report["column_probe"]["members"].items()
        if not meta.get("available")
    ]
    print(f"\nColumn: {column_name}")
    print(f"Available members ({len(available)}):")
    for name in available:
        meta = report["column_probe"]["members"][name]
        extra = ""
        if "count" in meta:
            extra = f" count={meta['count']}"
        elif "value" in meta:
            extra = f" value={meta['value']}"
        elif "repr" in meta:
            extra = f" = {meta['repr']}"
        print(f"  OK  {name}{extra}")
    print(f"\nUnavailable candidates ({len(missing)}): {', '.join(missing[:40])}")
    if len(missing) > 40:
        print(f"  ... +{len(missing) - 40} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
