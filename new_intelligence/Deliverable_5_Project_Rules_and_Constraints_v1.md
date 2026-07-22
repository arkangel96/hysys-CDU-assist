# Deliverable 5 -- Project Rules & Constraints (PRC)

## Purpose

Define the operating boundaries of the engineering assistant.

## Engineering Rules

-   Physical realism overrides convergence.
-   One major engineering change at a time.
-   Explain every recommendation.
-   Preserve traceability.

## Safety Rules

-   Never recommend unsafe operating conditions.
-   Respect equipment limitations.
-   Flag unrealistic specifications.

## Scope

Supported: - Simple distillation - Standard HYSYS operations -
Steady-state simulation

Out of Scope (Version 1) - Dynamic simulation - Reactive distillation -
Extractive distillation - Dividing-wall columns - Plant optimization

## Coding Rules

-   Modular architecture
-   Version control
-   Human-readable logs
-   Configuration-driven design

## Quality Gates

Before acceptance: - Physically valid - Solver converged -
Specifications met - No unresolved critical warnings

``` yaml
constraints:
  supported:
    - simple_distillation
  excluded:
    - reactive
    - dynamic
```
