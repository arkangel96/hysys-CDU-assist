"""COM adapter for HYSYS distillation / stripper columns."""
from __future__ import annotations

from typing import Any, Iterable

from column_models import (
    ColumnSnapshot,
    ColumnSpecState,
    ColumnState,
    SpecRole,
    StageProfile,
)
from hysys_api import HysysController, HysysError


def is_sentinel(value: Any) -> bool:
    """HYSYS empty/failed placeholder is typically -32767."""
    if value is None:
        return True
    try:
        v = float(value)
    except Exception:
        return True
    return abs(v + 32767.0) < 1.0 or abs(v - 32767.0) < 1.0


_CONDENSER_TYPE_MAP = {
    0: "None / Unknown",
    1: "Total",
    2: "Partial",
    3: "Full Reflux",
    4: "Once Through",
    5: "Scraped",
}


def _looks_like_molar_rate_spec(name: str, type_name: str = "") -> bool:
    blob = f"{name} {type_name}".lower()
    tokens = (
        "rate",
        "flow",
        "ovhd",
        "btms",
        "draw",
        "vapour",
        "vapor",
        "liquid flow",
        "prod rate",
    )
    return any(t in blob for t in tokens) and "frac" not in blob and "ratio" not in blob


def _si_kgmole_s_to_h(value: float | None) -> float | None:
    if value is None or is_sentinel(value):
        return None
    # HYSYS COM GoalValue for molar rates is typically kgmole/s
    if abs(value) < 500:  # heuristic: large worksheet values already in /h
        return value * 3600.0
    return value


def _pressure_bar(obj: Any, *members: str) -> float | None:
    for member in members:
        try:
            prop = getattr(obj, member, None)
        except Exception:
            prop = None
        if prop is None:
            continue
        try:
            if hasattr(prop, "GetValue"):
                for unit in ("bar", "bara", "barg"):
                    try:
                        value = float(prop.GetValue(unit))
                        if not is_sentinel(value):
                            return value
                    except Exception:
                        continue
            value = float(prop)
            if is_sentinel(value):
                continue
            # Assume Pa if huge
            if abs(value) > 1e4:
                return value / 1e5
            # Assume kPa if mid
            if abs(value) > 50:
                return value / 100.0
            return value
        except Exception:
            continue
    return None


def _map_condenser_type(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    try:
        code = int(raw)
    except Exception:
        return str(raw)
    return _CONDENSER_TYPE_MAP.get(code, f"TypeCode={code}")


def _items(collection: Any) -> Iterable[Any]:
    count = int(collection.Count)
    for index in range(count):
        try:
            yield collection.Item(index)
        except Exception:
            yield collection.Item(index + 1)


def _safe_get(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return None


def _number(obj: Any, *members: str) -> float | None:
    for member in members:
        try:
            value = getattr(obj, member)
            if hasattr(value, "Value"):
                value = value.Value
            return float(value)
        except Exception:
            continue
    return None


def _bool(obj: Any, *members: str) -> bool | None:
    for member in members:
        try:
            value = getattr(obj, member)
            if hasattr(value, "Value"):
                value = value.Value
            return bool(value)
        except Exception:
            continue
    return None


def _list_numbers(obj: Any, *members: str) -> list[float]:
    for member in members:
        try:
            value = getattr(obj, member)
            if hasattr(value, "Values"):
                value = value.Values
            elif hasattr(value, "Value"):
                value = value.Value
            return [float(x) for x in list(value)]
        except Exception:
            continue
    return []


class ColumnController:
    """Read/write distillation columns through an existing HysysController."""

    def __init__(self, hysys: HysysController) -> None:
        self.hysys = hysys

    def _require(self) -> None:
        if not self.hysys.connected or self.hysys.flowsheet is None:
            raise HysysError("Not connected to a HYSYS case.")

    def list_columns(self) -> list[str]:
        self._require()
        names: list[str] = []
        for op in _items(self.hysys.flowsheet.Operations):
            type_name = str(_safe_get(op, "TypeName") or "").lower()
            if type_name in {"distillation", "column", "absorber", "extractor"}:
                names.append(str(op.Name))
            elif _safe_get(op, "ColumnFlowsheet") is not None:
                names.append(str(op.Name))
        return sorted(set(names))

    def _column(self, name: str) -> Any:
        self._require()
        try:
            return self.hysys.flowsheet.Operations.Item(name)
        except Exception as exc:
            raise HysysError(f"Column not found: {name}") from exc

    def _column_flowsheet(self, column: Any) -> Any:
        cfs = _safe_get(column, "ColumnFlowsheet")
        if cfs is None:
            raise HysysError(f"Column '{column.Name}' has no ColumnFlowsheet (not a column op?).")
        return cfs

    def _main_tray_section(self, cfs: Any) -> Any | None:
        ops = _safe_get(cfs, "Operations")
        if ops is None:
            return None
        for op in _items(ops):
            if str(_safe_get(op, "TypeName") or "").lower() == "traysection":
                return op
            if "main" in str(op.Name).lower():
                return op
        return None

    def inspect(self, column_name: str) -> ColumnState:
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        ts = self._main_tray_section(cfs)

        state = ColumnState(
            name=str(column.Name),
            flowsheet_tag=str(_safe_get(cfs, "Name") or ""),
            type_name=str(_safe_get(column, "TypeName") or "distillation"),
            degrees_of_freedom=_safe_get(cfs, "DegreesOfFreedom"),
            reflux_ratio=_number(cfs, "RefluxRatio"),
        )
        if isinstance(state.degrees_of_freedom, bool):
            state.degrees_of_freedom = int(state.degrees_of_freedom)
        elif state.degrees_of_freedom is not None:
            try:
                state.degrees_of_freedom = int(state.degrees_of_freedom)
            except Exception:
                state.degrees_of_freedom = None

        # Connections
        for attr, target in (
            ("TopVapourProduct", "top_vapour_product"),
            ("BtmLiquidProduct", "bottoms_liquid_product"),
        ):
            stream = _safe_get(column, attr)
            if stream is not None:
                try:
                    setattr(state, target, str(stream.Name))
                except Exception:
                    pass

        feeds = _safe_get(column, "AttachedFeeds")
        products = _safe_get(column, "AttachedProducts")
        if feeds is not None:
            for item in _items(feeds):
                name = str(item.Name)
                type_name = str(_safe_get(item, "TypeName") or "").lower()
                if "energy" in type_name:
                    state.energy_streams.append(name)
                else:
                    state.feed_streams.append(name)
        if products is not None:
            for item in _items(products):
                name = str(item.Name)
                type_name = str(_safe_get(item, "TypeName") or "").lower()
                if "energy" in type_name:
                    state.energy_streams.append(name)
                else:
                    state.product_streams.append(name)

        # Stages / feed location / Connections pressures
        if ts is not None:
            try:
                state.number_of_stages = int(ts.NumberOfStages)
            except Exception:
                pass
            for attr in ("StageNumbering", "Numbering", "StageNumberingDirection"):
                raw = _safe_get(ts, attr)
                if raw is not None:
                    text = str(raw).strip()
                    if text:
                        if text in ("0", "TopDown", "Top Down"):
                            state.stage_numbering = "Top Down"
                        elif text in ("1", "BottomUp", "Bottom Up"):
                            state.stage_numbering = "Bottom Up"
                        else:
                            state.stage_numbering = text
                        break
            feed_stages = _safe_get(ts, "FeedStages")
            if feed_stages is not None:
                for feed in _items(feed_stages):
                    stage = _safe_get(feed, "IFaceStageNumber")
                    if stage is not None:
                        try:
                            state.feed_stage = int(stage)
                        except Exception:
                            pass
                    label = str(_safe_get(feed, "Name") or _safe_get(feed, "StageName") or "")
                    if not label and state.feed_stage is not None:
                        label = f"{state.feed_stage}_Main TS"
                    if label:
                        state.feed_stage_label = label
                    if state.feed_stage is not None:
                        break
            state.profile = StageProfile(
                temperatures=_list_numbers(ts, "Temperature", "TemperatureValue", "StageTemperature"),
                pressures=_list_numbers(ts, "Pressure", "PressureValue", "StagePressure"),
            )
            # Pressures from tray section or profile ends
            state.condenser_pressure_bar = _pressure_bar(
                ts, "TopPressure", "CondenserPressure", "Pressure"
            )
            state.reboiler_pressure_bar = _pressure_bar(
                ts, "BottomPressure", "ReboilerPressure"
            )
            state.condenser_dp_bar = _pressure_bar(ts, "TopPressureDrop", "CondenserPressureDrop")
            state.reboiler_dp_bar = _pressure_bar(
                ts, "BottomPressureDrop", "ReboilerPressureDrop"
            )
            if state.profile.pressures:
                if state.condenser_pressure_bar is None:
                    top_p = state.profile.pressures[0]
                    if not is_sentinel(top_p):
                        # profile often kPa
                        state.condenser_pressure_bar = (
                            top_p / 100.0 if top_p > 50 else top_p
                        )
                if state.reboiler_pressure_bar is None:
                    bot_p = state.profile.pressures[-1]
                    if not is_sentinel(bot_p):
                        state.reboiler_pressure_bar = (
                            bot_p / 100.0 if bot_p > 50 else bot_p
                        )

        # Condenser type (Connections)
        for obj in (column, cfs, ts):
            if obj is None:
                continue
            for attr in ("CondenserType", "CondenserConfig", "Condenser"):
                raw = _safe_get(obj, attr)
                if raw is None:
                    continue
                mapped = _map_condenser_type(raw)
                if mapped:
                    state.condenser_type = mapped
                    break
            if state.condenser_type:
                break
        if not state.condenser_type and state.top_vapour_product:
            # Full-reflux strippers expose vapor overhead, no liquid distillate draw
            has_liquid_dist = any(
                "dist" in n.lower() or "cond out" in n.lower() for n in state.product_streams
            )
            if not has_liquid_dist:
                state.condenser_type = "Full Reflux (inferred)"

        # Monitor iteration / eqm / heat-spec residuals (COM names)
        if cfs is not None:
            try:
                it = _safe_get(cfs, "CurrentIteration")
                if it is not None:
                    state.monitor_iteration = int(it)
            except Exception:
                pass
            state.monitor_equilibrium_error = _number(cfs, "EquilibriumError")
            state.monitor_heat_spec_error = _number(cfs, "HeatSpecError")
            state.monitor_step = _number(cfs, "StepSize", "Step")

        # Specs (Monitor / Specs page)
        specs = _safe_get(cfs, "Specifications")
        if specs is not None:
            for spec in _items(specs):
                is_active = bool(_bool(spec, "IsActive", "Active") or False)
                use_est = _bool(spec, "IsUsedAsEstimate", "IsEstimate", "UseAsEstimate", "Estimate")
                use_cur = _bool(spec, "IsCurrent", "UseAsCurrent")
                # Specs Summary "Current" column: for fixed specs HYSYS typically
                # marks Current with Active; expose both Active and Estimate clearly.
                if use_cur is None:
                    use_cur = is_active
                goal = _number(spec, "GoalValue")
                current = _number(spec, "CurrentValue")
                error = _number(spec, "Error", "ErrorValue", "WeightedError")
                tol = _number(spec, "Tolerance", "WeightedTolerance", "WeightedToleranceValue")
                type_name = str(_safe_get(spec, "TypeName") or "")
                name = str(spec.Name)
                goal_disp = None
                cur_disp = None
                disp_unit = ""
                if _looks_like_molar_rate_spec(name, type_name):
                    goal_disp = _si_kgmole_s_to_h(goal)
                    cur_disp = _si_kgmole_s_to_h(current)
                    disp_unit = "kgmole/h"
                if is_active:
                    role = SpecRole.ACTIVE_SPEC
                elif goal is None and current is not None:
                    role = SpecRole.INACTIVE_ESTIMATE
                else:
                    role = SpecRole.CALCULATED
                state.specs.append(
                    ColumnSpecState(
                        name=name,
                        type_name=type_name,
                        is_active=is_active,
                        use_as_estimate=use_est,
                        use_as_current=use_cur,
                        goal_value=goal,
                        current_value=current,
                        error=error,
                        weighted_tolerance=tol,
                        goal_display=goal_disp,
                        current_display=cur_disp,
                        display_unit=disp_unit,
                        role=role,
                        summary_current=use_cur,
                    )
                )

        active_errors = [s.score_error() for s in state.active_specs()]
        state.max_active_spec_error = max(active_errors) if active_errors else 0.0
        state.sum_active_spec_error = sum(active_errors)
        state.appears_converged = (
            state.degrees_of_freedom == 0
            and state.max_active_spec_error < 5e-4
            and bool(state.active_specs())
        )

        # Duties / product results from parent flowsheet streams
        for energy_name in state.energy_streams:
            duty = self._stream_heat(energy_name)
            lower = energy_name.lower()
            if "cond" in lower:
                state.condenser_duty = duty
            elif "reb" in lower:
                state.reboiler_duty = duty

        if state.top_vapour_product:
            state.overhead_molar_flow = self._stream_flow(state.top_vapour_product)
            state.overhead_temperature = self._stream_temperature(state.top_vapour_product)
            state.overhead_molar_flow_kgmole_h = self._stream_flow_unit(
                state.top_vapour_product, "kgmole/h"
            )
            if state.condenser_pressure_bar is None:
                state.condenser_pressure_bar = self._stream_pressure_bar(
                    state.top_vapour_product
                )
        if state.bottoms_liquid_product:
            state.bottoms_molar_flow = self._stream_flow(state.bottoms_liquid_product)
            state.bottoms_temperature = self._stream_temperature(state.bottoms_liquid_product)
            state.bottoms_molar_flow_kgmole_h = self._stream_flow_unit(
                state.bottoms_liquid_product, "kgmole/h"
            )
            state.bottoms_nh3_mass_frac = self.read_component_mass_fraction(
                state.bottoms_liquid_product, ("ammonia", "nh3")
            )
            if state.reboiler_pressure_bar is None:
                state.reboiler_pressure_bar = self._stream_pressure_bar(
                    state.bottoms_liquid_product
                )

        # Prefer stream kgmole/h for rate-spec display when names match products
        for spec in state.specs:
            lower = spec.name.lower()
            if "ovhd" in lower or "vap rate" in lower:
                if state.overhead_molar_flow_kgmole_h is not None:
                    spec.current_display = state.overhead_molar_flow_kgmole_h
                    spec.display_unit = "kgmole/h"
                    if spec.goal_display is None and spec.goal_value is not None:
                        spec.goal_display = _si_kgmole_s_to_h(spec.goal_value)
            if "btms" in lower or "bottoms" in lower:
                if state.bottoms_molar_flow_kgmole_h is not None:
                    spec.current_display = state.bottoms_molar_flow_kgmole_h
                    spec.display_unit = "kgmole/h"
                    if spec.goal_display is None and spec.goal_value is not None:
                        spec.goal_display = _si_kgmole_s_to_h(spec.goal_value)

        state.physical_solution = (
            not is_sentinel(state.condenser_duty)
            and not is_sentinel(state.reboiler_duty)
            and not is_sentinel(state.bottoms_temperature)
        )
        return state

    def _stream_pressure_bar(self, name: str) -> float | None:
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(name)
            return _pressure_bar(stream, "Pressure", "PressureValue")
        except Exception:
            return None

    def _stream_flow_unit(self, name: str, unit: str) -> float | None:
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(name)
            flow = getattr(stream, "MolarFlow", None)
            if flow is None:
                return None
            if hasattr(flow, "GetValue"):
                value = float(flow.GetValue(unit))
                return None if is_sentinel(value) else value
        except Exception:
            return None
        return None

    def read_component_mass_fraction(
        self, stream_name: str, name_contains: tuple[str, ...]
    ) -> float | None:
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(stream_name)
            comps = stream.ComponentMassFraction
            values = list(comps.Values)
            names = list(self.hysys.component_names)
            for comp_name, value in zip(names, values):
                lower = str(comp_name).lower()
                if any(token in lower for token in name_contains):
                    return None if is_sentinel(value) else float(value)
        except Exception:
            return None
        return None

    def refresh_estimates(self, column_name: str) -> list[str]:
        """Best-effort composition estimate refresh (State B recovery)."""
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        notes: list[str] = []
        for attr, value in (("IsUsingSolutionForEstimates", True),):
            try:
                setattr(cfs, attr, value)
                notes.append(f"set {attr}={value}")
            except Exception as exc:
                notes.append(f"{attr} failed: {exc}")
        for meth in ("UpdateCompositionEstimates", "NormalizeCompositionEstimates"):
            try:
                getattr(cfs, meth)()
                notes.append(f"{meth} OK")
            except Exception as exc:
                notes.append(f"{meth} failed: {exc}")
        return notes

    def _stream_heat(self, name: str) -> float | None:
        for coll_name in ("EnergyStreams", "MaterialStreams"):
            coll = _safe_get(self.hysys.flowsheet, coll_name)
            if coll is None:
                continue
            try:
                stream = coll.Item(name)
            except Exception:
                continue
            return _number(stream, "HeatFlowValue", "HeatFlow", "EnergyValue", "Energy")
        return None

    def _stream_flow(self, name: str) -> float | None:
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(name)
        except Exception:
            return None
        return _number(stream, "MolarFlowValue", "MolarFlow")

    def _stream_temperature(self, name: str) -> float | None:
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(name)
        except Exception:
            return None
        return _number(stream, "TemperatureValue", "Temperature")

    def snapshot(self, column_name: str) -> ColumnSnapshot:
        state = self.inspect(column_name)
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        specs_payload = []
        specs = _safe_get(cfs, "Specifications")
        if specs is not None:
            for spec in _items(specs):
                specs_payload.append(
                    {
                        "name": str(spec.Name),
                        "is_active": bool(_safe_get(spec, "IsActive")),
                        "is_estimate": bool(_bool(spec, "IsUsedAsEstimate") or False),
                        "goal_value": _number(spec, "GoalValue"),
                    }
                )
        solver_payload: dict[str, Any] = {}
        # Optional solver knobs if present on column flowsheet / nested objects
        for attr in ("DampingFactor", "FixedDampingFactor", "MaxIterations"):
            value = _number(cfs, attr)
            if value is not None:
                solver_payload[attr] = value
        return ColumnSnapshot(
            column_name=column_name,
            degrees_of_freedom=int(state.degrees_of_freedom or 0),
            reflux_ratio=state.reflux_ratio,
            specs=specs_payload,
            solver=solver_payload,
        )

    def restore(self, snap: ColumnSnapshot) -> None:
        column = self._column(snap.column_name)
        cfs = self._column_flowsheet(column)
        specs = _safe_get(cfs, "Specifications")
        if specs is None:
            return
        by_name = {str(s.Name): s for s in _items(specs)}
        for item in snap.specs:
            spec = by_name.get(item["name"])
            if spec is None:
                continue
            try:
                spec.IsActive = bool(item["is_active"])
            except Exception:
                pass
            if "is_estimate" in item:
                try:
                    spec.IsUsedAsEstimate = bool(item["is_estimate"])
                except Exception:
                    pass
            goal = item.get("goal_value")
            if goal is not None:
                try:
                    spec.GoalValue = float(goal)
                except Exception:
                    pass

    def set_spec_goal(self, column_name: str, spec_name: str, goal: float) -> None:
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        for spec in _items(cfs.Specifications):
            if str(spec.Name) == spec_name:
                try:
                    spec.GoalValue = float(goal)
                    return
                except Exception as exc:
                    raise HysysError(f"Could not set GoalValue on '{spec_name}': {exc}") from exc
        raise HysysError(f"Specification not found: {spec_name}")

    def set_spec_active(self, column_name: str, spec_name: str, active: bool) -> None:
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        for spec in _items(cfs.Specifications):
            if str(spec.Name) == spec_name:
                try:
                    spec.IsActive = bool(active)
                    return
                except Exception as exc:
                    raise HysysError(f"Could not set IsActive on '{spec_name}': {exc}") from exc
        raise HysysError(f"Specification not found: {spec_name}")

    def set_spec_estimate(self, column_name: str, spec_name: str, as_estimate: bool) -> None:
        """HYSYS Specs / Monitor 'Estimate' ↔ IsUsedAsEstimate."""
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        for spec in _items(cfs.Specifications):
            if str(spec.Name) == spec_name:
                try:
                    spec.IsUsedAsEstimate = bool(as_estimate)
                    return
                except Exception as exc:
                    raise HysysError(
                        f"Could not set IsUsedAsEstimate on '{spec_name}': {exc}"
                    ) from exc
        raise HysysError(f"Specification not found: {spec_name}")

    def sync_spec_goal_from_current(self, column_name: str, spec_name: str) -> float:
        """Specs Summary PE click: set Specified/Goal from Current calculated value."""
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        for spec in _items(cfs.Specifications):
            if str(spec.Name) == spec_name:
                current = _number(spec, "CurrentValue")
                if current is None or is_sentinel(current):
                    raise HysysError(f"No usable CurrentValue on '{spec_name}'")
                try:
                    spec.GoalValue = float(current)
                    return float(current)
                except Exception as exc:
                    raise HysysError(
                        f"Could not sync Goal from Current on '{spec_name}': {exc}"
                    ) from exc
        raise HysysError(f"Specification not found: {spec_name}")

    def apply_specs_summary(
        self,
        column_name: str,
        rows: list[dict[str, Any]],
    ) -> list[str]:
        """
        Apply Specs Summary Active / Estimate flags (and optional Goal).
        Each row: {name, is_active?, is_estimate?, goal_value?}.
        """
        notes: list[str] = []
        for row in rows:
            name = str(row["name"])
            if "is_active" in row:
                self.set_spec_active(column_name, name, bool(row["is_active"]))
                notes.append(f"{name}: Active={bool(row['is_active'])}")
            if "is_estimate" in row:
                try:
                    self.set_spec_estimate(column_name, name, bool(row["is_estimate"]))
                    notes.append(f"{name}: Estimate={bool(row['is_estimate'])}")
                except HysysError as exc:
                    notes.append(f"{name}: Estimate skip ({exc})")
            if row.get("goal_value") is not None:
                self.set_spec_goal(column_name, name, float(row["goal_value"]))
                notes.append(f"{name}: Goal={row['goal_value']}")
        return notes

    def swap_active_spec(
        self,
        column_name: str,
        deactivate: str,
        activate: str,
        activate_goal: float | None = None,
    ) -> None:
        """1-for-1 swap to keep DOF unchanged."""
        self.set_spec_active(column_name, deactivate, False)
        if activate_goal is not None:
            # Goal may only be writable after/before activate depending on version
            try:
                self.set_spec_goal(column_name, activate, activate_goal)
            except HysysError:
                pass
        self.set_spec_active(column_name, activate, True)
        if activate_goal is not None:
            self.set_spec_goal(column_name, activate, activate_goal)

    def run_column(self, column_name: str) -> None:
        """Request a column / case solve."""
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        errors: list[str] = []
        for action in (
            lambda: cfs.Run(),
            lambda: column.Run(),
            lambda: self.hysys.solve(),
        ):
            try:
                action()
                return
            except Exception as exc:
                errors.append(str(exc))
        raise HysysError("Could not run column: " + " | ".join(errors))
