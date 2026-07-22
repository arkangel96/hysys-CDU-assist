# Deliverable 2 -- Engineering Knowledge Base (EKB)

## Version 1.0

### Scope

This document defines the engineering knowledge required by an AI
assistant supporting **simple distillation columns in Aspen HYSYS**. It
focuses on domain knowledge rather than reasoning strategy.

# 1. Distillation Fundamentals

## Objective

Separate components based on volatility while meeting product
specifications with stable operation and acceptable energy usage.

Key concepts: - Vapor-liquid equilibrium (VLE) - Relative volatility -
Material balance - Energy balance - Stage efficiency (conceptual) -
Reflux and boil-up - Pressure effects

# 2. Core HYSYS Objects

The AI shall understand: - Material Stream - Energy Stream -
Distillation Column - Condenser - Reboiler - Feed - Product Streams -
Design Specs - Adjust Operations - Spreadsheet objects

# 3. Critical Engineering Variables

  Variable           Primary Effect                 Secondary Effect
  ------------------ ------------------------------ ---------------------------------
  Reflux Ratio       Improves separation            Increases duties
  Distillate Rate    Changes overhead recovery      Affects purity
  Bottoms Rate       Changes bottoms recovery       Affects purity
  Feed Stage         Internal composition profile   Energy usage
  Number of Stages   Separation capability          Capital cost
  Pressure           Relative volatility            Condenser/Reboiler temperatures
  Feed Condition     Internal traffic               Separation efficiency

# 4. Engineering Relationships

## Reflux

Higher reflux generally: - Improves purity - Improves recovery -
Increases condenser duty - Increases reboiler duty - Increases flooding
tendency

## Feed Stage

Incorrect feed stage may: - Increase energy - Reduce purity - Increase
remixing - Reduce efficiency

## Pressure

Higher pressure generally: - Reduces relative volatility - Makes
difficult separations harder - Changes utility requirements

# 5. Common Performance Indicators

The AI shall monitor: - Product purity - Component recovery - Reflux
ratio - Reboiler duty - Condenser duty - Flooding - Temperature
profile - Pressure profile - Solver convergence

# 6. Typical Failure Modes

Numerical: - Poor initialization - Overspecification - Tight tolerances

Engineering: - Low reflux - Wrong feed stage - Too few stages -
Unrealistic specifications - Unsuitable property package

# 7. Variable Priority

Preferred adjustment order: 1. Initialization 2. Operating variables 3.
Specifications 4. Feed stage 5. Number of stages 6. Property package
(only if justified)

# 8. Engineering Constraints

Never violate: - Physical feasibility - Equipment limitations -
Hydraulic limits - Product requirements - Safety constraints

# 9. Knowledge Gaps

When confidence is low, the AI should: - Explain uncertainty - Request
additional data - Avoid unsupported recommendations

# Machine Summary

``` yaml
domain:
  simple_distillation

objects:
  - streams
  - column
  - condenser
  - reboiler
  - design_specs
  - adjust

primary_variables:
  - reflux_ratio
  - distillate_rate
  - bottoms_rate
  - feed_stage
  - stages
  - pressure

performance_metrics:
  - purity
  - recovery
  - energy
  - hydraulics
  - convergence
```
