# Multi-Variable Iteration Map — CDU Assist v1

**Status:** Approved for CDU retarget (2026-07-22)  
**Scope:** CDU / atmospheric crude distillation in Aspen HYSYS — **not** simple column / VDU  
**Rule:** Intelligence must **not** rely on top reflux alone. RR/OVHD is one Category-1 option among draws, pumparounds, and steam.

Complementary PE OS: `new_intelligence/` (helps this map — does not supersede it).

**Note:** Quality GoalValue IDs (`quality_goal_nudge` / `astm_cut_goal_nudge`) are blocked while FINAL_TARGET is locked — monitor only; do not treat as free purity relax.

---

## 1. ChemE principle

```text
State first → choose VARIABLE FAMILY → one bounded iteration →
judge MULTI-PRODUCT + PHYSICS → keep / reverse → switch family or State F
```

A senior crude-tower PE does **not** “always increase RR” for a mid-cut miss.

---

## 2. Variable families (CDU)

| ID | Family | HYSYS knobs (typical) | Assist role |
|----|--------|----------------------|-------------|
| **A** | Numerical / init | Estimates, Active↔Estimate set; damping / max iter (often MANUAL) | State B first |
| **B** | Section energy / traffic | Top reflux / reflux flow; **pumparound duty / circ / return T**; Cond Q | State C separation weak in a section |
| **C** | Material split / yields | **Side-draw rates**; OVHD rate; residue / bottoms rate | Wrong cut location, yield fight, dry section |
| **C2** | Stripping | Main / side-stripper **steam** rates | Residue / stripper quality, wet bottoms |
| **D** | Product FINAL_TARGET | ASTM / TBP / cut / gap / cold props / composition on products | **Monitor / locked** — do not auto-relax |
| **E** | Feed / furnace context | F, T, P, assay, furnace / overflash | Diagnose / log — user usually changes |
| **F** | Structural | Feed / draw / PA stages, stage count, P profile, condenser type | **Think + recommend; write only with PE approval** |

---

## 3. State → preferred family (chooser)

| State | Prefer first | Then | Stop / escalate |
|-------|--------------|------|-----------------|
| **A** DOF ≠ 0 | Fix Active set (manual / recommend) | — | No GoalValue spam |
| **B** Nonphysical | **A** refresh estimates | **A** 1-for-1 baseline Active swap | Not quality chase |
| **C** Off FINAL_TARGET | Dominant residual family (**C** draw / **B** PA / top energy / **C2** steam) | Other Category-1 family | Flat product → switch; exhausted → **F** |
| **D** Targets OK, not operable | **C** draws / splits; PA return sanity | Specs Summary tips | Manual PE if still broken |
| **E** Acceptable | None | — | Done (all governing products + physical) |
| **F** Likely infeasible | Stop | Approval-only **F** structural | Do not relax FINAL_TARGET |

**Section rule:** Mid-cut / diesel–kero problems prefer **PA (B)** or **draw (C)** before top reflux. Light-end / OVHD problems may use top energy / OVHD rate.

---

## 4. Iteration rules (every family)

1. Change **one** major variable (one family).  
2. Bounded step.  
3. Solve; re-read **all governing products** + duties + flows + Messages.  
4. **Keep** only if multi-product/operability narrative improves.  
5. Else **reverse**.  
6. If product sensitivity flat on this family → **switch family**.  
7. If Category-1 families exhausted with target still miss → **State F**.

### Keep / reverse (plant judgment)

```text
KEEP if:
  physical after AND operable (or operability improved)
  AND locked FINAL_TARGETs did not worsen on any governing product
  AND (targets improved OR residuals/physics improved without product harm)

REVERSE if:
  unphysical OR operability worsened OR any locked product worsened
  OR no material product/physics gain
```

---

## 5. Strategy IDs (Trial Map)

| ID | Family | Auto? | Notes |
|----|--------|-------|-------|
| `refresh_estimates` | A | Yes | Numerical recovery |
| `spec_swap_last_resort` | A | Yes (careful) | Condenser / DOF-aware; legacy SWS recipe still in code |
| `reflux_nudge_up` / `reflux_nudge_down` | B | Yes if Active | Top section |
| `reflux_flow_nudge` | B | Yes if Active | |
| `pa_duty_nudge` / `pa_circ_nudge` / `pa_return_t_nudge` | B | **PLANNED / PARTIAL** | CDU core |
| `side_draw_nudge` | C | **PLANNED / PARTIAL** | CDU core |
| `ovhd_rate_nudge` | C | Yes if Active | Light ends |
| `bottoms_rate_nudge` / `residue_rate_nudge` | C | Yes if Active | |
| `steam_nudge` | C2 | **PLANNED** | |
| `quality_goal_nudge` | D | **Blocked** | Locked FINAL_TARGET — monitor only |
| `astm_cut_goal_nudge` | D | **Blocked** while locked | Prefer external FINAL_TARGET monitor |
| `feed_or_case_change` | E | Log / manual | Assay / furnace |
| `feed_stage_change` / `draw_stage_change` / `pa_stage_change` / `stage_count_change` | F | Approval-only | |
| `report_state_f` | — | Stop with evidence | |
| `fix_dof` | A | Manual | |
| `lower_damping` / `raise_iterations` | A | Manual in HYSYS | |

---

## 6. What “integrated” means in code (honest)

- Chooser picks among **A/B/C** today (shell from stripper validation).  
- **CDU PA / side-draw / steam families** are specified here — implement as thin coded layers next.  
- State **F** can be classified with evidence.  
- Keep/reverse uses FINAL_TARGET + operability (extend to multi-product).  
- Structural **F** never auto-executed.  
- Never auto-save `.hsc`; never auto-relax FINAL_TARGETs.

---

*CDU family map: 2026-07-22*
