"""Product quality state for CDU — independent of HYSYS solver residuals (Phase 2)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from cdu_case_config import CduCaseConfig, QualityTarget
from column_api import ColumnController, is_sentinel
from column_models import ColumnState


class QualityStatus(str, Enum):
    ON_SPEC = "on_spec"
    SLIGHTLY_OFF = "slightly_off"
    SEVERELY_OFF = "severely_off"
    UNAVAILABLE = "unavailable"
    UNRELIABLE = "unreliable"
    NOT_CONFIGURED = "not_configured"
    CONFLICTING = "conflicting"


class QualitySymptom(str, Enum):
    DIESEL_TOO_HEAVY = "diesel_too_heavy"
    DIESEL_TOO_LIGHT = "diesel_too_light"
    KEROSENE_OFF_SPEC = "kerosene_off_spec"
    NAPHTHA_TOO_HEAVY = "naphtha_too_heavy"
    RESIDUE_TOO_LIGHT = "residue_too_light"
    YIELD_OFF = "yield_off"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class PropertyReading:
    target_id: str
    product: str
    stream: str
    property: str
    value: float | None
    unit: str
    target_value: float | None
    constraint: str
    status: QualityStatus
    hard: bool
    deviation: float | None = None
    read_method: str = "unavailable"
    notes: str = ""


@dataclass(slots=True)
class ProductQualityState:
    objective: str = ""
    readings: list[PropertyReading] = field(default_factory=list)
    symptoms: list[QualitySymptom] = field(default_factory=list)
    configured_count: int = 0
    unavailable_count: int = 0
    hard_miss_count: int = 0

    def has_hard_miss(self) -> bool:
        return self.hard_miss_count > 0

    def primary_symptom(self) -> QualitySymptom | None:
        return self.symptoms[0] if self.symptoms else None


def _read_property(
    columns: ColumnController | None,
    stream: str,
    prop: str,
) -> tuple[float | None, str]:
    """Best-effort COM read — D86/flash often need case-specific setup."""
    prop_l = prop.lower()
    petroleum = prop_l in {"d86_95", "d86", "flash_point", "rvp", "tbp_95"}
    if columns is None or not stream or stream == "TBD":
        if petroleum:
            return None, "not_configured_com_path"
        return None, "unavailable"

    try:
        if prop_l in {"mass_flow", "flow", "molar_flow"}:
            val = columns._stream_flow_unit(stream, "kg/h")  # noqa: SLF001
            if val is None:
                val = columns._stream_flow(stream)  # noqa: SLF001
            if val is not None and not is_sentinel(val):
                return float(val), "com_stream_flow"
        if prop_l in {"temperature", "temp"}:
            val = columns._stream_temperature(stream)  # noqa: SLF001
            if val is not None and not is_sentinel(val):
                return float(val), "com_stream_temperature"
        # Petroleum properties (D86, flash) — scaffold until assay/COM path confirmed
        if petroleum:
            return None, "not_configured_com_path"
    except Exception:
        return None, "read_error"
    return None, "unavailable"


def _classify_reading(
    value: float | None,
    target: QualityTarget,
    read_method: str,
) -> tuple[QualityStatus, float | None, bool]:
    """Return status, deviation, met."""
    if not target.configured:
        return QualityStatus.NOT_CONFIGURED, None, True
    if value is None or is_sentinel(value):
        if read_method == "not_configured_com_path":
            return QualityStatus.NOT_CONFIGURED, None, True
        return QualityStatus.UNAVAILABLE, None, False

    dev = float(value) - float(target.target_value)
    tol = target.tolerance
    met = True
    status = QualityStatus.ON_SPEC

    if target.constraint == "maximum":
        met = float(value) <= float(target.target_value) + tol
        if not met:
            status = (
                QualityStatus.SEVERELY_OFF
                if dev > tol * 2
                else QualityStatus.SLIGHTLY_OFF
            )
    elif target.constraint == "minimum":
        met = float(value) >= float(target.target_value) - tol
        if not met:
            status = (
                QualityStatus.SEVERELY_OFF
                if dev < -tol * 2
                else QualityStatus.SLIGHTLY_OFF
            )
    else:  # target
        met = abs(dev) <= tol
        if not met:
            status = (
                QualityStatus.SEVERELY_OFF
                if abs(dev) > tol * 2
                else QualityStatus.SLIGHTLY_OFF
            )

    return status, dev, met


def _symptom_from_reading(reading: PropertyReading) -> QualitySymptom | None:
    if reading.status not in {
        QualityStatus.SLIGHTLY_OFF,
        QualityStatus.SEVERELY_OFF,
    }:
        return None
    pid = reading.target_id.upper()
    prop = reading.property.lower()
    dev = reading.deviation or 0.0

    if "DIESEL" in pid and "d86" in prop:
        return (
            QualitySymptom.DIESEL_TOO_HEAVY
            if reading.constraint == "maximum" and dev > 0
            else QualitySymptom.DIESEL_TOO_LIGHT
        )
    if "KERO" in pid:
        return QualitySymptom.KEROSENE_OFF_SPEC
    if "NAPH" in pid:
        return QualitySymptom.NAPHTHA_TOO_HEAVY
    if "RESIDUE" in pid and dev < 0:
        return QualitySymptom.RESIDUE_TOO_LIGHT
    if reading.constraint == "target" and dev != 0:
        return QualitySymptom.YIELD_OFF
    return QualitySymptom.UNKNOWN


def build_product_quality_state(
    state: ColumnState,
    case: CduCaseConfig,
    columns: ColumnController | None = None,
) -> ProductQualityState:
    readings: list[PropertyReading] = []
    symptoms: list[QualitySymptom] = []
    configured = 0
    unavailable = 0
    hard_miss = 0

    for target in case.enabled_targets():
        if target.configured:
            configured += 1
        value, read_method = _read_property(columns, target.stream, target.property)
        status, deviation, met = _classify_reading(value, target, read_method)
        if status == QualityStatus.UNAVAILABLE:
            unavailable += 1
        if target.hard and target.configured and not met:
            hard_miss += 1

        reading = PropertyReading(
            target_id=target.target_id,
            product=target.product,
            stream=target.stream,
            property=target.property,
            value=value,
            unit=target.unit,
            target_value=target.target_value,
            constraint=target.constraint,
            status=status,
            hard=target.hard,
            deviation=deviation,
            read_method=read_method,
            notes=target.notes,
        )
        readings.append(reading)
        symptom = _symptom_from_reading(reading)
        if symptom and symptom not in symptoms:
            symptoms.append(symptom)

    return ProductQualityState(
        objective=case.objective,
        readings=readings,
        symptoms=symptoms,
        configured_count=configured,
        unavailable_count=unavailable,
        hard_miss_count=hard_miss,
    )


def quality_targets_to_final_targets(case: CduCaseConfig) -> list:
    """Bridge configured quality targets to column_models.FinalTarget where possible."""
    from column_models import FinalTarget

    out: list[FinalTarget] = []
    for t in case.configured_targets():
        rel = "less_or_equal"
        if t.constraint == "minimum":
            rel = "greater_or_equal"
        elif t.constraint == "target":
            rel = "equal"
        prop = t.property.lower()
        property_type = "other"
        if "d86" in prop or "astm" in prop:
            property_type = "astm_d86"
        elif "flash" in prop:
            property_type = "cold_prop"
        elif "tbp" in prop:
            property_type = "tbp"
        elif "gap" in prop:
            property_type = "gap"
        elif "flow" in prop:
            property_type = "other"
        # Needle must not match Prod Flow / rate specs (avoid false measured = draw rate)
        needle = f"{prop}_{t.product.lower()}" if "d86" in prop or "flash" in prop else prop
        out.append(
            FinalTarget(
                id=t.target_id,
                description=f"{t.product} {t.property}",
                spec_name_contains=needle,
                component_name_contains=tuple(),
                stream=t.stream,
                relationship=rel,
                target_value=float(t.target_value),
                tolerance=t.tolerance,
                locked=True,
                hard=t.hard,
                property_type=property_type,
            )
        )
    return out


def quality_trial_delta(
    before: ProductQualityState,
    after: ProductQualityState,
) -> tuple[bool, bool, bool]:
    """
    Compare hard quality readings across a trial.

    Returns (any_improved, any_worsened, has_comparable).
    Only readings with numeric value+target on both sides count.
    """
    before_by = {r.target_id: r for r in before.readings}
    after_by = {r.target_id: r for r in after.readings}
    improved = False
    worsened = False
    comparable = False
    for tid, b in before_by.items():
        a = after_by.get(tid)
        if a is None or not b.hard:
            continue
        if b.value is None or a.value is None or b.target_value is None:
            continue
        if b.status in {
            QualityStatus.NOT_CONFIGURED,
            QualityStatus.UNAVAILABLE,
            QualityStatus.UNRELIABLE,
        }:
            continue
        if a.status in {
            QualityStatus.NOT_CONFIGURED,
            QualityStatus.UNAVAILABLE,
            QualityStatus.UNRELIABLE,
        }:
            continue
        comparable = True
        bv, av, tgt = float(b.value), float(a.value), float(b.target_value)
        if b.constraint == "maximum":
            if av < bv - 1e-12:
                improved = True
            if av > bv * 1.02 + 1e-12 and av > tgt:
                worsened = True
        elif b.constraint == "minimum":
            if av > bv + 1e-12:
                improved = True
            if av < bv * 0.98 - 1e-12 and av < tgt:
                worsened = True
        else:
            db, da = abs(bv - tgt), abs(av - tgt)
            if da < db - 1e-12:
                improved = True
            if da > db * 1.05 + 1e-12:
                worsened = True
    return improved, worsened, comparable


def merge_final_targets(case: CduCaseConfig | None = None) -> list:
    """FINAL_TARGET JSON wins on id collision; quality config fills gaps."""
    from cdu_case_config import load_case_config
    from cdu_targets import load_cdu_final_targets

    case = case or load_case_config()
    by_id: dict = {}
    for t in quality_targets_to_final_targets(case):
        by_id[t.id] = t
    for t in load_cdu_final_targets():
        by_id[t.id] = t
    return list(by_id.values())


def format_quality_board(pqs: ProductQualityState) -> str:
    lines = [
        "PRODUCT QUALITY STATE (L1 — independent of solver residuals)",
        f"  Objective: {pqs.objective or '—'}",
        f"  configured={pqs.configured_count} unavailable={pqs.unavailable_count} "
        f"hard_miss={pqs.hard_miss_count}",
    ]
    if pqs.symptoms:
        lines.append(
            "  Symptoms: " + ", ".join(s.value for s in pqs.symptoms)
        )
    for r in pqs.readings:
        tgt = r.target_value if r.target_value is not None else "TBD"
        val = r.value if r.value is not None else "—"
        lines.append(
            f"  • {r.target_id} ({r.stream}/{r.property}): "
            f"value={val} target={tgt} {r.unit} status={r.status.value} "
            f"[{r.read_method}]"
        )
        if r.notes and r.status == QualityStatus.NOT_CONFIGURED:
            lines.append(f"    note: {r.notes}")
    if pqs.configured_count == 0:
        lines.append(
            "  → Edit config/cdu_t100_case.json: set target_value for each product"
        )
    else:
        lines.append(
            "  → Quality targets configured; D86/flash COM still PARTIAL until assay path live"
        )
    return "\n".join(lines)
