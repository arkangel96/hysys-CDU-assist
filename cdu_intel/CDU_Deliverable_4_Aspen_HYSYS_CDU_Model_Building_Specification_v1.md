# CDU Deliverable 4

# Aspen HYSYS CDU Model-Building Specification

## Version 1.0

## Purpose

This specification defines a recommended engineering workflow for
building an Atmospheric Crude Distillation Unit (CDU) model in Aspen
HYSYS. The objective is to produce a physically consistent, traceable
model before attempting optimization.

------------------------------------------------------------------------

# 1. Engineering Philosophy

The model shall be built incrementally.

Do **not** activate all complexity at once. Establish a stable baseline
first, then introduce additional features one at a time.

Priority: 1. Crude characterization 2. Thermodynamics 3. Feed definition
4. Base column convergence 5. Side draws 6. Side strippers 7. Stripping
steam 8. Pumparounds 9. Product specifications 10. Energy refinement

------------------------------------------------------------------------

# 2. Basis Environment

Verify before creating the flowsheet:

-   Aspen HYSYS version
-   Unit set
-   Petroleum/Oil Environment enabled
-   Property package suitable for petroleum systems
-   Crude assay source documented

Record: - Simulation version - Assay version - Date - Engineer

------------------------------------------------------------------------

# 3. Crude Characterization Workflow

1.  Import crude assay.
2.  Validate assay data.
3.  Generate pseudo-components.
4.  Preserve light ends explicitly.
5.  Review density and molecular-weight trends.
6.  Save characterization baseline.

Never modify pseudo-components without recording the reason.

------------------------------------------------------------------------

# 4. Feed Stream Definition

Define:

-   Flowrate
-   Temperature
-   Pressure
-   Composition
-   Vapor fraction
-   Enthalpy

Confirm the feed entering the furnace matches the intended crude blend.

------------------------------------------------------------------------

# 5. CDU Column Configuration

Document:

-   Total stages
-   Stage numbering convention
-   Flash-zone location
-   Feed stage
-   Side draw stages
-   Side stripper connections
-   Pumparound draw/return stages
-   Top and bottom pressure

------------------------------------------------------------------------

# 6. Product Configuration

Typical products:

-   Off-gas
-   Naphtha
-   Kerosene
-   Diesel
-   Atmospheric Gas Oil
-   Atmospheric Residue

Initially use simple flow specifications before applying product-quality
constraints.

------------------------------------------------------------------------

# 7. Side Draws

Introduce one side draw at a time.

After each addition verify:

-   Material balance
-   Product flow
-   Temperature profile
-   Solver stability

------------------------------------------------------------------------

# 8. Side Strippers

For each stripper define:

-   Feed connection
-   Steam rate
-   Product outlet
-   Pressure
-   Temperature

Validate the stripper independently before tuning product quality.

------------------------------------------------------------------------

# 9. Stripping Steam

Introduce steam only after the base column converges.

Monitor:

-   Vapor traffic
-   Condenser duty
-   Product endpoints

------------------------------------------------------------------------

# 10. Pumparounds

For each pumparound record:

-   Draw stage
-   Return stage
-   Flow
-   Duty
-   Return temperature

Add only one pumparound at a time.

------------------------------------------------------------------------

# 11. Specifications

Recommended sequence:

1.  Pressure profile
2.  Product flow
3.  Reflux
4.  Furnace outlet condition
5.  Product quality
6.  Overflash

Avoid conflicting Design Specs and Adjust operations.

------------------------------------------------------------------------

# 12. Solver Strategy

Initialization:

1.  Relax tolerances if required.
2.  Converge the simplest model.
3.  Activate one additional feature.
4.  Re-run.
5.  Save stable cases frequently.

If convergence fails:

-   Roll back to the previous stable case.
-   Remove the last feature added.
-   Diagnose before making further changes.

------------------------------------------------------------------------

# 13. Validation Checklist

Before accepting the model:

-   Assay validated
-   Property package confirmed
-   Material balance closed
-   Heat balance closed
-   Stable pressure profile
-   Reasonable temperature profile
-   Product yields reasonable
-   Product qualities reviewed
-   No unresolved critical warnings

------------------------------------------------------------------------

# 14. Version Control

Save milestones:

-   00_Assay
-   01_BaseColumn
-   02_SideDraws
-   03_Strippers
-   04_Steam
-   05_Pumparounds
-   06_ProductSpecs
-   07_ValidatedBaseline

Never overwrite the validated baseline.

------------------------------------------------------------------------

# 15. Cursor Operating Rules

The AI shall:

-   Explain every recommended model change.
-   Change one major engineering variable at a time.
-   Preserve reproducibility.
-   Distinguish observations from assumptions.
-   Record every successful convergence path.

------------------------------------------------------------------------

# Machine Summary

``` yaml
workflow:
  - characterize_crude
  - define_feed
  - build_base_column
  - add_side_draws
  - add_strippers
  - add_steam
  - add_pumparounds
  - activate_specs
  - validate
  - save_baseline

rules:
  - incremental_build
  - preserve_baseline
  - one_major_change
  - validate_before_optimize
```

------------------------------------------------------------------------

# Status

CDU Deliverable 4 Version 1.0 completed.

Next: **CDU Deliverable 5 -- CDU Convergence and Troubleshooting
Playbook**
