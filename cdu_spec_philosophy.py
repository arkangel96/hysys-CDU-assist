"""HYSYS specification philosophy audit for CDU (Phase 2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from cdu_case_config import CduCaseConfig, SpecRoleEntry
from column_models import ColumnSpecState, ColumnState


class ConflictSeverity(str, Enum):
    BLOCK = "block"
    WARN = "warn"
    INFO = "info"


@dataclass(slots=True)
class SpecConflict:
    rule_id: str
    severity: ConflictSeverity
    message: str
    spec_names: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass(slots=True)
class SpecPhilosophyReport:
    dof: int | None
    spec_roles: list[dict] = field(default_factory=list)
    conflicts: list[SpecConflict] = field(default_factory=list)
    blocks_tuning: bool = False
    summary: str = ""

    def conflict_lines(self) -> list[str]:
        return [
            f"[{c.severity.value.upper()}] {c.rule_id}: {c.message}"
            for c in self.conflicts
        ]


def _active_specs(state: ColumnState) -> list[ColumnSpecState]:
    return state.active_specs()


def _names_matching(specs: list[ColumnSpecState], *tokens: str) -> list[str]:
    out: list[str] = []
    for spec in specs:
        name = spec.name.lower()
        if all(t in name for t in tokens):
            out.append(spec.name)
    return out


def _has_active(specs: list[ColumnSpecState], *tokens: str) -> bool:
    return bool(_names_matching(specs, *tokens))


def audit_spec_philosophy(
    state: ColumnState,
    case: CduCaseConfig | None = None,
) -> SpecPhilosophyReport:
    """Diagnose DOF and common CDU spec conflicts before tuning."""
    active = _active_specs(state)
    conflicts: list[SpecConflict] = []
    dof = state.degrees_of_freedom

    if dof is not None and dof != 0:
        conflicts.append(
            SpecConflict(
                rule_id="DOF-001",
                severity=ConflictSeverity.BLOCK,
                message=f"Degrees of freedom = {dof} (must be 0 before tuning)",
                recommendation="Activate/deactivate specs until DOF = 0",
            )
        )

    # PA rate + duty both active on same PA index
    for pa_idx in ("1", "2", "3"):
        rate_names = _names_matching(active, f"pa_{pa_idx}", "rate")
        duty_names = _names_matching(active, f"pa_{pa_idx}", "duty")
        if rate_names and duty_names:
            conflicts.append(
                SpecConflict(
                    rule_id="PA-CONFLICT",
                    severity=ConflictSeverity.WARN,
                    message=f"PA_{pa_idx} rate AND duty both Active — over-specification risk",
                    spec_names=rate_names + duty_names,
                    recommendation="Prefer duty OR rate as solver handle, not both",
                )
            )

    # Overhead: naphtha rate + liquid flow + active reflux
    oh_tokens = (
        _has_active(active, "naphtha", "rate")
        or _has_active(active, "naphtha", "prod")
    )
    liq = _has_active(active, "liquid", "flow")
    rr = _has_active(active, "reflux", "ratio")
    if sum((oh_tokens, liq, rr)) >= 2:
        conflicts.append(
            SpecConflict(
                rule_id="OH-CONFLICT",
                severity=ConflictSeverity.WARN,
                message="Multiple overhead handles Active (naphtha/liquid/reflux)",
                spec_names=_names_matching(active, "naphtha")
                + _names_matching(active, "liquid", "flow")
                + _names_matching(active, "reflux"),
                recommendation="Audit overhead spec philosophy — one primary OH handle",
            )
        )

    # Monitor-only spec incorrectly Active
    if case:
        for spec in active:
            role_entry = case.spec_role_for(spec.name)
            if role_entry and role_entry.role == "monitor_only":
                conflicts.append(
                    SpecConflict(
                        rule_id="MON-ACTIVE",
                        severity=ConflictSeverity.WARN,
                        message=f"'{spec.name}' is monitor_only but Active",
                        spec_names=[spec.name],
                        recommendation="Set Active OFF; use as estimate/monitor only",
                    )
                )

    # Many active product draws + fixed feed pattern
    draw_names = [
        s.name
        for s in active
        if "prod flow" in s.name.lower()
        or "prod rate" in s.name.lower()
        or "_ss" in s.name.lower()
    ]
    if len(draw_names) >= 4:
        conflicts.append(
            SpecConflict(
                rule_id="DRAW-MANY",
                severity=ConflictSeverity.INFO,
                message=f"{len(draw_names)} side-draw/product rates Active — verify material balance",
                spec_names=draw_names,
                recommendation="If cuts drift while converged, audit draw spec set (Section 5.7)",
            )
        )

    blocks = any(c.severity == ConflictSeverity.BLOCK for c in conflicts)
    role_rows: list[dict] = []
    for spec in state.specs:
        entry: SpecRoleEntry | None = case.spec_role_for(spec.name) if case else None
        inferred = _infer_role(spec)
        role_rows.append(
            {
                "name": spec.name,
                "active": spec.is_active,
                "role": entry.role if entry else inferred,
                "subsystem": entry.subsystem if entry else "",
            }
        )

    warn_count = sum(1 for c in conflicts if c.severity == ConflictSeverity.WARN)
    if blocks:
        summary = "Spec philosophy BLOCKS tuning — fix DOF first"
    elif warn_count:
        summary = f"Spec philosophy: {warn_count} warning(s) — review before aggressive tuning"
    else:
        summary = "Spec philosophy: no blocking conflicts detected"

    return SpecPhilosophyReport(
        dof=dof,
        spec_roles=role_rows,
        conflicts=conflicts,
        blocks_tuning=blocks,
        summary=summary,
    )


def _infer_role(spec: ColumnSpecState) -> str:
    name = spec.name.lower()
    if "frac" in name or "astm" in name or "tbp" in name or "d86" in name:
        return "monitor_only"
    if spec.is_active:
        return "solver_handle"
    return "monitor_only"


def format_spec_philosophy_board(report: SpecPhilosophyReport) -> str:
    lines = [
        f"SPEC PHILOSOPHY: {report.summary}",
        f"  DOF={report.dof} blocks_tuning={report.blocks_tuning}",
    ]
    for conflict in report.conflicts[:8]:
        lines.append(f"  • [{conflict.severity.value}] {conflict.message}")
        if conflict.recommendation:
            lines.append(f"    → {conflict.recommendation}")
    active_roles = [r for r in report.spec_roles if r.get("active")]
    if active_roles:
        lines.append("  ACTIVE SPEC ROLES:")
        for row in active_roles[:12]:
            sub = f" ({row['subsystem']})" if row.get("subsystem") else ""
            lines.append(f"    {row['name']}: {row['role']}{sub}")
    return "\n".join(lines)
