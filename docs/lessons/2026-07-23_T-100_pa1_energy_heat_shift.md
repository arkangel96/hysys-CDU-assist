# Lesson — PA_1 duty energy probe (heat shift to CondQ)

**Date:** 2026-07-23  
**Column tag:** T-100  
**Feed / assay:** Reference atmospheric crude case  
**Objective:** energy  
**Assist / Trial Map ID:** session T3 / `docs/trials/PA1_ENERGY_TRIAL_2026-07-23.md`  
**Related trial note:** [`../trials/PA1_ENERGY_TRIAL_2026-07-23.md`](../trials/PA1_ENERGY_TRIAL_2026-07-23.md)

---

## Context (case-specific — do not globalize numbers)

| Item | Value |
|------|-------|
| Unit set | Field (°F, Btu/hr, USGPM) |
| Hold | Naphtha + Kero rates locked Active |
| PA_1_Duty | stepped down in \|duty\| (less PA cooling) |

---

## What we tried

| Step | Family | MV | Change | Result |
|------|--------|-----|--------|--------|
| 1 | B_energy | PA_1_Duty | bounded \|duty\| cut | Converged, physical; CondQ rose |

**KEEP / REVERSE / STOP:** KEEP (energy probe with rate holds)  

**Why (PE):** Primary product rates held; heat moved up the tower (CondQ ↑) — expected for weaker top PA, not necessarily a net utility win.

---

## Mistake or surprise (if any)

Judging “energy win” by PA duty alone while CondQ rises can mislead if the objective is **net** condenser/reboiler utility. Separate **rate-hold keep** from **net-energy keep**.

---

## Takeaways

### Reusable (CDU class — OK on other feeds / similar columns)

- Energy campaign: one PA family at a time; hold nominated product rates.
- Weaker PA cooling often **shifts** heat to condenser — watch CondQ; don’t claim net save without a net metric.
- Quality/draw campaigns stay draw-first; don’t mix objectives in one trial.

### Case-specific (this feed / this night’s Goals only)

- Exact PA_1 / CondQ MMBtu/hr and naphtha/kero USGPM from that session.

### Do not

- Do not auto-relax FINAL_TARGETs to force an energy KEEP.
- Do not apply Decision Intel net-energy reverse and buildup rate-hold keep as if they were the same rule without stating which objective is active.

---

## Feed-change reminder

New feed changes PA/CondQ magnitudes and quality sensitivity. Reusable part is the **trial discipline**; numbers are not portable.
