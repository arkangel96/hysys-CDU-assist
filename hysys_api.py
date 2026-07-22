from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from models import OperationData, StreamData
from hysys_units import HysysDisplayUnits, discover_display_units


class HysysError(RuntimeError):
    """Raised when HYSYS cannot complete an automation request."""


class HysysController:
    PROG_IDS = ("HYSYS.Application", "HYSYS.Application.V15")

    def __init__(self) -> None:
        self.app: Any = None
        self.case: Any = None
        self.flowsheet: Any = None
        self.connected = False
        self.component_names: list[str] = []
        self.display_units = HysysDisplayUnits()

    def connect(self, case_path: str | None = None) -> None:
        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise HysysError("Live HYSYS connectivity requires Windows and pywin32.") from exc

        pythoncom.CoInitialize()
        errors: list[str] = []
        app = None
        for prog_id in self.PROG_IDS:
            try:
                app = win32com.client.GetActiveObject(prog_id)
                break
            except Exception as exc:
                errors.append(f"attach {prog_id}: {exc}")
        if app is None:
            for prog_id in self.PROG_IDS:
                try:
                    app = win32com.client.Dispatch(prog_id)
                    app.Visible = True
                    break
                except Exception as exc:
                    errors.append(f"start {prog_id}: {exc}")
        if app is None:
            raise HysysError("Could not attach to or start Aspen HYSYS. " + " | ".join(errors))

        try:
            if case_path:
                path = str(Path(case_path).resolve())
                self.case = app.SimulationCases.Open(path)
            else:
                self.case = self._active_case(app)
            if self.case is None:
                raise HysysError("HYSYS is running, but no simulation case is open.")
            self.app = app
            self.flowsheet = self.case.Flowsheet
            self.connected = True
            self.component_names = self.get_component_names()
            self.refresh_display_units()
        except Exception:
            self.disconnect()
            raise

    def refresh_display_units(self) -> HysysDisplayUnits:
        """Copy Temperature/Pressure/Flow units from the open HYSYS case."""
        if self.flowsheet is None:
            self.display_units = HysysDisplayUnits()
            return self.display_units
        self.display_units = discover_display_units(self.flowsheet)
        return self.display_units

    @staticmethod
    def _active_case(app: Any) -> Any:
        for getter in (
            lambda: app.ActiveDocument,
            lambda: app.SimulationCases.Item(0),
        ):
            try:
                case = getter()
                if case is not None:
                    return case
            except Exception:
                continue
        return None

    def disconnect(self) -> None:
        self.connected = False
        self.flowsheet = None
        self.case = None
        self.app = None
        self.component_names = []
        self.display_units = HysysDisplayUnits()

    def _require_connection(self) -> None:
        if not self.connected or self.flowsheet is None:
            raise HysysError("Not connected to a HYSYS case.")

    @staticmethod
    def _items(collection: Any) -> Iterable[Any]:
        count = int(collection.Count)
        for index in range(count):
            try:
                yield collection.Item(index)
            except Exception:
                # Some COM collections are one-based.
                yield collection.Item(index + 1)

    def get_component_names(self) -> list[str]:
        self._require_connection()
        candidates = (
            lambda: self.flowsheet.FluidPackage.Components,
            lambda: self.case.BasisManager.FluidPackages.Item(0).Components,
        )
        for getter in candidates:
            try:
                names = [str(item.Name) for item in self._items(getter())]
                if names:
                    return names
            except Exception:
                continue
        return []

    def set_components_manually(self, value: str) -> list[str]:
        self.component_names = [part.strip() for part in value.split(",") if part.strip()]
        return self.component_names

    def get_stream_objects(self) -> dict[str, Any]:
        self._require_connection()
        result: dict[str, Any] = {}
        for stream in self._items(self.flowsheet.MaterialStreams):
            name = str(stream.Name)
            if name:
                result[name] = stream
        return result

    @staticmethod
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

    # Worksheet display units — filled from HYSYS on connect (see display_units).
    # Kept as class defaults for fallback before connect.
    DISPLAY_UNITS = {
        "Temperature": "C",
        "Pressure": "bar",
        "Molar Flow": "kgmole/h",
        "Mass Flow": "kg/h",
    }
    PROPERTY_OBJECTS = {
        "Temperature": "Temperature",
        "Pressure": "Pressure",
        "Molar Flow": "MolarFlow",
        "Mass Flow": "MassFlow",
    }

    def _active_display_units(self) -> dict[str, str]:
        return self.display_units.as_display_map()

    @classmethod
    def _get_in_unit(cls, stream: Any, property_object: str, unit: str) -> float | None:
        try:
            prop = getattr(stream, property_object)
            return float(prop.GetValue(unit))
        except Exception:
            # Fallback to raw Value (may be SI)
            return cls._number(stream, property_object + "Value", property_object)

    def get_stream_data(self, stream: Any) -> StreamData:
        name = str(getattr(stream, "Name", "Unknown"))
        units = self._active_display_units()
        t_u = units["Temperature"]
        p_u = units["Pressure"]
        n_u = units["Molar Flow"]
        m_u = units["Mass Flow"]
        return StreamData(
            name=name,
            temperature=self._get_in_unit(stream, "Temperature", t_u),
            pressure=self._get_in_unit(stream, "Pressure", p_u),
            molar_flow=self._get_in_unit(stream, "MolarFlow", n_u),
            mass_flow=self._get_in_unit(stream, "MassFlow", m_u),
            composition=self.get_stream_composition(stream),
            temperature_unit=t_u,
            pressure_unit=p_u,
            molar_flow_unit=n_u,
            mass_flow_unit=m_u,
        )

    def get_stream_composition(self, stream: Any) -> dict[str, float]:
        if not self.component_names:
            return {}
        values = None
        for getter in (
            lambda: stream.ComponentMolarFractionValue,
            lambda: stream.ComponentMolarFraction.Values,
        ):
            try:
                values = list(getter())
                break
            except Exception:
                continue
        if values is None:
            return {}
        return {
            name: float(values[index])
            for index, name in enumerate(self.component_names)
            if index < len(values)
        }

    def set_stream_value(self, stream_name: str, property_name: str, value: float) -> None:
        self._require_connection()
        prop_name = self.PROPERTY_OBJECTS.get(property_name)
        unit = self._active_display_units().get(property_name)
        if prop_name is None or unit is None:
            raise HysysError(f"Unsupported stream property: {property_name}")
        try:
            stream = self.flowsheet.MaterialStreams.Item(stream_name)
            prop = getattr(stream, prop_name)
            prop.SetValue(float(value), unit)
        except Exception as exc:
            raise HysysError(
                f"HYSYS rejected {property_name} for stream {stream_name}. "
                "The property may be calculated by another specification or operation."
            ) from exc

    def get_operations(self) -> list[OperationData]:
        self._require_connection()
        operations: list[OperationData] = []
        for operation in self._items(self.flowsheet.Operations):
            name = str(getattr(operation, "Name", "Unknown"))
            operation_type = self._text_member(operation, "OperType", "OperationType", "TypeName")
            solved = self._bool_member(operation, "IsSolved", "Solved", "SolveStatus", "Status")
            operations.append(OperationData(name, operation_type, solved))
        return operations

    @staticmethod
    def _text_member(obj: Any, *members: str) -> str:
        for member in members:
            try:
                return str(getattr(obj, member))
            except Exception:
                continue
        return "Unknown"

    @staticmethod
    def _bool_member(obj: Any, *members: str) -> bool | None:
        for member in members:
            try:
                value = getattr(obj, member)
                if hasattr(value, "Value"):
                    value = value.Value
                return bool(value)
            except Exception:
                continue
        return None

    def solve(self) -> None:
        self._require_connection()
        errors: list[str] = []
        for action in (
            lambda: self.case.Solver.Solve(),
            lambda: setattr(self.case.Solver, "CanSolve", True),
            lambda: self.case.Solve(),
        ):
            try:
                action()
                return
            except Exception as exc:
                errors.append(str(exc))
        raise HysysError("Could not request a HYSYS solve: " + " | ".join(errors))

