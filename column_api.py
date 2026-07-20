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

        # Stages / feed location
        if ts is not None:
            try:
                state.number_of_stages = int(ts.NumberOfStages)
            except Exception:
                pass
            feed_stages = _safe_get(ts, "FeedStages")
            if feed_stages is not None:
                for feed in _items(feed_stages):
                    stage = _safe_get(feed, "IFaceStageNumber")
                    if stage is not None:
                        try:
                            state.feed_stage = int(stage)
                            break
                        except Exception:
                            pass
            state.profile = StageProfile(
                temperatures=_list_numbers(ts, "Temperature", "TemperatureValue", "StageTemperature"),
                pressures=_list_numbers(ts, "Pressure", "PressureValue", "StagePressure"),
            )

        # Specs
        specs = _safe_get(cfs, "Specifications")
        if specs is not None:
            for spec in _items(specs):
                is_active = bool(_bool(spec, "IsActive", "Active") or False)
                goal = _number(spec, "GoalValue")
                current = _number(spec, "CurrentValue")
                error = _number(spec, "Error")
                if is_active:
                    role = SpecRole.ACTIVE_SPEC
                elif goal is None and current is not None:
                    role = SpecRole.INACTIVE_ESTIMATE
                else:
                    role = SpecRole.CALCULATED
                state.specs.append(
                    ColumnSpecState(
                        name=str(spec.Name),
                        type_name=str(_safe_get(spec, "TypeName") or ""),
                        is_active=is_active,
                        goal_value=goal,
                        current_value=current,
                        error=error,
                        role=role,
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
        if state.bottoms_liquid_product:
            state.bottoms_molar_flow = self._stream_flow(state.bottoms_liquid_product)
            state.bottoms_temperature = self._stream_temperature(state.bottoms_liquid_product)

        return state

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
