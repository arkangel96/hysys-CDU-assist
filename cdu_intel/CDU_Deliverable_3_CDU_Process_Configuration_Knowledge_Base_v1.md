# CDU Deliverable 3

# CDU Process Configuration Knowledge Base

## Version 1.0

## Purpose

This document defines the engineering purpose, interactions, operating
philosophy, HYSYS implementation, and troubleshooting knowledge for each
major section of an Atmospheric Crude Distillation Unit (CDU).

The CDU shall be treated as an integrated process, where each subsystem
influences product quality, energy consumption, and column stability.

------------------------------------------------------------------------

# 1. Crude Feed System

## Purpose

Deliver a stable, well-characterized feed to the CDU.

## Monitor

-   Flow
-   Temperature
-   Pressure
-   Blend ratio
-   Water and salt content
-   API gravity

## Engineering Considerations

-   Stable feed is essential for steady operation.
-   Blend changes affect the entire column.

## Common Problems

-   Incorrect blend ratio
-   Feed property mismatch
-   Unstable flow

------------------------------------------------------------------------

# 2. Preheat Train

## Purpose

Recover heat from hot products before the furnace.

## Key Variables

-   Feed outlet temperature
-   Pressure drop
-   Heat recovery
-   Fouling indication

## HYSYS Notes

Represent exchanger network at an appropriate level of detail. Validate
duty against plant/design data.

## Typical Issues

-   Fouling
-   Excessive pressure drop
-   Heat imbalance

------------------------------------------------------------------------

# 3. Desalter

## Purpose

Remove salts, solids, and water to protect downstream equipment.

## Monitor

-   Salt removal efficiency
-   Water content
-   Temperature
-   Pressure

## Intelligence Rule

Poor desalting increases fouling and corrosion but is usually
represented only as a feed-quality effect in steady-state HYSYS models.

------------------------------------------------------------------------

# 4. Fired Heater

## Purpose

Raise crude temperature to the desired flash-zone condition.

## Key Variables

-   Coil outlet temperature
-   Coil outlet pressure
-   Duty
-   Pressure drop

## Engineering Rule

Do not increase furnace outlet temperature solely to force product
recovery without checking thermal limits and downstream impacts.

## Common Problems

-   Excessive duty
-   Unrealistic outlet temperature
-   Heat-balance mismatch

------------------------------------------------------------------------

# 5. Flash Zone

## Purpose

Create the initial vapor-liquid split entering the atmospheric column.

## Key Variables

-   Flash-zone pressure
-   Feed vapor fraction
-   Feed enthalpy
-   Overflash

## Engineering Rule

Flash-zone conditions govern the internal traffic throughout the column.

------------------------------------------------------------------------

# 6. Atmospheric Column

## Purpose

Separate crude into boiling-range products.

## Major Sections

-   Rectifying section
-   Flash zone
-   Stripping section

## Monitor

-   Stage temperatures
-   Pressure profile
-   Internal vapor flow
-   Internal liquid flow

## Common Problems

-   Poor separation
-   Temperature discontinuities
-   Product overlap

------------------------------------------------------------------------

# 7. Wash Section

## Purpose

Reduce heavy entrainment into upper products.

## Monitor

-   Wash oil circulation
-   Liquid loading
-   Temperature profile

## Typical Issues

-   Insufficient wash oil
-   Excess entrainment

------------------------------------------------------------------------

# 8. Overflash

## Purpose

Provide internal reflux and improve heavy-end separation.

## Engineering Rule

Too little overflash reduces separation. Too much overflash increases
furnace duty and internal traffic.

------------------------------------------------------------------------

# 9. Pumparounds

## Purpose

Remove heat and create internal reflux.

## Key Variables

-   Draw stage
-   Return stage
-   Duty
-   Flowrate
-   Return temperature

## Engineering Rule

Pumparounds simultaneously affect: - Energy recovery - Internal reflux -
Product quality - Temperature profile

------------------------------------------------------------------------

# 10. Side Draws

## Products

-   Naphtha
-   Kerosene
-   Diesel
-   Atmospheric Gas Oil

## Engineering Rule

Changing one side-draw rate influences neighboring products.

------------------------------------------------------------------------

# 11. Side Strippers

## Purpose

Strip light hydrocarbons using steam.

## Monitor

-   Steam rate
-   Bottom temperature
-   Product endpoint

## Common Problems

-   Insufficient stripping
-   Excess steam
-   Product contamination

------------------------------------------------------------------------

# 12. Stripping Steam

## Purpose

Reduce hydrocarbon partial pressure and improve fractionation.

## Engineering Rule

Increasing steam improves stripping but raises vapor traffic and
condenser load.

------------------------------------------------------------------------

# 13. Overhead System

## Components

-   Condenser
-   Accumulator
-   Reflux drum
-   Reflux pumps

## Monitor

-   Reflux ratio
-   Condenser duty
-   Overhead pressure
-   Off-gas rate

------------------------------------------------------------------------

# 14. Product Rundown

## Objectives

Maintain: - Product flow - Product temperature - Product quality

Validate: - Yield - Cut points - Specifications

------------------------------------------------------------------------

# 15. Atmospheric Residue

## Purpose

Deliver stable feed to downstream vacuum distillation or residue
processing.

## Monitor

-   Bottom temperature
-   Residue rate
-   Heavy-end recovery

------------------------------------------------------------------------

# 16. Integrated Interaction Matrix

  -----------------------------------------------------------------------
  Change         Primary Effect             Secondary Effect
  -------------- -------------------------- -----------------------------
  Furnace outlet Feed vaporization          Product yields, duties
  temperature                               

  Flash-zone     Separation                 Internal traffic
  pressure                                  

  Overflash      Heavy-end separation       Furnace duty

  Pumparound     Internal reflux            Heat recovery
  duty                                      

  Side-draw rate Product yield              Neighboring product quality

  Steam rate     Stripping                  Vapor loading

  Reflux         Upper separation           Condenser duty
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 17. HYSYS Modeling Philosophy

The AI shall:

1.  Validate crude characterization before building the flowsheet.
2.  Build a simplified converged CDU.
3.  Add side draws.
4.  Add side strippers.
5.  Add steam.
6.  Add pumparounds individually.
7.  Activate specifications gradually.
8.  Validate balances.
9.  Compare against plant or design data.
10. Save a stable baseline before optimization.

------------------------------------------------------------------------

# 18. Machine Summary

``` yaml
sections:
  - crude_feed
  - preheat_train
  - desalter
  - fired_heater
  - flash_zone
  - atmospheric_column
  - wash_section
  - overflash
  - pumparounds
  - side_draws
  - side_strippers
  - stripping_steam
  - overhead_system
  - product_rundown
  - atmospheric_residue

key_principles:
  - integrated_system
  - progressive_model_build
  - validate_before_optimize
  - preserve_baseline
```

------------------------------------------------------------------------

# Status

CDU Deliverable 3 Version 1.0 completed.

Next: **CDU Deliverable 4 -- Aspen HYSYS CDU Model-Building
Specification**
