# CDU Process Engineer Intelligence Requirements

**Status:** Engineering baseline — Phase 2 scaffold implemented in code.  
**Config:** `config/cdu_t100_case.json`  
**Code:** `cdu_quality_engine.py`, `cdu_spec_philosophy.py`, `cdu_case_config.py`

## Core principle

Never start at HYSYS solver handles (L4). Reason:

```text
L0 Refinery objective
  → L1 CDU / product targets
  → L2 Subsystem
  → L3 Mechanism
  → L4 HYSYS spec (DOF)
  → L5 Bounded trial
```

## Implemented (Phase 2 scaffold)

- Case config JSON (objectives, quality targets, spec roles, MV preference)
- Product Quality State on PE board (independent of solver residuals)
- Spec philosophy audit (DOF block, PA rate+duty, overhead conflicts)
- Quality symptom → preferred MV routing (diesel too heavy starter tree)
- Interactive-only mode flag in config

## Not yet implemented

- Full D86 / flash / TBP COM reads from streams
- Upstream gates (PreFlash, crude heater)
- Hydraulics operability
- Full §5 symptom library (all cuts)
- Quality-based trial scoring (§8.2)

## User action required

Edit `config/cdu_t100_case.json`:

1. Set `target_value` for each quality target  
2. Confirm stream names match HYSYS  
3. Adjust `spec_roles` if your Active set changes  

## Acceptance test (when targets are configured)

Converged T-100 with diesel D86 above target → engine proposes **draw reduction**
before blind PA duty nudge, with mechanism explanation on PE board.

---

*Full specification was provided in project chat (Sections 1–15). This file is the repo index.*
