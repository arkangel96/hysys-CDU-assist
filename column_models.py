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
    STATE_B_NUMERICAL = "state_b_numerical"
    FINAL_TARGET_MISS = "final_target_miss"
    OPERABILITY_FAIL = "operability_fail"
    LIKELY_INFEASIBLE = "likely_infeasible"


class EngineeringState(str, Enum):
    """Expert workflow States A–F."""

    A_INVALID = "A_invalid_model"
    B_NUMERICAL = "B_numerical"
    C_OFF_SPEC = "C_off_specification"
    D_CONSTRAINT = "D_constraints_violated"
    E_ACCEPTABLE = "E_acceptable"
    F_INFEASIBLE = "F_likely_infeasible"


class ResponseClass(str, Enum):
    CONVERGED_IMPROVED = "CONVERGED_IMPROVED"
    CONVERGED_STRONGLY_IMPROVED = "CONVERGED_STRONGLY_IMPROVED"
    CONVERGED_NO_MATERIAL_CHANGE = "CONVERGED_NO_MATERIAL_CHANGE"
    CONVERGED_WORSENED = "CONVERGED_WORSENED"
    CONVERGED_CONSTRAINT_VIOLATED = "CONVERGED_CONSTRAINT_VIOLATED"
    UNCONVERGED_RECOVERABLE = "UNCONVERGED_RECOVERABLE"
    UNCONVERGED_REPEATED = "UNCONVERGED_REPEATED"
    INVALID_STATE = "INVALID_STATE"
    TARGET_MET = "TARGET_MET"
    STOP_INFEASIBLE = "STOP_INFEASIBLE"


@dataclass(slots=True)
class FinalTarget:
    """External product requirement — separate from HYSYS Active specs."""

    id: str
    description: str
    spec_name_contains: str
    component_name_contains: tuple[str, ...]
    stream: str = "bottoms"  # bottoms | overhead
    relationship: str = "less_or_equal"  # less_or_equal | greater_or_equal | equal
    target_value: float = 0.0
    tolerance: float = 0.0
    locked: bool = True
    hard: bool = True


def default_cdu_targets() -> list[FinalTarget]:
    """Placeholder FINAL_TARGETs for CDU — configure per case after COM discovery.

    Cut / ASTM / TBP targets are case-specific. Until Phase 1 discovery, return
    an empty list so Assist does not invent stripper NH3 purity targets.
    """
    return []


def default_sw_stripper_targets() -> list[FinalTarget]:
    """Deprecated alias — CDU Assist no longer defaults to NH3 stripper targets."""
    return default_cdu_targets()


@dataclass(slots=True)
class ColumnSpecState:
    name: str
    type_name: str = ""
    is_active: bool = False
    use_as_estimate: bool | None = None
    use_as_current: bool | None = None
    goal_value: float | None = None
    current_value: float | None = None
    error: float | None = None
    weighted_tolerance: float | None = None
    # Worksheet-style display (e.g. kgmole/h for rate specs)
    goal_display: float | None = None
    current_display: float | None = None
    display_unit: str = ""
    role: SpecRole = SpecRole.CALCULATED
    # Specs Summary: Current column often tracks with Active for fixed primary specs
    summary_current: bool | None = None

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
    feed_stage_label: str = ""
    stage_numbering: str = ""
    degrees_of_freedom: int | None = None
    reflux_ratio: float | None = None
    top_vapour_product: str | None = None
    bottoms_liquid_product: str | None = None
    feed_streams: list[str] = field(default_factory=list)
    product_streams: list[str] = field(default_factory=list)
    energy_streams: list[str] = field(default_factory=list)
    # Design → Connections (READ)
    condenser_type: str = ""
    condenser_pressure_bar: float | None = None
    reboiler_pressure_bar: float | None = None
    condenser_dp_bar: float | None = None
    reboiler_dp_bar: float | None = None
    # Design → Monitor solver summary (READ)
    monitor_iteration: int | None = None
    monitor_step: float | None = None
    monitor_equilibrium_error: float | None = None
    monitor_heat_spec_error: float | None = None
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
    # Product / display enrichment (Layer 2 intelligence)
    bottoms_nh3_mass_frac: float | None = None
    overhead_molar_flow_kgmole_h: float | None = None
    bottoms_molar_flow_kgmole_h: float | None = None
    physical_solution: bool = False

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
    engineering_state: EngineeringState = EngineeringState.C_OFF_SPEC
    pe_read: str = ""
    potential: str = ""  # going_somewhere | marginal | nowhere | success
    final_target_status: dict[str, Any] = field(default_factory=dict)
    add_spec_recommendations: list[str] = field(default_factory=list)
    specs_summary_clicks: list[str] = field(default_factory=list)
    expert_context: Any = None  # cdu_expert_engine.ExpertContext when built
    product_quality: Any = None  # cdu_quality_engine.ProductQualityState
    spec_philosophy: Any = None  # cdu_spec_philosophy.SpecPhilosophyReport
    case_objective: str = ""
    interactive_only: bool = True


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
    response_class: ResponseClass | None = None
    pe_board: str = ""


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
    # Layer 2 intelligence policy
    allow_relax_final_targets: bool = False
    allow_baseline_spec_swap: bool = True
    min_bottoms_flow_kgmole_h: float = 1.0  # operability gate (worksheet)
    weak_response_relative: float = 0.02  # <2% change = no material change

