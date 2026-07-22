# Experiment Selection

**Module ID:** 35  
**Parent:** [`00_System_Architecture.md`](00_System_Architecture.md)  
**Reasoning engine:** [`33_Reasoning_Engine.md`](33_Reasoning_Engine.md)  
**Process state:** Experiment Planning (step 6) in [`32_State_Machine.md`](32_State_Machine.md)  
**Executable:** `column_engine.choose_trial_action()`, `trial_map.STRATEGY_CATALOG`

Integrated from `CDU_Expert_Modules_Starter/35_Experiment_Selection.md`.

---

## Purpose

Select the **minimum-impact, highest-value** single experiment from ranked hypotheses.

The automation shall **minimize unnecessary changes** to the HYSYS case.

---

## Selection priority (in order)

1. **Lowest risk** — no DOF break, no FINAL_TARGET relax, no structural edit  
2. **Highest information gain** — expected to move dominant gap  
3. **Reversible** — snapshot/restore available  
4. **Minimal energy penalty** — prefer small PA nudge over furnace swing  
5. **Minimal product disturbance** — avoid moving all draws at once  

**Hard rule:** only **one primary engineering experiment** per iteration unless coordinated action is explicitly required and audited.

---

## Decision flow

```text
Ranked hypotheses (from 33)
  → filter: preconditions + State A-F allowed actions
  → filter: Trial Map failed bands (36)
  → score: priority list above
  → pick top → map to strategy_id + bounded payload
  → predict response (for Evaluation step)
  → human approve (interactive default)
  → execute
```

---

## Category gates

| State | Allowed experiment families |
|-------|----------------------------|
| A | None — fix model |
| B | `refresh_estimates`, `baseline_spec_recovery`, `fix_dof` |
| C | Category-1: PA, draw, strip, reflux/OH, overflash (if mapped) |
| D | Operability: split recovery, dry-draw fix |
| F | None — report and stop |

**Never:** `cut_point_nudge` on locked FINAL_TARGET without user unlock.

---

## T-100 strategy catalog (linked)

| Strategy ID | When to select |
|-------------|----------------|
| `pa_duty_nudge` | Cut quality off, fractionation hypothesis, PA section identified |
| `side_draw_rate_nudge` | Yield / split wrong |
| `side_strip_steam_nudge` | Side product lights / strip deficiency |
| `reflux_or_oh_nudge` | Naphtha / OH end-point |
| `baseline_spec_recovery` | State B, high residuals |
| `spec_swap_last_resort` | Last resort, DOF=0, 1-for-1 only |

Full list: `trial_map.STRATEGY_CATALOG`, [`../cdu_convergence_playbook.md`](../cdu_convergence_playbook.md).

---

## Bounded step policy

- One PA, one knob (duty **or** rate) per trial  
- Typical step: small % of current GoalValue (configurable in `ConvergenceLimits`)  
- Wild jumps only if case clearly dead — PE judgment  

---

## Automation hook

| Capability | Status |
|------------|--------|
| Select from hypothesis | **Planned** |
| Interactive approve-next | Partial — GUI trials |
| Bounded payload | Yes |
| Strategy ID logging | Yes — Trial Map |

---

*Experiment selection · CDU Expert System*
