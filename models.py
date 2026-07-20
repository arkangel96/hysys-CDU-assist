from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class StreamData:
    name: str
    temperature: float | None = None
    pressure: float | None = None
    molar_flow: float | None = None
    mass_flow: float | None = None
    composition: dict[str, float] = field(default_factory=dict)
    # Display units matching typical HYSYS worksheet (not internal SI)
    temperature_unit: str = "C"
    pressure_unit: str = "bar"
    molar_flow_unit: str = "kgmole/h"
    mass_flow_unit: str = "kg/h"


@dataclass(slots=True)
class OperationData:
    name: str
    operation_type: str = "Unknown"
    is_solved: bool | None = None

