"""Phase 2 scaffold tests — quality state and spec philosophy."""
from __future__ import annotations

from cdu_case_config import load_case_config
from cdu_quality_engine import build_product_quality_state, format_quality_board
from cdu_spec_philosophy import audit_spec_philosophy
from column_models import ColumnSpecState, ColumnState


def _t100_state() -> ColumnState:
    return ColumnState(
        name="T-100",
        degrees_of_freedom=0,
        physical_solution=True,
        product_streams=["Naphtha", "Kerosene", "Diesel", "AGO", "Residue"],
        specs=[
            ColumnSpecState(name="Diesel_SS Prod Flow", is_active=True, goal_value=1.0, error=0.001),
            ColumnSpecState(name="PA_2_Rate(Pa)", is_active=True, goal_value=1.0, error=0.0),
            ColumnSpecState(name="PA_2_Duty(Pa)", is_active=True, goal_value=-1000.0, error=0.0),
            ColumnSpecState(name="Naphtha Prod Rate", is_active=True, goal_value=1.0, error=0.0),
            ColumnSpecState(name="Liquid Flow", is_active=True, goal_value=1.0, error=0.0),
            ColumnSpecState(name="Reflux Ratio", is_active=False, goal_value=1.0, error=0.0),
        ],
    )


def test_load_t100_config() -> None:
    case = load_case_config()
    assert case.column_name == "T-100"
    assert len(case.quality_targets) >= 1
    assert case.interactive_only is True


def test_spec_philosophy_pa_conflict() -> None:
    case = load_case_config()
    report = audit_spec_philosophy(_t100_state(), case)
    assert any(c.rule_id == "PA-CONFLICT" for c in report.conflicts)
    assert not report.blocks_tuning


def test_spec_philosophy_dof_block() -> None:
    state = _t100_state()
    state.degrees_of_freedom = 1
    report = audit_spec_philosophy(state)
    assert report.blocks_tuning


def test_quality_state_placeholders() -> None:
    case = load_case_config()
    pqs = build_product_quality_state(_t100_state(), case, columns=None)
    assert pqs.configured_count == 0  # target_value null in default JSON
    board = format_quality_board(pqs)
    assert "PRODUCT QUALITY STATE" in board
    assert "cdu_t100_case.json" in board
