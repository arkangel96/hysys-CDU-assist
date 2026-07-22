"""
Load CDU multi-product FINAL_TARGETs from config/cdu_final_targets.json.

Copy the example file and set _enabled true + plant target_value / spec_name_contains.
Never auto-relaxes locked targets.
"""
from __future__ import annotations

import json
from pathlib import Path

from column_models import FinalTarget

_ROOT = Path(__file__).resolve().parent
_DEFAULT_PATH = _ROOT / "config" / "cdu_final_targets.json"
_EXAMPLE_PATH = _ROOT / "config" / "cdu_final_targets.example.json"


def load_cdu_final_targets(path: Path | str | None = None) -> list[FinalTarget]:
    """
    Load enabled FINAL_TARGETs from JSON.

    Returns [] if file missing or no enabled rows — Assist still runs on
    DOF / physics / operability.
    """
    cfg_path = Path(path) if path else _DEFAULT_PATH
    if not cfg_path.is_file():
        return []

    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    rows = raw.get("targets") if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []

    out: list[FinalTarget] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("_enabled") is False:
            continue
        tid = str(row.get("id") or "").strip()
        if not tid:
            continue
        comps = row.get("component_name_contains") or []
        if isinstance(comps, str):
            comps = [comps]
        out.append(
            FinalTarget(
                id=tid,
                description=str(row.get("description") or tid),
                spec_name_contains=str(row.get("spec_name_contains") or ""),
                component_name_contains=tuple(str(c) for c in comps),
                stream=str(row.get("stream") or "spec"),
                relationship=str(row.get("relationship") or "less_or_equal"),
                target_value=float(row.get("target_value") or 0.0),
                tolerance=float(row.get("tolerance") or 0.0),
                locked=bool(row.get("locked", True)),
                hard=bool(row.get("hard", True)),
                property_type=str(row.get("property_type") or "cut"),
            )
        )
    return out


def cdu_targets_config_hint() -> str:
    """PE-board / diagnose hint when no targets are loaded."""
    if _DEFAULT_PATH.is_file():
        return f"FINAL_TARGET file present but empty/disabled: {_DEFAULT_PATH.name}"
    return (
        f"No CDU FINAL_TARGETs loaded — copy {_EXAMPLE_PATH.name} to "
        f"{_DEFAULT_PATH.name} and enable plant rows."
    )
