# CDU Engineering Intelligence Package
## Master Architecture and Development Specification
### Version 1.0

## 1. Purpose

This package defines **complementary** engineering intelligence for the
simulation, validation, troubleshooting, convergence, and performance
evaluation of an Atmospheric Crude Distillation Unit (CDU) in Aspen HYSYS.

It is meant to **help and strengthen** CDU Assist (States A–F, FINAL_TARGET
lock, Trial Map, COM safety) and related project docs — not replace them,
not override them, and not fight them.

CDU process knowledge in this folder deepens atmospheric crude reasoning
(assay, flash zone, pumparounds, side draws, cut points). Runtime Assist
rules (locked FINAL_TARGETs, no auto-save `.hsc`, one major family per
trial, Inventory coded truth) remain binding unless explicitly revised in
those Assist docs.

## 2. Complementary Integration Rules

### Relationship (non-negotiable)

| Source | Role |
|--------|------|
| CDU Assist Inventory / coded engine / `docs/` PE workflow | **Active judgment today** (States, FINAL_TARGET, trials, COM safety) |
| This package (`cdu_intel/` Deliverables 1–10) | **Complementary OS** — CDU domain mindset, knowledge, playbooks |
| `new_intelligence/` | Complementary general PE OS — reconcile with this package; no rival brain |
| Both / all together | Same PE direction; clarify and extend — **no competing authorities** |

### Rules

- Do **not** treat this package as superseding Assist Inventory or coded safety rules.
- Do **not** declare older Assist rules inactive.
- Do **not** combine conflicting advice as two competing authorities.
- When texts differ, **reconcile them**; until reconciled, prefer the **more specific validated Assist rule** (especially FINAL_TARGET lock, DOF, no auto-save, one MV family).
- New ideas from this package become active in code only after they are reviewed and fitted next to Inventory v1 — as **additions**, not replacements.

### Helpful source order (guidance, not supremacy)

1. Validated Assist / Inventory rules for this product  
2. This `cdu_intel` package (CDU domain depth)  
3. `new_intelligence/` complementary OS  
4. Project-specific design basis / assay  
5. General PE / distillation knowledge  

The AI shall not treat the CDU as a conventional single-feed, two-product
column. It shall not blindly reuse simple-column convergence recipes; reuse
only after review for CDU application — as **complementary** guidance next
to Assist States A–F.

## 3. CDU Simulation Philosophy

A CDU model is an integrated crude fractionation system, not merely a distillation column. The intelligence shall consider:

- Crude assay and petroleum characterization
- Pseudo-component generation
- Feed blending
- Crude preheat train
- Desalter representation
- Fired heater
- Atmospheric column and flash zone
- Overflash and wash section
- Pumparounds
- Side draws and side strippers
- Stripping steam
- Overhead condenser and accumulator
- Product cut points and qualities
- Pressure profile, hydraulics, heat balance, and convergence sequence

Physical consistency shall take priority over numerical convergence.

## 4. Package Scope

Included in Version 1:

- Steady-state atmospheric CDU simulation
- Crude assay import and pseudo-component generation
- Single and blended crude feeds
- Furnace, atmospheric column, pumparounds, side strippers, and steam
- Naphtha, kerosene, diesel, AGO, and atmospheric residue products
- Product cut-point and quality evaluation
- Energy balance, convergence, troubleshooting, and model validation

Excluded from Version 1:

- Detailed VDU modeling
- FCC or coker fractionators
- Reactive systems
- Dynamic simulation
- Detailed exchanger-network optimization
- Detailed fired-heater combustion
- Mechanical tray design
- Relief-system design
- Refinery LP optimization

## 5. Deliverables

### Deliverable 1 — CDU Engineering Reasoning Specification
Defines CDU-specific observation, validation, diagnosis, convergence, decision, experiment, evaluation, escalation, and learning strategies.

### Deliverable 2 — Crude Assay and Petroleum Characterization Knowledge Base
Covers assay types, TBP/ASTM/SimDist data, light ends, bulk properties, API gravity, molecular weight, sulfur, viscosity, Watson K, pseudo-components, blending, consistency checks, and missing-data handling.

### Deliverable 3 — CDU Process Configuration Knowledge Base
Covers the crude feed system, preheat train, desalter, preflash, fired heater, atmospheric column, flash zone, wash section, pumparounds, side draws, side strippers, overhead system, and residue handling.

### Deliverable 4 — Aspen HYSYS CDU Model-Building Specification
Defines basis setup, oil environment, characterization, property method, feed construction, column configuration, stage numbering, feeds/draws, pumparounds, side strippers, steam, pressure profile, specifications, initialization, solving, and rollback.

### Deliverable 5 — CDU Convergence and Troubleshooting Playbook
Defines simplified startup, progressive complexity activation, specification management, convergence recovery, temperature-profile diagnosis, pressure problems, heat-balance closure, product infeasibility, and last-known-good-case management.

### Deliverable 6 — CDU Product Quality and Cut-Point Intelligence
Defines yield basis, cut points, IBP/FBP, T5/T10/T50/T90/T95, naphtha endpoint, kerosene and diesel quality interfaces, AGO recovery, residue quality, overlap/gap, contamination, and recovery-versus-quality tradeoffs.

### Deliverable 7 — CDU Energy, Pumparound, and Furnace Intelligence
Defines furnace duty, coil-outlet temperature, flash-zone vaporization, pumparound duties and return temperatures, internal reflux, stripping steam, overflash, wash liquid, condenser duty, and heat-recovery reasoning.

### Deliverable 8 — CDU Validation, Testing, and Acceptance Specification
Defines material and heat-balance closure, assay consistency, yield and quality checks, temperature and pressure profile checks, phase checks, steam and furnace checks, hydraulic screening, sensitivity testing, and acceptance criteria.

### Deliverable 9 — CDU Learning and Case-Memory Specification
Defines how crude identity, assay version, model version, convergence path, failed and successful actions, product outcomes, energy outcomes, confidence, and lessons are stored and retrieved.

### Deliverable 10 — CDU Cursor Workspace and Operating Instructions
Defines the workspace structure, master standard, prompts, templates, tests, cases, memory, archive, and version-control rules.

## 6. Recommended Workspace

```text
CDU_Intelligence_Package/
├── 00_MASTER/
│   ├── CDU_MASTER_STANDARD.md
│   ├── CDU_PACKAGE_INDEX.md
│   └── CDU_CHANGELOG.md
├── 01_REASONING/
├── 02_CRUDE_ASSAY/
├── 03_PROCESS_CONFIGURATION/
├── 04_HYSYS_MODEL_BUILDING/
├── 05_CONVERGENCE/
├── 06_PRODUCT_QUALITY/
├── 07_ENERGY_AND_PUMPAROUNDS/
├── 08_VALIDATION/
├── 09_MEMORY/
├── 10_CASES/
├── 11_TEMPLATES/
├── 12_TESTS/
└── 99_ARCHIVE/
```

## 7. CDU Reasoning Hierarchy

1. Identify the simulation objective.
2. Confirm the crude assay and characterization basis.
3. Validate the feed and property method.
4. Validate the process configuration.
5. Confirm stages, feeds, draws, pumparounds, steam, and pressure profile.
6. Confirm degrees of freedom and active specifications.
7. Establish a simplified converged baseline.
8. Add complexity progressively.
9. Evaluate product yield and quality.
10. Evaluate heat balance and internal traffic.
11. Screen hydraulic behavior.
12. Compare against design, assay, or operating data.
13. Save the final case and lessons learned.

## 8. Mandatory CDU Engineering Questions

Before changing the model, determine:

- What crude or crude blend is being processed?
- Is the assay complete and internally consistent?
- How were pseudo-components generated?
- Which property method is being used?
- What are the furnace outlet and flash-zone conditions?
- What is the feed vaporization at the flash zone?
- What is the overflash target?
- What side-draw and product-quality targets apply?
- Which pumparounds and stripping-steam streams are active?
- What specifications are active?
- Is the issue numerical, thermodynamic, structural, process-related, or specification-related?

## 9. Complementary Cursor Prompt (CDU work)

> Use the CDU Engineering Intelligence Package (`cdu_intel/`) as
> **complementary** domain guidance for this task — alongside CDU Assist
> Inventory, States A–F, FINAL_TARGET lock, and Trial Map. Do not treat this
> package as superseding Assist safety rules. Reconcile conflicts in
> discussion; prefer validated Assist rules for FINAL_TARGET, DOF, no
> auto-save, and one family per trial. Treat crude characterization,
> flash-zone behavior, pumparounds, side strippers, stripping steam, product
> cut points, and CDU heat balance as one integrated system. Preserve the
> last known good case (Assist snapshot / engineer Save), explain every
> recommendation, and do not make random or simultaneous uncontrolled
> changes.

## 10. Development Sequence

1. CDU Master Standard
2. CDU Engineering Reasoning Specification
3. Crude Assay and Characterization Knowledge Base
4. CDU Process Configuration Knowledge Base
5. Aspen HYSYS CDU Model-Building Specification
6. CDU Convergence and Troubleshooting Playbook
7. CDU Product Quality and Cut-Point Intelligence
8. CDU Energy and Pumparound Intelligence
9. CDU Validation and Acceptance Specification
10. CDU Memory and Cursor Workspace Specification

## 11. Status

This document establishes the CDU package architecture. The next document is **Deliverable 1 — CDU Engineering Reasoning Specification**.
