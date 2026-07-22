# CDU T-100 live stress test results

**Date:** 2026-07-22  
**Script:** `stress_test_cdu_t100.py`  
**Column:** T-100 / COL1  
**Policy:** Snapshot → stress → diagnose → restore; never auto-save `.hsc`

## Results

| Case | Action | State | Family | Propose | Trial | Key result |
|------|--------|-------|--------|---------|-------|------------|
| 0_BASELINE | Inspect only | E_acceptable | - | none | - | phys=True; Active=13; Kero=271.25 USGPM; PA1Duty=-5.5e7 Btu/hr |
| 1_PA_DUTY_weak | PA_1_Duty Goal ×0.70 | E_acceptable | - | none | - | PA1Duty=-3.85e7 Btu/hr; max_err≈6e-6 |
| 2_KERO_DRAW_half | Kero_SS Prod Flow ×0.50 | E_acceptable | - | none | - | Kero=135.6 USGPM; phys=True |
| 3_RR_WRONG_ACTIVE | PA_1_Rate OFF; RR Active ON | B_numerical | A_init | refresh_estimates | - | Specs Summary tip: RR Active OFF |
| 9_RESTORE | Restore snapshot | E_acceptable | - | none | - | Active=13; Kero/PA duties restored |

## Notes

- Assist keep/reverse trials attempted: **0** (healthy stresses → no propose).
- User-observed HYSYS popup during session: *Flash failed when testing for two liquid phases.*
- Exit code: **0**; case restored.
