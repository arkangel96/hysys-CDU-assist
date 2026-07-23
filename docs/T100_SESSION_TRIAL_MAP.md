# T-100 Session Trial Map

**Purpose:** Track what we tried (variable-by-variable) and what’s next — so we don’t lose the thread.  
**Case:** Atmospheric Crude Tower / **T-100**  
**Playbook (complementary DOCS):** `new_intelligence/CDU_T100_Decision_Intelligence_v1.md`  
**Runtime brain:** coded Assist (`propose_action` / keep-reverse / case `mv_preference`) — Inventory is status of truth.
**Units:** HYSYS Field (°F, Btu/hr, USGPM) — no Assist conversion  

Live canvas twin (open beside chat): `canvases/t100-trial-map.canvas.tsx` in the Cursor project.

**Curated lessons (multi-feed safe):** [`lessons/README.md`](lessons/README.md) — after KEEP/REVERSE, add a short note with Feed/assay + Reusable vs Case-specific.

---

## Current holds

| Hold | Value | Status |
|------|-------|--------|
| Naphtha Prod Rate | ~670.83 USGPM Active | LOCKED |
| Kero_SS Prod Flow | ~271.25 USGPM Active | LOCKED |
| Hard quality (D86/flash) | Naph≤356 / Kero flash≥100 / Kero≤518 / Diesel≤680 °F | ON SPEC |
| Soft kero–diesel gap | ~10 F vs ≥27 F | OFF (soft) |
| PA_1_Duty | **−52.25 MMBtu/hr** (was −55.0) | After T3 KEEP |
| PA_2 / PA_3 | −35 / −35 MMBtu/hr | Untouched |
| Main trays / SS | 29 / 3+3+3 | No structural change |
| Condenser | ~112 MMBtu/hr (after T3; was ~109) | Watch |

---

## Done — trials

| ID | When | Family | MV | Change | Result | Keep? |
|----|------|--------|-----|--------|--------|-------|
| T0 | 2026-07-23 | Baseline | — | Inspect / connect | DOF=0, converged, physical | Baseline |
| T1 | 2026-07-23 | C rates | Naphtha + Kero rates | Sync Goal←Current | Rates locked Active | KEEP |
| T2 | 2026-07-23 | D quality | FINAL_TARGETs | Lock Field °F; COM D86/flash read | Hard ON; soft gap OFF | Soft miss accepted for now |
| T3 | 2026-07-23 | B energy | **PA_1_Duty** | −5% \|duty\|: −55.0 → −52.25 MMBtu/hr | Rates+hard quality OK; CondQ **+~2.75** MMBtu/hr | **KEEP** (stable) — net ≈ heat **shift** to CondQ, not true save |

### T3 net-energy note
\|PA_1\| down 2.75 MMBtu/hr ≈ CondQ up 2.75 MMBtu/hr. If PA_1 is crude-preheat recovery, this is not a utility win under Decision Intelligence §4.

---

## Backlog — things to try (priority)

| Pri | Family | MV | Action | Gate |
|-----|--------|-----|--------|------|
| 1 | B energy | PA_1 | **Fork:** reverse T3 (protect preheat) **or** stop PA_1 cuts and move on | Net-energy rule |
| 2 | B energy | PA_2_Duty | Bounded −% \|duty\| after PA_1 path closed | One family/trial |
| 3 | B energy | PA_3_Duty | Same | After PA_2 |
| 4 | C2 steam | Kero Reb / Diesel·AGO steam | Trim if quality margin; watch flash | After PA flatten |
| 5 | B CondQ | Atmos Cond | Observe only — don’t force lower CondQ | §8 Condenser rule |
| 6 | C draws | Diesel / AGO rates | Bounded only if band defined | Naphtha/kero stay locked |
| 7 | D soft | Kero–diesel gap | Optional campaign or PE soft-accept | Soft; approval for accept |
| 8 | F structural | Trays / feed / PA stages | Diagnose/propose only | Approval-only; last |

---

## Log template (copy for next trial)

```text
ID: T?
Family: B / C / C2 / D / F
MV:
Before:
After:
Δ PA / CondQ / steam:
Hard quality: pass / fail
Naphtha+kero rates: pass / fail
Converged: yes / no
Decision: KEEP / REVERSE
Why:
Next:
```

---

## Update rule

After every HYSYS trial: add a **Done** row here **and** update the canvas data so both stay aligned.
