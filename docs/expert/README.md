# CDU Expert System — Module Index

**Volume 0:** [`00_System_Architecture.md`](00_System_Architecture.md)

Integrated from `CDU_Expert_Modules_Starter` — domain modules **10–30**, platform intelligence **31–37**, validation **90**.

---

## Intelligence stack (process flow → decision → code)

```text
32 State Machine     — 10-step process flow + States A–F
33 Reasoning Engine  — observe → hypothesis → rank → predict → evaluate
34 Knowledge Base    — structured rules + symptom routing
35 Experiment Select — one minimum-impact trial
36 Learning System   — Trial Map memory + confidence
31 HYSYS Object Map  — COM abstraction (T-100)
37 Expert Pseudocode — reference implementation
```

Legacy paths: [`02_Reasoning_Engine.md`](02_Reasoning_Engine.md) → 33, [`03_Knowledge_Base.md`](03_Knowledge_Base.md) → 34.

---

## Core architecture (00–01)

| File | Role |
|------|------|
| [`00_System_Architecture.md`](00_System_Architecture.md) | Volume 0 master |
| [`01_Engineering_Philosophy.md`](01_Engineering_Philosophy.md) | Observe-before-act, escalation |

---

## Domain modules (10–30)

| File | Domain |
|------|--------|
| [`10_Crude_Assay.md`](10_Crude_Assay.md) | Crude characterization |
| [`20_Model_Validation.md`](20_Model_Validation.md) | Integrity, DOF |
| [`21_Feed_Preparation.md`](21_Feed_Preparation.md) | Preheat / blending |
| [`22_Fired_Heater.md`](22_Fired_Heater.md) | Crude heater |
| [`23_Flash_Zone.md`](23_Flash_Zone.md) | Flash / overflash |
| [`24_Main_Fractionator.md`](24_Main_Fractionator.md) | Tower, draws, OH |
| [`25_PumpArounds.md`](25_PumpArounds.md) | Pumparounds |
| [`26_Side_Strippers.md`](26_Side_Strippers.md) | Side strips |
| [`27_Product_Quality.md`](27_Product_Quality.md) | ASTM / TBP / cuts |
| [`28_Yield_Optimization.md`](28_Yield_Optimization.md) | Yield |
| [`29_Energy_Optimization.md`](29_Energy_Optimization.md) | Energy |
| [`30_Hydraulic_Diagnostics.md`](30_Hydraulic_Diagnostics.md) | Hydraulics |

---

## Platform intelligence (31–37)

| File | Role |
|------|------|
| [`31_HYSYS_Object_Map.md`](31_HYSYS_Object_Map.md) | COM ↔ engineering objects |
| [`32_State_Machine.md`](32_State_Machine.md) | **Process flow + A–F** |
| [`33_Reasoning_Engine.md`](33_Reasoning_Engine.md) | **Core reasoning loop** |
| [`34_Knowledge_Base.md`](34_Knowledge_Base.md) | **Rules + routing** |
| [`35_Experiment_Selection.md`](35_Experiment_Selection.md) | **Pick one trial** |
| [`36_Learning_System.md`](36_Learning_System.md) | **Memory + confidence** |
| [`37_Expert_Pseudocode.md`](37_Expert_Pseudocode.md) | Implementation algorithms |

---

## Validation

| File | Role |
|------|------|
| [`90_Test_Cases.md`](90_Test_Cases.md) | Scenarios + T-100 baseline |

---

## Repo links

| Doc | Use |
|-----|-----|
| [`../SCOPE_CDU_ASSIST.md`](../SCOPE_CDU_ASSIST.md) | Product scope |
| [`../cdu_com_discovery.md`](../cdu_com_discovery.md) | T-100 COM |
| [`../cdu_convergence_playbook.md`](../cdu_convergence_playbook.md) | Operational trials |

---

## Authoring

- **Platform intelligence (31–37):** edit `docs/expert/` directly  
- **Domain modules (10–30):** edit `docs/expert/` or refresh from starter + `python scripts/integrate_expert_modules.py`  
- **Priority with PE:** 27 → 25 → 26 → 24 → 90  

---

*CDU Expert System module index*
