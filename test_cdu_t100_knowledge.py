"""Tests for T-100 UI knowledge → expert routing."""
from __future__ import annotations

from cdu_case_config import load_case_config
from cdu_expert_engine import build_expert_context, generate_hypotheses
from cdu_t100_knowledge import (
    build_subsystem_routed_seeds,
    dominant_subsystem,
    specs_for_strategy,
    validate_t100_specs_summary,
)
from column_models import ColumnSpecState, ColumnState, ConvergenceLimits, EngineeringState


def _t100_state_c() -> ColumnState:
    return ColumnState(
        name="T-100",
        degrees_of_freedom=0,
        physical_solution=True,
        appears_converged=True,
        max_active_spec_error=0.05,
        specs=[
            ColumnSpecState(
                name="Diesel_SS Prod Flow",
                is_active=True,
                goal_value=100.0,
                error=0.04,
            ),
            ColumnSpecState(
                name="PA_2_Rate(Pa)",
                is_active=True,
                goal_value=875.0,
                error=0.001,
            ),
            ColumnSpecState(
                name="PA_2_Duty(Pa)",
                is_active=True,
                goal_value=-3.5e7,
                error=0.0,
            ),
            ColumnSpecState(name="Reflux Ratio", is_active=False, goal_value=1.0),
        ],
    )


def test_dominant_subsystem_diesel() -> None:
    assert dominant_subsystem(_t100_state_c()) == "diesel_section"


def test_prefer_pa_duty_over_rate() -> None:
    state = _t100_state_c()
    rate_specs = specs_for_strategy(state, "pa_duty_nudge")
    names = [s.name for s in rate_specs]
    assert "PA_2_Rate(Pa)" not in names
    assert "PA_2_Duty(Pa)" in names


def test_subsystem_routing_prefers_draw_first() -> None:
    case = load_case_config()
    limits = ConvergenceLimits()
    seeds = build_subsystem_routed_seeds(_t100_state_c(), case, limits)
    assert seeds
    assert seeds[0].strategy_id == "side_draw_rate_nudge"
    assert seeds[0].spec_name == "Diesel_SS Prod Flow"


def test_reflux_active_flagged() -> None:
    state = _t100_state_c()
    for spec in state.specs:
        if spec.name == "Reflux Ratio":
            spec.is_active = True
    issues = validate_t100_specs_summary(state, load_case_config())
    assert any("Reflux" in i for i in issues)


def test_expert_uses_subsystem_not_blind_pa() -> None:
    case = load_case_config()
    limits = ConvergenceLimits()
    hyps = generate_hypotheses(
        _t100_state_c(),
        EngineeringState.C_OFF_SPEC,
        limits,
        {},
        mv_preference=case.mv_preference,
        case_config=case,
    )
    assert hyps
    assert hyps[0].spec_name == "Diesel_SS Prod Flow"
    assert "subsystem=diesel_section" in hyps[0].mechanism
