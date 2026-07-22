# Case: CDU Assist v1 — New Intelligence

**Product:** CDU Assist  
**Version / line:** v1.0 — New Intelligence  
**GitHub repo:** `arkangel96/hysys-CDU-assist` (standalone)  
**Domain:** Aspen HYSYS CDU / atmospheric crude distillation (not simple column, not VDU)  
**Document role:** Case description for this product line — keep separate from other tower tools and from RR-only lab notes.

---

## 1. What this case is

This repository line is an **external Windows COM assist** for **CDU / atmospheric crude towers** in Aspen HYSYS:

- Multi-product atmospheric fractionator (side draws, pumparounds, cut points)
- Engineer workflow: connect → inspect → diagnose → bounded trials → keep/reverse
- Intelligence goal: judge like a **senior process / simulation engineer**, not a blind GoalValue optimizer

**Display name:** CDU Assist v1 — New Intelligence  

It is **not** an AspenTech product. HYSYS remains the thermodynamics and solver engine.

**Legacy simple-column validation note:** COM adapters, States A–F, and Trial Map were first validated on an SW Stripper (sour-water) case. Stripper-specific numbers below are historical proof of the intelligence shell — retarget for CDU crude cuts / ASTM / TBP as CDU features land.

---

## 2. What this case is not

| Out of scope | Why separate |
|--------------|--------------|
| **Simple Column Assist** | 2-product distillation / stripping |
| **VDU Assist** | Vacuum fractionator family — later tool |
| Generic “all HYSYS” studio | Wrong click map and wrong PE rules |
| Auto-save of `.hsc` | Engineer owns Save in HYSYS |
| Auto-Add Active specs when DOF = 0 | Recommend only |
| Auto-relax plant FINAL_TARGETs | Locked unless user allows |

Do **not** mix this case documentation with simple-column / VDU case folders or with one-off lab scripts that only exercise a single knob for experiments.

---

## 3. Reference HYSYS column

### 3.1 Product reference (CDU — target)

| Item | Description |
|------|-------------|
| Example unit | Atmospheric crude tower (e.g. case `Atmospheric Crude Tower.hsc` when used) |
| Products | OVHD / naphtha, side draws (kero / diesel / AGO as configured), atmospheric residue |
| Internals focus | Side draws, pumparounds, optional side strippers / steam, flash / overflash context |
| Plant-style FINAL_TARGETs | Multi-product ASTM D86 / TBP / cut / gap / cold props — **locked** |
| Typical Active set | Condenser-appropriate top energy + draw rates + PA duties (DOF = 0); cuts often Monitor |

### 3.2 Legacy COM validation (not CDU physics)

| Item | Description |
|------|-------------|
| Example unit | **SW Stripper** (sour-water) — shell proof only |
| Style | Full-reflux stripper, ~8 stages, feed ~3 |
| FINAL_TARGET used | Bottoms NH₃ ≤ **50 ppmw** (5e‑5) |
| Healthy Active set then | Reflux Ratio + Bottoms product rate |

Default targets/heuristics for Assist code must be **retargeted to §3.1** — do not ship NH₃ as the CDU plant model.

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
| **B_energy** | Top reflux / OVHD energy **and** pumparound duty / circ / return T |
| **C_split** | Side-draw rates, OVHD / residue rates |
| **C2_steam** | Stripping steam (main / side strippers) |
| **D_target** | Multi-product FINAL_TARGET (ASTM/cut/gap) — monitor / locked |
| **E_feed** | Feed / assay / furnace–overflash context (usually user / log) |
| **F_structural** | Feed / draw / PA stages, stage count, pressure — approval-only |

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
| [`SCOPE_CDU_ASSIST.md`](SCOPE_CDU_ASSIST.md) | Product identity & boundaries |
| [`INTELLIGENCE_INVENTORY_V1.md`](INTELLIGENCE_INVENTORY_V1.md) | Coded vs paper vs planned |
| [`MULTI_VARIABLE_ITERATION_MAP.md`](MULTI_VARIABLE_ITERATION_MAP.md) | ChemE family iteration map |
| [`expert_decision_workflow.md`](expert_decision_workflow.md) | Master PE bible (States A–F) |
| [`column_convergence_playbook.md`](column_convergence_playbook.md) | Operational / COM slice *(legacy SW Stripper)* |
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
# HYSYS case open first (CDU / atmospheric crude tower)
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

- Updates to **this product** stay under CDU Assist v1 New Intelligence.  
- Simple Column / VDU get **separate** case docs and repos/folders.  
- Do not file unrelated experiment notes into this case file.

---

*Case description created 2026-07-22 for GitHub tracking of CDU Assist v1 — New Intelligence.*
