# Intelligence Improvement Notes — CDU Assist v1

**Document type:** Expert review notes + living backlog / commentary  
**Status:** Superseded as *coded checklist* by [`INTELLIGENCE_INVENTORY_V1.md`](INTELLIGENCE_INVENTORY_V1.md) (2026-07-22)  
**Scope:** CDU / atmospheric crude distillation — see [`SCOPE_CDU_ASSIST.md`](SCOPE_CDU_ASSIST.md)  
**Canonical home of rules:** [`expert_decision_workflow.md`](expert_decision_workflow.md) **§28**  
**Operational slice:** [`column_convergence_playbook.md`](column_convergence_playbook.md)  
**Coded vs paper truth:** [`INTELLIGENCE_INVENTORY_V1.md`](INTELLIGENCE_INVENTORY_V1.md)

**Date:** 2026-07-21 (narrative) · inventory sync 2026-07-22 · **CDU intelligence retarget 2026-07-22**  
**Author perspective:** Senior process / HYSYS simulation engineer review of CDU Assist

> **Use the inventory file** to see what is CODED / PARTIAL / DOCS / PLANNED.  
> This note keeps the original gap narrative for context. Sections 3–4 below are partly historical — several “gaps” are now coded (see inventory §4–§5).  
> **CDU docs v1.1** (`new_intelligence/` D1–D5, MV map, Add Spec when-to-add) define the target PE brain; code still largely carries the stripper shell.

---

## 0. CDU intelligence backlog (2026-07-22)

| Priority | Gap | Owner |
|----------|-----|-------|
| P0 | Multi-product FINAL_TARGET table (ASTM/cut/gap) replace NH₃ default | **DONE** config 2026-07-23 — COM read still open |
| P0 | Side-draw + PA + steam strategy IDs in chooser | MV map → `column_engine` |
| P0 | Quality-first keep/reverse + interactive Assist | **DONE** 2026-07-23 — `INTELLIGENCE_BUILDUP_STRATEGY.md` |
| P1 | State E = all governing products + PA operability | workflow §28.5 |
| P1 | Live D86 / flash COM for diesel_too_heavy tree | `cdu_quality_engine` |
| P1 | CDU when-to-add in `column_spec_catalog` (code) | Add Spec catalog |
| P2 | Atmospheric reference-case validation protocol | CASE §3.1 |
| P3 | Learning schema fields (assay, slate, PA config) | `new_intelligence` D4 |

**Do not:** GoalValue spam, auto-relax FINAL_TARGETs, auto Specs.Add, silent structural writes.

## 1. Purpose of this note

Capture an honest assessment of the **decision intelligence** of CDU Assist, and the improvements required before it can behave like a high-level simulation process engineer.

**Integration status:** Content below is mirrored into:

- `expert_decision_workflow.md` §28 (implementation guidance, P0–P3, State E definition, anti-complexity)
- `column_convergence_playbook.md` principles P11–P14, gap list, §18 intelligence layers
- **`INTELLIGENCE_INVENTORY_V1.md`** — current coded/paper snapshot (preferred before adding new intelligence)

This file remains the **detailed backlog / commentary**. Prefer editing the inventory + §28 when changing status or policy.

---

## 2. Overall verdict

| Dimension | Assessment |
|-----------|------------|
| Ability to touch HYSYS (COM read/write) | Strong platform from prior Tower Assist work |
| CDU-specific COM (draws / PA / cuts) | **Not discovered yet** — Phase 1 |
| Simulation PE judgment / intelligence | Early / incomplete for CDU |
| Ready to replace a senior PE | **No** |
| Ready to assist a senior PE (interactive) | **Yes**, once boards show draws/PAs/quality and FINAL_TARGETs stay locked |

**Bottom line:** Reuse the COM + trial discipline platform. Rebuild CDU diagnosis, strategy catalog, and quality FINAL_TARGETs in layers — do not stretch stripper RR/NH₃ logic.

---

## 3. What is already good (platform)

| Strength | Why it matters |
|----------|----------------|
| COM read/write of Specs (`GoalValue`, `IsActive`) | Real automation surface |
| Snapshot / restore | Safe keep/reverse experiments |
| Bounded one-change trials | Correct PE discipline |
| States A–F + FINAL_TARGET concept | Right philosophy on paper |
| Trial Map trail | Memory of what was tried |
| Specs Summary Active/Estimate | DOF-safe baseline workflow |

These are a solid **prototype foundation**, not finished CDU intelligence.

---

## 4. Gaps — where Assist is still “junior” for CDU

### 4.1 No CDU object board yet (P0 / Phase 1–2)

Must show: side draws, pumparounds, side strippers, cut/ASTM/TBP quality vs FINAL_TARGET — not OH/btms/NH₃ only.

### 4.2 State classification before moves (P0)

Dead draws / sentinel duties → State B recovery, not cut-chasing as if healthy.

### 4.3 FINAL_TARGET ≠ Active GoalValue (P0)

Never auto-relax cut / ASTM / TBP plant targets to force green.

```text
FINAL_TARGET (cuts / ASTM / TBP)  → locked unless user explicitly allows
Category-1 MVs (draws, PA, OH, strip steam) → preferred experiments
Temporary baseline specs           → allowed for State B recovery (with audit)
```

### 4.4 Units and truth sources (P0)

Worksheet units; prefer stream / assay petroleum properties over raw COM display when they disagree.

### 4.5 Post-trial thinking (P0)

What improved / worsened / physical? → continue / reverse / switch / stop / State F.

### 4.6 Spec-role engine (P1)

When to use baseline Active pairs, monitor-only FINAL_TARGET, 1-for-1 swaps.

### 4.7 Operability gates (P0/P1)

No State E with dry draws, sentinel duties, absurd T profiles.

### 4.8 Going-nowhere detector (P2)

Flat response on a Category-1 family → switch or State F.

### 4.9 Interactive default (P1)

One trial → PE board → approve next. Batch Assist only when allowed.

### 4.10 Structural suggestions only (P3)

Never silent stage/PA/stripper layout edits.

---

## 5. Priority roadmap (CDU)

| Priority | Upgrade | PE intent |
|----------|---------|-----------|
| **P0** | States A–F classification before moves | Don’t solve the wrong problem |
| **P0** | External FINAL_TARGET layer (cuts / ASTM / TBP) | Don’t cheat quality to go green |
| **P0** | Worksheet units + stream/assay truth | Trust what HYSYS UI shows |
| **P0** | Response classes after every trial | Continue / reverse / switch / State F |
| **P0** | Operability gates (draws, duties, T) | Reject “fake green” |
| **P1** | Spec-role engine + interactive approve-next | Controlled Active selection |
| **P2** | Weak-response / going-nowhere detector | Fewer blind steps |
| **P3** | Structural suggestions (permission only) | Escalate with evidence |

---

## 6. What “better intelligence” is *not*

- More aggressive GoalValue spam  
- Auto-relaxing cut quality to force convergence  
- Changing many Actives without DOF and role rules  
- Pretending stripper RR logic is enough for crude cuts  
- Declaring success on residuals alone while draws/duties are nonphysical  
- Silent batch loops without PE-readable reasons  

---

## 7. Recommended definition of success (State E — CDU)

Assist may claim **State E** only when **all** are true:

1. HYSYS numerically healthy (no sentinel duties/flows on key products / PAs)  
2. Every hard **FINAL_TARGET** met on governing **products** (ASTM/cut/gap/props within tolerance)  
3. Preferred or approved Active spec set is consistent and DOF = 0  
4. Yields / material balance and PA return duties within configured bounds  
5. Temperature (and pressure) profiles pass basic physical checks (draw trays, flash, PA returns)  
6. Audit trail explains each Active/Goal change and why  

Otherwise: report **State B / C / D / F** with evidence — not a fake win.

---

## 8. Link to live SW Stripper lesson (legacy COM shell)

> Historical stripper validation — proves shell policies, not CDU cuts.

| Lesson | Carry into CDU |
|--------|----------------|
| FINAL_TARGET lock is mandatory | Yes — cuts/ASTM/TBP instead of NH₃ |
| Estimates / Active swap for State B | Yes — same discipline |
| Units mismatch traps | Yes — worksheet + stream truth |
| Tiny product flow after “success” | Yes — operability on draws/residue |
| Interactive PE judgment preferred | Yes |

---

## 9. Maintenance

1. Update playbook gap list  
2. Update workflow §28 / CDU applicability if policy changes  
3. Tick matching subsection here  
4. Implement only the next **layer**  

---

*Retargeted for CDU Assist — living backlog*
