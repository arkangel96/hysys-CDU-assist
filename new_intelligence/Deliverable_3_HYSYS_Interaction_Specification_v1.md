# Deliverable 3 -- HYSYS Interaction Specification (HIS)

## Version 1.1 — Atmospheric CDU

## Purpose

Define how the AI reasoning layer communicates with Aspen HYSYS for
**CDU / atmospheric crude columns** while preserving engineering
integrity.

## 1. Principles

- Read before writing.
- Validate before execution.
- Change one major engineering **family** at a time.
- Preserve the last known good case (Assist snapshot).
- Never auto-save the `.hsc`.
- Never auto-relax locked FINAL_TARGETs.
- Log every action.

## 2. Read Operations

Retrieve:

- Simulation metadata, property package, components / hypocomponents
- Feed stream(s): flow, T, P, vapor fraction, assay linkage when exposed
- Column: stages, feed stage, condenser type, pressure profile
- Side draws: names, stages, rates, linked product streams
- Pumparounds: duty, circulation, return T, stages (when COM exposes)
- Side strippers / steam rates (when present)
- Specifications: type, Active/Estimate, GoalValue, current value
- DOF / residual clues when available
- Solver status, Messages pane, modal popups
- Temperature / pressure profiles; key duties

## 3. Write Operations

### Allowed routine (Category-1 operating MVs)

When exposed by COM and not locked FINAL_TARGETs:

- Top reflux ratio / reflux flow / OVHD rate (condenser-appropriate)
- Side-draw product rates
- Pumparound duty / circulation / return-T GoalValues (when writable)
- Stripping steam rates (when operable specs)

### Approval-only / later (not routine Assist clicks)

- Feed stage, draw stage, PA return/draw stage
- Number of stages
- Pressure profile changes
- Furnace / flash-zone structural duty changes
- Property package / assay redefinition
- Relaxing or rewriting locked multi-product FINAL_TARGETs
- Auto Specs.Add when DOF = 0 (recommend only)

Record for every change: previous value, new value, reason, time,
family, products expected to move.

## 4. Execution Sequence

1. Read simulation (full CDU observe set).
2. Validate inputs / DOF / physical health.
3. Snapshot baseline (in-memory — **do not auto-save `.hsc`**).
4. Apply one engineering action (one family).
5. Execute solver.
6. Capture results (multi-product + Messages/popups).
7. Compare with baseline; restore snapshot if worse.
8. Persist to disk **only if the engineer explicitly saves** in HYSYS.

## 5. Capture Results

- Convergence / solver state
- Messages + modal popup clues
- Each governing product: ASTM / TBP / cut / gap / cold props as available
- Product yields / key stream flows
- PA duties, circ, return T
- Condenser / furnace / steam duties
- Temperature and pressure profiles
- Hydraulic indicators when available
- DOF / Active set after the trial

## 6. Error Handling

Stop automatic execution if:

- Solver fails hard / nonphysical cascade
- Invalid COM object / missing specification
- Property-package or assay error
- Popup indicates impossible draw / inconsistent Active set
- Numerical instability persists after one recovery attempt

## 7. Case Management

- Snapshot baseline (Assist / session memory)
- Log iterations (Trial Map / audit trail)
- Restore previous snapshot if a trial worsens
- Compare before/after **per product**
- Export engineering summary
- **Never auto-save or overwrite the HYSYS `.hsc`**

## 8. Audit Trail

Log: user request, diagnosis, family, variables changed, products
affected, results, confidence, lessons learned.

```yaml
domain: cdu_atmospheric

workflow:
  - read
  - validate
  - modify
  - execute
  - evaluate
  - store

allowed_changes_routine:
  - top_reflux_or_ovhd
  - side_draw_rates
  - pumparound_duty_circ_return_t
  - stripping_steam

approval_only:
  - feed_draw_pa_stages
  - stage_count
  - pressure_profile
  - furnace_flash_structural
  - property_package_assay
  - final_target_relax
  - specs_add_when_dof_zero
```
