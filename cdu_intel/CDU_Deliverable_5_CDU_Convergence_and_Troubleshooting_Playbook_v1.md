# CDU Deliverable 5 -- Convergence and Troubleshooting Playbook

## Purpose

Provide a structured engineering workflow for diagnosing and recovering
CDU simulations.

## Core Workflow

1.  Verify crude characterization.
2.  Verify thermodynamics.
3.  Confirm degrees of freedom.
4.  Simplify the model.
5.  Recover a stable baseline.
6.  Reintroduce complexity sequentially.

## Troubleshooting Categories

-   Crude assay problems
-   Property package issues
-   Initialization failures
-   Specification conflicts
-   Side stripper instability
-   Pumparound interaction
-   Overflash mismatch
-   Flash-zone issues
-   Product contamination
-   Solver oscillation

## Engineering Rules

-   Never change multiple major variables simultaneously.
-   Preserve the last converged case.
-   Diagnose before tuning.
