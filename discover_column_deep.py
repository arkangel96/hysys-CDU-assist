"""
Deep probe: SW Stripper ColumnFlowsheet specs, Main TS profiles,
Condenser/Reboiler duties & pressures, and write-capability checks.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

OUT = Path(__file__).resolve().parent / "column_com_deep.json"


def ok_get(obj: Any, name: str):
    try:
        return True, getattr(obj, name), ""
    except Exception as exc:
        return False, None, f"{type(exc).__name__}: {exc}"


def scalar(obj: Any, *names: str):
    for name in names:
        good, val, _ = ok_get(obj, name)
        if not good:
            continue
        try:
            if hasattr(val, "Value"):
                val = val.Value
            return name, float(val) if isinstance(val, (int, float)) or hasattr(val, "real") else val
        except Exception:
            try:
                return name, val
            except Exception:
                continue
    return None, None


def items(collection: Any):
    count = int(collection.Count)
    for i in range(count):
        for index in (i, i + 1):
            try:
                yield i, collection.Item(index)
                break
            except Exception:
                continue


def probe_spec(spec: Any) -> dict[str, Any]:
    info: dict[str, Any] = {}
    for name in (
        "Name", "TypeName", "IsActive", "Active", "IsEstimate", "Estimate",
        "CurrentValue", "SpecifiedValue", "GoalValue", "TargetValue", "Value",
        "Error", "WeightedError", "Tolerance", "Status",
        "LowerBound", "UpperBound",
    ):
        good, val, err = ok_get(spec, name)
        if not good:
            continue
        try:
            if hasattr(val, "Value"):
                val = val.Value
            info[name] = val
        except Exception as exc:
            info[name] = f"<err {exc}>"
    # Write tests (non-destructive restore)
    writable = {}
    for attr in ("IsActive", "SpecifiedValue", "GoalValue", "CurrentValue", "Value"):
        good, original, _ = ok_get(spec, attr)
        if not good:
            writable[attr] = {"readable": False}
            continue
        try:
            if hasattr(original, "Value"):
                raw = original.Value
                # try set same value back
                original.Value = raw
                writable[attr] = {"readable": True, "writable_via_Value": True, "sample": raw}
            else:
                setattr(spec, attr, original)
                writable[attr] = {"readable": True, "writable_direct": True, "sample": original}
        except Exception as exc:
            writable[attr] = {"readable": True, "writable": False, "error": str(exc)}
    info["write_probe"] = writable
    return info


def probe_traysection(ts: Any) -> dict[str, Any]:
    out: dict[str, Any] = {"Name": ts.Name, "NumberOfStages": int(ts.NumberOfStages)}
    # Feed stages
    good, feeds, _ = ok_get(ts, "FeedStages")
    if good:
        feed_info = []
        for i, item in items(feeds):
            entry = {"index": i}
            for attr in ("Name", "StageNumber", "Stage", "FeedStage", "StreamName"):
                g, v, _ = ok_get(item, attr)
                if g:
                    try:
                        entry[attr] = v.Value if hasattr(v, "Value") else v
                    except Exception:
                        entry[attr] = str(v)
            # Also try common StageNumber patterns on the feed connection
            for attr in dir(item):
                if attr.startswith("_"):
                    continue
                if "stage" in attr.lower() or "feed" in attr.lower() or attr == "Name":
                    g, v, _ = ok_get(item, attr)
                    if g and attr not in entry:
                        try:
                            entry[attr] = v.Value if hasattr(v, "Value") else (v if isinstance(v, (int, float, str, bool)) else type(v).__name__)
                        except Exception:
                            pass
            feed_info.append(entry)
        out["FeedStages"] = feed_info

    # Stage profile arrays
    profile_attrs = [
        "StageTemperature", "StagePressure", "StageNetLiqFlow", "StageNetVapFlow",
        "StageLiquidFlow", "StageVapourFlow", "Temperature", "Pressure",
        "NetLiqFlow", "NetVapFlow", "LiquidMolarFlowRate", "VapourMolarFlowRate",
        "StageFeedFlow", "StageDuty",
    ]
    profiles = {}
    for attr in profile_attrs:
        g, v, err = ok_get(ts, attr)
        if not g:
            continue
        try:
            if hasattr(v, "Values"):
                arr = list(v.Values)
            elif hasattr(v, "Value"):
                arr = list(v.Value) if hasattr(v.Value, "__iter__") and not isinstance(v.Value, str) else v.Value
            else:
                arr = list(v) if hasattr(v, "__iter__") and not isinstance(v, str) else v
            profiles[attr] = arr
        except Exception as exc:
            profiles[attr] = f"<err {exc}>"
    out["profiles"] = profiles
    out["dir_sample"] = [n for n in dir(ts) if not n.startswith("_")][:80]
    return out


def probe_unit(op: Any) -> dict[str, Any]:
    out = {"Name": str(op.Name), "TypeName": str(getattr(op, "TypeName", ""))}
    for attr in (
        "Pressure", "PressureValue", "Temperature", "TemperatureValue",
        "Duty", "DutyValue", "Energy", "EnergyValue",
        "VesselPressure", "DeltaP",
    ):
        name, val = scalar(op, attr)
        if name:
            out[name] = val
    # Energy stream attached?
    for attr in ("EnergyStream", "DutyStream", "AttachedEnergy", "Q"):
        g, v, _ = ok_get(op, attr)
        if g:
            try:
                out[attr] = str(getattr(v, "Name", type(v).__name__))
            except Exception:
                out[attr] = type(v).__name__
    out["dir_sample"] = [n for n in dir(op) if not n.startswith("_")][:60]
    return out


def main() -> int:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    app = win32com.client.GetActiveObject("HYSYS.Application")
    case = app.ActiveDocument
    col = case.Flowsheet.Operations.Item("SW Stripper")
    cfs = col.ColumnFlowsheet

    report: dict[str, Any] = {
        "column": str(col.Name),
        "degrees_of_freedom": int(cfs.DegreesOfFreedom),
        "reflux_ratio_property": float(cfs.RefluxRatio),
        "connections": {},
    }
    for conn in (
        "TopVapourProduct", "BtmLiquidProduct", "TopLiquidProduct",
        "TopWaterProduct", "BtmVapourFeed", "TopLiquidFeed",
    ):
        g, v, err = ok_get(col, conn)
        if g:
            try:
                report["connections"][conn] = str(getattr(v, "Name", v))
            except Exception:
                report["connections"][conn] = str(v)
        else:
            report["connections"][conn] = f"<unavailable: {err}>"

    report["attached_feeds"] = [str(s.Name) for _, s in items(col.AttachedFeeds)]
    report["attached_products"] = [str(s.Name) for _, s in items(col.AttachedProducts)]

    # Specs
    specs = []
    for i, spec in items(cfs.Specifications):
        specs.append(probe_spec(spec))
    report["specifications"] = specs

    # Ops inside column
    ops = {}
    for _, op in items(cfs.Operations):
        name = str(op.Name)
        if name == "Main TS":
            ops[name] = probe_traysection(op)
        else:
            ops[name] = probe_unit(op)
    report["column_operations"] = ops

    # Energy stream duties from parent attached products/feeds
    duties = {}
    for stream_name in ("Cond Q", "Reb Q"):
        try:
            # search material/energy on main FS
            for coll_name in ("EnergyStreams", "MaterialStreams"):
                coll = getattr(case.Flowsheet, coll_name)
                try:
                    s = coll.Item(stream_name)
                except Exception:
                    continue
                name, val = scalar(s, "HeatFlowValue", "HeatFlow", "EnergyValue", "Energy")
                duties[stream_name] = {name: val}
                break
        except Exception as exc:
            duties[stream_name] = {"error": str(exc)}
    report["duties"] = duties

    # Product compositions (NH3 etc.)
    products = {}
    for pname in ("Off Gas", "Stripper Bottoms"):
        try:
            s = case.Flowsheet.MaterialStreams.Item(pname)
        except Exception:
            s = cfs.MaterialStreams.Item(pname)
        entry = {}
        for attr, keys in {
            "T": ("TemperatureValue", "Temperature"),
            "P": ("PressureValue", "Pressure"),
            "F": ("MolarFlowValue", "MolarFlow"),
            "MassF": ("MassFlowValue", "MassFlow"),
        }.items():
            _, entry[attr] = scalar(s, *keys)
        # mass fractions if available
        for attr in ("ComponentMassFractionValue", "ComponentMolarFractionValue"):
            g, v, _ = ok_get(s, attr)
            if g:
                try:
                    entry[attr] = list(v)
                except Exception as exc:
                    entry[attr] = str(exc)
        products[pname] = entry
    report["products"] = products

    OUT.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"DOF = {report['degrees_of_freedom']}")
    print("Specs:")
    for s in specs:
        print(
            f"  - {s.get('Name')}: active={s.get('IsActive')} "
            f"current={s.get('CurrentValue')} err={s.get('Error')} "
            f"write={s.get('write_probe')}"
        )
    ts = ops.get("Main TS", {})
    print(f"Stages = {ts.get('NumberOfStages')}")
    print(f"FeedStages = {ts.get('FeedStages')}")
    print(f"Profile keys = {list(ts.get('profiles', {}).keys())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
