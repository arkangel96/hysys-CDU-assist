# CDU PreFlash + Crude Heater Intelligence

Version: 0.1 (Human-in-the-Loop) — propose-only PE Decision Board

## Purpose

This document defines the engineering intelligence for optimizing the
CDU PreFlash Drum and Crude Heater within Aspen HYSYS. It is intended
for a human-supervised engineering copilot.

**Policy:** Complementary to CDU Assist v1 — does **not** supersede Inventory /
`propose_action`. See [`00_COMPLEMENTARY_INTRO.md`](00_COMPLEMENTARY_INTRO.md).

## Integration Decisions (locked 2026-07-24)

### Overflash definition (v0.1)

> **The internal liquid flow descending below the flash zone, expressed as a
> percentage of fresh crude feed.**

- Do **not** hard-code the numerical operating band in code.
- Read project names/limits from case config (`config/cdu_t100_case.json` →
  `upstream_objects.overflash`).
- `band_min` / `band_max` may be `null` until the project sets them.
- Intelligence stays project-independent; only config carries plant numbers.

### Preferred manipulated variable

- **Primary MV:** Crude Heater Duty (`Crude Duty` / heater duty).
- **Secondary MV:** Heater Outlet Temperature (COT) — only when HYSYS
  implementation requires COT instead of duty.
- Objective is energy (heater severity), not “change COT for its own sake.”

### Version strategy

| Version | Mode |
|---------|------|
| **v0.1** | Engineering knowledge + PE Decision Board — **propose only**; PE approval before any write |
| **v0.2** (later) | Study runner (snapshot → bounded step → solve → validate → keep/restore → log) after multi-case validation |

No automatic heater optimization in v0.1.

---

## Optimization Objective

-   Minimize Crude Heater Duty (lowest feasible heater severity).
-   Keep Overflash within the approved operating band (when band configured).
-   Maintain Naphtha and Kerosene recovery.
-   Satisfy hard D86 and flash-point constraints.
-   Maintain CDU convergence.
-   Stay within heater and hydraulic limits.

## Operating Philosophy

Observe → Diagnose → Propose → Human Approval → Execute → Validate

Version 0.1 is recommendation-only. No autonomous optimization.

## PreFlash Philosophy

The PreFlash Drum is treated primarily as **context** for heater and
flash-zone behavior.

Monitor: Pressure, Temperature, Vapor fraction, Vapor flow, Liquid flow,
Composition, Light-end removal, Heater inlet condition.

Primary manipulated variable: **Heater Duty** (COT secondary).

## Validation Gates

### Hard Gates

-   CDU convergence
-   Material balance
-   Energy balance
-   Heater limits
-   Maximum COT
-   Maximum heater duty
-   Product quality
-   Naphtha recovery
-   Kerosene recovery
-   Hydraulic limits
-   Flooding margin
-   Condenser feasibility
-   Pump-around feasibility

### Soft Gates

Monitor only: Separation gap, Internal profiles, Energy distribution

## Decision Priority

1.  Safety
2.  Equipment limits
3.  Product quality
4.  Product recovery
5.  Overflash
6.  Energy minimization

## Rule PFH-001

Trigger: Overflash above target; Quality acceptable; Recovery acceptable

Action: Reduce Heater Duty (or COT if required) by one bounded step.

Validate: Overflash, Recovery, Product quality, Hydraulic loading, CDU convergence

## Rule PFH-002

Trigger: Overflash below target; Recovery below target; Heater within limits

Action: Increase Heater Duty (or COT if required) by one bounded step.

Validate: Overflash, Product recovery, Product quality, Heater limits, Hydraulic loading

## Rule PFH-003

Trigger: Invalid PreFlash pressure; Invalid vapor fraction; Material balance
issue; Abnormal flow

Action: Stop optimization. Report abnormal condition. Require engineer intervention.

## Rule PFH-004

Accept optimization only if: CDU converged; Heater duty improved; Overflash
within target (when band set); Product recovery maintained; Product quality
maintained; Hydraulic limits satisfied

Otherwise restore the previous snapshot.

**v0.1 note:** When overflash band is unset, do **not** claim in/out of band;
propose direction only from available evidence; never auto-execute.

## Workflow

1.  Read HYSYS state.
2.  Validate convergence.
3.  Read PreFlash.
4.  Read Heater.
5.  Diagnose overflash.
6.  Evaluate recovery.
7.  Evaluate quality.
8.  Determine limiting constraint.
9.  Recommend one bounded change.
10. Wait for engineer approval.
11. Execute.
12. Solve HYSYS.
13. Retrieve results.
14. Validate gates.
15. Keep or restore.

## Engineering Principle

Always evaluate the coupled system:

PreFlash → Heater Inlet → Crude Heater → Flash Zone → Overflash →
Product Recovery → Product Quality → CDU Hydraulics

The engineer remains the final authority for all decisions.

## Assist wiring (v0.1)

- Config: `config/cdu_t100_case.json` → `upstream_objects`
- Observe + PE board text: `cdu_preflash_heater.py` (read-only COM; propose-only)
- Inventory: `CDU-PFH-T100` — DOCS + PARTIAL board (not coded auto-MV)
- Runtime brain remains `propose_action` for column Category-1 MVs
