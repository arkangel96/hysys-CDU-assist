"""Build-up intelligence tests — diesel tree + quality-first keep/reverse."""
from __future__ import annotations

from cdu_case_config import load_case_config
from cdu_expert_engine import build_expert_context, propose_from_expert
from cdu_quality_engine import (
    ProductQualityState,
    PropertyReading,
    QualityStatus,
    QualitySymptom,
    build_product_quality_state,
    merge_final_targets,
    quality_trial_delta,
)
from column_engine import (
    evaluate_final_targets,
    should_keep_trial,
)
from column_models import (
    ColumnSpecState,
    ColumnState,
    ConvergenceLimits,
    EngineeringState,
    FinalTarget,
)


def _t100_state() -> ColumnState:
    return ColumnState(
        name="T-100",
        degrees_of_freedom=0,
        physical_solution=True,
        appears_converged=True,
        cdu_topology=True,
        product_streams=["Naphtha", "Kerosene", "Diesel", "AGO", "Residue"],
        bottoms_molar_flow_kgmole_h=1400.0,
        specs=[
            ColumnSpecState(
                name="Diesel_SS Prod Flow",
                is_active=True,
                goal_value=0.035,
                current_value=0.035,
                error=1e-5,
                goal_display=561.5,
                display_unit="USGPM",
                mv_family="side_draw",
            ),
            ColumnSpecState(
                name="PA_2_Duty(Pa)",
                is_active=True,
                goal_value=-35000000.0,
                current_value=-35000000.0,
                error=0.0,
                mv_family="pa_duty",
            ),
            ColumnSpecState(
                name="Kero_SS Prod Flow",
                is_active=True,
                goal_value=0.017,
                current_value=0.017,
                error=1e-5,
            ),
            ColumnSpecState(
                name="Reflux Ratio",
                is_active=False,
                goal_value=1.0,
                current_value=0.7,
                error=0.3,
            ),
        ],
    )


def _reading(
    tid: str,
    *,
    value: float,
    target: float,
    status: QualityStatus,
    constraint: str = "maximum",
    hard: bool = True,
) -> PropertyReading:
    return PropertyReading(
        target_id=tid,
        product="Diesel",
        stream="Diesel",
        property="D86_95",
        value=value,
        unit="degC",
        target_value=target,
        constraint=constraint,
        status=status,
        hard=hard,
        deviation=value - target,
        read_method="test_inject",
    )


def test_case_buildup_direction_locked() -> None:
    case = load_case_config()
    assert case.interactive_only is True
    assert case.primary_symptom_tree == "diesel_too_heavy"
    assert case.mv_preference["diesel_too_heavy"][0] == "side_draw_rate_nudge"
    assert case.configured_targets()
    diesel = next(t for t in case.configured_targets() if "DIESEL" in t.target_id)
    assert diesel.target_value == 360.0


def test_final_targets_loaded_and_unavailable_not_hard_miss() -> None:
    targets = merge_final_targets()
    assert any(t.id == "DIESEL_ASTM95" for t in targets)
    status = evaluate_final_targets(_t100_state(), targets)
    diesel = status["DIESEL_ASTM95"]
    assert diesel["available"] is False
    assert diesel["met"] is True  # non-gating until COM measures


def test_diesel_too_heavy_routes_to_diesel_draw_down() -> None:
    case = load_case_config()
    state = _t100_state()
    pqs = ProductQualityState(
        objective=case.objective,
        readings=[
            _reading(
                "DIESEL_D86_95",
                value=375.0,
                target=360.0,
                status=QualityStatus.SEVERELY_OFF,
            )
        ],
        symptoms=[QualitySymptom.DIESEL_TOO_HEAVY],
        configured_count=1,
        hard_miss_count=1,
    )
    ctx = build_expert_context(
        state,
        EngineeringState.C_OFF_SPEC,
        ConvergenceLimits(),
        {"DIESEL_ASTM95": {"met": False, "available": True, "hard": True}},
        product_quality=pqs,
        mv_preference=case.mv_preference,
        case_config=case,
    )
    assert ctx.selected_hypothesis is not None
    assert ctx.selected_hypothesis.symptom == "diesel_too_heavy"
    assert ctx.selected_hypothesis.strategy_id == "side_draw_rate_nudge"
    assert "Diesel" in (ctx.selected_hypothesis.spec_name or "")
    assert ctx.selected_hypothesis.direction < 0
    action = propose_from_expert(state, ctx, ConvergenceLimits())
    assert action is not None
    assert action.kind == "set_goal"
    assert "Diesel" in str(action.payload.get("spec_name", ""))
    assert float(action.payload["goal"]) < float(action.payload["previous"])


def test_quality_keep_rejects_residual_only_when_diesel_worsens() -> None:
    before_q = ProductQualityState(
        readings=[
            _reading(
                "DIESEL_D86_95",
                value=370.0,
                target=360.0,
                status=QualityStatus.SLIGHTLY_OFF,
            )
        ],
        symptoms=[QualitySymptom.DIESEL_TOO_HEAVY],
        configured_count=1,
        hard_miss_count=1,
    )
    after_worse = ProductQualityState(
        readings=[
            _reading(
                "DIESEL_D86_95",
                value=380.0,
                target=360.0,
                status=QualityStatus.SEVERELY_OFF,
            )
        ],
        symptoms=[QualitySymptom.DIESEL_TOO_HEAVY],
        configured_count=1,
        hard_miss_count=1,
    )
    after_better = ProductQualityState(
        readings=[
            _reading(
                "DIESEL_D86_95",
                value=365.0,
                target=360.0,
                status=QualityStatus.SLIGHTLY_OFF,
            )
        ],
        symptoms=[QualitySymptom.DIESEL_TOO_HEAVY],
        configured_count=1,
        hard_miss_count=1,
    )
    q_imp, q_wors, q_cmp = quality_trial_delta(before_q, after_worse)
    assert q_cmp and q_wors and not q_imp

    before = _t100_state()
    after = _t100_state()
    limits = ConvergenceLimits()
    targets: list[FinalTarget] = []
    # Residual looks better (lower score) but quality worsened → reverse
    assert not should_keep_trial(
        before,
        after,
        before_score=1.0,
        after_score=0.1,
        limits=limits,
        targets=targets,
        before_quality=before_q,
        after_quality=after_worse,
    )
    assert should_keep_trial(
        before,
        after,
        before_score=1.0,
        after_score=0.9,
        limits=limits,
        targets=targets,
        before_quality=before_q,
        after_quality=after_better,
    )


def test_quality_board_configured() -> None:
    case = load_case_config()
    pqs = build_product_quality_state(_t100_state(), case, columns=None)
    assert pqs.configured_count >= 1
