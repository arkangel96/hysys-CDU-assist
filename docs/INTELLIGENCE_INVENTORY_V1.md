# Intelligence Inventory — Simple Column Assist v1 (New Intelligence)

**Purpose:** Organize what intelligence already exists **before** adding anything new.  
**Product:** Simple Column Assist v1 — New Intelligence  
**Scope:** Simple distillation / stripping only (not CDU/VDU)  
**Date:** 2026-07-22  
**Rule:** Do not add a new PE rule until it has a row here (status + owner doc + code hook).

---

## 1. How to read this inventory

| Status | Meaning |
|--------|---------|
| **CODED** | Runs in Python today (`column_engine` / `column_api` / UI) |
| **PARTIAL** | Present but thin, case-hardcoded, or missing a PE path |
| **DOCS only** | In markdown PE bible / playbook — not executable yet |
| **PLANNED** | Agreed next layer — do not implement until inventory is stable |

**Anti-complexity:** Full PE judgment lives in docs. Code grows in thin layers.  
One new intelligence item = one inventory row + one validation on SW Stripper.

---

## 2. Document map (what each file owns)

| Document | Role | Do not use for |
|----------|------|----------------|
| [`expert_decision_workflow.md`](expert_decision_workflow.md) | Master PE bible (States A–F, MV hierarchy, recovery, §28) | Day-to-day click recipes |
| [`column_convergence_playbook.md`](column_convergence_playbook.md) | SW Stripper operational slice + COM transferability | Whole-industry rules |
| [`intelligence_improvement_notes.md`](intelligence_improvement_notes.md) | Living backlog / commentary | Current coded truth (use **this** inventory) |
| [`hysys_add_spec_catalog.md`](hysys_add_spec_catalog.md) | Add Spec catalog + when-to-add policy | Auto-Add execution |
| [`SCOPE_SIMPLE_COLUMN_ASSIST.md`](SCOPE_SIMPLE_COLUMN_ASSIST.md) | Product identity & boundaries | Engine detail |
| **This file** | **Coded vs paper vs planned snapshot** | Replacing the PE bible |

---

## 3. Layer snapshot (honest status)

| Layer | Content | Status (2026-07-22) |
|-------|---------|---------------------|
| **L1** | Read + one MV + snapshot keep/reverse + human judge | **CODED** |
| **L2** | States A–F, FINAL_TARGET lock, units/stream, PE board, response classes | **CODED** (State F now classifiable with evidence) |
| **L2+** | Multi-variable family chooser (energy/split/init) + product keep/reverse | **CODED** |
| **L3** | Full condenser-aware spec-role policy, sensitivity memory polish | **PARTIAL** |
| **L4** | Structural moves, 2×2, hydraulics | **DOCS only** — later + permission |

---

## 4. CODED intelligence (available now)

### 4.1 Platform / COM shell

| Item | Where | Notes |
|------|-------|-------|
| Connect / open case / solve | `hysys_api.py`, `gui.py` | Never auto-save |
| Stream inspect / edit / charts / Excel | `gui.py`, `exporter.py` | |
| Column inspect (specs, DOF, profile, duties) | `column_api.py` | |
| Spec GoalValue / IsActive / 1-for-1 swap | `column_api.py` | |
| Refresh composition estimates | `column_api.py` | State B recovery path |
| Snapshot / restore | `column_api.py` | Enables keep/reverse |

### 4.2 PE decision core

| Item | Where | Notes |
|------|-------|-------|
| Engineering States A–E | `column_engine.classify_engineering_state` | **State F not returned by classifier** (see gaps) |
| Diagnosis codes + summary | `column_engine.diagnose` | |
| External FINAL_TARGET object | `column_models.FinalTarget` | Separate from HYSYS Active |
| Default SWS NH₃ = 50 ppmw (5e‑5) | `default_sw_stripper_targets` | Locked, hard |
| Never auto-relax locked FINAL_TARGET | `propose_action`, keep logic | |
| Stream NH₃ mass frac check | `column_api` → `bottoms_nh3_mass_frac` | Prefer stream over spec Current |
| Worksheet-style rate display (kgmole/h) | `ColumnSpecState.goal_display` etc. | |
| Physical-solution / sentinel checks | `physical_solution`, duties, T | |
| Bottoms-flow operability gate | `operable()`, `min_bottoms_flow_kgmole_h` | Rejects fake green / dry bottoms |
| State D stop (operability fail) | `propose_action` → `operability_review` | Manual PE review |
| Category-1 RR nudge (State C) | `propose_action` | NH₃ miss → increase RR (SWS heuristic) |
| State B → refresh estimates first | `propose_action` / `run_one_trial` | |
| Baseline 1-for-1 swap NH₃→Ovhd | `baseline_swap` | **SWS Full Reflux heuristic** — not general policy |
| Response classes after trial | `classify_response` | Still score-heavy (PARTIAL) |
| Keep/reverse with restore | `ConvergenceAssistant.run_one_trial` | Also blocks NH₃ worsening when locked |
| Thrashing stop (3 consecutive reverses) | `assist()` | Treated as State F *evidence*, not classified F |
| Score function (residuals + soft physics) | `score_state` | Support metric — not plant truth |

### 4.3 PE orientation UI

| Item | Where | Notes |
|------|-------|-------|
| PE board text | `format_pe_board`, Intelligence window | State, FINAL_TARGET, strategy |
| Connections READ block | `format_connections_block` | Condenser type, P, feeds |
| Specs Summary Active/Estimate apply | GUI + `column_api` | |
| Specs Summary click recommendations | `column_spec_catalog.recommend_specs_summary_clicks` | Recommend only |
| Add Spec catalog + when-to-add | `column_spec_catalog`, Intelligence window | **No auto Specs.Add** |
| Trial Map path + strategy board | `trial_map.py`, `trial_map_window.py` | |
| Strategy catalog (stripper IDs) | `STRATEGY_CATALOG` | RR / estimates / NH₃ / swap / DOF |

### 4.4 Validated live lessons (encoded as policy examples)

| Lesson | Encoded as |
|--------|------------|
| Dead bottoms / sentinel duties | State B first — not purity chase |
| Full Reflux + high Ovhd Active → tiny bottoms | State D + Specs Summary click hints |
| NH₃ stress 0.1 ppm was wrong | Default FINAL_TARGET 50 ppmw |
| Units: COM SI vs worksheet kgmole/h | Display conversion |
| Spec Current vs stream NH₃ can disagree | Stream preferred for FINAL_TARGET |
| Active swap recovered State B | `baseline_swap` path (SWS-specific) |

---

## 5. PARTIAL — present but incomplete (do not pretend done)

| Item | What works | What’s missing |
|------|------------|----------------|
| **State F** | Stop messages / 3× reverse / locked-MV stop | `classify_engineering_state` never returns `F_INFEASIBLE` |
| **Response / sensitivity** | Classes exist; weak-response % on score | No \(S=\Delta y/\Delta u\) on FINAL_TARGET |
| **Keep/reverse judgment** | Score + physical + NH₃ worsen block | Not primarily product/operability narrative |
| **Spec-role engine** | One NH₃↔Ovhd swap recipe | Condenser-aware Active policy table |
| **Operability** | Bottoms flow gate | MB (F≈D+B), duty signs, T-profile gate for State E |
| **FINAL_TARGET layer** | NH₃ bottoms only | Generic multi-target (e.g. H₂S); overhead targets |
| **Interactive default** | PE board / one-trial API exist | Assist Loop can still batch without forced pause |
| **Appendix A in workflow** | Historical | Still says FINAL_TARGET “TODO” — **stale** |

---

## 6. DOCS only — PE bible not yet coded (do not dump into engine)

Keep in markdown until a thin layer is justified:

- Full MV ranking score \(R_j\)
- Formal bracketing / continuation methods
- Two-variable / 2×2 targeting
- Structural escalation (stages, feed stage, pressure) as Assist actions
- Hydraulic flooding / rating validation
- Solver damping / max iterations as AUTO (still MANUAL in playbook)
- Generic multi-column templates beyond SW Stripper
- CDU / VDU logic (out of product scope)

---

## 7. Strategy catalog inventory (Trial Map IDs)

| ID | Family | Status |
|----|--------|--------|
| `refresh_estimates` | Estimates | **CODED** |
| `reflux_nudge_up` / `reflux_nudge_down` | Active Spec | **CODED** |
| `nh3_goal_nudge` | Active Spec | Catalog row exists — **blocked by FINAL_TARGET lock** (correct) |
| `spec_swap_last_resort` | Spec Set | **PARTIAL** (SWS NH₃→Ovhd) |
| `fix_dof` | Spec Set | **CODED** as manual stop |
| `lower_damping` / `raise_iterations` | Solver | **DOCS / MANUAL** |
| `feed_or_case_change` | Case | **LOG / UI** |

---

## 8. Principles already binding (do not re-argue when adding)

```text
P1  DOF = 0 before tuning
P2  One family per trial
P3  Bounded steps
P4  Solve + re-read physics after every change
P5  Keep only on improvement; else reverse
P6  Estimates before Active philosophy change
P7  1-for-1 swap only; never add Active when DOF = 0
P8  Trial Map trail
P9  Human owns business targets
P10 Stop on thrashing
P11 FINAL_TARGET locked
P12 State before knob
P13 Worksheet units + stream truth
P14 Thin intelligence layers
```

---

## 9. Agreed next adds (queue) — integration started 2026-07-22

| # | Candidate | Status |
|---|-----------|--------|
| 1 | Real State F classification (flat FINAL_TARGET / exhausted families) | **CODED** |
| 2 | Keep/reverse on FINAL_TARGET + operability first | **CODED** |
| 3 | Multi-variable family chooser (A/B/C — not RR-only) | **CODED** |
| 3b | HYSYS popup clues — SEE + log + act in diagnosis (auto-OK dismiss) | **CODED** |
| 4 | Condenser-aware Active policy (beyond NH₃→Ovhd) | PARTIAL — still SWS swap recipe |
| 4b | Connections structural intelligence (feed/stages/P) approval-only | **CODED** — `column_connections.py` |
| 4c | Simple optimize (min RR / RebQ / CondQ / stages) | **CODED** — `column_optimize.py` |
| 5 | Optional second FINAL_TARGET (H₂S) via table | PLANNED |
| 6 | Learning/memory system from `new_intelligence/` | HELD |
| 7 | Workspace folder reorg (Deliverable 6) | HELD |

See [`MULTI_VARIABLE_ITERATION_MAP.md`](MULTI_VARIABLE_ITERATION_MAP.md) and `new_intelligence/00_COMPLEMENTARY_INTRO.md`.

**Explicitly not next:** GoalValue spam, auto-relax purity, auto Specs.Add, **silent** structural automation, CDU logic.

---

## 10. Code ↔ intelligence map

| PE concern | Primary code |
|------------|--------------|
| Inspect | `column_api.ColumnController.inspect` |
| Diagnose / state | `column_engine.diagnose`, `classify_engineering_state` |
| Plan one move | `column_engine.propose_action` |
| Execute / evaluate | `ConvergenceAssistant.run_one_trial` |
| PE board | `format_pe_board` |
| Trial memory | `trial_map.py` |
| Add Spec advice | `column_spec_catalog.py` |
| UI shell | `gui.py`, `intelligence_window.py`, `trial_map_window.py` |

---

## 11. Maintenance rule

When closing or adding intelligence:

1. Update **this inventory** first (status CODED / PARTIAL / PLANNED).  
2. Tick playbook gap list only if truly coded.  
3. Change policy in `expert_decision_workflow.md` §28 if the PE rule changes.  
4. Keep `intelligence_improvement_notes.md` as commentary — not the coded checklist.  
5. Validate on SW Stripper before claiming State E success.

---

*Inventory created 2026-07-22 to freeze “what we have” before the next intelligence add.*
