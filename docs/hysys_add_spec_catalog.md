# HYSYS Add Spec catalog (SW Stripper capture)

**Source:** Aspen HYSYS dialog *Add Specs – SW Stripper (COL1)* / Column Specification Types  
**Code:** `column_spec_catalog.py`  
**Policy:** Catalog + **when to add** intelligence is coded. **COM auto-Add is not executed** until validated — Assist **recommends**; you add in HYSYS if needed.

---

## Full Add Spec list (from your screenshot)

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

## When to add (PE intelligence — stripper)

| Situation | Prefer | Action |
|-----------|--------|--------|
| Normal SW Stripper | Reflux Ratio + Component Fraction (NH₃) | Use **existing** — don’t Add |
| State B (dead solve) | Draw Rate / Liquid Flow already on column | **Activate** existing Ovhd/Reflux Rate — don’t Add |
| Weak RR response, NH₃ missed | Reboil Ratio or Duty | **Recommend Add** (user) then 1-for-1 Active |
| No composition spec at all | Component Fraction | **Recommend Add** |
| Petroleum cut/gap/PA/VP | — | **Not for this stripper** |

---

## Code API

```python
from column_spec_catalog import (
    HYSYS_ADD_SPEC_TYPES,
    recommend_add_spec,
    stripper_priority_add_types,
)
```

Diagnose PE board now includes **ADD SPEC intelligence** lines.
