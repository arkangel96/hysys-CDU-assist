# Expert Pseudocode

**Module ID:** 37  
**Parent:** [`00_System_Architecture.md`](00_System_Architecture.md)  
**Reasoning engine:** [`33_Reasoning_Engine.md`](33_Reasoning_Engine.md)  
**State machine:** [`32_State_Machine.md`](32_State_Machine.md)

Reference algorithms for implementing the CDU Expert System in code.

---

## Master session (full process flow)

```text
function cdu_expert_session(column_name):
    # 1 Initialization
    connect_hysys()
    process_state = INITIALIZATION

    # 2 Model Validation → may set State A
    process_state = MODEL_VALIDATION
    if not validate_model(column_name):
        return guidance_state_A()

    # 3 Observation
    process_state = OBSERVATION
    state = inspect(column_name)
    evidence = collect_evidence(state)           # 31, domain 20-30

    # 4 Diagnosis
    process_state = DIAGNOSIS
    eng_state = classify_A_to_F(evidence)        # 32

    if eng_state == A: return fix_model_guidance(evidence)
    if eng_state == B: return numerical_recovery(evidence)
    if eng_state == E: return success_report(evidence)
    if eng_state == F: return infeasible_report(evidence)

    # 5-6 Hypothesis + Experiment Planning
    process_state = HYPOTHESIS_GENERATION
    targets = load_final_targets()               # 27, user config
    gaps = compare_targets(state, targets)
    hypotheses = []
    for gap in gaps:
        module = route_symptom_to_module(gap)    # 34
        hypotheses += module.generate_hypotheses(gap, evidence)

    ranked = rank_hypotheses(hypotheses)         # 33 confidence model
    process_state = EXPERIMENT_PLANNING
    experiment = select_experiment(ranked)       # 35 — one family

    if not user_approves(experiment):            # interactive default
        return pe_board_pending(experiment)

    # 7 Execution
    process_state = EXECUTION
    snapshot = save_state()
    prediction = experiment.expected_response
    result = execute_bounded_trial(experiment)

    # 8 Evaluation
    process_state = EVALUATION
    after = inspect(column_name)
    evaluation = evaluate_trial(snapshot, after, prediction)

    # 9 Learning
    process_state = LEARNING
    if evaluation.keep:
        update_confidence(experiment.hypothesis_id, +evaluation.score)
    else:
        restore(snapshot)
        update_confidence(experiment.hypothesis_id, -evaluation.score)

    log_trial_map(experiment, evaluation)        # 36
    return pe_board(evidence, ranked, evaluation)
```

---

## Module-specific functions (to implement)

| Module | Function |
|--------|----------|
| 25 PumpArounds | `pa_hypotheses(cut_gap, tower_section, evidence)` |
| 26 Side Strippers | `strip_hypotheses(side_product, evidence)` |
| 27 Product Quality | `quality_gaps(streams, final_targets)` |
| 24 Main Fractionator | `split_hypotheses(yield_gap, evidence)` |
| 35 Experiment Selection | `select_experiment(ranked, trial_map_history)` |
| 36 Learning | `update_confidence(hypothesis_id, delta, history)` |

---

## Implementation target

`column_engine.py` — explicit `generate_hypotheses()` / `rank_hypotheses()` calling rule tables from domain modules (YAML or Python dicts generated from markdown rules).

---

*Expert pseudocode · CDU Expert System*
