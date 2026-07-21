# Intelligence Improvement Notes — CDU Assist

**Document type:** Expert review notes + living backlog  
**Status:** Retargeted for CDU Assist (2026-07-21)  
**Scope:** Atmospheric crude distillation only — see [`SCOPE_CDU_ASSIST.md`](SCOPE_CDU_ASSIST.md)  
**Canonical home of rules:** [`expert_decision_workflow.md`](expert_decision_workflow.md) **§28** + CDU applicability section  
**Operational slice:** [`cdu_convergence_playbook.md`](cdu_convergence_playbook.md)

**Date:** 2026-07-21  
**Author perspective:** Senior process / HYSYS simulation engineer review of CDU Assist

---

## 1. Purpose of this note

Capture an honest assessment of the **decision intelligence** of CDU Assist, and the improvements required before it can behave like a high-level simulation process engineer on atmospheric crude towers.

This file remains the **detailed backlog / commentary**. Prefer editing workflow §28 when changing policy; keep this file in sync.

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

## 7. Definition of State E success (CDU)

Assist may claim **State E** only when **all** are true:

1. Numerically healthy (no sentinel duties/flows on key products/draws)  
2. Every hard **FINAL_TARGET** met on product stream / assay truth (within tolerance)  
3. Approved Active spec set consistent; DOF = 0  
4. Material split and duties within engineering bounds  
5. Temperature (and pressure) profiles pass basic physical checks  
6. Audit trail explains each Active/Goal change and why  

Otherwise: report **State B / C / D / F** with evidence — not a fake win.

---

## 8. Platform lessons carried from Simple Column Assist (unchanged PE rules)

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
