# CDU Assist v1 — Scope & Identity

| Field | Value |
|-------|--------|
| **Product name** | CDU Assist |
| **Version** | **1.0** (v1) |
| **Line / edition** | **New Intelligence** |
| **Display name** | CDU Assist v1 — New Intelligence |
| **For** | Aspen HYSYS (external COM assist — not an AspenTech product) |
| **Suggested folder** | `hysys-CDU-assist` |

This is the **first released intelligence revision** of CDU Assist:
States A–F, locked FINAL_TARGETs, Specs Summary Active/Estimate, PE board, and Trial Map.
Earlier “Automation Studio” naming is retired for this product line.

---

## What this tool is

Assist for **CDU / atmospheric crude distillation** in HYSYS:

- Atmospheric crude tower (side draws, pumparounds, cut points)
- Multi-product fractionator workflow
- Specs like reflux, draw rates, pumparound duties, product quality targets
- PE workflow: pre-estimate → Specs Summary Active/Estimate → converge → State A–F

**Legacy simple-column validation note:** Early COM / States A–F trials were proven on an SW Stripper (COL1) case. That stripper material remains in playbooks as historical validation only — not CDU process guidance.

---

## What this tool is NOT

| Future / separate tool | Why separate |
|------------------------|--------------|
| **Simple Column Assist** | 2-product distillation / stripping — separate tool |
| **VDU Assist** | Vacuum distillation — same family of complex fractionator logic |
| Generic “all HYSYS” studio | Wrong click map and wrong PE rules |

Do **not** stretch CDU Assist into simple-column or VDU products. New repos or modules later.

---

## What we already built (so you don’t lose the thread)

**Reusable Assist shell (CODED):**

1. Connect / inspect streams + Column Assistant UI  
2. Specs scoreboard + **Specs Summary** Active / Estimate apply  
3. Connections READ (stages, feed, P, condenser type)  
4. States A–F, FINAL_TARGET lock, PE board, Trial Map  
5. Add Spec catalog (recommend only — no auto Add)  

**Legacy stripper validation (COM shell proof — not CDU physics):**

6. Fake “converged” dry bottoms → pre-estimate MB → RR + Btms Active  
7. Realistic NH₃ FINAL_TARGET = **50 ppmw (5e‑5)**  
8. Live State E case: RR≈2.5, Btms≈12,500 kgmole/h, NH₃≪50 ppmw  

**CDU intelligence (docs v1.1 — code next):**

9. Multi-product FINAL_TARGETs (ASTM / TBP / cut / gap)  
10. Variable families: side draws, pumparounds, steam, top energy  
11. CDU when-to-add matrix + atmospheric reference case  

Helper scripts (optional / legacy): `apply_preestimate.py`, `rr_ladder.py`, `set_realistic_nh3.py`, `smoke_test_live.py`

---

## Naming family (planned)

```text
Tower Assist family (concept)
├── CDU Assist v1 — New Intelligence             ← THIS app
├── Simple Column Assist                         ← separate
└── VDU Assist                                   ← later, separate
```

---

## Docs map

| Doc | Role |
|-----|------|
| `docs/CASE_CDU_V1_NEW_INTELLIGENCE.md` | **This product case** — descriptions (this repo only) |
| `docs/DISCUSSION_HISTORY_2026-07-22.md` | Session discussion history (PE decisions / Agent notes) |
| `docs/SCOPE_CDU_ASSIST.md` | This file — identity & boundaries |
| `docs/INTELLIGENCE_INVENTORY_V1.md` | **Coded vs paper vs planned** — read before adding intelligence |
| `docs/MULTI_VARIABLE_ITERATION_MAP.md` | ChemE multi-family iteration (not RR-only) |
| `new_intelligence/` | Complementary PE OS package (does not supersede) |
| `docs/column_convergence_playbook.md` | COM / trial playbook *(legacy SW Stripper slice)* |
| `docs/expert_decision_workflow.md` | States A–F master PE workflow |
| `docs/intelligence_improvement_notes.md` | Backlog commentary |
| `docs/hysys_add_spec_catalog.md` | Add Spec types |

---

*Last updated: 2026-07-22 — named as v1 New Intelligence (CDU Assist)*
