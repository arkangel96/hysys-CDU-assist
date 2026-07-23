# T-100 case configuration (Phase 2 + build-up)

Edit **`cdu_t100_case.json`** to teach CDU Assist about your HYSYS case.  
FINAL_TARGETs: **`cdu_final_targets.json`** (copy from example if missing).  
Strategy: [`docs/INTELLIGENCE_BUILDUP_STRATEGY.md`](../docs/INTELLIGENCE_BUILDUP_STRATEGY.md).

## Units (binding)

**Use whatever HYSYS shows for the open case. Do not convert in Assist.**

- Targets and PE board numbers are in the case **display unit set** (this T-100 practice case: Field — **F**, USGPM, Btu/hr, …).
- Assist does **not** change the case to metric, and does **not** apply hand °C↔°F factors.
- When COM returns calculation-unit values, HYSYS converts via `GetValue(display)` / `FromCalculationUnit` so the number matches the worksheet / Boiling Point Curves table.

Set `unit` on each quality target to the HYSYS label (e.g. `"F"`), matching what you see in the UI.

## Quick start (3 steps)

1. Open the file in any text editor (Notepad is fine).
2. Set **`target_value`** for products you care about in **HYSYS display units** (practice: diesel D86 95% ≤ `680` **F**).
3. Save and restart CDU Assist (or click Refresh in PE Intelligence).

## Fields

| Field | Meaning |
|-------|---------|
| `objective` | Why you are tuning (shown on PE board) |
| `quality_targets` | Product, stream name, property, target |
| `spec_roles` | Which HYSYS specs are solver handles vs monitors |
| `mv_preference` | Knob order when a symptom is detected |
| `interactive_only` | `true` = Assist Loop one trial then stop (PE approves) |
| `primary_symptom_tree` | First hardened tree id (default `diesel_too_heavy`) |

## Stream names (from your T-100 discovery)

Products: `Naphtha`, `Kerosene`, `Diesel`, `AGO`, `Residue`, `Off Gas`

Side-draw specs: `Diesel_SS Prod Flow`, `Kero_SS Prod Flow`, `PA_2_Duty(Pa)`, etc.

## Quality reads

`D86_95` / `flash_point` are read from stream **Boiling Point Curves** / **Cold Properties** in display units. Gap = Diesel D86 5% − Kero D86 95%.

See also: `docs/CDU_PE_INTELLIGENCE_REQUIREMENTS.md`, `hysys_units.py`
