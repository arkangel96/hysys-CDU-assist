# CDU COM Discovery — T-100 (live case)

**Date:** 2026-07-21  
**Case:** user’s open atmospheric crude case in HYSYS  
**Column:** `T-100` (`columnop`, flowsheet tag `COL1` @ Main)  
**Related dumps:** `cdu_t100_inspect.json`, `column_com_discovery.json`

---

## 1. Case topology (confirmed)

| Piece | Names |
|-------|--------|
| Upstream ops | `PreFlash`, `Crude Heater`, `Mixer` |
| Column | `T-100` — 29 stages, feed stage ~28, DOF = 0 |
| Feeds | `Atm Feed`, `Main Steam`, `Diesel Steam`, `AGO Steam` |
| Products | `Naphtha`, `Kerosene`, `Diesel`, `AGO`, `Residue`, `Off Gas`, `Waste Water` |
| Energy | `Atmos Cond`, `Q-Trim`, `Kero_SS_Energy` |

This is a **real atmospheric CDU** with side draws, three pumparounds, and side strippers — exactly the v0.1 target class.

---

## 2. Specs currently Active (Category-1 surface)

All Active unless noted. Worksheet display uses kgmole/h for rate specs.

| Spec | COM type | Role |
|------|----------|------|
| `Kero_SS Prod Flow` | `clmdrawspec` | Side-strip product rate |
| `Diesel_SS Prod Flow` | `clmdrawspec` | Side-strip product rate |
| `AGO_SS Prod Flow` | `clmdrawspec` | Side-strip product rate |
| `PA_1_Rate(Pa)` / `PA_1_Duty(Pa)` | `clmpumpspec` | Pumparound rate + duty |
| `PA_2_Rate(Pa)` / `PA_2_Duty(Pa)` | `clmpumpspec` | Pumparound rate + duty |
| `PA_3_Rate(Pa)` / `PA_3_Duty(Pa)` | `clmpumpspec` | Pumparound rate + duty |
| `Naphtha Prod Rate` | `clmdrawspec` | OH liquid product rate |
| `Liquid Flow` | `clmliquidflowspec` | Internal / reflux-style liquid |
| `Kero Reb Duty` | `clmdutyspec` | Side-strip reboiler duty |
| `Vap Prod Flow` | `clmvapourflowspec` | Vapor product (≈0) |
| `Reflux Ratio` | `clmrefluxspec` | **Estimate only** (not Active) |

**Writable path (already used by Assist):** Specs → `GoalValue` / `IsActive` / estimates — same as Simple Column platform.

**Units trap:** COM Goal/Current for rates are SI (kgmole/s); worksheet display ≈ ×3600 → kgmole/h. Duties are large negative for PA coolers (heat removal).

---

## 3. ColumnFlowsheet collections (readable)

| Collection | Count / notes | Useful members |
|------------|---------------|----------------|
| `LiquidPumpArounds` | 3 (`PA_*`) | `DrawStage`, `ReturnStage`, `HeatFlow` / `HeatFlowValue`, `ReturnMolarFlow` / `Value`, `ReturnTemperature` / `Value`, `DeltaTemperature`, `FirstPumpAroundSpec`, `SecondPumpAroundSpec` |
| `VapourPumpArounds` | 0 | — |
| `SideStrippers` | 3 (`Kero_SS` / `Diesel_SS` / `AGO_SS`) | `DrawStage`, `ReturnStage`, `SteamFeedStream`, `ProductFlowRate` / `Value`, `SpecifiedProductFlowRate`, `ReboilRatio`, `LiquidProductStream`, `NumberOfStages` |
| `SideRectifiers` | 0 | — |
| `LiquidProducts` | Residue, Kerosene, Diesel, AGO, (+ Naphtha via attached) | Stream-like petroleum props (`BO*`, flows, T, P) |
| `VapourProducts` | `Off Gas` | |
| `WaterProducts` | `Waste Water` | |
| `Specifications` / `ActiveSpecifications` | Present | Same spec objects Assist already reads |
| Draw stage groups | `LiquidDrawColumnStages`, `HeavyDrawColumnStages`, `VapourDrawColumnStages`, `MixedDrawColumnStages` | Stage mapping — to probe next |

**Note:** Enumeration by `Item(i)` can duplicate names if 0-based vs 1-based indexing is wrong — use `Name` / `Count` carefully in code.

---

## 4. Readable vs writable (current knowledge)

| Surface | Read | Write via Assist today |
|---------|------|-------------------------|
| Spec GoalValue / IsActive | Yes | Yes (supported) |
| PA object HeatFlowValue / ReturnMolarFlowValue | Likely (Value members) | **Not yet** — prefer Spec GoalValue first |
| Side-strip ProductFlowRateValue / steam | Likely | **Not yet** — prefer Spec GoalValue first |
| Stream petroleum / ASTM / TBP | On product streams (`BO*` etc.) — **to confirm which are filled** | N/A (monitor) |
| Cut-point specs | Not present as Active on this case | Discover if inactive/available |
| Furnace / overflash | Outside column (`Crude Heater`, `PreFlash`) | Separate ops — Manual for now |

**Policy:** first Category-1 trials should nudge **existing Active specs** (PA duty/rate, SS prod flow, naphtha rate) — not invent new COM writes.

---

## 5. Operability / sentinel findings

Inspect reported `appears_converged=True` but `physical_solution=False` because:

- Condenser duty / OH–btms temperatures came back as sentinel `-32767`
- OH/btms kgmole/h mapping returned `None`

**Interpretation:** 2-product stripper assumptions in `column_api.inspect` do not map cleanly onto a multi-product CDU. Prefer:

- Named product streams (`Naphtha`, `Residue`, …) for T / flow / quality
- Energy streams `Atmos Cond`, `Kero_SS_Energy`, …
- Do **not** declare State E from stripper-style OH/btms alone

---

## 6. Implications for CDU Assist Trial Map

Validated strategy families for **this** case:

| Strategy ID | Live knob examples |
|-------------|-------------------|
| `pa_duty_nudge` | `PA_1_Duty(Pa)`, `PA_2_Duty(Pa)`, `PA_3_Duty(Pa)` |
| `pa_rate_nudge` (alias / same family) | `PA_*_Rate(Pa)` — **one PA, one of rate/duty per trial** |
| `side_draw_rate_nudge` | `Naphtha Prod Rate`, `*_SS Prod Flow` |
| `side_strip_steam_nudge` | Steam feeds +/or `Kero Reb Duty` (confirm which is preferred) |
| `reflux_or_oh_nudge` | Activate/nudge `Reflux Ratio` or `Liquid Flow` only with DOF care |
| `cut_point_nudge` | **Not available yet** on this Active set — probe inactive / Add Spec later |
| `overflash_or_furnace_nudge` | `Crude Heater` / `PreFlash` — Manual map event until mapped |

---

## 7. Next discovery steps

1. Read PA `DrawStage` / `ReturnStage` stage numbers + `HeatFlowValue` / `ReturnMolarFlowValue` units  
2. Read each side stripper steam rate + product stream quality  
3. Probe product streams for ASTM D86 / TBP / cut props (worksheet units)  
4. Enumerate **inactive** Specifications for cut/ASTM types  
5. Fix CDU Connections board: list draws / PAs / strippers instead of OH/btms-only  
6. Optional: re-run `discover_column_deep.py T-100` when convenient (prior run was slow/hung)

---

## 8. Success note

Opening this CDU case **does help** — we now have a live reference column (`T-100`) instead of guessing COM APIs.
