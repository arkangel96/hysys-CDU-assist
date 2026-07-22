# Trial note — PA_1 duty energy probe (T-100)

**Date:** 2026-07-23  
**Scope:** Atmospheric tower only  
**Decision:** Optimize largest PA energy first → **PA_1_Duty**

## Move

| Item | Before | After |
|------|--------|-------|
| PA_1_Duty (display) | −55.00e6 Btu/hr | **−53.35e6 Btu/hr** (−3% \|duty\|) |
| DOF | 0 | 0 |
| Converged | Yes | Yes |
| Physical | Yes | Yes |
| Monitor ITER | 6 (earlier inspect) | **2** |
| Condenser duty (COM) | ~31921 | ~32410 (↑ — expected) |

Product Active rates (kero / diesel / AGO / naphtha) still met (errors ~1e−6).

## Judgment

**KEEP** — first energy probe OK. Less top-PA heat removal → slightly more condenser duty (heat shifted up). Next: another small PA_1 step, or stop and review qualities when D86 COM available.

## Reverse

Ask Assist to restore if you want the −55e6 Btu/hr PA_1 duty back.
