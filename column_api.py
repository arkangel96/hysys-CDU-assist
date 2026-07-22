"""COM adapter for HYSYS distillation / stripper columns."""
from __future__ import annotations

from typing import Any, Iterable

from column_models import (
    ColumnSnapshot,
    ColumnSpecState,
    ColumnState,
    ConnectionStreamRow,
    SpecRole,
    StageProfile,
)
from hysys_api import HysysController, HysysError
from hysys_units import scale_si_to_display, _unit_label, _get_value
from cdu_connections import apply_connection_roles, infer_phase_type
from cdu_monitor import apply_monitor_spec_roles, classify_monitor_spec, default_unit_for_family
from cdu_subcooling import read_subcooling_from_com
from cdu_side_ops import apply_side_ops_read
from cdu_rating import apply_rating_read


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
    """Legacy metric-only fallback when HYSYS unit discovery is unavailable."""
    if value is None or is_sentinel(value):
        return None
    if abs(value) < 500:  # heuristic: large worksheet values already in /h
        return value * 3600.0
    return value


def _pressure_in_unit(obj: Any, unit: str, *members: str) -> float | None:
    for member in members:
        try:
            prop = getattr(obj, member, None)
        except Exception:
            prop = None
        if prop is None:
            continue
        try:
            if hasattr(prop, "GetValue"):
                try:
                    value = float(prop.GetValue(unit))
                    if not is_sentinel(value):
                        return value
                except Exception:
                    for alt in ("bar", "bara", "barg", "psia", "psig", "kPa"):
                        try:
                            value = float(prop.GetValue(alt))
                            if not is_sentinel(value):
                                return value
                        except Exception:
                            continue
            value = float(prop)
            if is_sentinel(value):
                continue
            return value
        except Exception:
            continue
    return None


def _pressure_bar(obj: Any, *members: str) -> float | None:
    return _pressure_in_unit(obj, "bar", *members)


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
        self.last_dialog_clues: list = []
        self.last_message_clues: list = []

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

        try:
            self.hysys.refresh_display_units()
        except Exception:
            pass
        du = getattr(self.hysys, "display_units", None)
        state = ColumnState(
            name=str(column.Name),
            flowsheet_tag=str(_safe_get(cfs, "Name") or ""),
            type_name=str(_safe_get(column, "TypeName") or "distillation"),
            degrees_of_freedom=_safe_get(cfs, "DegreesOfFreedom"),
            reflux_ratio=_number(cfs, "RefluxRatio"),
            temperature_unit=getattr(du, "temperature", "C") if du else "C",
            pressure_unit=getattr(du, "pressure", "bar") if du else "bar",
            molar_flow_unit=getattr(du, "molar_flow", "kgmole/h") if du else "kgmole/h",
            mass_flow_unit=getattr(du, "mass_flow", "kg/h") if du else "kg/h",
            volume_flow_unit=getattr(du, "volume_flow", "USGPM") if du else "USGPM",
            energy_unit=getattr(du, "energy", "Btu/hr") if du else "Btu/hr",
        )
        if isinstance(state.degrees_of_freedom, bool):
            state.degrees_of_freedom = int(state.degrees_of_freedom)
        elif state.degrees_of_freedom is not None:
            try:
                state.degrees_of_freedom = int(state.degrees_of_freedom)
            except Exception:
                state.degrees_of_freedom = None

        # Connections — AttachedFeeds / AttachedProducts + stage map for full table
        for attr, target in (
            ("TopVapourProduct", "top_vapour_product"),
            ("BtmLiquidProduct", "bottoms_liquid_product"),
            ("TopLiquidProduct", "overhead_liquid_product"),
        ):
            stream = _safe_get(column, attr)
            if stream is not None:
                try:
                    setattr(state, target, str(stream.Name))
                except Exception:
                    pass
        self._last_top_product = state.top_vapour_product
        self._last_btms_product = state.bottoms_liquid_product

        stage_by_stream = self._build_stage_label_map(column, cfs, ts)

        feeds = _safe_get(column, "AttachedFeeds")
        products = _safe_get(column, "AttachedProducts")
        if feeds is not None:
            for item in _items(feeds):
                name = str(item.Name)
                type_name = str(_safe_get(item, "TypeName") or "")
                is_energy = "energy" in type_name.lower()
                if is_energy:
                    state.energy_streams.append(name)
                else:
                    state.feed_streams.append(name)
                stage_label = stage_by_stream.get(name.lower(), "")
                if not stage_label:
                    stage_label = self._stage_label_from_attachment(item)
                vf = self._stream_vapor_fraction(name) if not is_energy else None
                phase = infer_phase_type(
                    name=name,
                    is_energy=is_energy,
                    type_name=type_name,
                    vapor_frac=vf,
                )
                state.inlet_rows.append(
                    ConnectionStreamRow(
                        name=name,
                        external_name=name,
                        stage_label=stage_label,
                        phase_type=phase,
                        direction="inlet",
                    )
                )
        if products is not None:
            for item in _items(products):
                name = str(item.Name)
                type_name = str(_safe_get(item, "TypeName") or "")
                is_energy = "energy" in type_name.lower()
                if is_energy:
                    if name not in state.energy_streams:
                        state.energy_streams.append(name)
                else:
                    state.product_streams.append(name)
                stage_label = stage_by_stream.get(name.lower(), "")
                if not stage_label:
                    stage_label = self._stage_label_from_attachment(item)
                vf = self._stream_vapor_fraction(name) if not is_energy else None
                water = "waste water" in name.lower() or "wastewater" in name.lower()
                phase = infer_phase_type(
                    name=name,
                    is_energy=is_energy,
                    type_name=type_name,
                    vapor_frac=vf,
                    water_draw=water,
                )
                state.outlet_rows.append(
                    ConnectionStreamRow(
                        name=name,
                        external_name=name,
                        stage_label=stage_label,
                        phase_type=phase,
                        direction="outlet",
                    )
                )

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
            # Pressures in HYSYS worksheet unit (field names *_bar are historical)
            p_u = state.pressure_unit
            state.condenser_pressure_bar = _pressure_in_unit(
                ts, p_u, "TopPressure", "CondenserPressure", "Pressure"
            )
            state.reboiler_pressure_bar = _pressure_in_unit(
                ts, p_u, "BottomPressure", "ReboilerPressure"
            )
            state.condenser_dp_bar = _pressure_in_unit(
                ts, p_u, "TopPressureDrop", "CondenserPressureDrop"
            )
            state.reboiler_dp_bar = _pressure_in_unit(
                ts, p_u, "BottomPressureDrop", "ReboilerPressureDrop"
            )
            if state.profile.pressures:
                # Profile arrays are often raw; prefer stream GetValue when missing
                if state.condenser_pressure_bar is None:
                    top_p = state.profile.pressures[0]
                    if not is_sentinel(top_p):
                        state.condenser_pressure_bar = float(top_p)
                if state.reboiler_pressure_bar is None:
                    bot_p = state.profile.pressures[-1]
                    if not is_sentinel(bot_p):
                        state.reboiler_pressure_bar = float(bot_p)

        # Role map + prefer Atm Feed / Residue / Off Gas / Naphtha when present
        apply_connection_roles(state)
        self._last_top_product = state.top_vapour_product
        self._last_btms_product = state.bottoms_liquid_product

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

        # Design → Subcooling (condenser)
        sub = read_subcooling_from_com(column, cfs, ts)
        state.condenser_subcool_degrees = sub.get("degrees")
        state.condenser_subcool_to = sub.get("subcool_to")
        state.condenser_subcool_to_mode = str(sub.get("subcool_to_mode") or "")

        # Design → Side Ops (strippers / PAs / side draws)
        apply_side_ops_read(
            state,
            column,
            cfs,
            ts,
            stream_molar=lambda n: self._stream_flow_display(n),
            stream_mass=lambda n: self._stream_mass_flow_display(n),
        )

        # Rating tab (Towers / Vessels / Equipment / Pressure Drop)
        apply_rating_read(state, column, cfs, ts)

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

        # Specs (Design → Specs list + Monitor table — same COM collection)
        if cfs is not None:
            for attr in ("DefaultBasis", "SpecBasis", "Basis", "FlowBasis"):
                raw = _safe_get(cfs, attr)
                if raw is None:
                    continue
                text = str(raw).strip()
                if text and not text.startswith("<"):
                    # Map common COM enums
                    if text in {"0", "Molar"}:
                        state.default_spec_basis = "Molar"
                    elif text in {"1", "Mass"}:
                        state.default_spec_basis = "Mass"
                    elif text in {"2", "LiquidVol", "Liquid Volume", "StdIdealLiqVol"}:
                        state.default_spec_basis = text
                    else:
                        state.default_spec_basis = text
                    break
            if not state.default_spec_basis:
                state.default_spec_basis = "Molar"  # T-100 screenshot default

        specs = _safe_get(cfs, "Specifications")
        if specs is not None:
            from cdu_specs import _map_fixed_ranged, _map_primary_alternate

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
                error = _number(spec, "Error", "ErrorValue", "WeightedError", "WeightedCalculatedError")
                tol = _number(spec, "Tolerance", "WeightedTolerance", "WeightedToleranceValue")
                abs_tol = _number(spec, "AbsoluteTolerance", "AbsTolerance")
                abs_err = _number(spec, "AbsoluteError", "AbsError", "AbsoluteCalculatedError")
                lower_b = _number(spec, "LowerBound", "LowerLimit", "Lower")
                upper_b = _number(spec, "UpperBound", "UpperLimit", "Upper")
                dry = _bool(
                    spec,
                    "IsDryFlowBasis",
                    "DryFlowBasis",
                    "IsDryBasis",
                    "DryBasis",
                )
                fixed_raw = _safe_get(spec, "FixedOrRanged")
                if fixed_raw is None:
                    fixed_raw = _safe_get(spec, "IsFixed")
                if fixed_raw is None:
                    fixed_raw = _safe_get(spec, "SpecMode")
                primary_raw = _safe_get(spec, "PrimaryOrAlternate")
                if primary_raw is None:
                    primary_raw = _safe_get(spec, "IsPrimary")
                if primary_raw is None:
                    primary_raw = _safe_get(spec, "IsAlternate")
                    if primary_raw is not None:
                        # invert alternate flag if that's what we got
                        try:
                            primary_raw = not bool(primary_raw)
                        except Exception:
                            pass
                spec_conv = _bool(spec, "IsConverged", "Converged", "SpecConverged")
                type_name = str(_safe_get(spec, "TypeName") or "")
                name = str(spec.Name)
                family, unit_cands = classify_monitor_spec(name, type_name)
                goal_disp, cur_disp, disp_unit = self._spec_worksheet_display(
                    spec, goal, current, family, unit_cands
                )
                molar_u = self._molar_flow_unit()
                if not disp_unit and _looks_like_molar_rate_spec(name, type_name):
                    goal_disp = self._molar_goal_display(goal)
                    cur_disp = self._molar_goal_display(current)
                    disp_unit = molar_u
                if is_active:
                    role = SpecRole.ACTIVE_SPEC
                elif goal is None and current is not None:
                    role = SpecRole.INACTIVE_ESTIMATE
                else:
                    role = SpecRole.CALCULATED
                fixed_s = _map_fixed_ranged(fixed_raw)
                prim_s = _map_primary_alternate(primary_raw)
                # Specs Summary T-100: Active rows show Fixed / Primary
                if not fixed_s and is_active:
                    fixed_s = "Fixed"
                if not prim_s and (is_active or use_cur):
                    prim_s = "Primary"
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
                        mv_family=family,
                        role=role,
                        summary_current=use_cur,
                        dry_flow_basis=dry,
                        fixed_or_ranged=fixed_s,
                        primary_or_alternate=prim_s,
                        absolute_tolerance=abs_tol,
                        absolute_error=abs_err,
                        spec_converged=spec_conv,
                        lower_bound=lower_b,
                        upper_bound=upper_b,
                    )
                )

        apply_monitor_spec_roles(state, display_units=du)

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
            molar_u = self._molar_flow_unit()
            state.overhead_molar_flow_kgmole_h = self._stream_flow_unit(
                state.top_vapour_product, molar_u
            )
            if state.condenser_pressure_bar is None:
                state.condenser_pressure_bar = self._stream_pressure_display(
                    state.top_vapour_product
                )
        if state.bottoms_liquid_product:
            state.bottoms_molar_flow = self._stream_flow(state.bottoms_liquid_product)
            state.bottoms_temperature = self._stream_temperature(state.bottoms_liquid_product)
            molar_u = self._molar_flow_unit()
            state.bottoms_molar_flow_kgmole_h = self._stream_flow_unit(
                state.bottoms_liquid_product, molar_u
            )
            state.bottoms_nh3_mass_frac = self.read_component_mass_fraction(
                state.bottoms_liquid_product, ("ammonia", "nh3")
            )
            if state.reboiler_pressure_bar is None:
                state.reboiler_pressure_bar = self._stream_pressure_display(
                    state.bottoms_liquid_product
                )

        # Prefer stream worksheet flow for rate-spec display when names match products
        molar_u = self._molar_flow_unit()
        for spec in state.specs:
            lower = spec.name.lower()
            if "ovhd" in lower or "vap rate" in lower or "overhead" in lower or "distill" in lower:
                if state.overhead_molar_flow_kgmole_h is not None:
                    spec.current_display = state.overhead_molar_flow_kgmole_h
                    spec.display_unit = molar_u
                    if spec.goal_display is None and spec.goal_value is not None:
                        spec.goal_display = self._molar_goal_display(spec.goal_value)
            if "btms" in lower or "bottoms" in lower or "residue" in lower:
                if state.bottoms_molar_flow_kgmole_h is not None:
                    spec.current_display = state.bottoms_molar_flow_kgmole_h
                    spec.display_unit = molar_u
                    if spec.goal_display is None and spec.goal_value is not None:
                        spec.goal_display = self._molar_goal_display(spec.goal_value)

        state.physical_solution = (
            not is_sentinel(state.condenser_duty)
            and not is_sentinel(state.reboiler_duty)
            and not is_sentinel(state.bottoms_temperature)
        )
        return state

    def _molar_flow_unit(self) -> str:
        try:
            return self.hysys.display_units.molar_flow
        except Exception:
            return "kgmole/h"

    def _pressure_unit(self) -> str:
        try:
            return self.hysys.display_units.pressure
        except Exception:
            return "bar"

    def _temperature_unit(self) -> str:
        try:
            return self.hysys.display_units.temperature
        except Exception:
            return "C"

    def _spec_worksheet_display(
        self,
        spec: Any,
        goal: float | None,
        current: float | None,
        family: str,
        unit_cands: tuple[str, ...],
    ) -> tuple[float | None, float | None, str]:
        """
        Copy Monitor worksheet units from HYSYS spec RealVariables when possible.
        Returns (goal_display, current_display, unit_label).
        """
        du = getattr(self.hysys, "display_units", None)
        preferred = default_unit_for_family(family, du)
        candidates = list(unit_cands)
        if preferred and preferred not in candidates:
            candidates.insert(0, preferred)

        goal_prop = None
        cur_prop = None
        for attr in ("Goal", "GoalValue", "SpecifiedValue"):
            prop = _safe_get(spec, attr)
            if prop is not None and (hasattr(prop, "GetValue") or _unit_label(prop)):
                goal_prop = prop
                break
        for attr in ("Current", "CurrentValue"):
            prop = _safe_get(spec, attr)
            if prop is not None and (hasattr(prop, "GetValue") or _unit_label(prop)):
                cur_prop = prop
                break

        unit = ""
        for prop in (goal_prop, cur_prop, spec):
            label = _unit_label(prop)
            if label:
                unit = label
                break
        if not unit:
            for cand in candidates:
                for prop in (goal_prop, cur_prop):
                    if prop is not None and _get_value(prop, cand) is not None:
                        unit = cand
                        break
                if unit:
                    break
        if not unit:
            unit = preferred

        def _disp(prop: Any, raw: float | None) -> float | None:
            if raw is None or is_sentinel(raw):
                return None
            if prop is not None and unit:
                got = _get_value(prop, unit)
                if got is not None and not is_sentinel(got):
                    return got
                scaled = scale_si_to_display(prop, float(raw), unit)
                if scaled is not None:
                    return scaled
            # Reflux / dimensionless — raw is fine
            if family == "reflux":
                return float(raw)
            # If magnitude already looks like Monitor worksheet (USGPM/Btu), keep raw
            return float(raw)

        goal_disp = _disp(goal_prop, goal)
        cur_disp = _disp(cur_prop, current)
        return goal_disp, cur_disp, unit or ""

    def _molar_goal_display(self, goal_si: float | None) -> float | None:
        """Scale COM GoalValue to HYSYS worksheet molar unit via stream GetValue ratio."""
        if goal_si is None or is_sentinel(goal_si):
            return None
        molar_u = self._molar_flow_unit()
        for stream_name in (
            getattr(self, "_last_top_product", None),
            getattr(self, "_last_btms_product", None),
        ):
            if not stream_name:
                continue
            try:
                stream = self.hysys.flowsheet.MaterialStreams.Item(stream_name)
                flow = getattr(stream, "MolarFlow", None)
                scaled = scale_si_to_display(flow, float(goal_si), molar_u)
                if scaled is not None:
                    return scaled
            except Exception:
                continue
        # Probe any material stream for a conversion ratio
        try:
            streams = self.hysys.flowsheet.MaterialStreams
            stream = streams.Item(0) if int(streams.Count) > 0 else None
            if stream is None:
                stream = streams.Item(1)
            flow = getattr(stream, "MolarFlow", None)
            scaled = scale_si_to_display(flow, float(goal_si), molar_u)
            if scaled is not None:
                return scaled
        except Exception:
            pass
        if molar_u.lower().replace(" ", "") in {"kgmole/h", "kmole/h"}:
            return _si_kgmole_s_to_h(goal_si)
        return float(goal_si)

    def _stream_pressure_display(self, name: str) -> float | None:
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(name)
            return _pressure_in_unit(
                stream, self._pressure_unit(), "Pressure", "PressureValue"
            )
        except Exception:
            return None

    def _stage_label_from_attachment(self, item: Any) -> str:
        for attr in (
            "StageName",
            "IFaceStageName",
            "FeedStageName",
            "DrawStageName",
            "Stage",
            "Name",
        ):
            raw = _safe_get(item, attr)
            if raw is None:
                continue
            text = str(raw).strip()
            if not text or text.lower() == str(getattr(item, "Name", "")).lower():
                if attr == "Name":
                    continue
                if not text:
                    continue
            # Prefer labels that look like HYSYS stage tags
            if any(
                t in text
                for t in ("_Main", "Condenser", "_SS", "Reb", "TS", "Stage")
            ) or text[:1].isdigit():
                return text
        stage_num = _safe_get(item, "IFaceStageNumber")
        if stage_num is None:
            stage_num = _safe_get(item, "StageNumber")
        if stage_num is None:
            stage_num = _safe_get(item, "FeedStage")
        if stage_num is not None:
            try:
                return f"{int(stage_num)}_Main TS"
            except Exception:
                pass
        return ""

    def _build_stage_label_map(
        self, column: Any, cfs: Any, ts: Any
    ) -> dict[str, str]:
        """Map stream name (lower) -> Connections stage label."""
        mapping: dict[str, str] = {}

        def _remember(stream_name: Any, label: str) -> None:
            if not stream_name or not label:
                return
            key = str(stream_name).strip().lower()
            if key and key not in mapping:
                mapping[key] = label

        def _probe_collection(coll: Any) -> None:
            if coll is None:
                return
            for item in _items(coll):
                label = self._stage_label_from_attachment(item)
                if not label:
                    stage = _safe_get(item, "IFaceStageNumber")
                    if stage is None:
                        stage = _safe_get(item, "StageNumber")
                    name_hint = str(_safe_get(item, "Name") or _safe_get(item, "StageName") or "")
                    if stage is not None and not name_hint:
                        try:
                            label = f"{int(stage)}_Main TS"
                        except Exception:
                            label = ""
                    elif name_hint:
                        label = name_hint
                for attr in (
                    "StreamName",
                    "FeedName",
                    "ProductName",
                    "AttachedStream",
                    "Stream",
                    "Name",
                ):
                    raw = _safe_get(item, attr)
                    if raw is None:
                        continue
                    try:
                        sname = str(getattr(raw, "Name", raw))
                    except Exception:
                        sname = str(raw)
                    if sname and sname.lower() not in {"name", "none"}:
                        _remember(sname, label)
                        break

        if ts is not None:
            for attr in ("FeedStages", "ProductStages", "DrawStages", "Feeds", "Products"):
                _probe_collection(_safe_get(ts, attr))
        if cfs is not None:
            ops = _safe_get(cfs, "Operations")
            if ops is not None:
                for op in _items(ops):
                    op_name = str(_safe_get(op, "Name") or "")
                    op_type = str(_safe_get(op, "TypeName") or "").lower()
                    # Side stripper / condenser stage tags from unit names
                    stage_guess = ""
                    if "condenser" in op_name.lower() or "condenser" in op_type:
                        stage_guess = "Condenser"
                    elif "_ss" in op_name.lower() or "stripper" in op_type:
                        stage_guess = op_name
                    elif "reb" in op_name.lower():
                        stage_guess = op_name
                    for attr in (
                        "FeedStages",
                        "ProductStages",
                        "AttachedFeeds",
                        "AttachedProducts",
                        "Feeds",
                        "Products",
                    ):
                        coll = _safe_get(op, attr)
                        if coll is None:
                            continue
                        for item in _items(coll):
                            label = self._stage_label_from_attachment(item) or stage_guess
                            sname = str(_safe_get(item, "Name") or "")
                            if not sname:
                                try:
                                    stream = _safe_get(item, "Stream", "AttachedStream")
                                    if stream is not None:
                                        sname = str(stream.Name)
                                except Exception:
                                    pass
                            _remember(sname, label)

        # Known COM named product slots → Condenser / bottom
        for attr, label in (
            ("TopVapourProduct", "Condenser"),
            ("TopLiquidProduct", "Condenser"),
            ("TopWaterProduct", "Condenser"),
            ("BtmLiquidProduct", ""),
        ):
            stream = _safe_get(column, attr)
            if stream is None:
                continue
            try:
                sname = str(stream.Name)
            except Exception:
                continue
            if label:
                _remember(sname, label)
            elif attr == "BtmLiquidProduct":
                # Will be refined after stage numbering / steam stage known
                pass

        return mapping

    def _stream_vapor_fraction(self, name: str) -> float | None:
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(name)
            for attr in ("VapourFraction", "VaporFraction", "MasterVapourFraction"):
                prop = getattr(stream, attr, None)
                if prop is None:
                    continue
                try:
                    if hasattr(prop, "GetValue"):
                        value = float(prop.GetValue())
                    elif hasattr(prop, "Value"):
                        value = float(prop.Value)
                    else:
                        value = float(prop)
                    if not is_sentinel(value):
                        return value
                except Exception:
                    continue
        except Exception:
            return None
        return None

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

    def _stream_flow_display(self, name: str) -> float | None:
        """Molar flow in HYSYS worksheet unit (no Assist conversion)."""
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(name)
        except Exception:
            return None
        unit = self._molar_flow_unit()
        flow = getattr(stream, "MolarFlow", None)
        if flow is not None and unit:
            got = _get_value(flow, unit)
            if got is not None and not is_sentinel(got):
                return got
        raw = _number(stream, "MolarFlowValue", "MolarFlow")
        if raw is None or is_sentinel(raw):
            return None
        return float(raw)

    def _stream_mass_flow_display(self, name: str) -> float | None:
        try:
            stream = self.hysys.flowsheet.MaterialStreams.Item(name)
        except Exception:
            return None
        unit = getattr(self.hysys, "display_units", None)
        mass_u = getattr(unit, "mass_flow", "lb/hr") if unit else "lb/hr"
        flow = getattr(stream, "MassFlow", None)
        if flow is not None:
            got = _get_value(flow, mass_u)
            if got is not None and not is_sentinel(got):
                return got
        raw = _number(stream, "MassFlowValue", "MassFlow")
        if raw is None or is_sentinel(raw):
            return None
        return float(raw)

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

    def add_specification(
        self,
        column_name: str,
        hysys_type_name: str,
        *,
        approved: bool = False,
        new_name: str | None = None,
        allow_when_dof_zero: bool = False,
    ) -> list[str]:
        """
        Try to create a column specification via COM (HYSYS Add Specs dialog types).

        Approval-only — never silent. Prefer HYSYS UI Add… if COM Add is unavailable
        on this HYSYS version (steps via format_add_spec_hysys_steps).
        """
        from column_spec_catalog import format_add_spec_hysys_steps, list_add_spec_names

        if not approved:
            raise HysysError(
                "Add Spec blocked — set approved=True after engineer confirmation."
            )
        names = list_add_spec_names()
        if hysys_type_name not in names:
            raise HysysError(
                f"Unknown Add Spec type '{hysys_type_name}'. "
                f"Must match HYSYS Column Specification Types exactly."
            )

        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        notes: list[str] = []

        dof = _safe_get(cfs, "DegreesOfFreedom")
        try:
            dof_i = int(dof) if dof is not None else None
        except Exception:
            dof_i = None
        if dof_i == 0 and not allow_when_dof_zero:
            steps = format_add_spec_hysys_steps(hysys_type_name, column_hint=column_name)
            raise HysysError(
                "DOF is already 0 — adding an Active spec will over-specify. "
                "Either deactivate one Active first (1-for-1), or confirm "
                "allow_when_dof_zero after you plan to leave the new spec Estimate-only.\n\n"
                + steps
            )

        before = {str(s.Name) for s in _items(cfs.Specifications)}
        specs = _safe_get(cfs, "Specifications")
        if specs is None:
            raise HysysError("No Specifications collection on ColumnFlowsheet.")

        errors: list[str] = []
        created = False

        # Common COM patterns across HYSYS versions
        attempts: list[tuple[str, Any]] = [
            ("Specifications.Add(type)", lambda: specs.Add(hysys_type_name)),
            ("Specifications.Add(type, name)", lambda: specs.Add(hysys_type_name, new_name or hysys_type_name)),
            ("Specifications.Create(type)", lambda: specs.Create(hysys_type_name)),
            ("Specifications.Append(type)", lambda: specs.Append(hysys_type_name)),
        ]
        # Available types collection → Add
        for coll_name in ("AvailableSpecTypes", "SpecTypes", "SpecificationTypes"):
            coll = _safe_get(cfs, coll_name)
            if coll is None:
                coll = _safe_get(specs, coll_name)
            if coll is None:
                continue

            def _add_from_available(c=coll) -> Any:
                # Try Item by name then Add
                try:
                    item = c.Item(hysys_type_name)
                except Exception:
                    item = None
                if item is not None and hasattr(specs, "Add"):
                    try:
                        return specs.Add(item)
                    except Exception:
                        pass
                if hasattr(c, "Add"):
                    return c.Add(hysys_type_name)
                raise RuntimeError(f"{coll_name} present but no Add path")

            attempts.append((f"{coll_name}+Add", _add_from_available))

        for label, fn in attempts:
            try:
                fn()
                notes.append(f"COM path ok: {label}")
                created = True
                break
            except Exception as exc:
                errors.append(f"{label}: {exc}")

        after = {str(s.Name) for s in _items(cfs.Specifications)}
        added = sorted(after - before)
        if added:
            notes.append(f"New spec object(s): {', '.join(added)}")
            if new_name and added:
                # Best-effort rename first new item
                for spec in _items(cfs.Specifications):
                    if str(spec.Name) == added[0] and str(spec.Name) != new_name:
                        try:
                            spec.Name = new_name
                            notes.append(f"Renamed -> {new_name}")
                        except Exception as exc:
                            notes.append(f"Rename skipped: {exc}")
                        break
            created = True

        if not created and not added:
            steps = format_add_spec_hysys_steps(hysys_type_name, column_hint=column_name)
            raise HysysError(
                "COM could not Add Spec on this HYSYS build (Add Specs is UI-first).\n"
                "Use the HYSYS dialog steps below, then Inspect.\n\n"
                + steps
                + "\n\nCOM attempts:\n  - "
                + "\n  - ".join(errors[:8])
            )

        notes.append(
            "Fill Specification Value / stage attach in HYSYS Specs detail; "
            "keep DOF=0 (Estimate-only or 1-for-1 Active swap)."
        )
        return notes

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
        """Request a column / case solve (HYSYS popups captured as PE clues)."""
        from hysys_dialog_watcher import HysysDialogWatcher, remember_clues

        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        errors: list[str] = []

        def _try_run() -> bool:
            for action in (
                lambda: cfs.Run(),
                lambda: column.Run(),
                lambda: self.hysys.solve(),
            ):
                try:
                    action()
                    return True
                except Exception as exc:
                    errors.append(str(exc))
            return False

        watcher = HysysDialogWatcher(auto_dismiss=True)
        watcher.start()
        try:
            ok = _try_run()
        finally:
            clues = watcher.stop()
            remember_clues(clues)
            existing = getattr(self, "last_dialog_clues", [])
            self.last_dialog_clues = list(existing) + list(clues)
            # Continuous Messages pane (warnings + solver trace) — PE clues
            try:
                from hysys_messages_reader import capture_hysys_messages

                case = getattr(self.hysys, "case", None)
                msg_clues = capture_hysys_messages(case)
                self.last_message_clues = list(msg_clues)
            except Exception:
                self.last_message_clues = []

        if not ok:
            raise HysysError("Could not run column: " + " | ".join(errors))

    def apply_structural_move(
        self,
        column_name: str,
        parameter: str,
        proposed: Any,
        *,
        approved: bool = False,
        run_after: bool = True,
    ) -> list[str]:
        """
        Apply one Design → Connections mechanical change.

        **Requires approved=True.** Never silent. Never auto-saves .hsc.
        """
        if not approved:
            raise HysysError(
                "Structural Connections write blocked — set approved=True after PE confirmation."
            )
        notes: list[str] = []
        column = self._column(column_name)
        cfs = self._column_flowsheet(column)
        ts = self._main_tray_section(cfs)
        if ts is None:
            raise HysysError("Could not locate Main tray section for structural write.")

        param = parameter.lower().strip()
        try:
            if param == "feed_stage":
                stage = int(proposed)
                feed_stages = _safe_get(ts, "FeedStages")
                if feed_stages is None:
                    raise HysysError("No FeedStages COM collection on tray section.")
                wrote = False
                for feed in _items(feed_stages):
                    for attr in ("IFaceStageNumber", "StageNumber", "FeedStage"):
                        try:
                            setattr(feed, attr, stage)
                            wrote = True
                            notes.append(f"feed_stage -> {stage} via {attr}")
                            break
                        except Exception:
                            continue
                    if wrote:
                        break
                if not wrote:
                    raise HysysError("Could not write feed stage via COM.")
            elif param == "stage_count":
                n = int(proposed)
                try:
                    ts.NumberOfStages = n
                    notes.append(f"stage_count -> {n}")
                except Exception as exc:
                    raise HysysError(f"Could not set NumberOfStages: {exc}") from exc
            elif param in {"p_cond", "condenser_pressure"}:
                p_bar = float(proposed)
                wrote = False
                for attr in ("TopPressure", "CondenserPressure"):
                    try:
                        setattr(ts, attr, p_bar * 100.0)
                        wrote = True
                        notes.append(f"{param} -> {p_bar} bar (wrote {attr} as kPa)")
                        break
                    except Exception:
                        try:
                            setattr(ts, attr, p_bar)
                            wrote = True
                            notes.append(f"{param} -> {p_bar} (wrote {attr} as-is)")
                            break
                        except Exception:
                            continue
                if not wrote:
                    raise HysysError("Could not write condenser pressure via COM.")
            elif param in {"p_reb", "reboiler_pressure"}:
                p_bar = float(proposed)
                wrote = False
                for attr in ("BottomPressure", "ReboilerPressure"):
                    try:
                        setattr(ts, attr, p_bar * 100.0)
                        wrote = True
                        notes.append(f"{param} -> {p_bar} bar (wrote {attr} as kPa)")
                        break
                    except Exception:
                        try:
                            setattr(ts, attr, p_bar)
                            wrote = True
                            notes.append(f"{param} -> {p_bar} (wrote {attr} as-is)")
                            break
                        except Exception:
                            continue
                if not wrote:
                    raise HysysError("Could not write reboiler pressure via COM.")
            elif param in {"condenser_type", "inlet_stream"}:
                raise HysysError(
                    f"'{param}' is MANUAL in HYSYS Design → Connections (not COM-auto)."
                )
            else:
                raise HysysError(f"Unknown structural parameter: {parameter}")
        except HysysError:
            raise
        except Exception as exc:
            raise HysysError(f"Structural apply failed: {exc}") from exc

        if run_after:
            try:
                self.run_column(column_name)
                notes.append("column run requested after structural change")
            except HysysError as exc:
                notes.append(f"run after structural change: {exc}")
        return notes
