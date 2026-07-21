"""CDU Expert System — process flow, hypotheses, experiment selection, learning."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from column_api import is_sentinel
from column_models import (
    ColumnSpecState,
    ColumnState,
    ConvergenceLimits,
    EngineeringState,
    ResponseClass,
    TrialAction,
    TrialResult,
)

if TYPE_CHECKING:
    from cdu_quality_engine import ProductQualityState, QualitySymptom
    from cdu_spec_philosophy import SpecPhilosophyReport


class ProcessState(str, Enum):
    """Ten-step expert session flow (docs/expert/32_State_Machine.md)."""

    INITIALIZATION = "initialization"
    MODEL_VALIDATION = "model_validation"
    OBSERVATION = "observation"
    DIAGNOSIS = "diagnosis"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    EXPERIMENT_PLANNING = "experiment_planning"
    EXECUTION = "execution"
    EVALUATION = "evaluation"
    LEARNING = "learning"
    COMPLETION = "completion"


@dataclass(slots=True)
class Hypothesis:
    rule_id: str
    subsystem: str
    symptom: str
    mechanism: str
    evidence: list[str]
    confidence: float
    strategy_id: str
    spec_name: str | None
    direction: float  # +1 increase GoalValue, -1 decrease
    predicted_response: str
    mv_family: str = ""
    reversible: bool = True


@dataclass(slots=True)
class ExpertContext:
    process_state: ProcessState
    evidence: list[str] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    ranked_hypotheses: list[Hypothesis] = field(default_factory=list)
    selected_hypothesis: Hypothesis | None = None


def _is_pa_spec(spec: ColumnSpecState) -> bool:
    n = spec.name.lower()
    t = spec.type_name.lower()
    return "pa_" in n or "pump" in t or "(pa)" in n


def _is_draw_spec(spec: ColumnSpecState) -> bool:
    n = spec.name.lower()
    return "prod rate" in n or "draw" in n or "_ss" in n


def _is_strip_energy_spec(spec: ColumnSpecState) -> bool:
    n = spec.name.lower()
    return "reb duty" in n or ("strip" in n and "steam" in n)


def _is_oh_spec(spec: ColumnSpecState) -> bool:
    n = spec.name.lower()
    return "liquid flow" in n or "naphtha" in n or "reflux ratio" in n


def classify_process_state(
    eng: EngineeringState,
    *,
    connected: bool = True,
) -> ProcessState:
    if not connected:
        return ProcessState.INITIALIZATION
    if eng == EngineeringState.A_INVALID:
        return ProcessState.MODEL_VALIDATION
    if eng == EngineeringState.E_ACCEPTABLE:
        return ProcessState.COMPLETION
    if eng == EngineeringState.F_INFEASIBLE:
        return ProcessState.COMPLETION
    if eng == EngineeringState.B_NUMERICAL:
        return ProcessState.DIAGNOSIS
    return ProcessState.HYPOTHESIS_GENERATION


def collect_evidence(
    state: ColumnState,
    eng: EngineeringState,
    target_status: dict[str, dict],
    *,
    product_quality: ProductQualityState | None = None,
    spec_report: SpecPhilosophyReport | None = None,
) -> list[str]:
    evidence: list[str] = []
    evidence.append(f"engineering_state={eng.value}")
    evidence.append(f"DOF={state.degrees_of_freedom}")
    evidence.append(f"physical={state.physical_solution} converged={state.appears_converged}")
    evidence.append(f"max_active_err={state.max_active_spec_error:.3g}")
    if product_quality and product_quality.symptoms:
        evidence.append(
            "quality_symptoms=" + ",".join(s.value for s in product_quality.symptoms)
        )
    if spec_report and spec_report.conflicts:
        evidence.append(f"spec_conflicts={len(spec_report.conflicts)}")
    if state.product_streams:
        evidence.append(f"products={','.join(state.product_streams)}")
    if state.feed_streams:
        evidence.append(f"feeds={','.join(state.feed_streams)}")
    for tid, info in target_status.items():
        if not info.get("met", True):
            evidence.append(f"FINAL_TARGET_miss={tid}")
    for spec in sorted(state.active_specs(), key=lambda s: s.score_error(), reverse=True)[:5]:
        evidence.append(
            f"active_spec={spec.name} err={spec.error} "
            f"goal={spec.goal_display or spec.goal_value}"
        )
    if is_sentinel(state.condenser_duty):
        evidence.append("sentinel_condenser_duty")
    return evidence


def _direction_from_spec_error(spec: ColumnSpecState) -> float:
    err = spec.error
    if err is not None and abs(err) >= 1e-12 and not is_sentinel(err):
        return -1.0 if float(err) > 0 else 1.0
    cur, goal = spec.current_value, spec.goal_value
    if (
        cur is not None
        and goal is not None
        and not is_sentinel(cur)
        and not is_sentinel(goal)
        and abs(float(goal)) > 1e-12
    ):
        return 1.0 if float(cur) < float(goal) else -1.0
    return 1.0


def _mv_family_for_spec(spec: ColumnSpecState) -> tuple[str, str]:
    if _is_pa_spec(spec):
        if "duty" in spec.name.lower():
            return "pa_duty_nudge", "Pumparound"
        return "pa_duty_nudge", "Pumparound"
    if _is_strip_energy_spec(spec):
        return "side_strip_steam_nudge", "Side stripper"
    if _is_draw_spec(spec):
        return "side_draw_rate_nudge", "Side draw"
    if _is_oh_spec(spec):
        return "reflux_or_oh_nudge", "Overhead"
    return "side_draw_rate_nudge", "Side draw"


def _find_spec_for_strategy(
    state: ColumnState, strategy_id: str, product_hint: str = ""
) -> ColumnSpecState | None:
    product_l = product_hint.lower()
    for spec in state.specs:
        name = spec.name.lower()
        if product_l and product_l not in name:
            continue
        sid, _ = _mv_family_for_spec(spec)
        if sid == strategy_id and spec.is_active and spec.goal_value is not None:
            return spec
    for spec in state.active_specs():
        sid, _ = _mv_family_for_spec(spec)
        if sid == strategy_id and spec.goal_value is not None:
            return spec
    return None


def _quality_routed_hypotheses(
    state: ColumnState,
    symptom_key: str,
    mechanism: str,
    mv_preference: dict[str, list[str]],
    limits: ConvergenceLimits,
) -> list[Hypothesis]:
    """Phase 3 starter — route quality symptom to preferred MV family."""
    from cdu_quality_engine import QualitySymptom

    order = mv_preference.get(symptom_key, [])
    if not order and symptom_key == QualitySymptom.DIESEL_TOO_HEAVY.value:
        order = [
            "side_draw_rate_nudge",
            "pa_duty_nudge",
            "side_strip_steam_nudge",
        ]

    product_hint = ""
    if "diesel" in symptom_key:
        product_hint = "diesel"
    elif "kero" in symptom_key:
        product_hint = "kero"

    hyps: list[Hypothesis] = []
    for rank, strategy_id in enumerate(order):
        spec = _find_spec_for_strategy(state, strategy_id, product_hint)
        if spec is None:
            continue
        direction = _direction_from_spec_error(spec)
        if symptom_key == QualitySymptom.DIESEL_TOO_HEAVY.value and strategy_id == "side_draw_rate_nudge":
            direction = -1.0  # reduce draw when cut too heavy
        _, mv_family = _mv_family_for_spec(spec)
        hyps.append(
            Hypothesis(
                rule_id=f"QRT-{symptom_key}-{strategy_id}",
                subsystem=mv_family.lower().replace(" ", "_"),
                symptom=symptom_key,
                mechanism=f"{mechanism} — preferred MV #{rank + 1}: {strategy_id}",
                evidence=[f"symptom={symptom_key}", f"spec={spec.name}"],
                confidence=0.82 - rank * 0.08,
                strategy_id=strategy_id,
                spec_name=spec.name,
                direction=direction,
                predicted_response=f"{symptom_key} improves via '{spec.name}'",
                mv_family=mv_family,
            )
        )
    return hyps


def generate_hypotheses(
    state: ColumnState,
    eng: EngineeringState,
    limits: ConvergenceLimits,
    target_status: dict[str, dict],
    *,
    spec_report: SpecPhilosophyReport | None = None,
    product_quality: ProductQualityState | None = None,
    mv_preference: dict[str, list[str]] | None = None,
) -> list[Hypothesis]:
    """Rules-first hypothesis generation for CDU (T-100 class)."""
    hyps: list[Hypothesis] = []
    mv_preference = mv_preference or {}

    if spec_report and spec_report.blocks_tuning:
        hyps.append(
            Hypothesis(
                rule_id="SPEC-001-block",
                subsystem="spec_philosophy",
                symptom="spec_philosophy_block",
                mechanism=spec_report.summary,
                evidence=[c.message for c in spec_report.conflicts[:3]],
                confidence=0.98,
                strategy_id="fix_dof",
                spec_name=None,
                direction=0.0,
                predicted_response="DOF/spec set corrected — then re-diagnose",
                mv_family="Spec Set",
            )
        )
        return hyps

    if eng == EngineeringState.A_INVALID:
        hyps.append(
            Hypothesis(
                rule_id="VAL-001-dof",
                subsystem="model_validation",
                symptom="invalid_spec_set",
                mechanism="DOF not zero — model not posed",
                evidence=[f"DOF={state.degrees_of_freedom}"],
                confidence=0.95,
                strategy_id="fix_dof",
                spec_name=None,
                direction=0.0,
                predicted_response="DOF returns to 0 after manual spec fix",
                mv_family="Spec Set",
            )
        )
        return hyps

    if eng == EngineeringState.B_NUMERICAL:
        hyps.append(
            Hypothesis(
                rule_id="REC-001-estimates",
                subsystem="model_validation",
                symptom="numerical_unhealthy",
                mechanism="estimates/stale — refresh before product moves",
                evidence=["physical=false or high residuals"],
                confidence=0.85,
                strategy_id="refresh_estimates",
                spec_name=None,
                direction=0.0,
                predicted_response="Residuals decrease; duties non-sentinel",
                mv_family="Estimates",
            )
        )
        if limits.allow_baseline_spec_swap and state.degrees_of_freedom == 0:
            hyps.append(
                Hypothesis(
                    rule_id="REC-002-baseline",
                    subsystem="model_validation",
                    symptom="numerical_recovery",
                    mechanism="temporary baseline Active pair",
                    evidence=["State B with DOF=0"],
                    confidence=0.55,
                    strategy_id="baseline_spec_recovery",
                    spec_name=None,
                    direction=0.0,
                    predicted_response="Physical solution restored",
                    mv_family="Spec Set",
                )
            )
        return hyps

    if eng == EngineeringState.D_CONSTRAINT:
        hyps.append(
            Hypothesis(
                rule_id="OP-001-operability",
                subsystem="constraints",
                symptom="operability_fail",
                mechanism="material split / dry draw / sentinel — manual PE",
                evidence=["operability gate failed"],
                confidence=0.9,
                strategy_id="feed_or_case_change",
                spec_name=None,
                direction=0.0,
                predicted_response="PE adjusts split or spec philosophy",
                mv_family="Case",
                reversible=False,
            )
        )
        return hyps

    if eng == EngineeringState.F_INFEASIBLE:
        hyps.append(
            Hypothesis(
                rule_id="INF-001-stop",
                subsystem="diagnostics",
                symptom="likely_infeasible",
                mechanism="Category-1 families exhausted or weak response",
                evidence=["State F"],
                confidence=0.95,
                strategy_id="report_infeasible",
                spec_name=None,
                direction=0.0,
                predicted_response="Stop — escalate structurally",
                mv_family="Spec Set",
                reversible=False,
            )
        )
        return hyps

    if eng != EngineeringState.C_OFF_SPEC:
        return hyps

    # Quality-driven routing (L1→L3) before residual-driven hypotheses
    if product_quality and product_quality.symptoms:
        from cdu_quality_engine import QualitySymptom

        for symptom in product_quality.symptoms:
            if symptom == QualitySymptom.DIESEL_TOO_HEAVY:
                hyps.extend(
                    _quality_routed_hypotheses(
                        state,
                        symptom.value,
                        "Diesel D86 95% above target — mechanism routing",
                        mv_preference,
                        limits,
                    )
                )
            elif symptom in {
                QualitySymptom.DIESEL_TOO_LIGHT,
                QualitySymptom.KEROSENE_OFF_SPEC,
            }:
                hyps.extend(
                    _quality_routed_hypotheses(
                        state,
                        symptom.value,
                        f"Quality symptom {symptom.value}",
                        mv_preference,
                        limits,
                    )
                )
        if hyps:
            return hyps[:6]

    target_miss = any(not info.get("met", True) for info in target_status.values())
    active_sorted = sorted(state.active_specs(), key=lambda s: s.score_error(), reverse=True)

    for spec in active_sorted:
        if spec.score_error() <= limits.max_active_spec_error and not target_miss:
            continue
        strategy_id, mv_family = _mv_family_for_spec(spec)
        direction = _direction_from_spec_error(spec)
        mechanism = f"dominant residual on '{spec.name}' — bounded {strategy_id}"
        if _is_pa_spec(spec) and "duty" in spec.name.lower():
            mechanism = (
                f"PA heat removal / fractionation via '{spec.name}' — "
                "one PA, one knob per trial"
            )
        elif _is_draw_spec(spec):
            mechanism = f"Material split / draw rate via '{spec.name}'"
        elif _is_strip_energy_spec(spec):
            mechanism = f"Side-strip energy via '{spec.name}'"

        base_conf = 0.5 + min(spec.score_error() * 1000, 0.35)
        if target_miss:
            base_conf += 0.05

        hyps.append(
            Hypothesis(
                rule_id=f"CDU-{strategy_id}-{spec.name[:20]}",
                subsystem=mv_family.lower().replace(" ", "_"),
                symptom="off_spec_or_high_residual",
                mechanism=mechanism,
                evidence=[f"spec={spec.name} err={spec.error}"],
                confidence=base_conf,
                strategy_id=strategy_id,
                spec_name=spec.name,
                direction=direction,
                predicted_response=f"Residual on '{spec.name}' improves; neighbors monitored",
                mv_family=mv_family,
            )
        )

    if not hyps and state.max_active_spec_error > limits.max_active_spec_error:
        hyps.append(
            Hypothesis(
                rule_id="REC-003-refresh-residual",
                subsystem="model_validation",
                symptom="high_residual",
                mechanism="refresh estimates before MV nudge",
                evidence=[f"max_err={state.max_active_spec_error}"],
                confidence=0.6,
                strategy_id="refresh_estimates",
                spec_name=None,
                direction=0.0,
                predicted_response="Residuals decrease",
                mv_family="Estimates",
            )
        )

    return hyps[:6]


def _failed_strategies(history: list[TrialResult]) -> set[str]:
    failed: set[str] = set()
    for trial in history:
        if trial.kept:
            continue
        sid = (trial.action.payload or {}).get("strategy_id")
        if sid:
            failed.add(str(sid))
    return failed


def rank_hypotheses(
    hypotheses: list[Hypothesis],
    history: list[TrialResult] | None = None,
    mv_preference: dict[str, list[str]] | None = None,
) -> list[Hypothesis]:
    """Rank by confidence; penalize recently failed strategies (learning)."""
    history = history or []
    mv_preference = mv_preference or {}
    failed = _failed_strategies(history)
    helped: set[str] = set()
    for trial in history:
        if trial.kept and (trial.action.payload or {}).get("strategy_id"):
            helped.add(str(trial.action.payload["strategy_id"]))

    pref_rank: dict[str, int] = {}
    for symptom, strategies in mv_preference.items():
        for i, sid in enumerate(strategies):
            pref_rank[sid] = min(pref_rank.get(sid, 99), i)

    scored: list[tuple[float, Hypothesis]] = []
    for h in hypotheses:
        score = h.confidence
        if h.strategy_id in failed:
            score -= 0.35
        if h.strategy_id in helped:
            score += 0.1
        if not h.reversible:
            score -= 0.05
        if h.symptom in mv_preference and h.strategy_id in mv_preference[h.symptom]:
            idx = mv_preference[h.symptom].index(h.strategy_id)
            score += 0.15 - idx * 0.03
        scored.append((score, h))

    scored.sort(key=lambda x: x[0], reverse=True)
    ranked: list[Hypothesis] = []
    for score, h in scored:
        ranked.append(
            Hypothesis(
                rule_id=h.rule_id,
                subsystem=h.subsystem,
                symptom=h.symptom,
                mechanism=h.mechanism,
                evidence=h.evidence,
                confidence=round(max(0.0, min(1.0, score)), 3),
                strategy_id=h.strategy_id,
                spec_name=h.spec_name,
                direction=h.direction,
                predicted_response=h.predicted_response,
                mv_family=h.mv_family,
                reversible=h.reversible,
            )
        )
    return ranked


def select_hypothesis(ranked: list[Hypothesis]) -> Hypothesis | None:
    if not ranked:
        return None
    best = ranked[0]
    if best.confidence < 0.25:
        return None
    return best


def build_expert_context(
    state: ColumnState,
    eng: EngineeringState,
    limits: ConvergenceLimits,
    target_status: dict[str, dict],
    history: list[TrialResult] | None = None,
    *,
    connected: bool = True,
    spec_report: SpecPhilosophyReport | None = None,
    product_quality: ProductQualityState | None = None,
    mv_preference: dict[str, list[str]] | None = None,
) -> ExpertContext:
    process = classify_process_state(eng, connected=connected)
    evidence = collect_evidence(
        state,
        eng,
        target_status,
        product_quality=product_quality,
        spec_report=spec_report,
    )
    hyps = generate_hypotheses(
        state,
        eng,
        limits,
        target_status,
        spec_report=spec_report,
        product_quality=product_quality,
        mv_preference=mv_preference,
    )
    ranked = rank_hypotheses(hyps, history, mv_preference=mv_preference)
    selected = select_hypothesis(ranked)
    if selected and eng in {
        EngineeringState.C_OFF_SPEC,
        EngineeringState.B_NUMERICAL,
    }:
        process = ProcessState.EXPERIMENT_PLANNING
    elif eng == EngineeringState.E_ACCEPTABLE:
        process = ProcessState.COMPLETION
    return ExpertContext(
        process_state=process,
        evidence=evidence,
        hypotheses=hyps,
        ranked_hypotheses=ranked,
        selected_hypothesis=selected,
    )


def _bounded_goal(
    spec: ColumnSpecState,
    direction: float,
    limits: ConvergenceLimits,
) -> float | None:
    if spec.goal_value is None or is_sentinel(spec.goal_value):
        return None
    base = float(spec.goal_value)
    frac = limits.reflux_nudge_fraction
    if "reflux ratio" in spec.name.lower():
        new_goal = base * (1.0 + direction * frac)
        return min(max(new_goal, limits.min_reflux_ratio), limits.max_reflux_ratio)
    if abs(base) < 1e-12:
        return base + direction * 1e-6
    new_goal = base * (1.0 + direction * frac)
    return new_goal


def hypothesis_to_action(
    hypothesis: Hypothesis,
    state: ColumnState,
    limits: ConvergenceLimits,
) -> TrialAction | None:
    sid = hypothesis.strategy_id

    if sid == "fix_dof":
        return TrialAction(
            kind="manual_dof",
            description=f"[{hypothesis.rule_id}] {hypothesis.mechanism}",
            payload={"dof": state.degrees_of_freedom, "strategy_id": sid},
        )

    if sid in {"feed_or_case_change", "report_infeasible"}:
        return TrialAction(
            kind="stop",
            description=f"[{hypothesis.rule_id}] {hypothesis.mechanism}",
            payload={"strategy_id": sid, "response": "STOP_INFEASIBLE"},
        )

    if hypothesis.symptom == "likely_infeasible":
        return TrialAction(
            kind="stop",
            description=f"[{hypothesis.rule_id}] {hypothesis.mechanism}",
            payload={"strategy_id": "fix_dof", "response": "STOP_INFEASIBLE"},
        )

    if sid == "refresh_estimates":
        return TrialAction(
            kind="refresh_estimates",
            description=(
                f"[{hypothesis.rule_id}] {hypothesis.mechanism} — "
                f"predict: {hypothesis.predicted_response}"
            ),
            payload={"strategy_id": sid, "hypothesis_id": hypothesis.rule_id},
        )

    if sid == "baseline_spec_recovery":
        return TrialAction(
            kind="refresh_estimates",
            description=f"[{hypothesis.rule_id}] Baseline recovery path — refresh first",
            payload={"strategy_id": "baseline_spec_recovery", "hypothesis_id": hypothesis.rule_id},
        )

    if not hypothesis.spec_name:
        return None

    spec = next((s for s in state.specs if s.name == hypothesis.spec_name), None)
    if spec is None or spec.goal_value is None:
        return None

    new_goal = _bounded_goal(spec, hypothesis.direction, limits)
    if new_goal is None or abs(new_goal - float(spec.goal_value)) < 1e-30:
        return None

    return TrialAction(
        kind="set_goal",
        description=(
            f"[{hypothesis.rule_id}] {hypothesis.mechanism} — "
            f"'{spec.name}' {spec.goal_value:.4g} → {new_goal:.4g} "
            f"(predict: {hypothesis.predicted_response})"
        ),
        payload={
            "spec_name": spec.name,
            "goal": new_goal,
            "previous": float(spec.goal_value),
            "strategy_id": sid,
            "hypothesis_id": hypothesis.rule_id,
            "family": hypothesis.mv_family.lower().replace(" ", "_"),
        },
    )


def propose_from_expert(
    state: ColumnState,
    expert: ExpertContext,
    limits: ConvergenceLimits,
) -> TrialAction | None:
    """Select trial from ranked hypotheses (35_Experiment_Selection)."""
    if expert.selected_hypothesis is None:
        if expert.ranked_hypotheses:
            expert.selected_hypothesis = expert.ranked_hypotheses[0]
        else:
            return None
    return hypothesis_to_action(expert.selected_hypothesis, state, limits)


def update_learning_from_trial(
    hypothesis_id: str | None,
    kept: bool,
    response: ResponseClass | None,
) -> float:
    """Return confidence delta for learning system (36)."""
    if not hypothesis_id:
        return 0.0
    if response == ResponseClass.TARGET_MET:
        return 0.3
    if kept and response in {
        ResponseClass.CONVERGED_IMPROVED,
        ResponseClass.CONVERGED_STRONGLY_IMPROVED,
    }:
        return 0.15
    if kept:
        return 0.05
    if response == ResponseClass.CONVERGED_NO_MATERIAL_CHANGE:
        return -0.1
    return -0.2


def format_expert_board(expert: ExpertContext) -> str:
    lines = [
        f"PROCESS FLOW: {expert.process_state.value}",
        "EVIDENCE:",
    ]
    for ev in expert.evidence[:8]:
        lines.append(f"  • {ev}")
    if expert.ranked_hypotheses:
        lines.append("HYPOTHESES (ranked):")
        for i, h in enumerate(expert.ranked_hypotheses[:5], 1):
            sel = " ← SELECTED" if expert.selected_hypothesis and h.rule_id == expert.selected_hypothesis.rule_id else ""
            lines.append(
                f"  {i}. [{h.confidence:.2f}] {h.rule_id} | {h.strategy_id}{sel}"
            )
            lines.append(f"     {h.mechanism}")
            if h.predicted_response:
                lines.append(f"     predict: {h.predicted_response}")
    else:
        lines.append("HYPOTHESES: (none — fix model or State E/F)")
    return "\n".join(lines)
