# Deliverable 4 -- Learning & Memory Specification (LMS)

## Version 1.1 — Atmospheric CDU

## Purpose

Define how the engineering assistant stores, retrieves, and reuses
engineering experience for **CDU / atmospheric crude** cases.

## Memory Levels

### Session Memory

- Current simulation state (profiles, Active set, DOF)
- Current hypothesis / State A–F
- Active experiment (family + knob)
- Recent changes and snapshot handle
- HYSYS Messages / popup clues this session

### Project Memory

- Successful convergence paths on this tower
- Failed strategies (do not repeat blindly)
- Preferred workflows for this product slate
- Engineering notes (assay ID, target sheet version)

### Knowledge Memory

- Reusable CDU heuristics (draw vs PA vs top energy)
- Common troubleshooting patterns
- Decision patterns keyed by section / product

## Case Record

Each completed experiment stores:

- Case ID, date, simulation / Assist version
- Crude assay ID / characterization tag (when known)
- Product slate + FINAL_TARGET set (ASTM / TBP / cut / gap / props)
- Column config digest: stages, draws, PAs, steam present?
- Initial conditions summary
- Diagnosis (State + family)
- Engineering action (family, knob, Δ)
- Result vector: physical, converged, per-product target deltas, yields
- Confidence, lessons learned

## Retrieval Strategy

Search by:

- Similar assay / crude family
- Similar column configuration (draw/PA count)
- Similar error / State / Messages clue
- Similar objective (which product / which ASTM or cut)
- Similar family that previously worked

## Learning Rules

- Reinforce successful actions **on the same product/section**.
- Reduce confidence in repeated failures.
- Never overwrite proven engineering knowledge without evidence.
- Do not transfer stripper NH₃ lessons as CDU cut guidance (legacy
  shell only).

```yaml
domain: cdu_atmospheric

memory:
  - session
  - project
  - knowledge

store:
  - assay_tag
  - final_target_set
  - column_config_digest
  - diagnosis
  - action_family
  - per_product_outcome
  - confidence
  - lessons

retrieve_by:
  - similar_assay
  - similar_column_config
  - similar_state_or_message
  - similar_product_objective
```
