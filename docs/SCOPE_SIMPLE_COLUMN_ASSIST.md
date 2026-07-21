# Simple Column Assist — Scope & Identity

**Product name:** Simple Column Assist  
**For:** Aspen HYSYS (external COM assist — not an AspenTech product)  
**Repo folder (legacy):** `hysys-automation-studio` (rename later if desired)

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
├── Simple Column Assist     ← THIS app
├── CDU Assist               ← later, separate
└── VDU Assist               ← later, separate
```

---

## Docs map

| Doc | Role |
|-----|------|
| `docs/SCOPE_SIMPLE_COLUMN_ASSIST.md` | This file — identity & boundaries |
| `docs/column_convergence_playbook.md` | SW Stripper COM / trial playbook |
| `docs/expert_decision_workflow.md` | States A–F master PE workflow |
| `docs/intelligence_improvement_notes.md` | Backlog |
| `docs/hysys_add_spec_catalog.md` | Add Spec types |

---

*Last updated: 2026-07-21*
