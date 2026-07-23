# Learning System

**Module ID:** 36  
**Parent:** [`00_System_Architecture.md`](00_System_Architecture.md)  
**Reasoning engine:** [`33_Reasoning_Engine.md`](33_Reasoning_Engine.md)  
**Process state:** Learning (step 9) in [`32_State_Machine.md`](32_State_Machine.md)  
**Executable:** `trial_map.build_trial_map`, Trial Map window, session history

Integrated from `CDU_Expert_Modules_Starter/36_Learning_System.md`.

---

## Purpose

Record what was tried, what worked, and update **confidence** for future hypothesis ranking.

Historical cases shall improve future decisions — not repeat blind failures.

---

## Record per iteration

| Field | Source |
|-------|--------|
| Initial state | Snapshot / `ColumnState` before |
| Hypothesis | Rule ID, mechanism, confidence before |
| Action | `TrialAction` — strategy_id, spec, delta |
| Prediction | Expected direction from rule |
| Actual response | After inspect — residuals, quality, physical |
| Success score | keep/reverse + response class |
| Final state | Snapshot after (if kept) |

**Storage today:** Trial Map path + activity log + curated [`docs/lessons/`](../lessons/README.md) (Reusable vs Case-specific; feed/assay tagged). **Future:** structured case memory per column/case (auto confidence still HELD).

---

## Confidence update rules

After each evaluation:

| Outcome | Effect on hypothesis / strategy |
|---------|--------------------------------|
| Kept + dominant gap improved | ↑ confidence; mark strategy HELPED |
| Kept + no material change | ↓ confidence; weak-response flag |
| Reversed / worsened | ↓ confidence; mark strategy FAILED |
| Operability violated | Block strategy band; force State D review |
| Repeated failure same family | Switch family or State F |

Future implementation may add Bayesian updating or reinforcement learning — **not required for v0.1**.

---

## Going-nowhere detector (P2)

Stop or escalate when:

- Same strategy_id failed ≥ N times without improvement  
- Flat sensitivity (e.g. PA duty ↑ three times, cut unchanged)  
- Trial Map shows thrashing  

Report State F with evidence — do not relax FINAL_TARGET.

---

## Integration with Trial Map

```text
trial_map.build_trial_map(column, history, state, diagnosis)
  → path trail (what was tried)
  → board status OPEN / HELPED / FAILED / NEXT
  → feeds back into 35_Experiment_Selection (skip FAILED)
```

---

## Automation hook

| Capability | Status |
|------------|--------|
| Trial trail | Yes |
| Strategy HELPED/FAILED | Yes |
| Hypothesis confidence store | **Planned** |
| Cross-case memory | Later |

---

*Learning system · CDU Expert System*
