# Trial — naphtha+kero fixed, PA_1 energy step 2

**Date:** 2026-07-23  
**Policy:** Primary product flows = **Naphtha** + **Kerosene** (both). Secondary = PA_1 duty energy.

## Before → after

| Item | Before | After |
|------|--------|-------|
| Naphtha Prod Rate | 670.83 USGPM (held) | held, \|err\|~7e−7 |
| Kero_SS Prod Flow | 271.25 USGPM (held) | held, \|err\|~6e−7 |
| PA_1_Duty | −53.35e6 Btu/hr | **−51.75e6 Btu/hr** (−3%) |
| DOF / converged / physical | 0 / Yes / Yes | 0 / Yes / Yes |
| CondQ (COM) | ~32410 | ~32880 ↑ |

## Judgment

**KEEP.** Primary flows fixed; PA_1 |duty| stepped down again; still converged.

Cumulative PA_1 from original −55.0e6 → **−51.75e6** (~6% less \|duty\| over two steps).
