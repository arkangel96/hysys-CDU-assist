# Deliverable 4 -- Learning & Memory Specification (LMS)

## Purpose

Define how the engineering assistant stores, retrieves, and reuses
engineering experience.

## Memory Levels

### Session Memory

-   Current simulation state
-   Current hypothesis
-   Active experiment
-   Recent changes

### Project Memory

-   Successful convergence paths
-   Failed strategies
-   Preferred workflows
-   Engineering notes

### Knowledge Memory

-   Reusable engineering heuristics
-   Common troubleshooting cases
-   Decision patterns

## Case Record

Each completed experiment stores: - Case ID - Date - Simulation
version - Initial conditions - Diagnosis - Engineering action - Result -
Confidence - Lessons learned

## Retrieval Strategy

Search by: - Similar feed - Similar column - Similar error - Similar
objective

## Learning Rules

-   Reinforce successful actions.
-   Reduce confidence in repeated failures.
-   Never overwrite proven engineering knowledge without evidence.

``` yaml
memory:
  - session
  - project
  - knowledge

store:
  - diagnosis
  - action
  - outcome
  - confidence
  - lessons
```
