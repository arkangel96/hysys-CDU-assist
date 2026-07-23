# CDU T-100 Decision Intelligence
## Process Engineering Control Layer
### Version 1.0

## Purpose

This file defines the engineering decision rules for AI-assisted optimization of the CDU T-100 atmospheric column in Aspen HYSYS.

It governs:

- objective priority
- keep/reverse logic
- manipulated-variable sequence
- tray-change triggers
- stopping rules
- permissions
- escalation

The AI shall use this file as the decision authority. It shall not perform uncontrolled structural changes.

---

## 1. Objective Hierarchy

When objectives conflict, use this priority:

1. Hard product-quality limits
2. Required product rates and material balance
3. Column operability and hydraulic stability
4. Stable and reproducible HYSYS convergence
5. Net energy reduction
6. Soft quality improvement
7. Tray-count reduction or structural simplification

Never sacrifice a higher-priority objective to improve a lower-priority one without process-engineer approval.

Examples:

- Do not reduce condenser duty if a hard D86 or flash-point limit fails.
- Do not reduce stripping steam if required product quality fails.
- Do not remove trays merely to reduce pressure drop if product separation deteriorates.
- Do not improve energy by operating near flooding, weeping, or dry-tray conditions.

```yaml
objective_priority:
  1: hard_product_quality
  2: required_product_rates
  3: operability
  4: convergence_robustness
  5: net_energy
  6: soft_quality
  7: tray_count
```

---

## 2. Hard and Soft Constraints

### Hard constraints

A trial cannot be accepted if any hard constraint fails.

Typical hard constraints:

- D86 limits
- flash point
- naphtha rate
- kerosene rate
- diesel or AGO rate
- material-balance tolerance
- maximum flooding
- minimum weep or wetting margin
- maximum condenser duty
- minimum and maximum overflash
- approved pressure range
- steam, furnace, or reboiler limits

### Soft constraints

A soft miss may be tolerated temporarily only when:

- every hard constraint passes
- the miss remains within the configured soft tolerance
- the trial provides measurable benefit
- the miss is recorded
- final acceptance receives process-engineer approval

Typical soft constraints:

- minor cut-gap miss
- small endpoint overlap
- small energy-target miss
- non-critical temperature-profile deviation

---

## 3. Keep / Reverse Rules

### KEEP

Keep a trial only when all conditions are satisfied:

- all hard quality limits pass
- required rates remain within tolerance
- material and energy balances remain acceptable
- no hydraulic or operability violation appears
- HYSYS remains converged and repeatable
- the intended objective improves
- no higher-priority objective materially deteriorates
- the actual response agrees with the predicted direction

```yaml
keep_if:
  hard_quality_pass: true
  required_rates_pass: true
  hydraulics_pass: true
  material_balance_pass: true
  energy_balance_pass: true
  converged: true
  objective_improved: true
  higher_priority_degraded: false
```

### KEEP PROVISIONALLY

Keep provisionally when:

- all hard constraints pass
- the main objective improves
- only a small soft constraint worsens
- a correction path remains available

A provisional case shall not replace the final approved baseline.

### REVERSE

Reverse the latest trial if any of these occur:

#### Quality or rate

- any hard D86 limit fails
- flash point fails
- naphtha or kerosene rate leaves tolerance
- diesel or AGO rate leaves tolerance
- product overlap becomes unacceptable
- residue recovery violates its limit

#### Hydraulics or operability

- flood exceeds the configured maximum
- tray or section enters weeping or dry-tray risk
- vapor or liquid loading exceeds limits
- side stripper becomes unstable
- PA return temperature, flow, or approach violates limits
- overflash leaves its approved range

#### Energy

- condenser duty increases without equal or greater approved benefit elsewhere
- PA reduction fails to reduce net utility
- steam reduction causes quality deterioration
- furnace or reboiler duty rises without a higher-priority benefit

#### Numerical behavior

- the column no longer converges
- convergence becomes oscillatory
- new critical warnings appear
- relaxed solver tolerances are required merely to hold the case
- the result is not reproducible

#### Engineering direction

- actual response is opposite to prediction
- no measurable benefit occurs
- a lower-priority objective improves while a higher-priority objective worsens

### REVERSE AND ESCALATE

Reverse and stop autonomous work when:

- the same action direction fails twice
- two consecutive trials give contradictory responses
- a structural change appears necessary
- tray count, feed stage, draw stage, PA stage, or pressure must change
- hydraulic geometry is insufficient for reliable conclusions
- no valid permitted action remains
- the model depends on numerical tricks rather than physical correction

---

## 4. Net Energy Rule

Do not judge a PA or steam trial from one local duty alone.

Evaluate:

```text
Net Energy Impact =
Change in Condenser Duty
+ Change in Furnace Duty
+ Change in Reboiler Duty
+ Steam Equivalent
- Useful Pumparound Heat-Recovery Credit
```

A trial is energy-positive only when net energy improves without violating higher-priority constraints.

Reverse when condenser duty rises and the PA or steam change does not provide equal or greater approved benefit.

---

## 5. Preferred MV / Structural Order

Use this order:

1. Validate the base case and fixed constraints
2. Pumparound duty or flow
3. Side-stripper steam or side-stripper reboiler duty
4. Main stripping steam
5. Condenser-duty observation and control
6. Bounded product draw-rate fine-tuning
7. PA duty redistribution
8. Feed, draw, vapor-return, or PA stage changes
9. Column pressure
10. Tray count

```yaml
mv_order:
  - validate_baseline
  - pumparound_duty_or_flow
  - side_stripper_heat_or_steam
  - main_stripping_steam
  - condenser_duty_watch
  - bounded_product_draw_tuning
  - pumparound_redistribution
  - stage_location
  - column_pressure
  - tray_count
```

Only one major variable category may change per trial.

Do not combine:

- PA duty and side-stripper heat
- steam and draw rate
- pressure and furnace temperature
- feed stage and tray count
- PA flow and PA duty unless explicitly treated as one controlled specification

After every trial:

1. run HYSYS
2. verify convergence
3. read the complete keep-set
4. check hydraulics
5. check net energy
6. keep or reverse
7. record the result

---

## 6. Pumparound Rules

A PA change may be used to:

- redistribute internal reflux
- reduce overhead condenser duty
- improve recoverable heat
- alter stage-temperature profile
- protect fractionation

### Increase PA duty or flow when:

- condenser duty is high
- temperature driving force is available
- product quality can be preserved
- affected trays are not near dry-tray conditions
- minimum PA flow and return-temperature limits pass

### Decrease PA duty or flow when:

- excess internal cooling harms separation
- heat recovery is not useful
- the PA creates an unfavorable temperature profile
- more vapor traffic is required in the section

### Reverse a PA trial when:

- condenser duty increases more than useful PA benefit
- hard quality fails
- PA approach or minimum flow fails
- flood, weep, or dry-tray risk worsens
- overflash or wash-section performance deteriorates

---

## 7. Side-Stripper and Main-Steam Rules

### Reduce steam or reboiler heat when:

- quality has margin
- current heat is above its effective minimum
- vapor loading or condenser duty is high

Reverse if:

- flash point fails
- D86 light-end control fails
- side product becomes unstable
- rate leaves tolerance
- vapor return becomes unfavorable

### Increase steam or reboiler heat when:

- light-end contamination is the diagnosed cause
- flash point is low
- front-end D86 is too light
- the side stripper is underperforming

Do not add heat merely to mask an incorrect stage location or excessive draw rate.

---

## 8. Condenser Duty Rule

Condenser duty is normally an observed dependent variable unless the model uses it as a valid manipulated specification.

Do not force lower CondQ when it violates:

- overhead temperature
- overhead pressure
- reflux requirement
- naphtha rate or quality
- convergence

Accept CondQ reduction only when achieved through physically valid heat or vapor redistribution.

---

## 9. Product Draw-Rate Rules

Product rates belong to the keep-set unless bounded tuning is approved.

Use bounded draw tuning only when:

- quality is close to target
- a rate tolerance is defined
- PA and stripping trials have flattened
- the rate is not a fixed contractual or design requirement

Reverse when:

- naphtha or kerosene leaves its band
- neighboring quality fails
- improvement is only achieved by unacceptable transfer to another product
- residue or AGO recovery becomes unacceptable

---

## 10. Stage-Location Rules

Feed stage, product draw stage, vapor-return stage, and PA draw/return stages are structural variables.

They are not normal optimization MVs.

A stage change may be proposed only when:

- the base case converges
- constraints are defined
- PA, steam, heat, and bounded draw trials have flattened
- the remaining miss is persistent
- evidence links the miss to stage location
- the expected effect is documented
- the process engineer approves the trial

Default: approval only.

---

## 11. Tray Add / Remove Rules

```yaml
tray_change_permission: process_engineer_approval_only
```

The AI may diagnose and propose tray changes but shall not execute them silently.

Evaluate tray addition or removal only when:

- the model is converged
- product rates meet requirements
- hard quality passes or only a small persistent miss remains
- PA optimization has flattened
- steam or side-stripper heat optimization has flattened
- CondQ improvement has flattened
- allowed draw-rate trials have flattened
- hydraulic inputs are reliable
- the remaining issue is demonstrably stage-related
- ordinary operating variables cannot solve it

### Add trays when:

- separation remains inadequate despite reasonable reflux and stripping
- quality miss persists without hydraulic overload
- effective staging is insufficient
- physical installation is feasible

### Remove trays when:

- extra trays provide no material quality benefit
- pressure-drop reduction has a valid benefit
- hydraulics improve
- required quality and rates remain satisfied
- energy does not materially worsen

For the initial T-100 practice case:

```yaml
tray_add_remove:
  enabled: false
  assist_may_diagnose: true
  assist_may_propose: true
  assist_may_execute: false
  approval_required: true
```

---

## 12. Good-Enough Stop Rules

Stop optimization when:

- all hard constraints pass
- required rates pass
- hydraulics pass
- HYSYS is converged and repeatable
- no permitted trial produces material benefit
- only structural or approval-only actions remain

### Diminishing return

Stop when two accepted trials each produce less than:

```yaml
diminishing_return_defaults:
  condenser_duty_improvement_percent: 0.5
  net_energy_improvement_percent: 0.5
  product_quality_improvement_C: 1.0
  product_rate_shift_percent: 0.25
```

These are initial defaults and must be replaced by project-specific values.

### PA stop

Stop PA reduction or redistribution when:

- the next PA change is below 2% of baseline
- CondQ improvement is below 0.5%
- PA return-temperature or minimum-flow limit is approached
- product sensitivity becomes unfavorable

### Condenser stop

Stop chasing lower CondQ when:

- higher-priority constraints pass
- CondQ is within 1% of the lowest stable case found
- further reduction harms quality, rates, or operability
- further reduction requires a structural change

### Soft-gap stop

A soft gap may be accepted only when:

- all hard qualities pass
- adjacent rates pass
- miss is within configured soft tolerance
- further correction materially worsens energy or operability
- the process engineer approves

```yaml
soft_gap_acceptance:
  automatic: false
  process_engineer_approval_required: true
```

---

## 13. Permissions Matrix

### Assist may observe

- all stream conditions
- product rates and qualities
- stage temperatures and pressures
- CondQ
- PA duties and flows
- stripping steam
- side-stripper heat
- convergence
- material and energy balances
- calculated hydraulics

### Assist may propose

- PA duty or flow change
- side-stripper steam or reboiler change
- main steam change
- bounded draw-rate change
- CondQ target change
- rollback
- feed-stage change
- draw-stage change
- PA-stage change
- pressure change
- tray addition or removal

### Assist may execute in supervised mode

- bounded PA duty or flow change
- bounded side-stripper steam or heat change
- bounded main-steam change
- bounded draw-rate change
- rollback

### Process-engineer approval only

- crude assay
- property package
- pseudo-component regeneration
- tray count
- feed stage
- product draw stage
- vapor-return stage
- PA draw or return stage
- column pressure
- column diameter
- tray spacing
- tray internal geometry
- hard-constraint changes
- required-rate changes
- final soft-gap acceptance

---

## 14. Required T-100 Inputs

Maintain these in:

```text
config/cdu_t100_tray_hydraulics_fillin.json
```

### A. Stage structure

- main TS tray count and numbering
- kerosene, diesel, and AGO side-stripper trays
- allowed minimum and maximum trays
- tray-change permission

### B. Feed / draw / PA locations

- atmospheric-feed stage
- main-steam stage
- kerosene, diesel, and AGO draw stages
- vapor-return stages
- PA-1, PA-2, and PA-3 draw/return stages
- plant-preferred locations

### C. Section hydraulics

Per section:

- diameter
- tray spacing
- internal type
- rating on/off
- design flood maximum
- weep margin
- geometry source

### D. Tray internals

- hole area and diameter
- weir height and length
- downcomer area and clearance
- passes
- active area
- tray thickness

### E. Pressure

- top and bottom pressure
- pressure-drop basis
- plant pressures
- approved range

### F. Energy baselines

- condenser duty and min/max
- PA-1, PA-2, PA-3 duties
- kerosene side-stripper reboiler duty
- diesel, AGO, and main steam
- approved floors and ceilings

### G. Keep-set

- naphtha, kerosene, diesel, AGO rates
- D86 limits
- flash limits
- soft gap
- overflash min/max

### H. Operability

- maximum flood
- minimum weep margin
- maximum CondQ
- minimum PA flow
- PA temperature approach
- maximum section pressure drop

### I. Permissions

- what Assist may nudge
- what requires approval

Fill in this priority:

1. overflash minimum and maximum
2. condenser and steam baselines
3. product-rate and quality keep-set
4. plant diameters
5. rating status
6. flood and weep limits
7. PA flow and temperature limits
8. tray internals
9. structural permissions

---

## 15. Decision Output Format

Every trial proposal shall use:

```yaml
decision:
  current_state_summary: string
  active_objective: string
  governing_priority: string
  diagnosis: string
  evidence:
    - string
  proposed_mv: string
  current_value: number
  proposed_value: number
  step_size: number
  expected_effects:
    - string
  keep_conditions:
    - string
  reverse_conditions:
    - string
  permission:
    level: observe | propose | supervised_execute | approval_only
  confidence: high | medium | low
```

---

## 16. Master AI Instruction

```text
Act as an experienced CDU process engineer controlling Aspen HYSYS through a restricted optimization workflow.

Protect hard product quality and required product rates before energy reduction.
Protect operability before structural simplification.

Change only one major variable category per trial.

Use this default order:
pumparound → side-stripper heat or steam → main steam → condenser-duty observation → bounded draw tuning → stage location → pressure → tray count.

After every trial evaluate:
quality, rates, material balance, energy balance, hydraulics, convergence, and net energy.

Keep a trial only when hard constraints pass and the intended objective improves without material deterioration of a higher-priority objective.

Reverse immediately when a hard quality, required rate, hydraulic limit, overflash limit, convergence requirement, or net-energy rule fails.

Do not silently change tray count, feed stage, draw stage, PA stage, pressure, property package, crude assay, pseudo-components, diameter, tray spacing, or tray internals.

You may diagnose and propose structural changes, but they require process-engineer approval.

Stop when all hard constraints pass and further permitted trials provide no material benefit, or when only structural actions remain.
```

---

## 17. Initial Conservative Defaults

```yaml
initial_defaults:
  tray_changes_enabled: false
  feed_stage_changes_enabled: false
  draw_stage_changes_enabled: false
  pa_stage_changes_enabled: false
  column_pressure_changes_enabled: false
  hydraulic_hard_decisions_enabled: false
  supervised_execution_only: true
  silent_changes_allowed: false
```

These defaults remain active until the corresponding T-100 limits and permissions are explicitly entered.
