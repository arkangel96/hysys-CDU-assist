# Simple Column Assist v1 — Scope & Identity

| Field | Value |
|-------|--------|
| **Product name** | Simple Column Assist |
| **Version** | **1.0** (v1) |
| **Line / edition** | **New Intelligence** |
| **Display name** | Simple Column Assist v1 — New Intelligence |
| **For** | Aspen HYSYS (external COM assist — not an AspenTech product) |
| **Suggested folder** | `hysys-simple-column-assist-v1` |

This is the **first released intelligence revision** of Simple Column Assist:
States A–F, locked FINAL_TARGETs, Specs Summary Active/Estimate, PE board, and Trial Map.
Earlier “Automation Studio” naming is retired for this product line.

---

## What this tool is

Assist for **simple distillation / stripping columns** in HYSYS:

- 2 main products (e.g. overhead vapor + bottoms liquid)
- Few components (e.g. sour-water stripper: H₂S / NH₃ / H₂O)
- Specs like reflux ratio, product rates, one purity FINAL_TARGET
- PE workflow: pre-estimate → Specs Summary Active/Estimate → converge → State A–F

**Validated live example:** SW Stripper (COL1) — Full Reflux stripper, 8 stages.

---

## What this tool is NOT

| Future / separate tool | Why separate |
|------------------------|--------------|
| **CDU Assist** | Crude distillation — many side draws, pumparounds, cut points |
| **VDU Assist** | Vacuum distillation — same family of complex fractionator logic |
| Generic “all HYSYS” studio | Wrong click map and wrong PE rules |

Do **not** stretch Simple Column Assist into CDU/VDU. New repos or modules later.

---

## What we already built (so you don’t lose the thread)

1. Connect / inspect streams + Column Assistant UI  
2. Specs scoreboard + **Specs Summary** Active / Estimate apply  
3. Connections READ (stages, feed, P, condenser type)  
4. States A–F, FINAL_TARGET lock, PE board, Trial Map  
5. Add Spec catalog (recommend only — no auto Add)  
6. Plant lesson: fake “converged” dry bottoms → pre-estimate MB → RR + Btms Active  
7. Realistic NH₃ FINAL_TARGET = **50 ppmw (5e‑5)**, not 0.1 ppm stress value  
8. Live State E case: RR≈2.5, Btms≈12,500 kgmole/h, NH₃≪50 ppmw  

Helper scripts (optional): `apply_preestimate.py`, `rr_ladder.py`, `set_realistic_nh3.py`, `smoke_test_live.py`

---

## Naming family (planned)

```text
Tower Assist family (concept)
├── Simple Column Assist v1 — New Intelligence   ← THIS app
├── CDU Assist                                   ← later, separate
└── VDU Assist                                   ← later, separate
```

---

## Docs map

| Doc | Role |
|-----|------|
| `docs/CASE_SIMPLE_COLUMN_V1_NEW_INTELLIGENCE.md` | **This product case** — descriptions for GitHub (keep separate from other tower cases) |
| `docs/SCOPE_SIMPLE_COLUMN_ASSIST.md` | This file — identity & boundaries |
| `docs/INTELLIGENCE_INVENTORY_V1.md` | **Coded vs paper vs planned** — read before adding intelligence |
| `docs/MULTI_VARIABLE_ITERATION_MAP.md` | ChemE multi-family iteration (not RR-only) |
| `new_intelligence/` | Complementary PE OS package (does not supersede) |
| `docs/column_convergence_playbook.md` | SW Stripper COM / trial playbook |
| `docs/expert_decision_workflow.md` | States A–F master PE workflow |
| `docs/intelligence_improvement_notes.md` | Backlog commentary |
| `docs/hysys_add_spec_catalog.md` | Add Spec types |

---

*Last updated: 2026-07-22 — named as v1 New Intelligence*
