"""
Copy display units from the open HYSYS case (no Assist-side unit conversion).

Policy (binding):
- Use whatever unit set HYSYS shows for the open case (Field, SI, …).
- Do **not** hard-code metric↔imperial factors in Assist.
- When COM returns calculation-unit values, ask HYSYS
  ``UnitConversionSet.FromCalculationUnit`` / ``RealVariable.GetValue(display)``
  so the number matches the worksheet.

Reads preferred unit labels from stream RealVariables, then uses
GetValue(unit) / SetValue(value, unit) so HYSYS performs any conversion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# UnitConversionSetManager name → index (Aspen HYSYS steady-state)
_UCS_TEMPERATURE = 1
_UCS_DELTA_TEMP = 24


# Fallbacks only if HYSYS does not expose a unit label on the property.
_FALLBACK = {
    "Temperature": ("F", "C", "K", "R"),
    "Pressure": ("psia", "psig", "bar", "bara", "barg", "kPa", "atm", "Pa"),
    "MolarFlow": ("lbmole/hr", "lbmol/h", "lbmole/h", "kgmole/h", "kmole/h", "mol/h", "lbmol/s", "kgmole/s"),
    "MassFlow": ("lb/h", "kg/h", "lb/s", "kg/s"),
    "StdIdealLiqVolFlow": ("USGPM", "USgal/min", "gpm", "barrel/day", "m3/h", "m3/s"),
    "LiquidVolumeFlow": ("USGPM", "USgal/min", "gpm", "barrel/day", "m3/h", "m3/s"),
    "HeatFlow": ("Btu/hr", "Btu/h", "MMBtu/hr", "kJ/h", "kW", "MJ/h"),
}


@dataclass(slots=True)
class HysysDisplayUnits:
    temperature: str = "C"
    pressure: str = "bar"
    molar_flow: str = "kgmole/h"
    mass_flow: str = "kg/h"
    volume_flow: str = "USGPM"
    energy: str = "Btu/hr"
    source: str = "fallback"

    def as_display_map(self) -> dict[str, str]:
        return {
            "Temperature": self.temperature,
            "Pressure": self.pressure,
            "Molar Flow": self.molar_flow,
            "Mass Flow": self.mass_flow,
            "Volume Flow": self.volume_flow,
            "Energy": self.energy,
        }


def _unit_label(prop: Any) -> str | None:
    """Best-effort read of the unit string HYSYS shows for a RealVariable."""
    if prop is None:
        return None
    for attr in ("Units", "Unit", "DisplayUnits", "UnitName", "units"):
        try:
            raw = getattr(prop, attr)
        except Exception:
            continue
        if raw is None:
            continue
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
        for nested in ("Name", "DisplayName", "UnitName", "Symbol", "ShortName"):
            try:
                name = getattr(raw, nested)
                if name is not None and str(name).strip():
                    return str(name).strip()
            except Exception:
                continue
        try:
            text = str(raw).strip()
            if text and not text.startswith("<") and text.lower() != "none":
                return text
        except Exception:
            continue
    return None


def _get_value(prop: Any, unit: str) -> float | None:
    try:
        return float(prop.GetValue(unit))
    except Exception:
        return None


def _pick_working_unit(prop: Any, candidates: tuple[str, ...]) -> str | None:
    label = _unit_label(prop)
    if label:
        # Prefer exact label if GetValue accepts it
        if _get_value(prop, label) is not None:
            return label
        # Sometimes label is "F" but GetValue wants "deg F" etc. — still return label;
        # caller will fall back if GetValue fails.
        for c in candidates:
            if c.lower() == label.lower() and _get_value(prop, c) is not None:
                return c
        return label
    for c in candidates:
        if _get_value(prop, c) is not None:
            return c
    return None


def discover_display_units(flowsheet: Any) -> HysysDisplayUnits:
    """
    Sample the first material stream and copy its property units from HYSYS.
    """
    units = HysysDisplayUnits(source="fallback")
    try:
        streams = flowsheet.MaterialStreams
        if int(streams.Count) < 1:
            return units
        try:
            stream = streams.Item(0)
        except Exception:
            stream = streams.Item(1)
    except Exception:
        return units

    found = 0
    mapping = (
        ("Temperature", "temperature", _FALLBACK["Temperature"]),
        ("Pressure", "pressure", _FALLBACK["Pressure"]),
        ("MolarFlow", "molar_flow", _FALLBACK["MolarFlow"]),
        ("MassFlow", "mass_flow", _FALLBACK["MassFlow"]),
    )
    for prop_name, field, candidates in mapping:
        try:
            prop = getattr(stream, prop_name)
        except Exception:
            prop = None
        picked = _pick_working_unit(prop, candidates)
        if picked:
            setattr(units, field, picked)
            found += 1

    # Volume / energy — probe common RealVariable names (first working unit wins)
    vol_set = False
    energy_set = False
    for prop_name, field, candidates in (
        ("StdIdealLiqVolFlow", "volume_flow", _FALLBACK["StdIdealLiqVolFlow"]),
        ("LiquidVolumeFlow", "volume_flow", _FALLBACK["LiquidVolumeFlow"]),
        ("IdealLiquidVolumeFlow", "volume_flow", _FALLBACK["LiquidVolumeFlow"]),
        ("HeatFlow", "energy", _FALLBACK["HeatFlow"]),
        ("Energy", "energy", _FALLBACK["HeatFlow"]),
    ):
        if field == "volume_flow" and vol_set:
            continue
        if field == "energy" and energy_set:
            continue
        try:
            prop = getattr(stream, prop_name)
        except Exception:
            prop = None
        picked = _pick_working_unit(prop, candidates)
        if picked:
            setattr(units, field, picked)
            found += 1
            if field == "volume_flow":
                vol_set = True
            else:
                energy_set = True

    units.source = "hysys_stream" if found else "fallback"
    return units


def scale_si_to_display(prop: Any, si_value: float | None, display_unit: str) -> float | None:
    """
    Map a COM SI-ish raw value to worksheet display using HYSYS GetValue ratio.

    Prefer ``from_calculation_to_display`` for absolute temperatures — ratio
    scaling is wrong across C/F offset. Kept for flow/energy RealVariables.
    """
    if si_value is None:
        return None
    try:
        si_value = float(si_value)
    except Exception:
        return None
    display = _get_value(prop, display_unit)
    if display is None:
        return None
    try:
        raw = float(getattr(prop, "Value", None))
    except Exception:
        raw = None
    if raw is None or abs(raw) < 1e-30:
        # Cannot form ratio — if |si| looks like already-display, return as-is
        return si_value
    return si_value * (display / raw)


def _unit_conversion_set(app: Any, set_index: int) -> Any | None:
    try:
        return app.UnitConversionSetManager.GetUnitConversionSet(int(set_index))
    except Exception:
        return None


def current_display_unit(app: Any, set_index: int = _UCS_TEMPERATURE) -> str | None:
    """HYSYS CurrentDisplayUnit for a unit set (e.g. Temperature → ``F``)."""
    ucs = _unit_conversion_set(app, set_index)
    if ucs is None:
        return None
    try:
        return str(ucs.CurrentDisplayUnit)
    except Exception:
        return None


def from_calculation_to_display(
    app: Any,
    value: float | None,
    *,
    set_index: int = _UCS_TEMPERATURE,
    display_unit: str | None = None,
) -> float | None:
    """
    Convert a HYSYS **calculation-unit** number to the case **display** unit.

    Uses HYSYS ``Unit.FromCalculationUnit`` — no Assist °C/°F algebra.
    """
    if value is None or app is None:
        return None
    try:
        value = float(value)
    except Exception:
        return None
    ucs = _unit_conversion_set(app, set_index)
    if ucs is None:
        return None
    unit_name = display_unit or current_display_unit(app, set_index)
    if not unit_name:
        return None
    try:
        for i in range(int(ucs.Count)):
            u = ucs.Item(i)
            if str(getattr(u, "Name", "")).lower() == str(unit_name).lower():
                return float(u.FromCalculationUnit(value))
    except Exception:
        return None
    return None


def temperature_to_display(app: Any, calc_value: float | None) -> float | None:
    """Absolute temperature: calculation unit → CurrentDisplayUnit (Temperature set)."""
    return from_calculation_to_display(app, calc_value, set_index=_UCS_TEMPERATURE)


def delta_temperature_to_display(app: Any, calc_delta: float | None) -> float | None:
    """Temperature difference (gaps): calculation → display via Delta Temp. set."""
    return from_calculation_to_display(app, calc_delta, set_index=_UCS_DELTA_TEMP)
