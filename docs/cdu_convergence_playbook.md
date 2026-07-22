# CDU Convergence Playbook — Expert Process Engineer Flow

**Document role:** Operational playbook for **CDU Assist v0.1** — maps PE decisions to **what HYSYS exposes** and **what CDU Assist can read or write**.

**Master intelligence (read first):**
[`expert_decision_workflow.md`](expert_decision_workflow.md) — States A–F, FINAL_TARGETs vs HYSYS specs, trial response classes, recovery, infeasibility, **§28 intelligence layers / P0–P3**.

**Scope / identity:**
[`SCOPE_CDU_ASSIST.md`](SCOPE_CDU_ASSIST.md)

**Intelligence backlog:**
[`intelligence_improvement_notes.md`](intelligence_improvement_notes.md)

**COM discovery (Phase 1):**
`docs/cdu_com_discovery.md` — create after live probe of a crude atmospheric tower.

This playbook is the **CDU constrained slice**. Do **not** use stripper RR / NH₃ purity as the primary path.

**Reference case:** TBD (tutorial / anonymized atmospheric crude tower)

**Audience:** Process engineers validating strategy · developers implementing `column_engine.py` · operators using Column Assistant + Trial Map

**Version:** 0.1.0 draft · strategy IDs illustrative until COM discovery

**Policy:** do **not** auto-relax cut / ASTM / TBP FINAL_TARGETs. Prefer Category-1 operating MVs (draws, PA, reflux/OH, side-strip, overflash). Report State F on weak response. Implement Assist in **layers**.

---

## Table of contents

1. [Purpose and scope](#1-purpose-and-scope)
2. [Expert principles (non-negotiables)](#2-expert-principles-non-negotiables)
3. [Transferability matrix — PE thought ↔ HYSYS knob](#3-transferability-matrix--pe-thought--hysys-knob)
4. [Master convergence flow](#4-master-convergence-flow)
5. [Phase A — Inspect](#5-phase-a--inspect)
6. [Phase B — Diagnose (CDU families)](#6-phase-b--diagnose-cdu-families)
7. [Phase C — Plan (one Category-1 family)](#7-phase-c--plan-one-category-1-family)
8. [Phase D — Execute trial](#8-phase-d--execute-trial)
9. [Phase E — Evaluate (keep or reverse)](#9-phase-e--evaluate-keep-or-reverse)
10. [Phase F — Escalate](#10-phase-f--escalate)
11. [Symptom → strategy quick reference](#11-symptom--strategy-quick-reference)
12. [Strategy catalog (Trial Map IDs)](#12-strategy-catalog-trial-map-ids)
13. [Operability gates](#13-operability-gates)
14. [Stop, reverse, and human-intervention rules](#14-stop-reverse-and-human-intervention-rules)
15. [Worked example — live CDU case](#15-worked-example--live-cdu-case)
16. [Implementation mapping](#16-implementation-mapping)
17. [Glossary](#17-glossary)
18. [Intelligence layers (P0–P3)](#18-intelligence-layers-p0p3)

---

## 1. Purpose and scope

### What this document is

A **flow-type operational playbook** for atmospheric crude tower convergence. Each section answers: what the PE thinks → what HYSYS shows → what Assist may read/write → keep/reverse/stop.

### In scope (v0.1 class)

- Atmospheric crude column with side draws and pumparounds
- Optional side strippers
- Cut / ASTM / TBP style product targets (as exposed)
- Interactive PE mode (one trial → board → approve next)

### Out of scope

- Simple stripper NH₃ / RR-only playbook as the main path
- Vacuum tower (VDU Assist later)
- Silent structural redesign

---

## 2. Expert principles (non-negotiables)

| ID | Principle |
|----|-----------|
| P1 | Spec set first — DOF = 0 before numerical tuning |
| P2 | One MV family per trial |
| P3 | Bounded steps |
| P4 | Solve after every change; re-read residuals, duties, profiles, product quality |
| P5 | Keep only on improvement — else reverse immediately |
| P6 | Estimates before Active philosophy changes |
| P7 | Spec swap last resort — 1-for-1; never add Active when DOF already 0 |
| P8 | Never auto-save `.hsc` |
| P9 | Never auto-relax FINAL_TARGET |
| P10 | Interactive PE mode preferred |
| P11–P14 | Layered intelligence; worksheet units; stream/assay truth; no fake State E |

---

## 3. Transferability matrix — PE thought ↔ HYSYS knob

> **Status:** placeholders until `docs/cdu_com_discovery.md` is filled from a live case.

| PE thought | Likely HYSYS surface | Assist R/W (planned) |
|------------|----------------------|----------------------|
| Side draw too high/low | Draw rate spec / product stream flow | R + bounded GoalValue |
| Cut too light/heavy | Cut / ASTM / TBP spec or stream petroleum props | R first; W only if policy-allowed |
| Poor mid-tower fractionation | Pumparound duty / return T / flow | R + bounded nudge |
| Lights left in side product | Side-strip steam / reboil | R + bounded nudge |
| OH / naphtha end-point | Reflux / distillate / OH handles | R + bounded nudge |
| Overflash / flash-zone | Furnace / flash / overflash ops or specs | Discover; Manual if not on column |
| Pressure profile | Stage / condenser / reboiler P | READ v0.1; write later |
| Structure (stages, PA location) | Column design | Never silent — Phase/P3 permission |

---

## 4. Master convergence flow

```text
Connect → Inspect (A) → Classify State A–F (B)
  → if A: fix model
  → if B: numerical recovery only
  → if C: one Category-1 trial (D) → Evaluate (E) → loop
  → if D: fix constraints / operability
  → if E: stop / report success
  → if F: stop; escalate structurally; do not relax FINAL_TARGET
```

---

## 5. Phase A — Inspect

Read-only orientation checklist:

- [ ] Column name, type, stage count, feed stage(s)
- [ ] Condenser / reboiler type and pressures
- [ ] Side draws: names, stages, linked streams, rate specs
- [ ] Pumparounds: duty / flow / return T, draw/return stages
- [ ] Side strippers (if any)
- [ ] Specs Summary: Active vs Estimate, DOF
- [ ] Product quality vs FINAL_TARGETs (cuts / ASTM / TBP as available)
- [ ] Duties, T profile, dry-draw / sentinel checks

---

## 6. Phase B — Diagnose (CDU families)

Replace stripper “rectification vs stripping only” with:

| Family | Meaning |
|--------|---------|
| Overall material split wrong | Draw rates / overflash / residue |
| Cut too light / too heavy | TBP/ASTM off on a product |
| Overlap / gap between adjacent cuts | Adjacent product quality conflict |
| PA heat-removal deficiency | Poor fractionation, wrong mid-tower T |
| Side-strip deficiency | Light ends left in side product |
| Overhead / naphtha end-point | OH system / reflux issues |
| Furnace / flash-zone / overflash | Feed thermal / overflash handles |
| Weak response | Structural / State F evidence |
| Nonphysical “solved” | Sentinel duties, dry draws, absurd T |

---

## 7. Phase C — Plan (one Category-1 family)

Preferred Category-1 MVs (exact COM knobs after discovery):

1. Side-draw rates / cut specs (if writable & policy-allowed)
2. Pumparound duty / return T / flow
3. Reflux / overhead product handles
4. Side-strip steam / reboil (if present)
5. Overflash / flash-zone related operating handles (if exposed)

Category-2/3 later: pressure profile, furnace COT, feed T; structural stage/PA/stripper layout.

---

## 8. Phase D — Execute trial

1. Snapshot Active flags + GoalValues  
2. Change **one** family only, within bounds  
3. Solve  
4. Re-read residuals, duties, draws, quality board  
5. Classify response  

---

## 9. Phase E — Evaluate (keep or reverse)

Keep only if: numerical health not worse, dominant error improved, quality moved toward FINAL_TARGET (or State B recovery progressed), and operability gates pass.

Else: restore snapshot immediately.

---

## 10. Phase F — Escalate

When Category-1 families show weak response or repeated failure: stop; report State F / structural suggestions; **never** silently edit structure or relax FINAL_TARGET.

---

## 11. Symptom → strategy quick reference

| Symptom | First strategy ID (illustrative) |
|---------|----------------------------------|
| Unconverged / sentinel duties | `baseline_spec_recovery` |
| Residue / split wrong | `side_draw_rate_nudge` |
| Mid-tower T / fractionation weak | `pa_duty_nudge` |
| Cut ASTM/TBP off | `cut_point_nudge` (policy-gated) |
| OH end-point | `reflux_or_oh_nudge` |
| Side product lights | `side_strip_steam_nudge` |
| Overflash suspect | `overflash_or_furnace_nudge` |
| Feed/case changed outside Assist | `feed_or_case_change` |

---

## 12. Strategy catalog (Trial Map IDs)

Finalize after COM discovery. Planned IDs in `trial_map.STRATEGY_CATALOG`:

| ID | Family |
|----|--------|
| `refresh_estimates` | Estimates |
| `pa_duty_nudge` | Pumparound |
| `side_draw_rate_nudge` | Side draw |
| `cut_point_nudge` | Cut / quality (policy-gated) |
| `reflux_or_oh_nudge` | Overhead |
| `side_strip_steam_nudge` | Side stripper |
| `overflash_or_furnace_nudge` | Flash / furnace |
| `baseline_spec_recovery` | Spec set (State B) |
| `spec_swap_last_resort` | Spec set (1-for-1) |
| `fix_dof` | Spec set |
| `feed_or_case_change` | Case (manual map event) |

Each strategy: **one family**, bounds, keep/reverse, response-class narrative.

---

## 13. Operability gates

Do **not** declare State E if any of:

- Dry or near-zero critical draws / residue when plant expects flow  
- Sentinel duties (e.g. absurd COM placeholders)  
- Absurd temperature profile  
- FINAL_TARGETs unmet (unless user explicitly unlocked)  
- DOF ≠ 0  

---

## 14. Stop, reverse, and human-intervention rules

- Max trials per Assist session: configurable (default ~12); stop earlier on thrashing  
- Weak response → switch family or stop with State F evidence  
- Human approves next move in interactive mode  
- Never auto-save case  

---

## 15. Worked example — live CDU case

**Status:** TBD after Phase 5 validation.

Record: starting state, FINAL_TARGETs, successful PE path, State E definition for that case.

---

## 16. Implementation mapping

| Playbook piece | Code |
|----------------|------|
| Inspect / Connections | `column_api.py`, Column Assistant UI |
| Diagnose / States A–F | `column_engine.py` |
| Trial Map | `trial_map.py`, `trial_map_window.py` |
| PE board | `intelligence_window.py`, `format_pe_board` |
| Spec catalog | `column_spec_catalog.py` |
| COM discovery scripts | `discover_column_com.py`, `discover_column_deep.py` |

---

## 17. Glossary

| Term | Meaning |
|------|---------|
| Overflash | Liquid from flash zone returning to tray section below feed |
| PA | Pumparound — mid-tower heat removal loop |
| Cut point | Petroleum boiling-range / assay cut definition |
| ASTM D86 / TBP | Standard boiling curves used as product quality |
| FINAL_TARGET | External plant requirement (locked) |
| Category-1 MV | Preferred operating experiment family |

---

## 18. Intelligence layers (P0–P3)

| Layer | Content |
|-------|---------|
| **P0** | State A–F before moves; locked FINAL_TARGET; worksheet units + stream/assay truth; post-trial continue/reverse/switch/stop; operability gates |
| **P1** | Spec-role engine + interactive approve-next |
| **P2** | Weak-response / going-nowhere detector |
| **P3** | Structural suggestions only (never silent structure edits) |

---

*CDU Assist playbook v0.1.0 — living draft*
