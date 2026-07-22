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
    component_name_contains: tuple[str, ...] = ()
    stream: str = "bottoms"  # bottoms | overhead | product | spec
    relationship: str = "less_or_equal"  # less_or_equal | greater_or_equal | equal
    target_value: float = 0.0
    tolerance: float = 0.0
    locked: bool = True
    hard: bool = True
    # CDU: astm_d86 | tbp | cut | gap | cold_prop | composition | other
    property_type: str = "composition"


def default_cdu_targets() -> list[FinalTarget]:
    """
    Atmospheric CDU multi-product FINAL_TARGETs.

    Loads enabled rows from config/cdu_final_targets.json when present.
    Otherwise empty — Assist classifies States A–F on DOF / physics /
    operability; quality State C/E gates activate when targets are provided.
    Never invents NH3 / stripper purity targets.
    """
    try:
        from cdu_targets import load_cdu_final_targets

        return load_cdu_final_targets()
    except Exception:
        return []


def default_final_targets(*, product_line: str = "cdu") -> list[FinalTarget]:
    """CDU Assist FINAL_TARGET factory — atmospheric crude only."""
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
    # Worksheet-style display (copy HYSYS Monitor units — USGPM / Btu/hr / lbmole/hr)
    goal_display: float | None = None
    current_display: float | None = None
    display_unit: str = ""
    # CDU Monitor MV family (side_draw | pa_rate | pa_duty | ...)
    mv_family: str = ""
    role: SpecRole = SpecRole.CALCULATED
    # Specs Summary: Current column often tracks with Active for fixed primary specs
    summary_current: bool | None = None
    # Design → Specs detail pane (T-100 Specs page)
    dry_flow_basis: bool | None = None
    fixed_or_ranged: str = ""  # Fixed | Ranged | ""
    primary_or_alternate: str = ""  # Primary | Alternate | ""
    absolute_tolerance: float | None = None
    absolute_error: float | None = None
    spec_converged: bool | None = None
    # Specs Summary ranged bounds (Lower / Upper) — empty when Fixed
    lower_bound: float | None = None
    upper_bound: float | None = None

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
class SideStripperRow:
    """Design → Side Ops → Side Strippers table row."""

    name: str
    num_stages: int | None = None
    liq_draw_stage: str = ""
    vap_return_stage: str = ""
    outlet_flow: float | None = None
    reboiler_duty: float | None = None


@dataclass(slots=True)
class SideRectifierRow:
    """Design → Side Ops → Side Rectifiers table row."""

    name: str
    num_stages: int | None = None
    vap_draw_stage: str = ""
    liq_return_stage: str = ""
    vap_prod_flow: float | None = None
    condenser_duty: float | None = None


@dataclass(slots=True)
class PumpAroundRow:
    """Design → Side Ops → Pump Arounds table row."""

    name: str
    draw_stage: str = ""
    return_stage: str = ""
    flow: float | None = None
    duty: float | None = None
    draw_temperature: float | None = None
    return_temperature: float | None = None
    export: bool = False


@dataclass(slots=True)
class SideDrawRow:
    """Design → Side Ops → Side Draws table row."""

    stream_name: str
    draw_stage: str = ""
    phase_type: str = ""  # L | V | W
    mole_flow: float | None = None
    mass_flow: float | None = None


@dataclass(slots=True)
class TowerSizingRow:
    """Rating → Towers tower sizing section."""

    section_name: str
    uniform_section: bool | None = None
    internal_type: str = ""
    diameter: float | None = None
    tray_packed_space: float | None = None
    tray_packed_volume: float | None = None
    heat_model: str = ""
    rating_calculations: bool | None = None
    hold_up: float | None = None
    weeping_factor: float | None = None
    sizing_analysis_tag: str = ""


@dataclass(slots=True)
class VesselSizingRow:
    """Rating → Vessels row."""

    vessel_name: str
    diameter: float | None = None
    length: float | None = None
    volume: float | None = None
    orientation: str = ""
    has_boot: bool | None = None
    include_for_costing: bool | None = None


@dataclass(slots=True)
class RatingEquipmentRow:
    """Rating → Equipment list item."""

    name: str
    type_name: str = ""


@dataclass(slots=True)
class RatingPressureRow:
    """Rating → Pressure Drop stage row."""

    stage_label: str
    pressure: float | None = None
    pressure_drop: float | None = None


@dataclass(slots=True)
class RatingPressureSolver:
    """Rating → Pressure Drop solver options."""

    pressure_tolerance: float | None = None
    pressure_drop_tolerance: float | None = None
    damping_factor: float | None = None
    max_press_iterations: int | None = None


@dataclass(slots=True)
class ConnectionStreamRow:
    """One Design → Connections inlet/outlet row (HYSYS table shape)."""

    name: str
    external_name: str = ""
    stage_label: str = ""
    phase_type: str = ""  # L | V | W | Q | ""
    direction: str = "inlet"  # inlet | outlet
    role: str = "unknown"
    # crude_feed | stripping_steam | energy_in | residue | naphtha | offgas |
    # waste_water | side_product | pa_energy | condenser_duty | unknown

    def display_line(self) -> str:
        stage = self.stage_label or "—"
        if self.direction == "outlet" and self.phase_type:
            return f"{self.name} @ {stage} | {self.phase_type}"
        return f"{self.name} @ {stage}"


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
    # Design → Connections (READ) — full table rows (T-100 CDU shape)
    inlet_rows: list[ConnectionStreamRow] = field(default_factory=list)
    outlet_rows: list[ConnectionStreamRow] = field(default_factory=list)
    steam_streams: list[str] = field(default_factory=list)
    side_products: list[str] = field(default_factory=list)
    pa_energy_streams: list[str] = field(default_factory=list)
    overhead_liquid_product: str | None = None
    cdu_topology: bool = False
    # Design → Monitor Active families (from spec names)
    active_side_draw_specs: list[str] = field(default_factory=list)
    active_pa_rate_specs: list[str] = field(default_factory=list)
    active_pa_duty_specs: list[str] = field(default_factory=list)
    volume_flow_unit: str = "USGPM"
    energy_unit: str = "Btu/hr"
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
    # Design → Specs page (list + detail pane)
    default_spec_basis: str = ""  # Molar | Mass | ...
    # Design → Subcooling (condenser)
    condenser_subcool_degrees: float | None = None
    condenser_subcool_to: float | None = None
    condenser_subcool_to_mode: str = ""
    # Design → Side Ops (READ)
    side_ops_flow_basis: str = ""  # Molar | Mass | Volume
    side_strippers: list[SideStripperRow] = field(default_factory=list)
    side_rectifiers: list[SideRectifierRow] = field(default_factory=list)
    pump_arounds: list[PumpAroundRow] = field(default_factory=list)
    side_draws: list[SideDrawRow] = field(default_factory=list)
    # Rating tab (READ)
    rating_length_unit: str = "ft"
    rating_volume_unit: str = "ft3"
    rating_pressure_drop_unit: str = "psi"
    rating_towers: list[TowerSizingRow] = field(default_factory=list)
    rating_vessels: list[VesselSizingRow] = field(default_factory=list)
    rating_equipment: list[RatingEquipmentRow] = field(default_factory=list)
    rating_pressure_rows: list[RatingPressureRow] = field(default_factory=list)
    rating_pressure_solver: RatingPressureSolver = field(default_factory=RatingPressureSolver)
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
    # Worksheet molar flows (field name historical; values use molar_flow_unit)
    overhead_molar_flow_kgmole_h: float | None = None
    bottoms_molar_flow_kgmole_h: float | None = None
    physical_solution: bool = False
    # Copied from open HYSYS case (no Assist-side conversion)
    temperature_unit: str = "C"
    pressure_unit: str = "bar"
    molar_flow_unit: str = "kgmole/h"
    mass_flow_unit: str = "kg/h"

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
    # Multi-variable intelligence (not RR-only)
    preferred_family: str = ""  # A_init | B_energy | C_split | D_target | E_feed | F_structural
    pe_hypothesis: str = ""
    # HYSYS modal popup clues captured during solve
    hysys_dialog_clues: list[str] = field(default_factory=list)
    # Continuous Messages window clues (warnings / solver trace)
    hysys_message_clues: list[str] = field(default_factory=list)
    # Design → Connections structural proposals (Family F — approval-only)
    structural_recommendations: list[str] = field(default_factory=list)
    # Optional expert-engine overlay (merged CDU modules) — never block core chooser
    expert_context: Any | None = None


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
    # Layer 2+ multi-variable intelligence policy
    allow_relax_final_targets: bool = False
    allow_baseline_spec_swap: bool = True
    min_bottoms_flow_kgmole_h: float = 1.0  # operability gate (worksheet)
    weak_response_relative: float = 0.02  # <2% change = no material change
    flat_product_relative: float = 0.02  # product move below this = flat
    max_flat_trials_before_f: int = 2  # flat product trials → State F evidence
    rate_nudge_fraction: float = 0.05
    require_profile_for_state_e: bool = False  # optional tighter State E

