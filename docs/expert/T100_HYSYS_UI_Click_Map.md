# T-100 HYSYS UI Click Map (PE-provided)

**Column:** `T-100` / sub-flowsheet tag `COL1`  
**Fluid package:** Basis-1 / Peng-Robinson  
**Source:** Process engineer screenshots + COM discovery  
**Status:** Living document — add tabs as PE posts more screens

---

## How CDU Assist uses this

| Layer | This document |
|-------|----------------|
| PE training | Where to click in HYSYS for T-100 |
| Expert L2–L3 | Subsystem boundaries (OH / SS / PA / feed) |
| COM mapping | Links UI stream names → `column_api` / specs |
| Config | Cross-check `config/cdu_t100_case.json` stream names |

---

## Top-level column tabs

| Tab | PE use | Assist today |
|-----|--------|--------------|
| **Design** | Connections, Monitor, Specs, Specs Summary | READ Connections + Specs via COM |
| Parameters | Column solver / stage data | Not automated |
| Side Ops | Side strippers, pump-arounds detail | Partial via COM collections |
| Internals | Trays, packing | READ only (future hydraulics) |
| Rating | Flooding / tray rating | Not coded |
| Worksheet | Stream / duty tables | Partial stream reads |
| Performance | Profiles | Stage T/P via COM (partial) |
| Flowsheet | Return to main PFD | Manual |
| Reactions | Usually N/A for CDU | — |
| Dynamics | Not in scope v0.1 | — |

---

## Design → sidebar

| Sidebar item | Purpose | Assist |
|--------------|---------|--------|
| **Connections** | Inlets/outlets, pressure, stage numbering | **READ** — `format_connections_block()` |
| **Monitor** | Solver iteration, equilibrium / heat spec error | **READ** — monitor fields on `ColumnState` |
| **Specs** | Active specs, GoalValue, Current, Error | **READ + WRITE** GoalValue / Active / Estimate |
| **Specs Summary** | Active vs Current matrix | Recommend clicks; APPLY in GUI |
| Subcooling | Condenser subcool | Not coded |
| Notes | Documentation | — |

**PE workflow order (typical):** Connections (sanity) → Monitor (converged?) → Specs (residuals) → Specs Summary (philosophy).

---

## Design → Connections (confirmed from PE screen)

### Header

- **Name:** T-100  
- **Sub-flowsheet tag:** COL1  
- **Stage numbering:** Top Down  
- **Pressure:** dP Top = 9.000 psi, P Top = 19.70 psia, P Bot = 32.70 psia  
- **Status bar:** Converged (green)  
- **Update Outlets:** checked  

### Inlet streams (external → internal stage)

| Internal name | External stream | Stage | Basis |
|---------------|-----------------|-------|-------|
| Main Steam | Main Steam | 29_Main TS | T-P Flash |
| Q-Trim | Q-Trim | 28_Main TS | None Req'd |
| Atm Feed | Atm Feed | 28_Main TS | T-P Flash |
| Kero_SS_Energy | *(<< Stream >> on screen — likely Kero_SS_Energy)* | Kero_SS_Reb | None Req'd |
| Diesel Steam | Diesel Steam | 3_Diesel_SS | T-P Flash |
| AGO Steam | AGO Steam | 3_AGO_SS | T-P Flash |

**Engineering notes:**

- **Atm Feed + Q-Trim @ stage 28** — main column feed zone (near bottom on top-down numbering).  
- **Main Steam @ stage 29** — stripping steam to bottom / residue section.  
- **Side-strip steam:** Diesel Steam, AGO Steam enter at `3_Diesel_SS` / `3_AGO_SS`.  
- **Kero reboil** tied to `Kero_SS_Reb` stage via energy stream.

### Outlet streams (internal → external product)

| Internal name | External stream | Stage | Type | Basis |
|---------------|-----------------|-------|------|-------|
| Residue | Residue | 29_Main TS | L (liquid) | T-P Flash |
| Atmos Cond | Atmos Cond | Condenser | Q (duty) | None Req'd |
| Off Gas | Off Gas | Condenser | V (vapor) | T-P Flash |
| Waste Water | Waste Water | Condenser | W (water) | T-P Flash |
| Naphtha | Naphtha | Condenser | L | T-P Flash |
| Kerosene | Kerosene | Kero_SS_Reb | L | T-P Flash |
| Diesel | Diesel | 3_Diesel_SS | L | T-P Flash |
| AGO | AGO | 3_AGO_SS | L | T-P Flash |
| PA_1_Q | *(<< Stream >>)* | — | Q | None Req'd |
| PA_2_Q | *(<< Stream >>)* | — | Q | None Req'd |
| PA_3_Q | *(<< Stream >>)* | — | Q | None Req'd |

**Product stream names for quality / FINAL_TARGET config:**

`Naphtha`, `Kerosene`, `Diesel`, `AGO`, `Residue`, `Off Gas`, `Waste Water`

### Subsystem map (from Connections)

```text
Condenser zone     → Naphtha, Off Gas, Waste Water, Atmos Cond
Kero side strip    → Kerosene @ Kero_SS_Reb, Kero_SS_Energy
Diesel side strip  → Diesel @ 3_Diesel_SS, Diesel Steam
AGO side strip     → AGO @ 3_AGO_SS, AGO Steam
Bottom / residue   → Residue @ 29_Main TS, Main Steam, Atm Feed
Pump-arounds       → PA_1_Q, PA_2_Q, PA_3_Q (duty streams)
```

---

## Bottom bar buttons (Connections / Monitor)

| Button | PE action | Assist |
|--------|-----------|--------|
| **Run** | Re-solve column | COM `Run()` after trial |
| Reset | Reset column | Not automated |
| Delete | Remove column | Never auto |
| Column Environment... | Sub-flowsheet | Manual |
| Update Outlets | Sync outlet specs | PE leaves checked |

---

## Design → Monitor (confirmed from PE screen)

**Path:** Design → **Monitor** (left sidebar)

### Solver status (top)

| Field | Value (this case) | Assist COM |
|-------|-------------------|------------|
| Iter | 1 | `monitor_iteration` |
| Step | 1.0000 | `monitor_step` |
| Equilibrium | 1.47201e-12 | `monitor_equilibrium_error` |
| Heat / Spec | 9.09196e-06 | `monitor_heat_spec_error` |
| **DOF** | **0** | `degrees_of_freedom` |
| Status bar | **Converged** (green) | `appears_converged` |

**Buttons (PE):** `Input Summary` · `View Initial Estimates...` (State B recovery)

### Profile chart

- **Title:** Temperature vs. Tray Position from Top  
- **Radio options:** **Temp** (selected) · Press · Flows  
- Use for sanity: flat/wrong profile → State B before tuning products  

### Specifications table (worksheet view on Monitor)

Columns: **Name · Specified · Current · Wt. Error · Active · Estimate · Current**

| Spec name | Specified (worksheet) | Active | Estimate | PE role |
|-----------|----------------------|--------|----------|---------|
| Kero_SS Prod Flow | 271.3 USGPM | ✓ | | Side-draw solver handle |
| Diesel_SS Prod Flow | 561.5 USGPM | ✓ | | Side-draw solver handle |
| AGO_SS Prod Flow | 131.3 USGPM | ✓ | | Side-draw solver handle |
| PA_1_Rate(Pa) | 1458 USGPM | ✓ | | PA circulation handle |
| PA_1_Duty(Pa) | -5.500e+007 Btu/hr | ✓ | | PA heat removal handle |
| PA_2_Rate(Pa) | 875.0 USGPM | ✓ | | PA circulation handle |
| PA_2_Duty(Pa) | -3.500e+007 Btu/hr | ✓ | | PA heat removal handle |
| PA_3_Rate(Pa) | 875.0 USGPM | ✓ | | PA circulation handle |
| PA_3_Duty(Pa) | -3.500e+007 Btu/hr | ✓ | | PA heat removal handle |
| Naphtha Prod Rate | 670.8 USGPM | ✓ | | Overhead product rate |
| Liquid Flow | 102.1 USGPM | ✓ | | Overhead / reflux-related |
| Kero Reb Duty | 7.500e+006 Btu/hr | ✓ | | Kero side-strip energy |
| Vap Prod Flow | 0.0000 lbmole/hr | ✓ | | Vapor product (≈0) |
| Reflux Ratio | 1.000 | **✗** | ✓ | **Monitor / estimate only** |

**Spec philosophy flags (Assist will warn):**

- All three PAs have **both Rate and Duty Active** → `PA-CONFLICT` warning  
- **Reflux Ratio** not Active (good — estimate/monitor)  
- Naphtha rate + Liquid flow both Active → `OH-CONFLICT` watch  

**Table buttons:** `View...` · **`Add Spec...`** · `Group Active` · `Update Inactive`

---

## Add Spec dialog (Column Specification Types)

**Opened from:** Design → Monitor (or Specs) → **Add Spec...**

**Dialog title:** `Add Specs - T-100...`  
**Button:** `Add Spec(s)...` at bottom  

Full HYSYS list (scroll — two pages, PE screenshots):

| # | HYSYS type name | CDU relevance |
|---|-----------------|---------------|
| 1 | Column Cold Properties Spec | Rare |
| 2 | Column Component Flow | Sometimes |
| 3 | Column Component Fraction | Quality — usually monitor only |
| 4 | Column Component Ratio | Rare |
| 5 | Column Component Recovery | Sometimes |
| 6 | Column Cut Point | **CDU petroleum cuts** |
| 7 | Column Draw Rate | **CDU side draws** (on T-100) |
| 8 | Column DT (Heater/Cooler) Spec | PA / exchanger ΔT |
| 9 | Column Dt Spec | Tray ΔT |
| 10 | Column Duty | Reboiler / condenser |
| 11 | Column Duty Ratio | Rare |
| 12 | Column Feed Ratio | Rare |
| 13 | Column Gap Cut Point | **CDU gap cuts** |
| 14 | Column Liquid Flow | **Overhead** (on T-100) |
| 15 | Column Physical Properties Spec | Column property |
| 16 | Column Pump Around | **PA** (on T-100) |
| 17 | Column Reboil Ratio Spec | Side stripper |
| 18 | Column Recovery | Product recovery |
| 19 | Column Reflux Feed Ratio Spec | Rare |
| 20 | Column Reflux Fraction Spec | Rare |
| 21 | Column Reflux Ratio | Reflux (T-100: estimate only) |
| 22 | Column Stream Property Spec | Stream on column |
| 23 | Column Tee Split Spec | Rare |
| 24 | Column Temperature | Tray / product T |
| 25 | Column Transport Properties Spec | Rare |
| 26 | Column User Property Spec | User-defined |
| 27 | Column Vapour Flow | Vapor product |
| 28 | Column Vapour Fraction Spec | Rare |
| 29 | Column Vapour Pressure Spec | RVP-related |
| 30 | End Point Based Column Cut Point Spec | **CDU D86 / TBP endpoints** |
| 31 | End Point Based Column Gap Spec | **CDU gap endpoints** |
| 32 | Stream Specification | Generic |

**Assist today:** recommend only — no auto Add Spec. Catalog in `column_spec_catalog.py`.  
Also opened from Design → Specs → **Add...** (same dialog).

---

## Design → Specs (confirmed from PE screen)

**Path:** Design → **Specs** (left sidebar)  
**Role:** Primary **read/write** surface for CDU Assist trials (COM `Specifications` collection).

### Left panel — Column Specifications list

Same 14 specs as Monitor. **Selected example:** `PA_1_Rate(Pa)`

| Button / control | PE use | Assist |
|------------------|--------|--------|
| **View...** | View spec details | — |
| **Add...** | Opens Add Spec dialog | Recommend only |
| **Delete** | Remove spec | Never auto |
| **Update Specs from Dynamics** | Dynamics sync | Not coded |
| **Default Basis** | Molar (dropdown) | Note for unit interpretation |
| **Degrees of Freedom** | Must be 0 | READ `degrees_of_freedom` |
| **Switch To Alternate Specs** | Alternate spec set | Disabled on this case |

### Right panel — detail for selected spec (`PA_1_Rate(Pa)` example)

| UI field | Example value | COM / Assist field |
|----------|---------------|-------------------|
| Spec Name | PA_1_Rate(Pa) | `spec.Name` |
| Converged ? | No (yellow) | Per-spec converge flag |
| **Active** | ✓ checked | `IsActive` — **Assist WRITES** |
| **Use As Estimate** | ✓ checked | `IsUsedAsEstimate` — **Assist WRITES** |
| **Current** | ✓ checked | Summary / sync Current→Goal |
| Dry Flow Basis | ☐ unchecked | Case-specific |
| Fixed/Ranged Spec | **Fixed** | Primary DOF style |
| Primary/Alternate Spec | **Primary** | Spec set role |
| **Specification Value** | **1458 USGPM** | `GoalValue` — **Assist WRITES (trials)** |
| Current Calculated Value | *(empty when unsettled)* | `CurrentValue` READ |
| Weighted Tolerance | 1.000e-002 | `weighted_tolerance` |
| Weighted Calculated Error | *(empty)* | `error` READ |
| Absolute Tolerance | 4.403 USGPM | Display tolerance |
| Absolute Calculated Error | *(empty)* | Absolute error display |

**COM unit note:** Worksheet shows **USGPM**; COM `GoalValue` is typically SI (e.g. kgmole/s). Assist converts for PE board display.

### Checkbox philosophy (PE vs Assist)

| Pattern | Example on T-100 | Assist interpretation |
|---------|------------------|------------------------|
| Active ✓ only | Most product/PA specs | **Solver handle** — trials may nudge GoalValue |
| Estimate ✓, Active ✗ | Reflux Ratio (Monitor) | **Monitor only** — do not nudge |
| Active ✓ + Estimate ✓ + Current ✓ | PA_1_Rate on Specs page | Active DOF; Estimate helps initialization — flag in spec audit if quality spec |

### Status bar note

This screen showed **Unconverged** (red) while Monitor earlier showed **Converged** — case state changes when specs are edited or before Run. Assist always **Run** after a trial and re-read.

**Assist trial write path (L5):**

```text
Specs → select spec → GoalValue (Specification Value)
                    → IsActive / IsUsedAsEstimate (Specs Summary recommendations)
```

Implemented in `column_api.set_spec_goal()`, `set_spec_active()`, `set_spec_estimate()`.

---

## Design → Specs Summary (confirmed from PE screen)

**Path:** Design → **Specs Summary** (left sidebar)  
**Role:** Matrix view of **Active** vs **Current** for every spec — PE sanity check and Assist **click recommendations**.

### Table columns

| Column | Meaning |
|--------|---------|
| *(Spec name)* | Same 14 specs as Monitor / Specs |
| **Specified Value** | Goal / setpoint (worksheet units) |
| **Active** | Spec is a solver DOF (`IsActive`) |
| **Current** | “Current” checkbox on summary (tracks with spec) |
| Fixed/Range | Fixed vs ranged spec |
| Prim/Alt | Primary vs alternate |
| Lower / Upper | Ranged bounds (all `<empty>` on T-100 — Fixed specs) |

### T-100 rows (PE confirmed)

| Spec | Specified | Active | Current | Notes |
|------|-----------|--------|---------|-------|
| Kero_SS Prod Flow | 271.3 | ✓ | ✓ | Side draw |
| Diesel_SS Prod Flow | 561.5 | ✓ | ✓ | Side draw |
| AGO_SS Prod Flow | 131.3 | ✓ | ✓ | Side draw |
| PA_1_Rate(Pa) | 1458 | ✓ | ✓ | PA rate |
| PA_1_Duty(Pa) | -5.500e+007 | ✓ | ✓ | PA duty |
| PA_2_Rate(Pa) | 875.0 | ✓ | ✓ | PA rate |
| PA_2_Duty(Pa) | -3.500e+007 | ✓ | ✓ | PA duty |
| PA_3_Rate(Pa) | 875.0 | ✓ | ✓ | PA rate |
| PA_3_Duty(Pa) | -3.500e+007 | ✓ | ✓ | PA duty |
| Naphtha Prod Rate | 670.8 | ✓ | ✓ | Overhead |
| Liquid Flow | 102.1 | ✓ | ✓ | Overhead |
| Kero Reb Duty | 7.500e+006 | ✓ | ✓ | Side strip |
| Vap Prod Flow | 0.0000 | ✓ | ✓ | Vapor |
| **Reflux Ratio** | 1.000 | **✗** | **✗** | **Not a DOF — monitor/estimate** |

**PE pattern on this case:** 13 Active DOFs + Reflux off Active → **DOF = 0** when model is posed.

### How Assist uses Specs Summary

- PE board section: **“SPECS SUMMARY clicks”** from `recommend_specs_summary_clicks()`  
- GUI can APPLY: Active ON/OFF, Estimate ON/OFF, sync Current→Goal  
- **Policy:** locked FINAL_TARGET / quality specs → recommend **Active OFF**, **Estimate ON** (monitor only)

**Difference vs Specs page:** Summary shows **Active + Current** grid only (no Estimate column here — Estimate is on Specs detail / Monitor table).

---

## Tabs still needed from PE (please post next)

- [x] **Design → Monitor** — iteration, spec table, profile  
- [x] **Design → Specs** — detail panel, checkboxes, GoalValue  
- [x] **Add Spec dialog** — full type list  
- [x] **Design → Specs Summary** — Active vs Current grid  
- [ ] **Side Ops** — PA draw/return trays, side stripper detail  
- [ ] **Worksheet** — diesel/kero D86 or TBP on streams  
- [ ] Upstream: **Crude Heater**, **PreFlash**  

---

## Cross-reference

- COM spec names: [`../cdu_com_discovery.md`](../cdu_com_discovery.md)  
- Case config: [`../../config/cdu_t100_case.json`](../../config/cdu_t100_case.json)  
- Object abstraction: [`31_HYSYS_Object_Map.md`](31_HYSYS_Object_Map.md)
