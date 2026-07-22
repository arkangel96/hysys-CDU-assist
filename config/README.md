# T-100 case configuration (Phase 2 + build-up)

Edit **`cdu_t100_case.json`** to teach CDU Assist about your HYSYS case.  
FINAL_TARGETs: **`cdu_final_targets.json`** (copy from example if missing).  
Strategy: [`docs/INTELLIGENCE_BUILDUP_STRATEGY.md`](../docs/INTELLIGENCE_BUILDUP_STRATEGY.md).

## Quick start (3 steps)

1. Open the file in any text editor (Notepad is fine).
2. Set **`target_value`** for products you care about (trial baseline diesel D86 95% = `360` °C — replace with plant).
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

## Properties not readable yet

`D86_95`, `flash_point` show as **not_configured** until we add the HYSYS COM read path.
Set targets anyway — when reads work, evaluation turns on automatically.

See also: `docs/CDU_PE_INTELLIGENCE_REQUIREMENTS.md`
