# Multi-Variable Iteration Map — Simple Column Assist v1

**Status:** Approved for integration (2026-07-22)  
**Scope:** Simple distillation / stripping in Aspen HYSYS — **not** CDU/VDU  
**Rule:** Intelligence must **not** rely on reflux ratio alone. RR is one Category-1 option among several.

Complementary PE OS: `new_intelligence/` (helps this map — does not supersede it).

---

## 1. ChemE principle

```text
State first → choose VARIABLE FAMILY → one bounded iteration →
judge PRODUCT + PHYSICS → keep / reverse → switch family or State F
```

A senior process engineer does **not** “always increase RR.”

---

## 2. Variable families

| ID | Family | HYSYS knobs (typical) | Assist role |
|----|--------|----------------------|-------------|
| **A** | Numerical / init | Estimates, Active↔Estimate set; damping / max iter (often MANUAL) | State B first |
| **B** | Energy / separation power | Reflux ratio, reflux flow, boilup, Cond Q / Reb Q | State C separation weak |
| **C** | Material split | Distillate / Ovhd rate, bottoms rate, D/F | Wrong split, dry bottoms, Full Reflux traps |
| **D** | Product FINAL_TARGET | Composition / purity on product stream | **Monitor / locked** — do not auto-relax |
| **E** | Feed context | F, T, P, composition, VF | Diagnose / log — user usually changes |
| **F** | Structural | Feed stage, stage count, P_cond/P_reb, condenser type, inlet stream | **Think + recommend; write only with PE approval** (`column_connections.py`) |

---

## 3. State → preferred family (chooser)

| State | Prefer first | Then | Stop / escalate |
|-------|--------------|------|-----------------|
| **A** DOF ≠ 0 | Fix Active set (manual) | — | No GoalValue spam |
| **B** Nonphysical | **A** refresh estimates | **A** 1-for-1 baseline Active swap | Not purity chase |
| **C** Off FINAL_TARGET / residuals | Dominant residual family (**B** or **C**) | Other Category-1 family | Flat product → switch; exhausted → **F** |
| **D** Targets OK, not operable | **C** split rates (Ovhd/Btms) | Specs Summary tips | Manual PE if still dry |
| **E** Acceptable | None | — | Done |
| **F** Likely infeasible | Stop | Approval-only **F** structural | Do not relax FINAL_TARGET |

---

## 4. Iteration rules (every family)

1. Change **one** major variable.  
2. Bounded step.  
3. Solve; re-read stream product + duties + flows (worksheet units).  
4. **Keep** only if product/operability narrative improves (not score alone).  
5. Else **reverse**.  
6. If product sensitivity flat on this family → **switch family**.  
7. If Category-1 families exhausted with target still miss → **State F**.

### Keep / reverse (plant judgment)

```text
KEEP if:
  physical after AND operable (or operability improved)
  AND locked FINAL_TARGETs did not worsen
  AND (FINAL_TARGET improved OR residuals/physics improved without product harm)

REVERSE if:
  unphysical OR operability worsened OR locked product worsened
  OR no material product/physics gain
```

---

## 5. Strategy IDs (Trial Map)

| ID | Family | Auto? |
|----|--------|-------|
| `refresh_estimates` | A | Yes |
| `spec_swap_last_resort` | A | Yes (careful, condenser-aware) |
| `reflux_nudge_up` / `reflux_nudge_down` | B | Yes |
| `reflux_flow_nudge` | B | Yes if Active |
| `boilup_nudge` | B | Yes if Active |
| `ovhd_rate_nudge` | C | Yes if Active |
| `bottoms_rate_nudge` | C | Yes if Active |
| `nh3_goal_nudge` | D | **Blocked** while FINAL_TARGET locked |
| `feed_or_case_change` | E | Log / manual |
| `feed_stage_change` / `stage_count_change` | F | Approval-only |
| `report_state_f` | — | Stop with evidence |
| `fix_dof` | A | Manual |
| `lower_damping` / `raise_iterations` | A | Manual in HYSYS |

---

## 6. What “integrated” means in code

- Chooser picks among **A/B/C** (not RR-only).  
- State **F** can be classified with evidence.  
- Keep/reverse uses FINAL_TARGET + operability.  
- Structural **F** never auto-executed.

---

*Approved integration start: 2026-07-22*
