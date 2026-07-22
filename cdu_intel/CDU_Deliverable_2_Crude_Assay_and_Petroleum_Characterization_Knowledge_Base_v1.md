# CDU Deliverable 2

# Crude Assay and Petroleum Characterization Knowledge Base

## Version 1.0

## Purpose

This document defines the engineering knowledge required to correctly
characterize crude oils in Aspen HYSYS before building or validating an
Atmospheric Crude Distillation Unit (CDU) model.

The AI shall treat crude characterization as the foundation of the
entire CDU simulation.

------------------------------------------------------------------------

# 1. Engineering Principles

-   Characterization quality determines simulation quality.
-   Incorrect assays cannot be corrected by tuning the column.
-   Preserve the original assay data.
-   Record all assumptions used to fill missing properties.
-   Distinguish measured from estimated data.

------------------------------------------------------------------------

# 2. Supported Assay Types

The AI shall recognize and interpret:

-   True Boiling Point (TBP)
-   ASTM D86
-   ASTM D1160
-   Equilibrium Flash Vaporization (EFV)
-   Simulated Distillation (SIMDIS)
-   Laboratory assay blends
-   Vendor refinery assays

For each assay, identify: - Source - Units - Temperature basis -
Pressure basis - Data completeness

------------------------------------------------------------------------

# 3. Required Crude Properties

Collect and validate:

-   Crude name
-   Assay version
-   API gravity
-   Density
-   Sulfur
-   Nitrogen
-   Molecular weight
-   Viscosity
-   Pour point
-   Watson K factor
-   Distillation curve
-   Light ends
-   Metals (if available)

------------------------------------------------------------------------

# 4. Pseudo-Component Generation

The AI shall:

-   Preserve light components explicitly.
-   Generate continuous pseudo-components.
-   Avoid cut overlaps or gaps.
-   Verify density and molecular-weight trends.
-   Check characterization consistency.

------------------------------------------------------------------------

# 5. Blend Intelligence

For blended crudes:

-   Verify blend fractions sum to 100%.
-   Track each crude independently.
-   Preserve individual assay identity.
-   Confirm blended bulk properties.

------------------------------------------------------------------------

# 6. Validation Checklist

Before accepting a characterization:

-   Distillation curve is monotonic.
-   Density trend is reasonable.
-   MW trend is reasonable.
-   No duplicated fractions.
-   No missing cut ranges.
-   Light ends are balanced.
-   Property method is compatible.

------------------------------------------------------------------------

# 7. Common Characterization Errors

-   Missing light ends
-   Wrong cut temperatures
-   Inconsistent density
-   Incorrect pseudo-component count
-   Mixed assay bases
-   Wrong units
-   Duplicate fractions
-   Excessive extrapolation

------------------------------------------------------------------------

# 8. Engineering Heuristics

The AI should:

-   Reject characterization that violates physical trends.
-   Warn when estimated data dominate measured data.
-   Prefer complete laboratory assays.
-   Preserve traceability for every estimated value.

------------------------------------------------------------------------

# 9. Machine Summary

``` yaml
focus:
  - crude_assay
  - pseudo_components
  - blend_validation

validate:
  - tbp_curve
  - density
  - molecular_weight
  - sulfur
  - api
  - light_ends

reject_if:
  - duplicate_cuts
  - inconsistent_properties
  - unknown_basis
```

------------------------------------------------------------------------

# Status

CDU Deliverable 2 Version 1.0 completed.

Next: **CDU Deliverable 3 -- CDU Process Configuration Knowledge Base**
