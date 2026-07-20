"""Data models for external distillation-column convergence assistance."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SpecRole(str, Enum):
    ACTIVE_SPEC = "active_spec"
    INACTIVE_ESTIMATE = "inactive_estimate"
    CALCULATED = "calculated"


class DiagnosisCode(str, Enum):
    CONVERGED = "converged"
    UNDER_SPECIFIED = "under_specified"
    OVER_SPECIFIED = "over_specified"
    SPEC_ERROR_HIGH = "spec_error_high"
    POOR_ESTIMATES = "poor_estimates"
    PROFILE_UNPHYSICAL = "profile_unphysical"
    DUTY_EXTREME = "duty_extreme"
    PHASE_SUSPECT = "phase_suspect"
    UNKNOWN_FAILURE = "unknown_failure"


@dataclass(slots=True)
class ColumnSpecState:
    name: str
    type_name: str = ""
    is_active: bool = False
    goal_value: float | None = None
    current_value: float | None = None
    error: float | None = None
    role: SpecRole = SpecRole.CALCULATED

    def score_error(self) -> float:
        if self.error is None:
            return 0.0
        if abs(self.error) >= 1e4:
            return 0.0
        return abs(float(self.error))


@dataclass(slots=True)
class StageProfile:
    temperatures: list[float] = field(default_factory=list)
    pressures: list[float] = field(default_factory=list)


@dataclass(slots=True)
class ColumnSnapshot:
    column_name: str
    degrees_of_freedom: int
    reflux_ratio: float | None
    specs: list[dict[str, Any]] = field(default_factory=list)
    solver: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ColumnState:
    name: str
    flowsheet_tag: str = ""
    type_name: str = "distillation"
    number_of_stages: int | None = None
    feed_stage: int | None = None
    degrees_of_freedom: int | None = None
    reflux_ratio: float | None = None
    top_vapour_product: str | None = None
    bottoms_liquid_product: str | None = None
    feed_streams: list[str] = field(default_factory=list)
    product_streams: list[str] = field(default_factory=list)
    energy_streams: list[str] = field(default_factory=list)
    specs: list[ColumnSpecState] = field(default_factory=list)
    profile: StageProfile = field(default_factory=StageProfile)
    condenser_duty: float | None = None
    reboiler_duty: float | None = None
    overhead_molar_flow: float | None = None
    bottoms_molar_flow: float | None = None
    overhead_temperature: float | None = None
    bottoms_temperature: float | None = None
    max_active_spec_error: float = 0.0
    sum_active_spec_error: float = 0.0
    appears_converged: bool = False
    notes: list[str] = field(default_factory=list)

    def active_specs(self) -> list[ColumnSpecState]:
        return [s for s in self.specs if s.is_active]

    def inactive_specs(self) -> list[ColumnSpecState]:
        return [s for s in self.specs if not s.is_active]


@dataclass(slots=True)
class Diagnosis:
    codes: list[DiagnosisCode] = field(default_factory=list)
    summary: str = ""
    recommended_strategy: str = ""
    details: list[str] = field(default_factory=list)
    severity: str = "info"


@dataclass(slots=True)
class TrialAction:
    kind: str
    description: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TrialResult:
    action: TrialAction
    before_score: float
    after_score: float
    kept: bool
    message: str
    after_state: ColumnState | None = None


@dataclass(slots=True)
class ConvergenceLimits:
    max_iterations: int = 12
    max_active_spec_error: float = 5e-4
    min_reflux_ratio: float = 0.05
    max_reflux_ratio: float = 100.0
    max_duty_abs: float = 5e7
    max_temperature_c: float = 400.0
    min_temperature_c: float = -50.0
    reflux_nudge_fraction: float = 0.05
    damping_min: float = 0.1
    damping_max: float = 1.0
    damping_step: float = 0.1
