# State Machine

## Major States

1. Initialization
2. Model Validation
3. Observation
4. Diagnosis
5. Hypothesis Generation
6. Experiment Planning
7. Execution
8. Evaluation
9. Learning
10. Completion

## Transition Rules

The expert system shall never skip Observation before Diagnosis.

Every experiment shall produce a new state snapshot.

Rollback shall be available whenever confidence decreases.