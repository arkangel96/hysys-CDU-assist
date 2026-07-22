# Case: Simple Column Assist v1 — New Intelligence

**Product:** Simple Column Assist  
**Version / line:** v1.0 — New Intelligence  
**Domain:** Aspen HYSYS simple distillation / stripping (not CDU, not VDU)  
**Document role:** Dedicated case description for this product line — keep separate from other tower tools and from ad-hoc parameter experiments.

---

## 1. What this case is

This repository line is an **external Windows COM assist** for **simple columns** in Aspen HYSYS:

- Typically **two main products** (e.g. overhead vapor + bottoms liquid)
- Few components (validated on **sour-water stripper**: H₂S / NH₃ / H₂O)
- Engineer workflow: connect → inspect → diagnose → bounded trials → keep/reverse
- Intelligence goal: judge like a **senior process / simulation engineer**, not a blind GoalValue optimizer

**Display name:** Simple Column Assist v1 — New Intelligence  

It is **not** an AspenTech product. HYSYS remains the thermodynamics and solver engine.

---

## 2. What this case is not

| Out of scope | Why separate |
|--------------|--------------|
| **CDU Assist** | Many side draws, pumparounds, cut points / ASTM / TBP |
| **VDU Assist** | Vacuum fractionator family — later tool |
| Generic “all HYSYS” studio | Wrong click map and wrong PE rules |
| Auto-save of `.hsc` | Engineer owns Save in HYSYS |
| Auto-Add Active specs when DOF = 0 | Recommend only |
| Auto-relax plant FINAL_TARGETs | Locked unless user allows |

Do **not** mix this case documentation with CDU/VDU case folders or with one-off lab scripts that only exercise a single knob for experiments.

---

## 3. Reference HYSYS column (validated)

| Item | Description |
|------|-------------|
| Example unit | **SW Stripper** (sour-water stripper) |
| Style | Full-reflux stripper |
| Stages | 8 (typical validated setup) |
| Feed stage | ~3 |
| Products | Off-gas (ovhd) + stripper bottoms |
| Plant-style FINAL_TARGET | Bottoms NH₃ ≤ **50 ppmw** (5e‑5 mass frac), locked |
| Typical healthy Active set | Reflux Ratio + Bottoms product rate (DOF = 0) |

Other simple columns (stabilizer, depropanizer, etc.) can reuse the **same intelligence shell**; default targets/heuristics must be retargeted — do not assume NH₃ forever.

---

## 4. New Intelligence — what was added

### 4.1 Reasoning system
- States **A–F** before knob moves  
- External **FINAL_TARGET** separate from HYSYS Active GoalValue  
- One major change per trial, snapshot keep/reverse  
- Multi-variable families (not a single-knob brain):

| Family | Role |
|--------|------|
| **A_init** | Estimates, Active/Estimate philosophy, numerical recovery |
| **B_energy** | Reflux ratio / reflux flow / boilup / duties |
| **C_split** | Overhead / distillate / bottoms rates |
| **D_target** | Product FINAL_TARGET — monitor / locked |
| **E_feed** | Feed context (usually user / log) |
| **F_structural** | Feed stage, stages, pressure — approval-only |

### 4.2 HYSYS awareness (clues)
- **Modal popups** (e.g. invalid Ovhd draw > feed) → detect, log, use as PE evidence, dismiss OK so multi-run is not stuck  
- **Messages pane** (warnings, Not Converged, Temperature Cross, invalid T, …) → capture after solve when possible, feed Diagnose / PE board  

### 4.3 Safety
- Never auto-save the HYSYS case file  
- Never auto-relax locked product FINAL_TARGETs  
- Prefer interactive PE board; batch Assist is opt-in  

---

## 5. Key docs in this repo (this case only)

| Doc | Purpose |
|-----|---------|
| [`SCOPE_SIMPLE_COLUMN_ASSIST.md`](SCOPE_SIMPLE_COLUMN_ASSIST.md) | Product identity & boundaries |
| [`INTELLIGENCE_INVENTORY_V1.md`](INTELLIGENCE_INVENTORY_V1.md) | Coded vs paper vs planned |
| [`MULTI_VARIABLE_ITERATION_MAP.md`](MULTI_VARIABLE_ITERATION_MAP.md) | ChemE family iteration map |
| [`expert_decision_workflow.md`](expert_decision_workflow.md) | Master PE bible (States A–F) |
| [`column_convergence_playbook.md`](column_convergence_playbook.md) | SW Stripper operational / COM slice |
| [`../new_intelligence/00_COMPLEMENTARY_INTRO.md`](../new_intelligence/00_COMPLEMENTARY_INTRO.md) | Complementary PE OS package (does **not** supersede) |

---

## 6. Key code modules

| Module | Role |
|--------|------|
| `column_engine.py` | State classify, multi-family propose, keep/reverse, PE board |
| `column_api.py` | HYSYS column COM inspect / specs / run |
| `trial_map.py` | Strategy catalog + trail board |
| `hysys_dialog_watcher.py` | Popup SEE → log → act |
| `hysys_messages_reader.py` | Messages pane capture → log → clues |
| `gui.py` | Desktop Column Assistant UI |

---

## 7. How to run (this case)

```powershell
# HYSYS case open first (simple column / SW Stripper)
cd <this-repo>
.\.venv\Scripts\Activate.ps1
python main.py
```

Connect → select column → **Inspect** → **Diagnose** → review Family / Hypothesis / HYSYS clues → Dry-Run / One Trial.

Keep the HYSYS **Messages** window open if you want Messages-pane clues captured via UI.

---

## 8. Success definition (State E) for this case

Assist may call the case **acceptable** only when:

1. Numerically healthy (no sentinel / nonphysical duties on key streams)  
2. Hard FINAL_TARGETs met on the **product stream**  
3. DOF = 0 with a consistent Active set  
4. Operability OK (flows / duties / basic T window)  
5. Audit trail explains moves (Trial Map / PE board)  

Otherwise report State A/B/C/D/F with evidence — including HYSYS popup and Messages clues when available.

---

## 9. Maintenance rule

- Updates to **this product** stay under Simple Column Assist v1 New Intelligence.  
- CDU / VDU get **separate** case docs and repos/folders.  
- Do not file unrelated experiment notes into this case file.

---

*Case description created 2026-07-22 for GitHub tracking of Simple Column Assist v1 — New Intelligence.*
