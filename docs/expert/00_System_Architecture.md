# CDU Expert System Specification
## Volume 0 – Master Architecture

**Status:** Living specification  
**Audience:** Software developers building an external Aspen HYSYS CDU Expert System  
**Product:** CDU Assist (`hysys-CDU-assist`)

> This repository does **not** document how to use Aspen HYSYS.  
> It specifies how an experienced refinery process simulation engineer reasons while using Aspen HYSYS.

**Related docs in this repo:**

| Doc | Role |
|-----|------|
| [`../SCOPE_CDU_ASSIST.md`](../SCOPE_CDU_ASSIST.md) | Product identity, v0.1 success, safety |
| [`../expert_decision_workflow.md`](../expert_decision_workflow.md) | States A–F, FINAL_TARGET, trial discipline (Tower Assist bible) |
| [`../cdu_convergence_playbook.md`](../cdu_convergence_playbook.md) | Operational click map for CDU Assist v0.1 |
| [`../cdu_com_discovery.md`](../cdu_com_discovery.md) | Live COM map — reference column `T-100` |
| [`02_Reasoning_Engine.md`](02_Reasoning_Engine.md) | How Volume 0 maps to executable code layers |
| [`README.md`](README.md) | Planned module index |

---

# Project Goal

The objective is to develop an external engineering intelligence that can:

- Inspect a CDU HYSYS case
- Understand refinery objectives
- Diagnose engineering problems
- Select engineering experiments
- Manipulate HYSYS variables
- Evaluate responses
- Learn from previous iterations

The external program is the **engineer**.

Aspen HYSYS is the **numerical solver**.

---

# Design Philosophy

The automation shall reason using engineering objectives rather than direct variable manipulation.

Never:

```text
Problem → Variable
```

Always:

```text
Observation
  → Evidence Collection
  → Hypothesis Generation
  → Hypothesis Ranking
  → Experiment Selection
  → HYSYS Execution
  → Engineering Evaluation
  → Knowledge Update
```

This is the **non-negotiable reasoning spine**. Executable Assist grows in thin layers that implement slices of this loop — not one opaque mega-brain.

---

# Layered Intelligence

```text
Level 0   Corporate objective
Level 1   Refinery objective
Level 2   CDU objective
Level 3   Subsystem objective
Level 4   Equipment objective
Level 5   Manipulated variable (HYSYS COM knob)
```

**Mapping to CDU Assist today:**

| Level | Example (T-100 class) | Where coded / documented |
|-------|------------------------|---------------------------|
| L0–L1 | Corporate margin, crude slate | **Future** — user / case config |
| L2 | Meet cut specs, yields, energy | `FinalTarget` layer + user FINAL_TARGETs |
| L3 | “Diesel too light”, “PA heat weak” | Diagnosis families → `column_engine.diagnose` |
| L4 | PA_2 duty, Diesel_SS flow, Kero strip steam | `cdu_com_discovery.md`, spec catalog |
| L5 | `GoalValue` / `IsActive` on named spec | `column_api`, bounded trials |

**Rule:** Level 5 moves are **never** chosen without Level 3–4 hypothesis. That is what separates expert Assist from GoalValue spam.

---

# Major Knowledge Domains

Each domain shall eventually contain:

- Engineering objective
- Physics
- Observations
- Required HYSYS objects
- Hidden state
- Diagnostic rules
- Hypotheses
- Confidence model
- Manipulated variables
- Interaction matrix
- Failure modes
- Recovery logic
- Optimization strategy
- Automation pseudocode

| # | Domain | Planned module | Status |
|---|--------|----------------|--------|
| 1 | Crude characterization | [`10_Crude_Assay.md`](10_Crude_Assay.md) | Starter framework |
| 2 | Thermodynamics | `11_Property_Method.md` | Planned |
| 3 | Feed preparation | [`21_Feed_Preparation.md`](21_Feed_Preparation.md) | Starter + T-100 |
| 4 | Fired heater | [`22_Fired_Heater.md`](22_Fired_Heater.md) | Starter + T-100 |
| 5 | Flash zone | [`23_Flash_Zone.md`](23_Flash_Zone.md) | Starter + T-100 |
| 6 | Main fractionator | [`24_Main_Fractionator.md`](24_Main_Fractionator.md) | **Starter + T-100** |
| 7 | Wash section | (under fractionator) | Planned |
| 8 | Pump-arounds | [`25_PumpArounds.md`](25_PumpArounds.md) | **Starter + T-100** |
| 9 | Side draws | [`24_Main_Fractionator.md`](24_Main_Fractionator.md) | **Starter + T-100** |
| 10 | Side strippers | [`26_Side_Strippers.md`](26_Side_Strippers.md) | **Starter + T-100** |
| 11 | Overhead | [`24_Main_Fractionator.md`](24_Main_Fractionator.md) | Starter + T-100 |
| 12 | Product quality | [`27_Product_Quality.md`](27_Product_Quality.md) | **Starter + T-100** |
| 13 | Energy | [`29_Energy_Optimization.md`](29_Energy_Optimization.md) | Starter framework |
| 14 | Hydraulics | [`30_Hydraulic_Diagnostics.md`](30_Hydraulic_Diagnostics.md) | Starter framework |
| 15 | Constraints | `expert_decision_workflow.md` § constraints | Partial |
| 16 | Diagnostics | [`32_State_Machine.md`](32_State_Machine.md) | Partial — States A–F |
| 17 | Optimization | [`28_Yield_Optimization.md`](28_Yield_Optimization.md) | Starter framework |

**Module index:** [`03_Knowledge_Base.md`](03_Knowledge_Base.md) → [`34_Knowledge_Base.md`](34_Knowledge_Base.md)  
**Process / reasoning:** [`32_State_Machine.md`](32_State_Machine.md), [`33_Reasoning_Engine.md`](33_Reasoning_Engine.md), [`35_Experiment_Selection.md`](35_Experiment_Selection.md), [`36_Learning_System.md`](36_Learning_System.md)  
**Source templates:** `CDU_Expert_Modules_Starter/` (integrated 2026-07-21, modules 31–36 + 90 added)

---

# Master Decision Loop

1. Load HYSYS model  
2. Validate model integrity  
3. Validate crude assay  
4. Validate property package  
5. Validate equipment connectivity  
6. Build engineering state  
7. Determine operating objective  
8. Collect all measurements  
9. Detect abnormalities  
10. Generate hypotheses  
11. Rank hypotheses  
12. Select minimum-impact experiment  
13. Execute one engineering action  
14. Run HYSYS  
15. Evaluate predicted vs actual response  
16. Update confidence  
17. Repeat until objectives are met or no feasible path exists  

**CDU Assist v0.1 implements steps 1, 5–6, 8 (partial), 9 (partial), 12–15, 16 (partial).**  
Steps 2–4, 7, 10–11 are the **next intelligence build** — documented in domain modules, not invented in code until COM + rules exist.

---

# Engineering Rules

The automation SHALL:

- Observe before acting  
- Change one major variable at a time unless coordinated actions are required  
- Record every experiment  
- Prefer reversible actions  
- Detect interactions between subsystems  
- Reject physically unrealistic solutions even if HYSYS converges  
- Escalate from local adjustments to structural changes only when justified  

These align with PE rules P1–P7 in [`SCOPE_CDU_ASSIST.md`](../SCOPE_CDU_ASSIST.md) and States A–F in [`expert_decision_workflow.md`](../expert_decision_workflow.md).

Additional CDU-specific rules:

- **FINAL_TARGET lock** — cut / ASTM / TBP plant targets are not auto-relaxed to force convergence  
- **Worksheet + stream truth** — prefer product stream / assay over raw COM display when they disagree  
- **Interactive default** — one trial → PE board → human approves next (batch Assist only when allowed)

---

# Planned Repository (module tree)

```text
docs/expert/
  00_System_Architecture.md      ← this file (Volume 0)
  01_Engineering_Philosophy.md
  02_Reasoning_Engine.md
  03_Knowledge_Base.md
  10_Crude_Assay.md
  11_Property_Method.md
  12_Pseudo_Components.md
  20_Model_Validation.md
  21_Feed_Preparation.md
  22_Fired_Heater.md
  23_Flash_Zone.md
  24_Main_Fractionator.md
  25_PumpArounds.md
  26_Side_Strippers.md
  27_Product_Quality.md
  28_Yield_Optimization.md
  29_Energy_Optimization.md
  30_Hydraulic_Diagnostics.md
  31_HYSYS_Object_Map.md
  32_State_Machine.md
  31_HYSYS_Object_Map.md
  32_State_Machine.md
  33_Reasoning_Engine.md
  34_Knowledge_Base.md
  35_Experiment_Selection.md
  36_Learning_System.md
  37_Expert_Pseudocode.md
  90_Test_Cases.md
  README.md
```

Modules are added **one at a time** with enough detail that a developer can implement reasoning without inventing engineering logic.

---

# Long-Term Scope

This master document intentionally remains architecture-focused.

The complete specification is expected to exceed 100 pages and will be expanded module-by-module.

Each module should be detailed enough that a software engineer can implement the reasoning without needing to invent the engineering logic.

---

# Appendix A — Integration with CDU Assist codebase (v0.1)

| Volume 0 concept | Current code / doc |
|------------------|-------------------|
| Load model / collect measurements | `hysys_api.py`, `column_api.inspect` |
| Build engineering state | `column_models.ColumnState`, `Diagnosis` |
| Detect abnormalities | `diagnose()`, operability gates (partial) |
| Select experiment | `choose_trial_action()`, `trial_map.STRATEGY_CATALOG` |
| Execute + reversible | snapshot/restore, `ConvergenceAssistant` |
| Evaluate response | keep/reverse, response classes (partial) |
| Record experiments | Trial Map, activity log |
| Hypothesis generation / ranking | **Not yet** — target `02_Reasoning_Engine.md` + domain modules |
| Confidence / learning | **Not yet** — P2+ |

**Reference case:** `T-100` — see [`../cdu_com_discovery.md`](../cdu_com_discovery.md).

---

*Volume 0 · integrated into CDU Assist 2026-07-21*
