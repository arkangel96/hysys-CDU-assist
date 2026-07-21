# Engineering Philosophy

**Parent:** [`00_System_Architecture.md`](00_System_Architecture.md)  
**Status:** Stub — expand with refinery/CDU-specific objective hierarchy

---

## Core principle

The external program models **how a senior refinery simulation engineer thinks**, not how HYSYS happens to expose COM members.

HYSYS answers: “What is the numerical result if I set these specs?”  
The expert system answers: “Given plant objectives and evidence, what is the **next defensible experiment**?”

---

## Observation before action

No Level-5 (COM) move without:

1. A classified engineering state (States A–F — see [`32_State_Machine.md`](32_State_Machine.md))
2. A subsystem-level symptom (Level 3)
3. A ranked hypothesis (Level 4 equipment / mechanism)
4. A bounded, reversible experiment plan

---

## Objectives vs variables

| Wrong | Right |
|-------|--------|
| “Nudge PA_2_Duty because residual high” | “Mid-cut fractionation weak → PA_2 heat removal likely deficient → bounded PA_2 duty increase → check diesel/kero ASTM and neighbor cuts” |
| “Relax ASTM GoalValue to converge” | “State C off-spec on diesel 95% D86 → try draw rate then PA in diesel section → FINAL_TARGET stays locked” |
| “Change three Actives at once” | “One family per trial; record; keep or reverse” |

---

## Physical realism over HYSYS green

A converged case can still be **engineering garbage**:

- Dry or near-zero draws  
- Sentinel duties (`-32767`)  
- Absurd temperature profile  
- FINAL_TARGETs unmet on stream truth  

Assist may **not** claim success (State E) in those situations.

---

## Escalation discipline

```text
Category-1 operating MVs  →  draws, PA, reflux/OH, strip steam (default)
Category-2                →  furnace COT, flash/overflash, pressure profile
Category-3 structural     →  stages, PA location, stripper count (permission only)
```

Weak response on Category-1 → switch family or report State F — do not silently edit structure or relax FINAL_TARGET.

---

## Human in the loop (v0.1 default)

Interactive mode: **one trial → PE board → engineer judges → approve next**.

The expert system **proposes**; the engineer **owns** the case file.

---

## Related

- [`../expert_decision_workflow.md`](../expert_decision_workflow.md) — detailed States A–F and trial rules  
- [`../SCOPE_CDU_ASSIST.md`](../SCOPE_CDU_ASSIST.md) — product boundaries  
- [`02_Reasoning_Engine.md`](02_Reasoning_Engine.md) — executable mapping  

---

*Stub · to be expanded with your refinery objective examples*
