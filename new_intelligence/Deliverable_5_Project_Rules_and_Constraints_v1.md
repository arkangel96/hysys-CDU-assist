# Deliverable 5 -- Project Rules & Constraints (PRC)

## Version 1.1 — Atmospheric CDU

## Purpose

Define the operating boundaries of the engineering assistant for
**CDU Assist**.

## Engineering Rules

- Physical realism overrides convergence.
- One major engineering **family** at a time.
- Explain every recommendation.
- Preserve traceability (Trial Map / audit).
- Multi-product FINAL_TARGETs are locked unless the engineer allows
  change.
- Do not default mid-cut problems to top reflux only.

## Safety Rules

- Never recommend unsafe operating conditions.
- Respect equipment and hydraulic limitations (incl. PA returns).
- Flag unrealistic specifications and impossible draws.

## Scope

**Supported (v1 product line):**

- CDU / atmospheric crude distillation in Aspen HYSYS
- Steady-state simulation
- Standard HYSYS column operations: draws, pumparounds, steam,
  condenser specs, petroleum cut / ASTM-oriented targets as exposed

**Out of Scope (Version 1):**

- Dynamic simulation
- Reactive / extractive / dividing-wall columns
- Plant-wide economic optimization
- Simple Column Assist (2-product distillation / stripping) — separate
- VDU Assist — separate later tool

## Coding Rules

- Modular architecture
- Version control
- Human-readable logs
- Configuration-driven design
- Never auto-save `.hsc`; never silent Specs.Add; never auto-relax
  FINAL_TARGETs

## Quality Gates

Before acceptance (State E intent):

- Physically valid
- Solver converged (or PE-accepted with explained residuals)
- Governing multi-product FINAL_TARGETs met
- No unresolved critical Messages / popups
- Audit trail explains moves

```yaml
constraints:
  domain: cdu_atmospheric
  supported:
    - cdu_atmospheric
    - steady_state
    - side_draws
    - pumparounds
    - stripping_steam
    - petroleum_cut_astm_targets
  excluded:
    - simple_column_product_line
    - vdu_product_line
    - reactive
    - dynamic
    - plant_teo_optimization
  never:
    - auto_save_hsc
    - auto_relax_final_targets
    - auto_specs_add_when_dof_zero
```
