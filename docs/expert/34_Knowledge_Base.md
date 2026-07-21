# Knowledge Base

**Module ID:** 34  
**Parent:** [`00_System_Architecture.md`](00_System_Architecture.md)  
**Reasoning engine:** [`33_Reasoning_Engine.md`](33_Reasoning_Engine.md)  
**Domain modules:** `10`–`30` in this folder

Integrated from `CDU_Expert_Modules_Starter/34_Knowledge_Base.md` + module registry.

> **Note:** [`03_Knowledge_Base.md`](03_Knowledge_Base.md) redirects here (legacy path).

---

## Design rule

**No hard-coded engineering logic outside the knowledge base.**

Rules live in domain modules (`20`–`30`) as structured entries. The reasoning engine **loads and ranks** rules — it does not embed PE judgment inline.

---

## Rule record (required shape)

Each engineering rule shall contain:

| Field | Purpose |
|-------|---------|
| **Rule ID** | Stable key (e.g. `PA-001-diesel-light-fractionation`) |
| **Engineering objective** | L3 symptom owner |
| **Preconditions** | State C, product X off-spec, yields OK, etc. |
| **Observable variables** | Evidence to collect |
| **Manipulated variables** | L5 COM knobs (one family) |
| **Constraints** | DOF, FINAL_TARGET lock, bounds |
| **Expected response** | For prediction vs evaluation |
| **Side effects** | Neighbor cuts, energy, hydraulics |
| **Recovery strategy** | If wrong direction / weak response |

Rules are authored in domain modules first; this file indexes and routes them.

---

## Module registry

| ID | Module | Layer | T-100 | Automation |
|----|--------|-------|-------|------------|
| 10 | [`10_Crude_Assay.md`](10_Crude_Assay.md) | Feed / thermo | — | Planned |
| 20 | [`20_Model_Validation.md`](20_Model_Validation.md) | Validation | Yes | Partial |
| 21 | [`21_Feed_Preparation.md`](21_Feed_Preparation.md) | Upstream | Yes | Manual |
| 22 | [`22_Fired_Heater.md`](22_Fired_Heater.md) | Upstream | Yes | Cat-2 |
| 23 | [`23_Flash_Zone.md`](23_Flash_Zone.md) | Upstream | Yes | Cat-2 |
| 24 | [`24_Main_Fractionator.md`](24_Main_Fractionator.md) | Tower | Yes | Partial |
| 25 | [`25_PumpArounds.md`](25_PumpArounds.md) | PA | **Yes** | Partial |
| 26 | [`26_Side_Strippers.md`](26_Side_Strippers.md) | Strip | **Yes** | Partial |
| 27 | [`27_Product_Quality.md`](27_Product_Quality.md) | Quality | **Yes** | Monitor |
| 28 | [`28_Yield_Optimization.md`](28_Yield_Optimization.md) | Yield | — | Planned |
| 29 | [`29_Energy_Optimization.md`](29_Energy_Optimization.md) | Energy | Partial | Planned |
| 30 | [`30_Hydraulic_Diagnostics.md`](30_Hydraulic_Diagnostics.md) | Hydraulics | — | Planned |

### Platform modules

| ID | Module | Role |
|----|--------|------|
| 31 | [`31_HYSYS_Object_Map.md`](31_HYSYS_Object_Map.md) | COM abstraction |
| 32 | [`32_State_Machine.md`](32_State_Machine.md) | Process flow + A–F |
| 33 | [`33_Reasoning_Engine.md`](33_Reasoning_Engine.md) | Core loop |
| 35 | [`35_Experiment_Selection.md`](35_Experiment_Selection.md) | Pick one trial |
| 36 | [`36_Learning_System.md`](36_Learning_System.md) | Memory / confidence |
| 37 | [`37_Expert_Pseudocode.md`](37_Expert_Pseudocode.md) | Algorithms |
| 90 | [`90_Test_Cases.md`](90_Test_Cases.md) | Validation |

---

## Symptom → module routing

| Observation (L3) | Primary | Secondary |
|------------------|---------|-----------|
| Assay / crude mismatch | 10 | 20 |
| Model won't solve / DOF | 20 | 24 |
| Feed / heater / flash wrong | 21, 22, 23 | 20 |
| Wrong total yields / splits | 24, 28 | 27 |
| Cut too light / heavy | 27 | 25, 26 |
| Overlap / gap between cuts | 27 | 24, 25 |
| Mid-tower T / fractionation weak | 25 | 24 |
| Side product wet with lights | 26 | 27 |
| OH / naphtha end-point | 24 | 25 |
| Energy / PA trade-off | 29 | 25 |
| Flooding / capacity | 30 | 24 |

---

## Authoring priority (with PE)

1. [`27_Product_Quality.md`](27_Product_Quality.md) — FINAL_TARGETs + quality rules  
2. [`25_PumpArounds.md`](25_PumpArounds.md) — PA decision trees  
3. [`26_Side_Strippers.md`](26_Side_Strippers.md) — strip rules  
4. [`24_Main_Fractionator.md`](24_Main_Fractionator.md) — draw vs quality  
5. [`90_Test_Cases.md`](90_Test_Cases.md) — validate rules on T-100  

Re-merge domain starters: `python scripts/integrate_expert_modules.py`

---

*Knowledge base · CDU Expert System*
