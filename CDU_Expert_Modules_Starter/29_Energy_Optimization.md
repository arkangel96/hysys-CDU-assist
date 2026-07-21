# Energy Optimization

> This module defines the engineering reasoning used by the external CDU expert system. It is intended to drive automation, not to explain Aspen HYSYS menus.

## Scope

- Furnace duty
- Pump-around recovery
- Steam minimization
- Condenser duty
- Overall energy strategy

## Engineering Objective

Describe the subsystem objective before changing any variable.

## Required Observations

- Required HYSYS variables
- Derived engineering variables
- Historical trend
- Constraints

## Engineering Reasoning

For every abnormal observation:

1. Collect evidence.
2. Generate multiple hypotheses.
3. Rank hypotheses.
4. Select the smallest meaningful engineering experiment.
5. Predict the response.
6. Execute in HYSYS.
7. Compare prediction versus actual response.
8. Update confidence.

## Diagnostic Questions

- Is the current state physically realistic?
- Which subsystem is most likely responsible?
- Which manipulated variable has the highest engineering value?
- What unintended effects are expected?

## Knowledge Base Entries

- Observable variables
- Hidden states
- Manipulated variables
- Constraints
- Failure modes
- Recovery strategies

## Future Expansion

This module is intentionally a framework. It will be expanded into a detailed engineering specification with decision trees, interaction matrices, confidence scoring, and automation pseudocode.
