# Symptom tree: diesel_too_heavy (first hardened path)

**Inventory id:** `CDU-SYM-DIESEL-HEAVY`  
**Status:** CODED (routing + keep policy) — live D86 COM still PARTIAL  
**Case:** T-100 / Atmospheric Crude Tower

## PE observe

- Diesel ASTM D86 95% (or EP) **above** plant maximum
- Neighbor cuts (kero / AGO) may shift — watch gaps

## Mechanism (L3)

Too much heavy material pulled into diesel cut → reduce diesel draw first; then mid PA heat; then strip steam. Top RR is last on CDU with Active draws/PAs.

## Preferred MV order (L4) — must match `config/cdu_t100_case.json`

1. `side_draw_rate_nudge` → **Diesel_SS Prod Flow** GoalValue **down**
2. `pa_duty_nudge` → PA duty on diesel belt (prefer PA_2)
3. `side_strip_steam_nudge` → diesel stripper steam / energy
4. `reflux_or_oh_nudge` — last resort only

## Stop / fail

- Reverse if diesel quality worsens or operability fails
- Do not Activate Reflux Ratio while draws/PAs close DOF
- Do not auto-relax FINAL_TARGET

## Code hooks

| Step | Module |
|------|--------|
| Symptom classify | `cdu_quality_engine._symptom_from_reading` |
| MV seeds | `cdu_t100_knowledge.build_subsystem_routed_seeds` |
| Expert route | `cdu_expert_engine._quality_routed_hypotheses` |
| Keep/reverse | `column_engine.should_keep_trial` + `quality_trial_delta` |

## Unit acceptance

`test_cdu_buildup_intelligence.py` — diesel symptom → Diesel_SS draw decrease first.
