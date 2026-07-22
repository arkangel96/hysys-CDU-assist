# Intelligence Improvement Notes — Simple Column Assist v1

**Document type:** Expert review notes + living backlog / commentary  
**Status:** Superseded as *coded checklist* by [`INTELLIGENCE_INVENTORY_V1.md`](INTELLIGENCE_INVENTORY_V1.md) (2026-07-22)  
**Scope:** Simple distillation / stripping only — see [`SCOPE_SIMPLE_COLUMN_ASSIST.md`](SCOPE_SIMPLE_COLUMN_ASSIST.md)  
**Canonical home of rules:** [`expert_decision_workflow.md`](expert_decision_workflow.md) **§28**  
**Operational slice:** [`column_convergence_playbook.md`](column_convergence_playbook.md)  
**Coded vs paper truth:** [`INTELLIGENCE_INVENTORY_V1.md`](INTELLIGENCE_INVENTORY_V1.md)

**Date:** 2026-07-21 (narrative) · inventory sync 2026-07-22  
**Author perspective:** Senior process / HYSYS simulation engineer review of Simple Column Assist

> **Use the inventory file** to see what is CODED / PARTIAL / DOCS / PLANNED.  
> This note keeps the original gap narrative for context. Sections 3–4 below are partly historical — several “gaps” are now coded (see inventory §4–§5).

---

## 1. Purpose of this note

Capture an honest assessment of the **decision intelligence** of Simple Column Assist, and the improvements required before it can behave like a high-level simulation process engineer.

**Integration status:** Content below is mirrored into:

- `expert_decision_workflow.md` §28 (implementation guidance, P0–P3, State E definition, anti-complexity)
- `column_convergence_playbook.md` principles P11–P14, gap list, §18 intelligence layers
- **`INTELLIGENCE_INVENTORY_V1.md`** — current coded/paper snapshot (preferred before adding new intelligence)

This file remains the **detailed backlog / commentary**. Prefer editing the inventory + §28 when changing status or policy.

---

## 2. Overall verdict

| Dimension | Assessment |
|-----------|------------|
| Ability to touch HYSYS (COM read/write) | Strong for v0.1 |
| Simulation PE judgment / intelligence | Early / incomplete |
| Ready to replace a senior PE | **No** |
| Ready to assist a senior PE (interactive) | **Yes**, if product specs stay locked and trials pause for review |

**Bottom line:** Improve the intelligence substantially — not by more random Active flips or GoalValue spam, but by encoding **state classification, protected product targets, physical realism checks, and stop-when-going-nowhere logic**.

The COM bridge is the foundation. The expert part still has to be **built into the decision engine** from the expert workflow — **in layers** (see §5 / workflow §28.2).

---

## 3. What is already good

| Strength | Why it matters |
|----------|----------------|
| COM read/write of Specs (`GoalValue`, `IsActive`) | Real automation surface — same knobs a PE uses |
| Snapshot / restore | Safe experiments; enables keep/reverse |
| Bounded one-change trials | Correct PE discipline (one family per trial) |
| Expert workflow markdown (States A–F, FINAL_TARGET concept) | Right philosophy on paper |
| Live lesson: Active swap for State B recovery | Proves the path works when a PE chooses it |
| Trial Map trail | Memory of what was tried |

These are a solid **prototype foundation**, not finished intelligence.

---

## 4. Gaps — where Assist is still “junior”

### 4.1 Does not classify the problem like a PE

A senior PE first asks: **State A / B / C / D / E / F?**

Today Assist mostly defaults to “nudge a GoalValue.”

Example failure mode: **dead bottoms / duties = -32767** should force **numerical recovery (State B)**, not purity or RR chasing as if the column were healthy.

**Improvement:** Implement explicit state classification before any targeting move. → **P0**

---

### 4.2 Confuses HYSYS active specs with plant product targets

Earlier stress-test path almost “succeeded” by relaxing NH₃ GoalValue — **wrong for plant logic**.

Senior rule:

```text
FINAL_TARGET (e.g. bottoms NH3)  → locked unless user explicitly allows
Category-1 MVs (RR, duty, rates) → preferred experiments
Temporary baseline specs         → allowed for State B recovery (with audit)
```

**Improvement:** External target layer separate from HYSYS `IsActive` / `GoalValue` drivers. → **P0**

---

### 4.3 Units and truth sources are weak

Example: Ovhd Vap Rate shown as **~4.64** (COM internal) vs **~16,707 kgmole/h** (worksheet). Same flow — different units.

Also: NH₃ **spec CurrentValue** can disagree with **bottoms stream** mass fraction.

**Improvement:** Always present worksheet units; for product purity prefer stream (+ balances). → **P0**

---

### 4.4 Weak thinking after each trial

Senior loop after every solve:

```text
What improved? What worsened?
Did the dominant error shift?
Is the solution physical (duties, bottoms flow, T profile)?
Continue same MV / reverse / switch family / stop / infeasible?
```

Today: score up/down → keep/reverse. Too thin.

**Improvement:** Response classes + PE narrative after each iteration. → **P0**

---

### 4.5 Spec Active selection is not policy-driven

The program **can** flip `IsActive` (`set_spec_active`, `swap_active_spec`).

Assist Loop does **not** yet own **when** to use baseline pairs, monitor-only FINAL_TARGET, 1-for-1 swaps, or continuation back to the final Active pair.

Live recovery that swapped NH₃ → Ovhd was **PE/chat decision + script execution**, not Assist Loop autonomy.

**Improvement:** Spec-role engine with permission gates. → **P1**

---

### 4.6 Material-balance / operability checks missing

A case can be “converged” with NH₃ under target and still be **rejected in design review** if bottoms flow is essentially zero or duties/split are absurd.

**Improvement:** Operability gates before declaring State E. → **P1**

---

### 4.7 No strong “going nowhere” detector

Example: RR increased with **flat** NH₃ response → stop that family; escalate or report State F.

**Improvement:** Track local sensitivity; switch or stop with reason. → **P2**

---

### 4.8 Interactive PE mode is not first-class

User preference: **one trial → see board → judge → approve next**.

Assist Loop still leans toward batch auto-clicking.

**Improvement:** Default interactive mode; batch Assist only when explicitly allowed. → **P1**

---

## 5. Anti-complexity + priority roadmap

Full intelligence in MD; thin executable layers:

```text
Layer 1 (now):     Read + one MV + keep/reverse + YOU judge
Layer 2 (next):    States A–F + locked FINAL_TARGET + units/stream checks
Layer 3 (later):   Spec-role swaps, sensitivity, State F reporting
Layer 4 (much later): Structural moves, 2×2 matrices, hydraulics
```

| Priority | Upgrade | PE intent |
|----------|---------|-----------|
| **P0** | States A–F classification before moves | Don’t solve the wrong problem |
| **P0** | External FINAL_TARGET layer (locked product specs) | Don’t cheat purity to go green |
| **P0** | Worksheet units + stream product checks | Trust what HYSYS UI shows |
| **P0** | Response classes after every trial | Continue / reverse / switch / State F |
| **P1** | Spec-role engine (baseline vs final Active set) | Controlled Active selection |
| **P1** | Operability gates (bottoms flow, duties, T profile) | Reject “fake green” |
| **P1** | Interactive PE judgment board in GUI | User stays in the loop |
| **P2** | Local sensitivity / bracketing / continuation | Fewer blind steps |
| **P2** | Failure-region memory | Don’t re-enter same failed band |
| **P3** | Structural escalation (feed stage, stages, pressure) | Only with evidence + permission |

---

## 6. What “better intelligence” is *not*

- More aggressive GoalValue spam  
- Auto-relaxing product specs to force convergence  
- Changing many Actives without DOF and role rules  
- Declaring success on residuals alone while bottoms/duties are nonphysical  
- Silent batch loops without PE-readable reasons  

---

## 7. Recommended definition of success (future Assist)

Assist may claim **State E (acceptable)** only when **all** are true:

1. HYSYS numerically healthy (no sentinel duties/flows on key products)  
2. Every hard **FINAL_TARGET** met on the **product stream** (within tolerance)  
3. Preferred or approved Active spec set is consistent and DOF = 0  
4. Material split and duties are within configured engineering bounds  
5. Temperature (and pressure) profiles pass basic physical checks  
6. Audit trail explains each Active/Goal change and why  

Otherwise: report **State B / C / D / F** with evidence — not a fake win.

---

## 8. Link to live SW Stripper lesson (context)

| Lesson | Implication for intelligence |
|--------|------------------------------|
| RR recovery helped energy path | Category-1 MV logic is valid |
| NH₃ GoalValue relax is not plant-OK | FINAL_TARGET lock is mandatory |
| Estimates / Active swap recovered State B | Spec-role + recovery hierarchy needed in engine |
| Units mismatch (Ovhd 4.64 vs 16707) | Display/compare in worksheet units |
| Tiny bottoms flow after “success” | Operability gate required |
| Assist didn’t choose Active swap alone | Decision engine still behind COM capability |
| Connections Full Reflux + Ovhd Active | READ connections into PE board (coded 2026-07-21) |
| Monitor Ovhd kgmole/h vs COM SI | Specs table shows worksheet-style rate units |

---

## 9. Maintenance

When closing a backlog item:

1. Update checklist in playbook gap list  
2. Update workflow §28 if policy changes  
3. Tick or annotate the matching subsection here  
4. Implement only the next **layer** — do not jump to Layer 4 without Layer 2  

---

*Integrated into workflow v0.1.1 / playbook v0.1.1 — living backlog*
