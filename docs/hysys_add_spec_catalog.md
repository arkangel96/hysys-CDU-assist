# HYSYS Add Spec catalog — CDU Assist

**Product:** CDU Assist v1 — New Intelligence  
**Code:** `column_spec_catalog.py`  
**Policy:** Catalog + **when to add** intelligence. **COM auto-Add is not executed** until validated — Assist **recommends**; engineer adds in HYSYS if needed.

**Source dialog:** Aspen HYSYS *Add Specs - T-100 / COL1* / Column Specification Types (capture 2026-07-22)  
**Reference JSON:** `config/cdu_t100_add_specs_reference.json`

---

## Full Add Spec list (HYSYS column types)

1. Column Cold Properties Spec  
2. Column Component Flow  
3. Column Component Fraction  
4. Column Component Ratio  
5. Column Component Recovery  
6. Column Cut Point  
7. Column Draw Rate  
8. Column DT (Heater/Cooler) Spec  
9. Column Dt Spec  
10. Column Duty  
11. Column Duty Ratio  
12. Column Feed Ratio  
13. Column Gap Cut Point  
14. Column Liquid Flow  
15. Column Physical Properties Spec  
16. Column Pump Around  
17. Column Reboil Ratio Spec  
18. Column Recovery  
19. Column Reflux Feed Ratio Spec  
20. Column Reflux Fraction Spec  
21. Column Reflux Ratio  
22. Column Stream Property Spec  
23. Column Tee Split Spec  
24. Column Temperature  
25. Column Transport Properties Spec  
26. Column User Property Spec  
27. Column Vapour Flow  
28. Column Vapour Fraction Spec  
29. Column Vapour Pressure Spec  
30. End Point Based Column Cut Point Spec  
31. End Point Based Column Gap Spec  
32. Stream Specification  

---

## T-100 Monitor → Add Spec type map

| Monitor name (example) | HYSYS Add Spec type |
|------------------------|---------------------|
| Kero/Diesel/AGO_SS Prod Flow, Naphtha Prod Rate | Column Draw Rate |
| PA_*_Rate(Pa) | Column Pump Around |
| PA_*_Duty(Pa), Kero Reb Duty | Column Duty (+ PA family) |
| Liquid Flow | Column Liquid Flow |
| Vap Prod Flow | Column Vapour Flow |
| Reflux Ratio (Estimate) | Column Reflux Ratio |

---

## When to add (PE intelligence — atmospheric CDU)

| Situation | Prefer | Action |
|-----------|--------|--------|
| Healthy CDU, DOF = 0 (T-100) | Existing draw / PA / duty / liquid / vap set | Use **existing** — don’t Add |
| State B (dead / wild solve) | Existing Draw / PA / Duty already on column | **Activate / Estimate** existing — don’t Add first |
| Yield wrong, quality OK-ish | Draw Rate on governing product | Prefer Active draw GoalValue; Add only if missing |
| Mid-cut / section traffic weak | Pump Around rate/duty | **Recommend Add** PA only if circuit missing, then 1-for-1 Active |
| Cut / ASTM / gap miss (FINAL_TARGET locked) | Cut Point / Gap / EP Cut / Cold Props / RVP | Spec may exist as Monitor; **do not** turn locked plant target into free GoalValue spam |
| Light-end miss | Naphtha Draw / Vap Prod / RR Estimate | Prefer existing; RR last on CDU |
| Residue / stripper quality | Steam / Kero Reb Duty | Prefer existing duty/steam — don’t relax cut |
| DOF = 0 already | — | **Never** auto-Add Active; recommend 1-for-1 swap only |

---

## DOF reminder (multi-product)

Atmospheric towers often carry **many** Active specs (draws + PAs + duties + liquid + vap).  
Before recommending Add:

1. Count DOF.  
2. Prefer Activate / Estimate / 1-for-1 swap.  
3. Add only when the needed MV type is **absent**.  
4. Keep FINAL_TARGETs external/locked.

---

## Code API

```python
from column_spec_catalog import (
    HYSYS_ADD_SPEC_TYPES,
    recommend_add_spec,
    cdu_priority_add_types,
    match_existing_spec_to_type,
)
```

Diagnose PE board may include **ADD SPEC intelligence** lines (recommend only).  
Intelligence window → **Add Spec Catalog** shows CDU when-to-add + T-100 examples.
