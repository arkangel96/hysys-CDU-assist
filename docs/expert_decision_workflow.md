# Expert Decision Workflow for Automating Aspen HYSYS Distillation Columns

**Document status:** Engineering specification – Version 0.1.1  
**Primary purpose:** Define the reasoning, decision hierarchy, iteration logic, recovery logic, and HYSYS interaction requirements for an external program that automates rigorous distillation-column convergence and product-specification attainment.

**Related CDU Assist docs:**

| Document | Role |
|----------|------|
| **This file** | Master PE reasoning specification (intelligence) — shared Tower Assist bible |
| [`expert/00_System_Architecture.md`](expert/00_System_Architecture.md) | **CDU Expert System Volume 0** — observation→hypothesis→experiment architecture |
| [`expert/02_Reasoning_Engine.md`](expert/02_Reasoning_Engine.md) | Maps Volume 0 loop to executable code |
| [`cdu_convergence_playbook.md`](cdu_convergence_playbook.md) | CDU Assist v0.1 operational slice + COM transferability |
| [`SCOPE_CDU_ASSIST.md`](SCOPE_CDU_ASSIST.md) | Product identity & boundaries |
| [`intelligence_improvement_notes.md`](intelligence_improvement_notes.md) | CDU backlog: gaps, P0–P3 roadmap, anti-complexity layers |
| `trial_map.py` / `column_engine.py` | Current executable subset — must be aligned to this workflow over time |

**v0.2.0:** Integrated CDU Expert System Volume 0 (`docs/expert/`).

**v0.1.1:** Integrated senior-PE intelligence review (layered implementation, Assist gaps, success definition for State E).

---

## 1. Purpose

This document defines how an experienced process-simulation engineer reasons while developing, converging, tuning, and validating a rigorous distillation column in Aspen HYSYS.

The objective is not merely to automate HYSYS commands or repeat trial-and-error adjustments. The objective is to convert expert engineering judgment into a structured decision system that can:

- Read the present HYSYS case and column configuration.
- Determine whether the case is properly posed.
- Establish a numerically stable baseline solution.
- Compare calculated products against required specifications.
- Diagnose the dominant separation deficiency.
- Select the most appropriate manipulated variable.
- Determine the direction and magnitude of the next move.
- Run HYSYS and classify the resulting response.
- Recover safely from failed or degraded runs.
- Escalate from operating changes to structural changes only when justified.
- Distinguish numerical failure from physical infeasibility.
- Preserve an auditable record of every engineering decision.

This document is intended to become the reasoning specification behind a Python, C#, or similar external automation program connected to Aspen HYSYS.

---

## 2. Scope

The initial scope is a conventional steady-state rigorous HYSYS column with:

- One or more feed streams
- An overhead product
- A bottoms product
- A total or partial condenser, where applicable
- A reboiler, where applicable
- Equilibrium stages or stages with specified efficiency
- Optional side draws, side strippers, pump-arounds, or stripping media in later extensions
- Product requirements expressed as composition, recovery, flow, temperature, vapor pressure, endpoint, or another calculated property

The methodology is applicable to:

- Distillation columns
- Stabilizers
- Strippers
- Deethanizers / Depropanizers / Debutanizers / Demethanizers
- Splitters / Fractionators
- Absorbers and reboiled absorbers, with adjusted variable priorities
- Petroleum fractionation columns, with additional assay and property-target logic

The first implementation should avoid trying to automate every possible column configuration. It should begin with a constrained class of columns and expand after the reasoning engine has been validated.

**CDU Assist first class:** atmospheric crude tower (side draws, pumparounds, cut/ASTM/TBP targets) — see [`cdu_convergence_playbook.md`](cdu_convergence_playbook.md).

**Prior validation (platform lessons):** Simple Column Assist / SW Stripper proved COM trial discipline, FINAL_TARGET lock, snapshot/restore, and States A–F. Those PE rules carry forward; the click map does not.

---

## 2.1 CDU / complex fractionator applicability

This master workflow applies to petroleum fractionation with the following adjustments:

| Topic | Simple stripper lesson | CDU Assist application |
|-------|------------------------|-------------------------|
| FINAL_TARGET | e.g. bottoms NH₃ mass frac | Cut points / ASTM / TBP / flash-freeze-cloud as plant requires |
| Category-1 MVs | RR, bottoms rate, energy | Side-draw rates, PA duty/return, reflux/OH, side-strip steam, overflash handles |
| Diagnosis | Rectification vs stripping | Split / cut light-heavy / overlap / PA / side-strip / OH / furnace-overflash / nonphysical |
| State E gates | Tiny bottoms, sentinel duties | Dry draws, sentinel duties, absurd T, unmet cut FINAL_TARGETs |
| Do not | Auto-relax purity to fake success | Auto-relax cuts to fake success |
| Structural | Feed stage / stages later | PA location, draw stage, stripper adds — permission only (P3) |

COM knobs for draws / PAs / petroleum specs must be **discovered live** (`docs/cdu_com_discovery.md`) — do not invent APIs.

---

## 3. Fundamental State Classification

The program must never treat all unsuccessful cases as the same problem.

Every run shall be classified into one of the following primary states.

### State A – Invalid or incomplete model

The column cannot be meaningfully solved because the model is not properly defined.

Examples:

- Feed is not fully specified or flashed.
- Required streams are disconnected.
- Pressure profile is undefined or contradictory.
- Condenser or reboiler configuration is inconsistent with the intended service.
- Degrees of freedom are not zero.
- Active specifications are dependent, redundant, or contradictory.
- Thermodynamic method is inappropriate for the system.
- A product target references an absent or negligible component.
- A manipulated variable has no remaining physical range.

**Rule:** No iterative optimization is allowed in this state. The model-definition problem must be corrected first.

### State B – Numerically unconverged

The model is properly posed, but HYSYS has not obtained a stable tray-by-tray solution.

Examples:

- Column solver does not converge.
- Specification residuals remain excessive.
- Temperature, flow, or composition estimates oscillate.
- Internal flows collapse or become nonphysical.
- A trial move causes solver failure.
- The solution is highly dependent on initialization.
- Duties / flows show sentinel values (e.g. -32767).

**Rule:** The current task is numerical recovery, not product optimization.

### State C – Numerically converged but off specification

HYSYS has solved the column, but one or more product requirements are not satisfied.

Examples:

- Overhead purity is low / heavy-key leakage high.
- Light-key leakage in the bottoms is high.
- Component recovery is outside target.
- Product vapor pressure, endpoint, or composition is off target.
- Product flow is incorrect.
- Product specifications conflict with each other.

**Rule:** This is the main state for expert iterative targeting.

### State D – Specifications achieved but constraints violated

Product requirements are achieved, but the solution is not acceptable.

Examples:

- Reflux ratio is unreasonable.
- Reboiler or condenser duty is excessive.
- Tray flooding / weeping / low internal traffic.
- Temperature exceeds material or process limits.
- Pressure violates equipment or downstream constraints.
- Product yield is unacceptable / utility limit exceeded.
- The solution is extremely sensitive and operationally fragile.

**Rule:** The task is constrained optimization or redesign.

### State E – Acceptable converged solution

All required product specifications and constraints are satisfied, and the solution passes final validation.

### State F – Likely infeasible under current structure

The program has gathered enough evidence that the target cannot be achieved reliably using the current:

- Stage count / feed-stage location
- Pressure level or profile
- Feed thermal condition
- Condenser/reboiler configuration / tray efficiency
- Operating-variable range / product split
- Thermodynamic basis

**Rule:** This state triggers structural escalation or an infeasibility report — not silent product-spec relaxation.

---

## 4. Overall Expert Workflow

```text
START
  |
  v
Read HYSYS case and objective
  |
  v
Validate thermodynamics, feed, topology, pressure, and degrees of freedom
  |
  +--> Invalid? --> Stop iteration and issue model-definition diagnosis
  |
  v
Read current convergence status
  |
  +--> Unconverged? --> Numerical stabilization workflow
  |
  v
Create and save a converged baseline
  |
  v
Calculate normalized product-specification errors
  |
  +--> All targets met? --> Constraint and hydraulic validation
  |
  v
Classify the dominant separation problem
  |
  v
Select candidate manipulated variables
  |
  v
Rank candidates by physical relevance, sensitivity, remaining range,
      numerical robustness, and cross-effects
  |
  v
Select one controlled trial move
  |
  v
Save recovery snapshot
  |
  v
Apply bounded change and solve HYSYS
  |
  +--> Solver failed? --> Restore, reduce step, retry, or reject move
  |
  v
Measure target response and cross-effects
  |
  v
Update local sensitivities, action history, and best-state record
  |
  v
Continue same variable, reverse, reduce step, switch variable,
or escalate structurally
  |
  v
Repeat until accepted, infeasible, or stopped by safety limits
```

**Studio interactive mode (preferred for PE review):** pause after each trial with a PE judgment board (facts → read → potential → next move → user approval).

---

## 5. Information the Program Must Read from HYSYS

The automation should build a complete `ColumnState` object before making decisions.

### 5.1 Case-level information

- HYSYS case name and version
- Unit set / fluid package / component list
- Oil/assay environment, if applicable
- Active flowsheet / column object identity
- Solver status / calculation state / simulation mode

### 5.2 Feed information

For every feed: total molar and mass flow, T, P, vapor fraction, enthalpy, composition, phase condition, feed-stage location, feed quality relative to column pressure, light-key and heavy-key content, water/non-condensables/electrolytes/associating components, near phase boundary, externally controlled by another operation.

### 5.3 Column structure

Number of stages, stage-numbering convention, condenser/reboiler type, feed stages, side draws, side strippers, pump-arounds, stripping steam/gas, efficiencies, tray/packing definitions, sections, connections, draw stages.

### 5.4 Pressure information

Top/bottom pressure, per-stage profile, section ΔP, condenser ΔP, reboiler pressure relationship, feed vs stage pressure, discontinuities, fixed vs calculated vs externally constrained.

### 5.5 Active HYSYS specifications

For every specification: name, active/inactive, type, target, current, error/residual, associated stream/stage/phase/component, manipulated variable, bounds, independence, temporary convergence vs final process requirement.

### 5.6 Column results

Top/bottom T, stage T/P, L/V traffic, stage compositions, K-values where accessible, Cond Q / Reb Q, reflux flow/ratio, distillate/bottoms/boilup flows and ratios, product phases/compositions/recoveries, balance errors, solver messages, residuals, hydraulic indicators where configured.

### 5.7 External design targets

**The target layer must be stored separately from HYSYS active specifications.**

Example:

```yaml
target_id: OH_HK_MAX
description: Maximum heavy-key concentration in overhead
product_stream: Overhead
property_type: component_mole_fraction
component: HeavyKey
relationship: less_than_or_equal
target_value: 0.005
hard_or_soft: hard
priority: 1
tolerance: 0.0001
normalization_scale: 0.005
```

This separation is essential because a final process requirement may temporarily be inactive inside HYSYS during baseline convergence — and because **product quality targets must not be auto-relaxed** to force numerical “success.”

**SW Stripper example:** bottoms NH₃ mass fraction `5e-5` (50 ppmw) is a typical plant **FINAL_TARGET**. The old stress value `1e-7` (0.1 ppm) is unrealistically tight for SWS and is not used as the default.

---

## 6. Pre-Iteration Validation

The program must perform validation before it attempts any tuning.

### 6.1 Thermodynamic validation

Flag risks (EOS vs activity methods, water/HC, electrolytes, critical/cryogenic, K-value vs expected boiling order, near-azeotropes). Stop or request approval when validity is uncertain. Iteration cannot fix a wrong property package.

### 6.2 Feed validation

Flow > minimum, composition sums ≈ 1, no negative flows, valid T/P, successful flash, adequate pressure for stage, plausible VF, key components present, valid feed stage, sensible multi-feed order.

### 6.3 Structure validation

Meaningful stage count, condenser/reboiler match service, products connected, valid side attachments, efficiencies in range, no impossible connections, pressure decreases bottom→top unless justified, DOF = 0 when solving.

### 6.4 Specification validation

Too few/many actives, duplicates, same DOF controlled twice, contradictory purity/recovery, near-zero component as controlling composition, out-of-bounds specs, fixed product flows inconsistent with feed, distillate+bottoms violating balance, no free MV left for HYSYS, impossible recoveries.

---

## 7. Baseline Convergence Strategy

An expert does not normally begin with the most difficult final purity specifications active. The first goal is a robust, physically plausible converged column.

### 7.1 Baseline principles

- Use simple, independent, numerically stable specifications.
- Avoid extreme reflux or boilup.
- Produce nonzero internal liquid and vapor traffic.
- Plausible top/bottom temperatures and explainable T profile.
- Reasonable material split (lights up, heavies down).
- Avoid hydraulic extremes; remain converged after a small disturbance.

### 7.2 Typical baseline specification concepts

Depends on column type. Candidates: RR + distillate rate; reflux flow + reboiler duty; distillate + boilup ratio; D/F + RR; bottoms flow + RR; one product flow + one energy-side spec.

Store templates by column class — do not assume one pair is universal.

### 7.3 Baseline initialization hierarchy

1. Use existing converged solution if trustworthy.
2. HYSYS estimates / shortcut estimate.
3. Expected top/bottom boiling T at P; interpolate stage T.
4. Initialize compositions by volatility.
5. Moderate reflux/boilup; relaxed product targets.
6. Converge with simple specs → save baseline → introduce final specs gradually.

### 7.4 Baseline quality tests

Reject if internal L/V ≈ 0 in an active section, unexplained T spikes, reversed profiles without justification, excessive imbalances, extreme RR/boilup, split contradicts volatility, unstable after 1–2% perturbation, or residuals still out of tolerance despite “converged” flag.

---

## 8. Product-Error Representation

For every target \(i\), calculate a signed normalized error.

Equality:

\[
e_i = \frac{y_i - y_{i,\text{target}}}{s_i}
\]

Maximum limit:

\[
e_i = \max\left(0,\frac{y_i - y_{i,\max}}{s_i}\right)
\]

Minimum limit:

\[
e_i = \max\left(0,\frac{y_{i,\min} - y_i}{s_i}\right)
\]

Overall objective:

\[
J = \sum_i w_i e_i^2 + P_{\text{constraints}} + P_{\text{solver}} + P_{\text{movement}}
\]

The score retains the best state. It does **not** replace engineering classification (States A–F).

---

## 9. Separation-Diagnosis Framework

Diagnose the controlling problem before selecting a variable.

### 9.1 Overhead rectification deficiency

Symptoms: HK too high in OH, shallow upper composition profile, inadequate liquid traffic, top T too high; increased reflux improves OH purity.

Actions: ↑ reflux/RR; rebalance distillate; check condenser; more rectifying stages / feed down; pressure if permitted; reassess keys and specs.

### 9.2 Bottom stripping deficiency

Symptoms: LK too high in bottoms, shallow lower profile, inadequate vapor traffic, bottom T too low; ↑ boilup improves bottoms.

Actions: ↑ reboiler duty / boilup / boilup ratio; rebalance draws; stripping medium; feed up; more stripping stages; pressure if permitted; check specs suppressing vapor.

### 9.3 Incorrect overall material split

Symptoms: purity OK but recovery wrong; wrong yields; reflux changes purity but not recovery.

Actions: change D or B rate; recovery/flow specs; pair split with reflux/boilup; check feed; check mutual consistency of flow targets.

### 9.4 Both ends off specification

Possible: both reflux and boilup insufficient; bad split; inadequate stages; bad feed stage; unfavorable P/feed condition; coupled/contradictory specs; bad thermo.

Test two independent MVs and build a local sensitivity matrix.

### 9.5 Weak response to operating changes

Large RR/boilup change → minimal purity gain; duties rise with little separation improvement.

Interpretations: stage-limited, relative-volatility limit, pinch, feed-stage limit, pressure limit, near thermodynamic limit, wrong keys, conflicting specs, bad solution branch.

**Triggers structural assessment / State F evidence.**

### 9.6 Nonmonotonic or opposite response

Measured HYSYS response takes priority over textbook directionality (subject to sanity checks). Other active specs may counteract; phase/regime changes; side draws; nonlinear property targets.

---

## 10. Manipulated-Variable Hierarchy

### 10.1 Category 1 – Direct operating variables (preferred first)

**Rectification-side:** reflux flow, RR, condenser duty, distillate rate, top T target, OH component target (as HYSYS MV — not as relaxing external FINAL_TARGET), OH vapor/liquid draw.

**Stripping-side:** reboiler duty, boilup, boilup ratio, bottoms rate, bottom T target, bottom component target (same caveat), stripping steam/gas.

**Overall split:** distillate/bottoms flow, D/F, component recovery, product yield.

### 10.2 Category 2 – Operating-condition variables

Column/top pressure, pressure profile, feed T / VF / preheat, condenser T constraint, utilities — broader effects; stronger justification or explicit permission.

### 10.3 Category 3 – Structural variables

Stage count, feed stage, side-draw location, side-stripper stages, pump-around location, efficiency/HETP, condenser/reboiler type.

**Not ordinary iteration variables.** Use only after operating evidence shows inadequacy.

### 10.4 Candidate ranking score

\[
R_j = aI_j + bS_j + cM_j + dN_j - eC_j - fV_j
\]

Where \(I\) = physical influence, \(S\) = sensitivity, \(M\) = remaining range, \(N\) = numerical robustness, \(C\) = cross-effect penalty, \(V\) = violation risk.

---

## 11. Controlled Trial-Move Logic

Each variable adjustment is an experiment.

### 11.1 Before the move

Confirm converged (or State B recovery path), save snapshot, record targets and cross-targets, duties/T/flows/hydraulics, hard bounds, and that the same failed move is not being repeated.

### 11.2 Initial step size

\[
\Delta u = \operatorname{clip}(f u, \Delta u_{\min}, \Delta u_{\max})
\]

Configure by variable class (RR/boilup moderate; product flow smaller; pressure very small; feed stage ±1; stage count defined increment + reinit). Not hard-coded universally.

### 11.3 Direction selection

From physical expectation, sensitivity history, active-spec behavior, constraint proximity, previous rejected directions.

### 11.4 After the move — response classes

| Class | Meaning |
|-------|---------|
| `CONVERGED_IMPROVED` | Dominant target better; acceptable cross-effects |
| `CONVERGED_STRONGLY_IMPROVED` | Clear, large improvement |
| `CONVERGED_NO_MATERIAL_CHANGE` | Weak response — consider switch/escalate |
| `CONVERGED_WORSENED` | Reverse / reject direction |
| `CONVERGED_TARGET_IMPROVED_CROSS_TARGET_WORSENED` | Coupling — two-variable logic |
| `CONVERGED_CONSTRAINT_VIOLATED` | Specs OK path but operability fail |
| `UNCONVERGED_RECOVERABLE` | Rollback + smaller step |
| `UNCONVERGED_REPEATED` | Reject region |
| `INVALID_STATE` | Model broken |
| `DISCONTINUOUS_RESPONSE` | Regime change — caution |

---

## 12. Response and Sensitivity Evaluation

\[
S_{ij} = \frac{y_i^{(k)} - y_i^{(k-1)}}{u_j^{(k)} - u_j^{(k-1)}}
\]

### 12.1 Continue same variable

Dominant target improves; cross-effects OK; meaningful sensitivity; no hard constraint; robust solve; next step in trusted interval.

### 12.2 Reduce step size

Small remaining error; nonlinear; overshoot; many HYSYS iterations; near constraint; sign change; phase/regime change.

### 12.3 Reverse direction

Opposite response repeatable; overshoot; bracket established; reversal not repeating a failed state.

### 12.4 Switch variable

Sensitivity below threshold; poor improvement per duty; excessive cross-damage; variable at bound; repeated solver fails; ≥2 no-progress attempts; higher-ranked candidate exists; **dominant deficiency changed**.

### 12.5 Escalate structurally

Operating MVs exhausted; sensitivities flatten; duties/hydraulics unreasonable; targets unmet; evidence of inadequate stages / bad feed / unfavorable P; target outside demonstrated envelope → State F.

---

## 13. One-Variable Targeting Methods

### 13.1 Bracketing

For monotonic targets: move until cross or limit → define \([u_L, u_H]\) → bisection / regula falsi / safeguarded secant → retain only converged points.

### 13.2 Safeguarded secant

\[
u_{\text{next}} = u_k + \frac{y_{\text{target}} - y_k}{(y_k - y_{k-1})/(u_k - u_{k-1})}
\]

Limit max relative move; stay in bracket; reject tiny/sign-flipping sensitivity; fall back after failure.

### 13.3 Continuation

Start baseline → relaxed target → tighten incrementally → save each state → reduce increment on difficulty → assess feasibility if stall.

Often more robust than activating the final stringent target immediately.

---

## 14. Two-Variable, Two-Target Logic

For simultaneous OH and bottoms quality: build local \(2\times 2\) response matrix from baseline perturbations; check conditioning; bounded \(\Delta\mathbf{u} = -\mathbf{S}^{-1}\mathbf{e}\) with trust region, damping, rollback.

Re-estimate after material movement — columns are nonlinear.

---

## 15. Specification-Switching Logic in HYSYS

Final product requirements do not always need to remain active HYSYS column specifications during the entire workflow.

### 15.1 Specification roles

| Role | Meaning |
|------|---------|
| `FINAL_TARGET` | External product requirement — **do not auto-relax** |
| `BASELINE_CONVERGENCE_SPEC` | Stable DOF pair for baseline |
| `TEMPORARY_STABILIZATION_SPEC` | Help numerical recovery |
| `OPERATING_CONSTRAINT` | Soft/hard plant limit |
| `MONITOR_ONLY` | Track but do not drive |

### 15.2 Switching principles

- Keep correct number of independent active HYSYS specs.
- Deactivate difficult purity as active HYSYS driver before using stable flow/ratio/T/duty for baseline.
- Approach final target via continuation.
- Swap one-at-a-time; snapshot before every swap.
- Never activate two finals that demand the same DOF.
- Keep external target evaluation active even if HYSYS purity spec is inactive.

### 15.3 Example sequence

```text
Initial active HYSYS: Reflux ratio + Distillate flow → baseline
Targeting: adjust RR / boilup externally toward external FINAL_TARGETs
Transition: deactivate RR; activate OH composition at relaxed value; tighten
Final: preferred final HYSYS pair; verify external targets + constraints
```

Exact sequence from validated template library per column class.

---

## 16. Numerical-Recovery Workflow

When a trial causes HYSYS failure:

1. Stop further movement.
2. Record failure context and solver messages.
3. Restore last converged snapshot.
4. Verify restoration.
5. Reduce rejected move (configurable factor).
6. Retry within limited count.
7. If successful → reduce trust radius.
8. If unsuccessful → reject that direction/variable in current region.
9. Consider continuation or temporary stabilization.
10. Reinitialize only after rollback-based recovery is exhausted.

### 16.1 Recovery hierarchy

Rollback → smaller step → midpoint → tighten bounds → restore baseline specs → relax difficult *temporary* target (not FINAL_TARGET without permission) → improve estimates → reinitialize → rebuild from best saved → escalate to model review.

### 16.2 Failure memory

Store failed **regions**, not only single points (variable, direction, start/fail values, other-state signature, classification, retry count, trusted bound). Prevents re-entering the same failed region.

---

## 17. Structural Escalation Logic

Evidence-driven only: feed-stage assessment (±1 stage trials), stage-count increase when purity response flattens / pinch / low relative volatility, pressure with explicit process constraints, feed thermal condition when duties/traffic abnormal.

Do not use stage count as a routine tuning variable.

---

## 18. Hydraulic and Operability Validation

A specification-achieving solution is not accepted until constraints pass: flooding, weeping, entrainment, downcomer, ΔP, Cond/Reb utility approach, stage T limits, product phase, reflux drum / reboiler VF, reasonable RR/boilup, sensitivity to small feed disturbance, stable restart from nearby init.

Where HYSYS column analysis/hydraulics are available, read them after process targeting.

---

## 19. Stopping Criteria

### 19.1 Successful stop

HYSYS numerically converged; every hard external target within tolerance; soft score OK; no hard constraint violated; hydraulics OK; balances pass; stable after small perturbation; final preferred HYSYS spec set active; snapshot + report saved.

### 19.2 Infeasible stop

Allowed operating MVs exhausted/bounded; sensitivities negligible; structural trials (in scope) fail; duties/hydraulics unacceptable before targets; mutually incompatible targets; continuation stalls; thermo/phase limit demonstrated.

Report **“likely infeasible under current assumptions”** — do not claim mathematical impossibility unless independently established. **Do not auto-relax FINAL_TARGET.**

### 19.3 Safety stop

HYSYS unresponsive; nonphysical/corrupted values; restore fails; inconsistent object model; max iterations / failed solves / wall-clock; hard engineering boundary; original case not checkpointed.

---

## 20. Required Memory and Audit Trail

Each iteration record should contain: iteration_id, timestamp, parent_state_id, case, column, convergence_status, active_specs, dominant_error, selected_variable, selection_reason, old/new value, step_basis, expected_direction, solver_result/messages, targets before/after, normalized errors, constraints, duties, top/bottom T, max flooding, response_class, sensitivity, best_state_score, rollback, next_decision.

Required saved states: ORIGINAL, last converged, best overall, best per major target, best feasible, BASELINE, FINAL, failed-state boundaries.

**Maps to Studio Trial Map path + board** (extend with PE narrative / response_class).

---

## 21. Software Architecture

| Module | Responsibility |
|--------|----------------|
| HYSYS Adapter | Attach, read/write, specs, solve, checkpoints, units, COM exceptions |
| State Extractor | Standardized ColumnState |
| Validation Engine | Thermo/feed/topology/P/specs/DOF |
| Diagnostic Engine | Rectification / stripping / split / coupled / numerical / structural / thermo / constraint |
| Decision Engine | Rank actions; select next experiment |
| Solver Supervisor | Apply step, solve, timeout, rollback, retries |
| Sensitivity / Optimization | Response matrix, bracketing, secant, trust region |
| Knowledge Base | Templates, bounds, step policies, escalation, version maps |
| History Store | Iterations, snapshots, failures, decisions |
| Report Generator | Convergence report, warnings, infeasibility evidence |

---

## 22. High-Level Pseudocode

```python
def automate_column(case, column, targets, permissions, limits):
    original = save_checkpoint(case, "ORIGINAL")

    state = read_column_state(case, column)
    validation = validate_model(state, targets)

    if not validation.is_valid:
        return report_invalid_model(validation)

    if not state.is_converged:
        state = establish_baseline(case, column, state, targets, permissions)

    if not state.is_converged:
        restore_checkpoint(original)
        return report_baseline_failure()

    baseline = save_checkpoint(case, "BASELINE")
    history = initialize_history(state, targets)
    trust_region = initialize_trust_region(state)

    for iteration in range(limits.max_iterations):
        state = read_column_state(case, column)
        assessment = assess_state(state, targets, permissions)

        if assessment.is_acceptable:
            if validate_final_solution(case, column, state, targets):
                final = save_checkpoint(case, "FINAL")
                return report_success(final, history)

        if assessment.requires_numerical_recovery:
            recovered = numerical_recovery(case, column, history)
            if not recovered:
                return report_numerical_failure(history)
            continue

        diagnosis = diagnose_separation(state, targets, history)

        candidates = generate_candidate_actions(
            state=state,
            diagnosis=diagnosis,
            targets=targets,
            permissions=permissions,
            history=history,
        )

        ranked = rank_actions(candidates, state, targets, history)

        if not ranked:
            structural = assess_structural_escalation(
                state, targets, permissions, history
            )
            if not structural.allowed_or_promising:
                return report_likely_infeasible(history, structural)
            action = structural.best_action
        else:
            action = ranked[0]

        # Interactive mode: present PE board and wait for approval here.

        recovery_point = save_checkpoint(case, f"PRE_{iteration}")
        apply_action(case, column, action)
        result = solve_hysys(case, column, limits.solve_policy)

        if not result.converged:
            restore_checkpoint(recovery_point)
            outcome = handle_failed_action(action, result, trust_region, history)
            record_iteration(history, state, action, result, outcome)
            continue

        new_state = read_column_state(case, column)
        response = evaluate_response(
            old_state=state,
            new_state=new_state,
            action=action,
            targets=targets,
        )

        update_sensitivities(history, response)
        update_trust_region(trust_region, response)
        update_best_states(case, new_state, targets, history)
        record_iteration(history, state, action, result, response)

    restore_best_feasible_state(case, history)
    return report_iteration_limit(history)
```

---

## 23. Expert Decision Example

**Problem:** Column numerically converged. OH HK limit 0.5 mol%; current 2.0 mol%. Bottoms LK recovery also below target. RR = 2.0; reboiler duty moderate; no hydraulic constraint active.

**Expert-system sequence:**

1. Confirm targets and key definitions.
2. Confirm condenser configuration and OH phase/basis.
3. Classify primary: rectification deficiency; secondary: stripping/split.
4. Select RR as first diagnostic MV.
5. Save baseline; increase RR by bounded step; solve.
6. Measure OH HK, bottoms LK, D, Cond Q, Reb Q, internal traffic.
7. Strong OH improve, bottoms OK → continue / bracket.
8. OH improve, bottoms worsen → coupling; test boilup from restored baseline; build 2×2 matrix.
9. OH barely improves → weak sensitivity; inspect stages/feed/P/specs → structural evidence.
10. Solver fails → restore; half step; retry once; else reject trust region.
11. Continue until both targets met or limits → State F report.

Intelligence is not “increase reflux.” Intelligence is *why*, *how large*, *success metrics*, *when RR stops being useful*, *what follows*, *numerical vs operational vs structural*.

---

## 24. Implementation Principles

1. Never change multiple unrelated variables without diagnostic reason.
2. Never optimize an unconverged state (State B first).
3. Never discard the last converged state.
4. Never treat solver failure as proof of process infeasibility.
5. Never treat numerical convergence as proof of engineering acceptability.
6. Prefer measured HYSYS response over assumed directionality.
7. Keep external design targets separate from active HYSYS specifications.
8. Use continuation for difficult targets.
9. Use bracketing / safeguarded methods after monotonic response is shown.
10. Escalate to structure only with evidence.
11. Track cross-effects on every important target.
12. Preserve a complete audit trail.
13. Make every variable, limit, tolerance, and policy configurable.
14. Require explicit permission before changing process-design assumptions.
15. Report uncertainty honestly.
16. **Never auto-relax FINAL_TARGET product specs without explicit user permission.**

---

## 25. Information Still Required for Detailed HYSYS Mapping

Next revision should map this reasoning to exact HYSYS interfaces for the installed version:

- Aspen HYSYS version / bitness
- External language (Python / C#)
- Automation interface and type library
- Exact column types in scope
- Screenshots or exports: Design, Monitor, Specs, Solver, Parameters, Worksheet, Rating/Hydraulics
- Typical final product specifications
- Variables the program may change vs human approval
- Representative converged and difficult cases

---

## 26. Planned Next Sections (Version 0.2)

- Exact HYSYS UI and object-model mapping
- Column specification taxonomy
- Variable-by-variable decision tables
- Decision trees for OH / bottoms / recovery / duty
- HYSYS solver-message classification
- Step-size and trust-region tables
- Feed-stage / stage-count / pressure workflows
- Side-draw, side-stripper, pump-around logic
- Petroleum-property target logic
- YAML/JSON knowledge-base schema
- Python/C# class design
- Test-case and validation protocol
- Failure-mode and safeguards matrix
- Interactive PE judgment board UI fields

---

## 27. Reference Basis

This specification is an engineering reasoning framework informed by standard rigorous-distillation practice and Aspen HYSYS column concepts. AspenTech’s official HYSYS Unit Operations documentation describes the HYSYS Column as a separate subflowsheet with its own specifications and convergence behavior. AspenTech also provides a HYSYS Customization Guide for external software interaction and official material on column analysis and hydraulic troubleshooting.

Because exact automation object names and accessible properties vary by HYSYS release and installed type libraries, they must be verified against the user’s installed Aspen HYSYS version before code is finalized.

---

## Appendix A — Studio v0.1 transferability (current COM)

Map of this workflow to what **CDU Assist** can do today. Full detail remains in [`cdu_convergence_playbook.md`](cdu_convergence_playbook.md).

| Workflow concept | Studio today | Tag |
|------------------|--------------|-----|
| DOF / active specs / GoalValue / Current / Error | `column_api.inspect` | AUTO read |
| Set GoalValue / IsActive / 1-for-1 swap | `set_spec_goal`, `set_spec_active`, `swap_active_spec` | AUTO write |
| Snapshot / restore | `snapshot` / `restore` | AUTO |
| Run column | `run_column` | AUTO |
| Stage T/P profiles | Main TS | AUTO read |
| Cond Q / Reb Q | Energy streams | AUTO read |
| Feed composition / T / P / F | Stream writers | AUTO (Stream tab) |
| External FINAL_TARGET layer | Not implemented yet | TODO |
| States A–F classification | Partial (diagnosis codes) | TODO |
| Response classes after trial | Keep/reverse + score only | TODO |
| Refresh estimates / solver damping | HYSYS UI | MANUAL |
| Hydraulics flooding | Not mapped | MANUAL / future |
| Structural (stages, feed tray) | Not in Assist | PERMISSION / later |
| Interactive PE pause board | Chat + Trial Map trail | TODO in GUI |

**Non-negotiable Studio policy (from this workflow):**

```text
FINAL_TARGET (e.g. cut / ASTM / TBP)  → locked unless user explicitly allows
Category-1 MVs (draws, PA, OH, strip steam) → preferred Assist experiments
Weak response / State F          → stop and report; do not relax product targets
```

---

## Appendix B — Alignment with platform lessons (Simple Column → CDU)

Prior Simple Column / SW Stripper live tests proved PE rules that **carry into CDU unchanged**. The click map changes; the discipline does not.

| Lesson from prior live test | Workflow clause for CDU |
|-----------------------------|-------------------------|
| Category-1 MV fixed energy/split deficiency | Category-1 draws/PA/OH; State C targeting |
| Product GoalValue relax forced “converged” | Violates §5.7 / §15 / §24.16 — wrong for cuts too |
| Weak MV response → switch / State F | §9.5 — same |
| Sentinel duties | State B numerical recovery before quality chasing |
| PE wants see-every-iteration judgment | Interactive pause in §4 / §22 |
| Active swap recovered physical solve | §15 spec roles; State B baseline |
| External stream quality vs inactive GoalValue | FINAL_TARGET vs HYSYS Active (§5.7) |
| COM internal vs worksheet units | Worksheet units mandatory (§28.3) |
| Tiny product flow after “green” | Operability gate before State E (§28.5) |
| Assist did not choose Active swap alone | Decision engine behind COM (§28.2) |

---

## 28. Intelligence implementation guidance (integrated review)

This section integrates the senior HYSYS / PE review for **CDU Assist**. Full backlog narrative remains in [`intelligence_improvement_notes.md`](intelligence_improvement_notes.md).

### 28.1 Current capability vs judgment

| Dimension | Assessment |
|-----------|------------|
| Ability to touch HYSYS (COM read/write) | Strong platform for v0.1 |
| CDU draws / PA / cut COM discovery | Pending Phase 1 |
| Simulation PE judgment in Assist Loop | Early / incomplete for CDU |
| Ready to replace a senior PE | **No** |
| Ready to assist a senior PE (interactive) | **Yes**, if FINAL_TARGETs stay locked and trials pause for review |

COM is the foundation. Expert judgment must be encoded in layers — not as one opaque mega-brain.

### 28.2 Anti-complexity rule (mandatory)

Full PE intelligence lives in **this document**. Executable Assist must grow in **thin layers**:

```text
Layer 1 (now):   Read + one MV + keep/reverse + human judge
Layer 2 (next):  States A–F + locked FINAL_TARGET + units/stream checks
Layer 3:         Spec-role swaps, sensitivity, State F reporting
Layer 4 (later): Structural moves, 2×2 matrices, hydraulics
```

**Do not** implement Sections 1–27 of this workflow in code in one pass. Rich docs, thin automation; expand only after CDU COM discovery and live validation.

### 28.3 Known Assist gaps (must close over time)

1. **State classification** — dead draws / sentinel duties → State B recovery, not GoalValue spam.  
2. **FINAL_TARGET vs Active specs** — never auto-relax cut / ASTM / TBP to force green.  
3. **Units / truth sources** — worksheet units; prefer product **stream / assay** for quality checks.  
4. **Post-trial thinking** — response classes, not score-only keep/reverse.  
5. **Active selection policy** — `IsActive` swaps only via spec-role rules + DOF = 0.  
6. **Operability gates** — reject dry draws / absurd duties as “success.”  
7. **Going-nowhere detector** — flat sensitivity → switch family or State F.  
8. **Interactive default** — one trial → PE board → approve; batch Assist only when allowed.

### 28.4 Implementation priority (P0–P3)

| Priority | Upgrade | PE intent |
|----------|---------|-----------|
| **P0** | States A–F before moves | Don’t solve the wrong problem |
| **P0** | External FINAL_TARGET layer (cuts / ASTM / TBP) | Don’t cheat quality |
| **P0** | Worksheet units + stream/assay checks | Trust HYSYS UI numbers |
| **P0** | Response classes after every trial | Continue / reverse / switch / State F |
| **P1** | Spec-role engine (baseline vs final Active set) | Controlled Active selection |
| **P1** | Operability gates (draws, duty, T profile) | Reject fake green |
| **P1** | Interactive PE judgment board in GUI | User stays in the loop |
| **P2** | Sensitivity / bracketing / continuation | Fewer blind steps |
| **P2** | Failure-region memory | Don’t re-enter failed bands |
| **P3** | Structural escalation | Evidence + permission only |

### 28.5 Definition of State E success (Assist may claim success only if all true)

1. Numerically healthy (no sentinel duties/flows on key products/draws).  
2. Every hard FINAL_TARGET met on the **product stream / assay** (within tolerance).  
3. Approved Active spec set consistent; DOF = 0.  
4. Material split and duties within engineering bounds.  
5. T (and P) profiles pass basic physical checks.  
6. Audit trail explains each Active/Goal change and why.

Otherwise report State B / C / D / F with evidence — not a fake win.

### 28.6 What better intelligence is *not*

- Aggressive GoalValue spam  
- Auto-relaxing product / cut specs  
- Random Active flips without role/DOF rules  
- Residuals-only success with nonphysical draws  
- Stripper RR logic pretended as enough for crude cuts  
- Silent batch loops without PE-readable reasons  

---

*End of Version 0.1.2*
