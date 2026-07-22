# Intelligence Build-Up Strategy (locked direction)

**Status:** Active — 2026-07-23  
**Product:** CDU Assist v1 — New Intelligence  
**Gate:** [`INTELLIGENCE_INVENTORY_V1.md`](INTELLIGENCE_INVENTORY_V1.md)

## Tower production + energy (locked 2026-07-23)

**Primary (do not relax while optimizing energy):** naphtha **and** kerosene product flows  
(`Naphtha Prod Rate`, `Kero_SS Prod Flow`) — plant nomination style; both fixed.  

**Secondary:** PA heat — **PA_1** first (largest |duty|), then PA_2, PA_3.  

**Follow:** diesel / AGO rates (may stay Active for DOF, but not the optimization objective).  

**Trial rule:** nudge only `PA_*_Duty`; keep only if DOF=0, converged, physical, and primary naphtha+kero rate errors stay tiny.

## Tower energy focus (locked 2026-07-23)

**Scope:** atmospheric tower only (not PreFlash / furnace).  
**First MV:** **PA_1_Duty** — largest |PA duty| on T-100 (~55e6 Btu/hr).  
**Order:** PA_1 → PA_2 → PA_3 (`energy_optimize_order` in `config/cdu_t100_case.json`).  
**Trial style:** one bounded duty nudge; leave other PAs and draws alone; keep/reverse on converge + operability.

## Default AI role (always on)

Cursor Agent in this repo defaults to a **senior Aspen HYSYS CDU process engineer** (peer level with the user). You do **not** need to restate that each chat.

| Mechanism | Path |
|-----------|------|
| Cursor rule (`alwaysApply`) | [`.cursor/rules/cdu-hysys-senior-pe.mdc`](../.cursor/rules/cdu-hysys-senior-pe.mdc) |
| Strategy / identity note | This section |

Binding PE habits in that rule: diagnose before knobs, one MV family, FINAL_TARGET lock, draw/PA/steam before RR, no auto-save / no silent structural writes. Assay conversion stays a separate program unless explicitly in scope.

## Locked direction (confirm-direction)

| Choice | Decision |
|--------|----------|
| Intelligence source | **Clone PE judgment first** (oracle = you), then amplify |
| Operating mode | **Interactive-first** (`interactive_only: true`) |
| Not chosen now | Library dump into engine; autonomy-first Assist Loop |

**Surpass** means: consistency, case memory, breadth, speed — not silent redesign of T-100.

## Safety while building

- One Inventory row + one T-100 validation per new rule
- One MV family per trial; snapshot keep/reverse
- Never auto-relax FINAL_TARGETs; never auto Specs.Add; never silent structural writes
- Docs first when unsure; thin code layers only

## Reasoning stack (encode this, not a second brain)

```text
L0 Case objective (config)
L1 Product FINAL_TARGETs / quality
L2 Subsystem (kero / diesel / PA / OH)
L3 Mechanism
L4 Existing Active GoalValue nudge
L5 Bounded trial + quality-first keep/reverse
```

## First symptom tree (pick-first-symptom)

**Hardened first:** `diesel_too_heavy` — see [`symptoms/DIESEL_TOO_HEAVY.md`](symptoms/DIESEL_TOO_HEAVY.md).

Next trees only after this path matches PE acceptance on T-100: `kerosene_off_spec`, then PA heat balance.

## Near-term P0–P2

| Pri | Item | Code / config |
|-----|------|----------------|
| P0 | Plant quality / FINAL_TARGET numbers | `config/cdu_t100_case.json`, `config/cdu_final_targets.json` |
| P0 | Quality-first keep/reverse | `column_engine.should_keep_trial`, `cdu_quality_engine.quality_trial_delta` |
| P1 | Diesel too-heavy MV order | case `mv_preference` + expert quality routing |
| P2 | Acceptance checklist | below |

## Acceptance checklist (Assist said what I would say)

When diesel D86 95% is above target (or PE injects that symptom in tests):

1. [ ] Diagnose prefers **State C** (or quality symptom visible on PE board), not blind RR
2. [ ] First proposed MV is **Diesel_SS Prod Flow decrease** (`side_draw_rate_nudge`)
3. [ ] Second preference is **PA duty** on diesel belt (`pa_duty_nudge`), not Activate RR
4. [ ] Trial that worsens diesel quality is **REVERSED** even if residual score improved
5. [ ] Trial that improves diesel quality and stays operable is **KEPT**
6. [ ] With `interactive_only`, Assist Loop runs **one** trial then stops for PE review
7. [ ] Unavailable D86 COM does **not** fake State C hard-miss (targets stay non-gating until measured)

## Build cadence

1. PE states observe → diagnose → MV → keep why (5–10 lines)
2. Inventory row → thin code → unit test → live T-100 smoke
3. If Assist disagrees with PE → PE wins; patch rule

Defer: autonomous multi-trial loops, structural escalation, full `cdu_intel/` dump.
