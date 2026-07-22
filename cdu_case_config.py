"""CDU case configuration — objectives, quality targets, spec roles (Phase 2)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_CASE_PATH = ROOT / "config" / "cdu_t100_case.json"


@dataclass(slots=True)
class QualityTarget:
    target_id: str
    product: str
    stream: str
    property: str
    target_value: float | None
    unit: str = ""
    constraint: str = "maximum"  # maximum | minimum | target
    hard: bool = True
    tolerance: float = 0.0
    enabled: bool = True
    notes: str = ""

    @property
    def configured(self) -> bool:
        return self.target_value is not None


@dataclass(slots=True)
class SpecRoleEntry:
    name: str
    role: str  # solver_handle | plant_target | monitor_only | hard_constraint | soft_objective
    subsystem: str = ""


@dataclass(slots=True)
class CduCaseConfig:
    case_id: str = "default"
    column_name: str = "T-100"
    objective: str = ""
    interactive_only: bool = True
    primary_symptom_tree: str = "diesel_too_heavy"
    quality_targets: list[QualityTarget] = field(default_factory=list)
    spec_roles: list[SpecRoleEntry] = field(default_factory=list)
    mv_preference: dict[str, list[str]] = field(default_factory=dict)
    upstream_objects: dict[str, str] = field(default_factory=dict)

    def spec_role_for(self, spec_name: str) -> SpecRoleEntry | None:
        for entry in self.spec_roles:
            if entry.name.lower() == spec_name.lower():
                return entry
        return None

    def enabled_targets(self) -> list[QualityTarget]:
        return [t for t in self.quality_targets if t.enabled]

    def configured_targets(self) -> list[QualityTarget]:
        return [t for t in self.enabled_targets() if t.configured]


def _parse_quality_target(raw: dict) -> QualityTarget:
    return QualityTarget(
        target_id=str(raw["target_id"]),
        product=str(raw.get("product", "")),
        stream=str(raw.get("stream", "")),
        property=str(raw.get("property", "")),
        target_value=raw.get("target_value"),
        unit=str(raw.get("unit", "")),
        constraint=str(raw.get("constraint", "maximum")),
        hard=bool(raw.get("hard", True)),
        tolerance=float(raw.get("tolerance", 0.0)),
        enabled=bool(raw.get("enabled", True)),
        notes=str(raw.get("notes", "")),
    )


def load_case_config(path: Path | str | None = None) -> CduCaseConfig:
    path = Path(path) if path else DEFAULT_CASE_PATH
    if not path.is_file():
        return default_t100_config()
    data = json.loads(path.read_text(encoding="utf-8"))
    return CduCaseConfig(
        case_id=str(data.get("case_id", "default")),
        column_name=str(data.get("column_name", "T-100")),
        objective=str(data.get("objective", "")),
        interactive_only=bool(data.get("interactive_only", True)),
        primary_symptom_tree=str(
            data.get("primary_symptom_tree", "diesel_too_heavy") or "diesel_too_heavy"
        ),
        quality_targets=[_parse_quality_target(r) for r in data.get("quality_targets", [])],
        spec_roles=[
            SpecRoleEntry(
                name=str(r["name"]),
                role=str(r.get("role", "solver_handle")),
                subsystem=str(r.get("subsystem", "")),
            )
            for r in data.get("spec_roles", [])
        ],
        mv_preference={
            str(k): [str(v) for v in vals]
            for k, vals in data.get("mv_preference", {}).items()
        },
        upstream_objects={
            str(k): str(v) for k, v in data.get("upstream_objects", {}).items()
        },
    )


def default_t100_config() -> CduCaseConfig:
    """Fallback when JSON missing — minimal T-100 placeholders from COM discovery."""
    return CduCaseConfig(
        case_id="t100_baseline",
        column_name="T-100",
        objective="Configure config/cdu_t100_case.json with your targets",
        interactive_only=True,
        primary_symptom_tree="diesel_too_heavy",
        quality_targets=[
            QualityTarget(
                target_id="DIESEL_D86_95",
                product="Diesel",
                stream="Diesel",
                property="D86_95",
                target_value=None,
                unit="degC",
                constraint="maximum",
                hard=True,
                notes="Set target_value in config/cdu_t100_case.json",
            ),
        ],
        spec_roles=[
            SpecRoleEntry("Diesel_SS Prod Flow", "solver_handle", "diesel_section"),
            SpecRoleEntry("PA_2_Duty(Pa)", "solver_handle", "pumparound"),
            SpecRoleEntry("Kero Reb Duty", "solver_handle", "side_stripper"),
        ],
        mv_preference={
            "diesel_too_heavy": [
                "side_draw_rate_nudge",
                "pa_duty_nudge",
                "side_strip_steam_nudge",
            ],
        },
    )
