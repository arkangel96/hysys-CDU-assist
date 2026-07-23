"""Unit tests for PreFlash + Crude Heater PFH v0.1 (no live HYSYS required)."""
from __future__ import annotations

from cdu_case_config import load_case_config
from cdu_preflash_heater import (
    HeaterSnapshot,
    OverflashSnapshot,
    PreFlashSnapshot,
    diagnose_pfh,
    format_pfh_board_section,
)
from column_models import ColumnState


def test_upstream_config_parses_overflash_null_band():
    case = load_case_config()
    up = case.upstream_objects
    assert up.preflash == "PreFlash"
    assert up.crude_heater == "Crude Heater"
    assert up.crude_duty_energy == "Crude Duty"
    assert up.primary_mv == "heater_duty"
    assert up.secondary_mv == "cot"
    assert up.overflash.band_min is None
    assert up.overflash.band_max is None
    assert "liquid_below_flash" in up.overflash.definition


def test_pfh003_stops_on_bad_preflash():
    up = load_case_config().upstream_objects
    pf = PreFlashSnapshot(name="PreFlash", ok=False, notes=["Invalid vapour fraction"])
    ht = HeaterSnapshot(name="Crude Heater", duty=1e8, ok=True)
    of = OverflashSnapshot(definition=up.overflash.definition, status="unavailable")
    state = ColumnState(name="T-100", degrees_of_freedom=0, appears_converged=True, physical_solution=True)
    diag = diagnose_pfh(pf, ht, of, state, up)
    assert diag.stop_optimization
    assert any(r.rule_id == "PFH-003" for r in diag.recommendations)


def test_pfh_observe_when_band_unset():
    up = load_case_config().upstream_objects
    pf = PreFlashSnapshot(name="PreFlash", temperature=200.0, pressure=50.0, vapour_fraction=0.2, ok=True)
    ht = HeaterSnapshot(name="Crude Heater", duty=1e8, cot=650.0, ok=True)
    of = OverflashSnapshot(
        definition=up.overflash.definition,
        status="unavailable",
        band_configured=False,
    )
    state = ColumnState(name="T-100", degrees_of_freedom=0, appears_converged=True, physical_solution=True)
    diag = diagnose_pfh(pf, ht, of, state, up)
    assert not diag.stop_optimization
    assert any(r.rule_id == "PFH-observe" for r in diag.recommendations)
    assert any(r.rule_id == "PFH-004" for r in diag.recommendations)


def test_pfh001_when_overflash_above_band():
    up = load_case_config().upstream_objects
    pf = PreFlashSnapshot(name="PreFlash", ok=True, vapour_fraction=0.3)
    ht = HeaterSnapshot(name="Crude Heater", duty=1e8, ok=True)
    of = OverflashSnapshot(
        definition=up.overflash.definition,
        value_pct_feed=5.0,
        band_min=1.0,
        band_max=3.0,
        band_configured=True,
        status="above",
    )
    state = ColumnState(name="T-100", degrees_of_freedom=0, appears_converged=True, physical_solution=True)
    diag = diagnose_pfh(pf, ht, of, state, up)
    assert any(r.rule_id == "PFH-001" for r in diag.recommendations)


def test_format_pfh_board_without_columns():
    text = format_pfh_board_section(columns=None, state=None)
    assert "PROPOSE ONLY" in text
    assert "auto-execute" in text.lower() or "Await PE approval" in text
