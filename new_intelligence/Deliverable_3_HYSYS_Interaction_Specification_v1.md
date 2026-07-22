# Deliverable 3 -- HYSYS Interaction Specification (HIS)

## Version 1.0

## Purpose

Define how the AI reasoning layer communicates with Aspen HYSYS while
preserving engineering integrity.

## 1. Principles

-   Read before writing.
-   Validate before execution.
-   Change one major engineering variable at a time.
-   Preserve the last known good case.
-   Log every action.

## 2. Read Operations

Retrieve: - Simulation metadata - Property package - Components -
Streams (flow, T, P, composition, vapor fraction) - Column data (stages,
feed stage, reflux, duties) - Specifications - Solver status - Warnings
and errors

## 3. Write Operations

Allowed (operating / reversible first):
- Reflux ratio
- Distillate rate / bottoms rate (when appropriate for condenser type)
- Specification GoalValues that are **Category-1 operating MVs**
  (not locked plant FINAL_TARGETs)

Approval-only / later (do not treat as routine Assist clicks):
- Feed stage
- Number of stages
- Pressure profile changes
- Property package changes
- Relaxing or rewriting locked FINAL_TARGET product specs

Record for every change: - Previous value - New value - Reason - Time

## 4. Execution Sequence

1.  Read simulation.
2.  Validate inputs.
3.  Snapshot / remember baseline (in-memory or Assist snapshot — **do not auto-save the .hsc**).
4.  Apply one engineering action.
5.  Execute solver.
6.  Capture results.
7.  Compare with baseline; restore snapshot if worse.
8.  Persist the HYSYS case to disk **only if the engineer explicitly saves**.

## 5. Capture Results

-   Convergence
-   Product purity
-   Recovery
-   Duties
-   Temperature profile
-   Pressure profile
-   Hydraulic indicators
-   Warning messages

## 6. Error Handling

Stop automatic execution if: - Solver fails - Invalid object - Missing
specification - Property-package error - Numerical instability

## 7. Case Management

-   Snapshot baseline (Assist / session memory)
-   Log iterations (Trial Map / audit trail)
-   Restore previous snapshot if a trial worsens
-   Compare before/after results
-   Export engineering summary
-   **Never auto-save or overwrite the HYSYS `.hsc` file** — user owns Save in HYSYS

## 8. Audit Trail

Log: - User request - Diagnosis - Variables changed - Results -
Confidence - Lessons learned

``` yaml
workflow:
  - read
  - validate
  - modify
  - execute
  - evaluate
  - store

allowed_changes_routine:
  - reflux
  - distillate
  - bottoms

approval_only:
  - feed_stage
  - stages
  - pressure
  - property_package
  - final_target_relax
```
