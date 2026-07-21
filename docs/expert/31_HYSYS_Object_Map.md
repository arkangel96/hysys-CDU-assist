# HYSYS Object Mapping

**Module ID:** 31  
**Parent:** [`00_System_Architecture.md`](00_System_Architecture.md)  
**Live discovery:** [`../cdu_com_discovery.md`](../cdu_com_discovery.md)  
**JSON:** `column_com_discovery.json`, `column_com_deep.json`, `cdu_t100_inspect.json`

Integrated from `CDU_Expert_Modules_Starter/31_HYSYS_Object_Map.md` + T-100 COM evidence.

---

## Purpose

Stable **abstraction layer** between Aspen HYSYS COM and the expert system.

The reasoning engine must **never** depend on HYSYS UI names alone. It interacts with **logical engineering objects** mapped to COM.

---

## Mapping philosophy

**Example:**

| Engineering object | HYSYS objects |
|--------------------|---------------|
| Fired heater outlet temperature | `Crude Heater` block, outlet stream `Temperature` |
| PA_2 heat removal duty | Spec `PA_2_Duty(Pa)`, `LiquidPumpArounds` item `PA_2` |
| Diesel side-strip product rate | Spec `Diesel_SS Prod Flow`, `SideStrippers.Diesel_SS` |

---

## Required mapping (per equipment)

For every logical object define:

- Object ID  
- Type (stream / column / PA / side strip / heater)  
- Inputs / outputs  
- Specifications (Active / Estimate)  
- Degrees of freedom contribution  
- Read-only vs writable variables  
- Constraints  

---

## Interface contract (target code)

Every mapped object shall expose:

| Method | Role |
|--------|------|
| `ReadState()` | Evidence for Observation |
| `Validate()` | Model validation / State A |
| `CalculateDerivedVariables()` | Worksheet units, stream truth |
| `ApplyAction()` | Bounded L5 write |
| `Rollback()` | Snapshot restore |

**Today:** only spec-level `ReadState` / `ApplyAction` / `Rollback` via `column_api`.

---

## T-100 reference map

| Engineering object | HYSYS surface | Read | Write (v0.1) |
|--------------------|---------------|------|--------------|
| Main fractionator | `T-100`, `ColumnFlowsheet` | Yes | Via specs |
| Side draw rates | `clmdrawspec` — `Naphtha Prod Rate`, `*_SS Prod Flow` | Yes | `GoalValue`, `IsActive` |
| Pumparounds | `LiquidPumpArounds`, `PA_*_Rate/Duty` | Yes | Spec `GoalValue` |
| Side strippers | `SideStrippers`, steam feeds | Partial | Spec / manual |
| Strip reboil | `Kero Reb Duty`, `Kero_SS_Energy` | Partial | Spec |
| Products | Naphtha…Residue streams | Yes | Monitor |
| Energy | `Atmos Cond`, `Q-Trim` | Partial | Manual |
| Furnace / flash | `Crude Heater`, `PreFlash` | Separate ops | Manual |

---

## Spec type → strategy family

| COM type | Examples | Trial Map |
|----------|----------|-----------|
| `clmpumpspec` | `PA_1_Duty(Pa)` | `pa_duty_nudge` |
| `clmdrawspec` | `Naphtha Prod Rate` | `side_draw_rate_nudge` |
| `clmdutyspec` | `Kero Reb Duty` | `side_strip_steam_nudge` |
| `clmliquidflowspec` | `Liquid Flow` | `reflux_or_oh_nudge` |
| `clmrefluxspec` | `Reflux Ratio` | `reflux_or_oh_nudge` |

---

## Future expansion

Map every CDU object class: streams, HX, columns, side strippers, pumps, valves, controllers — per [`00_System_Architecture.md`](00_System_Architecture.md) domain list.

**Not yet mapped:** ASTM/TBP on streams, inactive cut specs, PA direct `HeatFlowValue`, hydraulics.

---

*HYSYS object map · CDU Expert System*
