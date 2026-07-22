# Deliverable 2 -- Engineering Knowledge Base (EKB)

## Version 1.1 — Atmospheric CDU

### Scope

This document defines the engineering knowledge required by an AI
assistant supporting **CDU / atmospheric crude distillation columns in
Aspen HYSYS**. It focuses on domain knowledge rather than reasoning
strategy.

**Legacy note:** Earlier v1.0 content targeted simple 2-product
distillation. That framing is retired here.

---

# 1. Atmospheric CDU Fundamentals

## Objective

Fractionate crude oil into a **multi-product slate** (typically OVHD /
naphtha, kerosene, diesel/LGO, AGO/HVGO side draw if present, and
atmospheric residue) while meeting **cut / ASTM / TBP / property**
targets with stable vapor-liquid traffic, operable pumparounds, and
acceptable furnace / condenser energy.

Key concepts:

- Crude assay / oil characterization / hypocomponents (not pure
  components)
- Flash zone / overflash
- Side draws and (where used) side strippers
- Pumparounds (heat removal + internal reflux shaping)
- Cut points, gaps / overlaps, ASTM D86 / TBP
- Stripping steam (main column and/or side strippers)
- Material balance across **all** products + residue
- Energy balance: furnace / flash + PAs + condenser + reboiler/steam

---

# 2. Core HYSYS Objects (CDU)

The AI shall understand:

- Material / Energy streams
- Oil Manager / Assay / Blend / hypocomponent set
- Atmospheric Column (or Column SubFlowsheet)
- Condenser (Partial / Total / Full Reflux as configured)
- Furnace / feed heater / flash zone context
- Side-draw product streams
- Pumparound circuits (duty, circulation, return T)
- Side strippers + stripping steam (if present)
- Column design specs (rate, cut point, gap, draw, PA, cold props, …)
- Spreadsheet / Adjust (use carefully; prefer transparent specs)

---

# 3. Critical Engineering Variables

| Variable | Primary effect | Secondary effect |
|----------|----------------|------------------|
| Top reflux / OVHD rate | Light-end split, OVHD quality | Condenser duty, top traffic |
| Side-draw rates | Product yields / cut location | Neighboring product contamination |
| Pumparound duty / circ / return T | Internal reflux & section traffic | Separation sharpness, condenser load |
| Stripping steam rates | Residue / draw stripping | Condenser water / energy |
| Flash-zone / furnace duty (context) | Overflash, vaporization | Flooding, residual quality |
| Column pressure profile | Relative volatility, utility T | Condenser / PA temperatures |
| Feed stage / draw stage / PA stage | Profile shape | Remixing, energy |
| Number of stages (structural) | Separation capacity | Capital / convergence difficulty |
| Locked product FINAL_TARGETs | Plant quality intent | Must not be auto-relaxed |

---

# 4. Engineering Relationships

## Side draws

- Increasing a draw rate moves more mass into that product and usually
  **shifts the cut** (heavier or lighter contamination depending on
  location and traffic).
- Draw changes without PA / reflux compensation often break neighboring
  ASTM specs (gap collapse or overlap).

## Pumparounds

- PA duty removes heat mid-column → increases liquid reflux below the
  PA → sharpens separation in that section; too much PA can starve
  vapor / flood return hydraulics.
- Prefer diagnosing **section traffic** (T profile, draw T, PA ΔT)
  before chasing a single purity knob.

## Overflash / flash zone

- Insufficient overflash → poor fractionation above flash, dirty
  residue / AGO; excessive overflash → energy waste and flooding risk.
- Treat furnace / feed vaporization as **context** (often user-owned)
  unless Assist has an approved MV.

## Top energy vs mid-column energy

- Top reflux alone cannot fix a mid-cut problem caused by wrong PA or
  draw. Do **not** default to “always increase RR.”

## Pressure

- Higher pressure generally reduces relative volatility and shifts
  utility temperatures; change only with PE approval.

---

# 5. Common Performance Indicators (CDU)

Monitor:

- Solver convergence + HYSYS Messages / popups
- **Each product** ASTM D86 / TBP / cut / gap / cold properties as
  specified
- Product yields vs material balance (feed ≈ Σ products + losses)
- Temperature profile (esp. draw trays, flash zone, PA returns)
- PA duties, circulation, return temperatures
- Condenser / furnace / steam duties
- Hydraulic indicators (flooding, ΔP) when available
- Degrees of freedom and Active vs Estimate specs

---

# 6. Typical Failure Modes

**Numerical**

- Bad estimates / dry sections / wild duties
- Overspecification (DOF < 0) or underspecification (DOF > 0)
- Extreme GoalValues (draw > available traffic)

**Process / CDU**

- Wrong draw rates (yield vs quality fight)
- Insufficient or excessive PA duty
- Overflash too low / too high
- Neighboring cuts overlapping (gap negative)
- Locked FINAL_TARGET conflict with Active GoalValue set
- Steam too low → wet / off-spec residue or stripper products

**Thermodynamic**

- Poor assay / characterization
- Unsuitable property package for petroleum

**Hydraulic**

- Flooding in PA or packed/tray sections
- Excessive pressure drop

---

# 7. Variable Priority (CDU)

Preferred adjustment order:

1. Initialization / Estimates / Active↔Estimate consistency (numerical)
2. Operating MVs: draw rates, PA duty/circ, top reflux/OVHD (one family)
3. Steam rates (if operable and not locked)
4. Review FINAL_TARGET set (monitor / locked — no auto-relax)
5. Feed / draw / PA stage (approval-only structural)
6. Stage count / pressure / property package (escalate)

---

# 8. Engineering Constraints

Never violate:

- Physical feasibility (nonphysical T, P, duties, dry impossible draws)
- Locked plant FINAL_TARGETs
- Equipment / hydraulic limits
- Safety constraints
- One major MV family per Assist trial

---

# 9. Knowledge Gaps

When confidence is low, the AI should:

- Explain uncertainty
- Request assay / target sheet / which product is governing
- Avoid unsupported recommendations
- Escalate structural or characterization changes

---

# Machine Summary

```yaml
domain:
  cdu_atmospheric

objects:
  - streams
  - oil_assay_hypocomponents
  - atmospheric_column
  - condenser
  - furnace_flash_zone
  - side_draws
  - pumparounds
  - side_strippers
  - stripping_steam
  - design_specs

primary_variables:
  - top_reflux_or_ovhd_rate
  - side_draw_rates
  - pumparound_duty_circ_return_t
  - stripping_steam
  - flash_overflash_context
  - pressure_profile
  - feed_draw_pa_stages
  - stage_count

performance_metrics:
  - astm_tbp_cut_gap
  - product_yields
  - energy_pa_condenser_furnace
  - hydraulics
  - convergence
  - multi_product_final_targets
```
