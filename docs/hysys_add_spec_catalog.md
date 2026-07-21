# HYSYS Add Spec catalog (CDU Assist)

**Source:** Aspen HYSYS *Add Specs* / Column Specification Types dialog  
**Code:** `column_spec_catalog.py`  
**Product:** CDU Assist — see [`SCOPE_CDU_ASSIST.md`](SCOPE_CDU_ASSIST.md)  
**Policy:** Catalog + **when to add** intelligence is coded. **COM auto-Add is not executed** until validated — Assist **recommends**; you add in HYSYS if needed.

Petroleum cut / gap / PA types are preferred for CDU. Component-fraction purity examples remain in the catalog only as transferable notes from earlier Tower Assist work.

---

## Full Add Spec list (from HYSYS dialog)

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

Exact ordering and availability vary by HYSYS release and column configuration.

---

## CDU priority (Assist recommendations)

Prefer existing draw / PA / reflux / petroleum cut specs before adding new ones.

```python
from column_spec_catalog import cdu_priority_add_types

for spec in cdu_priority_add_types()[:8]:
    print(spec.hysys_name, spec.policy.value)
```

| Situation | Typical Active pair | Notes |
|-----------|---------------------|-------|
| Healthy CDU baseline | Draw rates + PA / reflux as case requires | DOF = 0 first |
| State B recovery | Temporary baseline Actives | Audit; restore FINAL_TARGET monitor-only |
| Cut quality FINAL_TARGET | Monitor / Estimate | Do not auto-relax |

---

*Retargeted for CDU Assist — living catalog*
