# CDU Assist — Scope & Identity

**Product name:** CDU Assist  
**For:** Aspen HYSYS (external COM assist — not an AspenTech product)  
**Repo folder:** `hysys-CDU-assist`

---

## What this tool is

Assist for **atmospheric crude distillation units (CDU)** in HYSYS:

- Crude feed (assay / petroleum hypotheticals / assay-based thermo)
- Preheat / furnace → flash-zone feed to atmospheric tower
- Overhead system (condenser / reflux / naphtha / offgas as configured)
- Multiple side draws (e.g. kero, LGO, HGO — names vary by case)
- Pumparounds (PA) for heat removal / fractionation control
- Optional side strippers
- Bottoms → atmospheric residue
- Product quality as **cut points / TBP / ASTM D86 / flash / freeze / cloud** (not single-component ppm purity)

**PE workflow:** Inspect → Specs Summary Active/Estimate → State A–F diagnose → bounded Category-1 trials → keep/reverse.

**Reference case (Phase 5):** TBD — tutorial / anonymized atmospheric crude tower `.hsc`.

---

## What this tool is NOT

| Out of scope | Why |
|--------------|-----|
| **Simple Column Assist** behavior | 2-product stripper RR / NH₃ purity chasing — wrong click map |
| **VDU Assist** | Vacuum tower — later product in the same family |
| Auto-relax cut / ASTM FINAL_TARGETs | Never fake State E by softening plant targets |
| Silent structural edits | Stage counts, PA locations, stripper adds need permission |
| Auto-save of `.hsc` | Case ownership stays with the engineer |

Do **not** stretch stripper MV logic (RR + bottoms rate + one purity) into CDU.

---

## Product family

```text
Tower Assist family
├── Simple Column Assist   ← DONE / REFERENCE (other folder)
├── CDU Assist             ← THIS app
└── VDU Assist             ← later
```

---

## Reused platform vs replaced domain

**Keep (platform):** Connect / inspect, Specs Summary, snapshot/restore, States A–F shell, PE board, Trial Map, bounded one-family trials, no auto-save.

**Replace (domain):** FINAL_TARGET model (cuts / ASTM / TBP), diagnosis families, STRATEGY_CATALOG, COM readers for draws / PAs / side strippers, playbook, helpers.

---

## Spec roles (critical)

| Role | Meaning |
|------|---------|
| **FINAL_TARGET** | External plant/product requirement — locked unless user explicitly allows change |
| **Baseline Active** | Temporary Active set to get State B → converged (audit required) |
| **Category-1 MVs** | Preferred experiments: draw rates, PA duty/return, reflux/OH, side-strip steam, overflash handles |
| **Monitor-only** | Read quality vs FINAL_TARGET without making it the Active driver if that hurts convergence |

---

## Safety (non-negotiable)

- P1 Spec set first — DOF = 0 before numerical tuning  
- P2 One family per trial  
- P3 Bounded steps  
- P4 Solve after every change; re-read residuals, duties, profiles  
- P5 Keep only on improvement — else reverse  
- P6 Estimates before Active philosophy changes  
- P7 Spec swap last resort — 1-for-1; never add Active when DOF already 0  
- Never auto-save the HYSYS case  
- Never auto-relax FINAL_TARGET to fake success  

---

## v0.1 success definition

A PE can: connect → see draws / PAs / key specs / quality board → get State A–F diagnosis → run bounded reversible Category-1 trials → keep FINAL_TARGETs locked → export Trial Map trail.

**Not success:** auto-relax cuts, blind Active flips, stripper RR logic as the CDU path, State E on nonphysical solutions.

---

## Docs map

| Doc | Role |
|-----|------|
| `docs/SCOPE_CDU_ASSIST.md` | This file — identity & boundaries |
| `docs/expert/00_System_Architecture.md` | **CDU Expert System Volume 0** |
| `docs/expert/README.md` | Full module index + intelligence stack |
| `docs/expert/32_State_Machine.md` | Process flow (10 steps) + States A–F |
| `docs/expert/33_Reasoning_Engine.md` | Observe → hypothesis → rank → evaluate |
| `docs/expert/34_Knowledge_Base.md` | Structured rules + symptom routing |
| `docs/expert/35_Experiment_Selection.md` | One minimum-impact trial |
| `docs/expert/36_Learning_System.md` | Trial Map memory + confidence |
| `docs/expert/31_HYSYS_Object_Map.md` | COM abstraction (T-100) |
| `docs/expert/25_PumpArounds.md` | PA domain intelligence |
| `docs/expert/27_Product_Quality.md` | Quality / FINAL_TARGET domain |
| `docs/cdu_convergence_playbook.md` | CDU PE click map / operational slice |
| `docs/expert_decision_workflow.md` | Master States A–F PE intelligence (shared bible) |
| `docs/cdu_com_discovery.md` | Phase 1 COM discovery (T-100) |
| `docs/intelligence_improvement_notes.md` | CDU gaps P0–P3 backlog |
| `docs/hysys_add_spec_catalog.md` | Add Spec types (expand for CDU) |

---

## Build phases

| Phase | Focus |
|-------|--------|
| **0** | Identity & docs rebrand (this release) |
| **1** | Live COM discovery on a real CDU `.hsc` |
| **2** | Inspect / Diagnose only (CDU boards) |
| **3** | Trial Map CDU strategies |
| **4** | Intelligence P0 → P3 |
| **5** | Live validation reference case |

---

*Last updated: 2026-07-21*
