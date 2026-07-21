"""Unit tests for CDU expert reasoning engine (no HYSYS required)."""
from __future__ import annotations

from cdu_expert_engine import (
    ProcessState,
    build_expert_context,
    generate_hypotheses,
    hypothesis_to_action,
    propose_from_expert,
    rank_hypotheses,
)
from column_models import (
    ColumnSpecState,
    ColumnState,
    ConvergenceLimits,
    EngineeringState,
    TrialAction,
    TrialResult,
)


def _cdu_state_c_off_spec() -> ColumnState:
    return ColumnState(
        name="T-100",
        degrees_of_freedom=0,
        physical_solution=True,
        appears_converged=True,
        max_active_spec_error=0.05,
        product_streams=["Naphtha", "Kerosene", "Diesel", "AGO", "Residue"],
        feed_streams=["Crude"],
        specs=[
            ColumnSpecState(
                name="PA_1 Duty",
                type_name="Pump Around Duty",
                is_active=True,
                goal_value=1.0e6,
                current_value=1.1e6,
                error=0.04,
            ),
            ColumnSpecState(
                name="Diesel_SS Prod Rate",
                is_active=True,
                goal_value=100.0,
                current_value=95.0,
                error=0.001,
            ),
            ColumnSpecState(
                name="Liquid Flow",
                is_active=True,
                goal_value=50.0,
                current_value=48.0,
                error=0.002,
            ),
        ],
        condenser_duty=-1e5,
        reboiler_duty=2e6,
        bottoms_temperature=350.0,
    )


def test_state_c_generates_pa_hypothesis_first() -> None:
    state = _cdu_state_c_off_spec()
    limits = ConvergenceLimits()
    hyps = generate_hypotheses(
        state, EngineeringState.C_OFF_SPEC, limits, target_status={}
    )
    assert hyps
    assert hyps[0].strategy_id == "pa_duty_nudge"
    assert hyps[0].spec_name == "PA_1 Duty"


def test_expert_context_process_flow_state_c() -> None:
    state = _cdu_state_c_off_spec()
    limits = ConvergenceLimits()
    ctx = build_expert_context(
        state, EngineeringState.C_OFF_SPEC, limits, target_status={}
    )
    assert ctx.process_state == ProcessState.EXPERIMENT_PLANNING
    assert ctx.selected_hypothesis is not None
    assert ctx.ranked_hypotheses[0].confidence >= ctx.ranked_hypotheses[-1].confidence


def test_hypothesis_to_action_bounded_nudge() -> None:
    state = _cdu_state_c_off_spec()
    limits = ConvergenceLimits(reflux_nudge_fraction=0.05)
    ctx = build_expert_context(
        state, EngineeringState.C_OFF_SPEC, limits, target_status={}
    )
    assert ctx.selected_hypothesis is not None
    action = hypothesis_to_action(ctx.selected_hypothesis, state, limits)
    assert action is not None
    assert action.kind == "set_goal"
    assert action.payload["spec_name"] == "PA_1 Duty"
    assert action.payload["strategy_id"] == "pa_duty_nudge"
    assert action.payload["goal"] != action.payload["previous"]


def test_learning_penalizes_failed_strategy() -> None:
    state = _cdu_state_c_off_spec()
    limits = ConvergenceLimits()
    hyps = generate_hypotheses(
        state, EngineeringState.C_OFF_SPEC, limits, target_status={}
    )
    history = [
        TrialResult(
            action=TrialAction(
                "set_goal",
                "failed PA trial",
                payload={"strategy_id": "pa_duty_nudge"},
            ),
            before_score=1.0,
            after_score=1.1,
            kept=False,
            message="reversed",
        )
    ]
    ranked = rank_hypotheses(hyps, history)
    pa = next(h for h in ranked if h.strategy_id == "pa_duty_nudge")
    draw = next(h for h in ranked if h.strategy_id == "side_draw_rate_nudge")
    assert draw.confidence > pa.confidence


def test_state_b_refresh_hypothesis() -> None:
    state = ColumnState(
        name="T-100",
        degrees_of_freedom=0,
        physical_solution=False,
        max_active_spec_error=1.0,
    )
    limits = ConvergenceLimits()
    ctx = build_expert_context(
        state, EngineeringState.B_NUMERICAL, limits, target_status={}
    )
    assert ctx.process_state == ProcessState.EXPERIMENT_PLANNING
    assert ctx.selected_hypothesis is not None
    assert ctx.selected_hypothesis.strategy_id == "refresh_estimates"
    action = propose_from_expert(state, ctx, limits)
    assert action is not None
    assert action.kind == "refresh_estimates"


def test_state_a_dof_manual() -> None:
    state = ColumnState(name="T-100", degrees_of_freedom=1, physical_solution=True)
    limits = ConvergenceLimits()
    ctx = build_expert_context(
        state, EngineeringState.A_INVALID, limits, target_status={}
    )
    action = propose_from_expert(state, ctx, limits)
    assert action is not None
    assert action.kind == "manual_dof"
