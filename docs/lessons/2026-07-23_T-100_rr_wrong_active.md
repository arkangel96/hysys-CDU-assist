# Lesson — Wrong RR Active → State B (refresh estimates first)

**Date:** 2026-07-23  
**Column tag:** T-100  
**Feed / assay:** Reference atmospheric crude case (open HYSYS session)  
**Objective:** diagnose  
**Assist / Trial Map ID:** live `stress_test_cdu_t100.py` case `3_RR_WRONG_ACTIVE`  
**Related trial note:** —

---

## Context (case-specific — do not globalize numbers)

| Item | Value |
|------|-------|
| Unit set | Field (USGPM, Btu/hr) |
| Stress | PA_1_Rate Active OFF; Reflux Ratio Active ON |
| Baseline | DOF=0, State E, 13 Actives before stress |

---

## What we tried

| Step | Family | MV | Change | Result |
|------|--------|-----|--------|--------|
| 1 | A_init | — | Wrong Active pair (RR on, PA rate off) | State **B_numerical** |
| 2 | A_init | refresh_estimates | Propose from Assist | Correct first move |

**KEEP / REVERSE / STOP:** N/A (diagnose + propose only; snapshot restored)  

**Why (PE):** Bad Specs Summary Active set → numerical/recover path before product MV chase.

---

## Mistake or surprise (if any)

Activating top RR while dropping a healthy PA rate Active is a stripper-era / wrong-DOF habit on CDU — board correctly went State B, not “raise RR for quality.”

---

## Takeaways

### Reusable (CDU class — OK on other feeds / similar columns)

- When Actives look wrong (RR on, draw/PA traffic broken) → **State B / A_init**: refresh estimates / Specs Summary before draw or PA GoalValue spam.
- Prefer draw/PA Actives for DOF; RR monitor/estimate when draws/PAs already close DOF.

### Case-specific (this feed / this night’s Goals only)

- Exact PA_1_Rate / RR GoalValues from that session — do not copy to a new assay.

### Do not

- Do not treat “Activate RR” as the default recovery on atmospheric CDU.
- Do not skip restore after stress scripts (this run restored; keep that habit).

---

## Feed-change reminder

New feed/assay → confirm feed OK / characterization before reusing the Active-set pattern. Same tower tag ≠ same operating point.
