# Discussion History — Simple Column Assist v1 New Intelligence

**Session date:** 2026-07-22  
**Channel:** Cursor Agent interface (chat above Assist + HYSYS COM)  
**Repo:** `arkangel96/simple-column-assist-v1-new-intelligence`  
**Purpose:** Preserve PE / product decisions from this working session so later work does not lose context.

---

## 1. Product framing

- This line is **Simple Column Assist v1 — New Intelligence** for Aspen HYSYS **simple distillation / stripping** only.
- **Not** CDU, **Not** VDU, **Not** full Aspen ecosystem / hydraulics / TEA.
- Validated reference: **SW Stripper** (Full Reflux, ~8 stages, feed ~3, locked bottoms NH₃ ≤ 50 ppmw).
- Lives in its **own GitHub repo** — do not mix into base `simple-column-assist` or RR-only lab notes.

---

## 2. What “intelligence” means here

Agreed meaning: **judgment like a simulation PE**, not GoalValue spam.

Already in scope / coded in this line:

| Theme | Decision |
|-------|----------|
| Multi-variable | Not RR-only — families A_init / B_energy / C_split (+ D locked target, E feed, F structural) |
| States A–F | State E = acceptable success (product + physical + operable); F = escalate / structural |
| FINAL_TARGET | Locked plant product — never auto-relax to “win” |
| Monitor / Specs / Specs Summary | Same COM knobs PE uses; Active/Estimate readable and writable |
| Connections | READ + think; structural WRITE approval-only |
| Condenser Total / Partial / Full Reflux | READ + judgment; change = manual in HYSYS (not silent COM) |
| Popups / Messages | PE clues (SEE → LOG → ACT), not only dismiss |
| Keep / reverse | Product + operability first |

Complementary package: `new_intelligence/` — **helps, does not supersede** Inventory / Assist rules.

---

## 3. Agent interface vs Assist window

| Layer | Role |
|-------|------|
| **Assist GUI** | Desktop buttons (Inspect, Diagnose, Optimize 1, Specs Summary, Connections approve) |
| **Agent interface** | This Cursor chat — same Python/COM brain; can inspect / diagnose / optimize without opening Assist |
| **HYSYS** | Thermodynamics + solver; engineer owns Save (`.hsc` never auto-saved) |

Naming agreed: call this chat the **Agent interface**.

---

## 4. Optimization discussion

### Need more intelligence first?
- For **daily Assist / State E**: already usable — do not block on “more brain.”
- For **simple optimize**: needed a **thin layer** (objective + lock NH₃ + stop when flat) — **coded** in this session (`column_optimize.py`).

### Simple objectives (keep simple — no complicated NLP)
1. Min reflux ratio  
2. Min reboiler duty  
3. Min condenser duty  
4. Min stage count (mechanical — approval)

### Rules agreed
- Optimize only when FINAL_TARGET already met (State E first).  
- One bounded step; KEEP only if objective improves **and** product/operability still OK.  
- Flat → reverse / stop.  
- Stages: justify before cutting; approval-only.

### Why min stages (discussion)
- Stages set separation capacity vs energy/CAPEX trade-off.  
- Use when under-staged (high RR forever) or design “can we do n−1?”  
- **Not** first knob when already State E at mild RR — squeeze RR/duty first.

### Clarity UX
- Optimize dropdown = what is minimized (Min RR / Reb Q / Cond Q / stages).  
- Optimize 1 must report BEFORE / ACTION / AFTER / KEEP|REVERSE in plain language.  
- Bug fixed: `name 'action' is not defined` on Optimize 1.

---

## 5. Are we “ahead”?

Scoped answer (distillation judgment niche only):

- **Ahead of typical COM / Excel / VBA macros** — yes (state, families, locked target, keep/reverse, approval structural).  
- **Not** competing with Aspen full suite / hydraulics / economics.  
- **Not** smarter than a senior PE’s head — Assist is junior–mid sim PE support.  
- User observation: “never seen anything like this” in this niche — fair for an **external** PE-style Assist + Agent loop.

---

## 6. Are we done?

**v1 stop point — yes**, for this product slice:

- Multi-variable judgment + simple optimize + Connections F + Agent path + compact UI.  

**Optional later** (only if live pain appears):

- Prove every structural COM write on live HYSYS  
- Second FINAL_TARGET (e.g. H₂S)  
- Deeper learning/memory from `new_intelligence/`  
- Condenser-type COM write (currently intentional manual)

**Do we need more intelligence now?**  
**No — not required.** Use live cases; add intelligence when a real failure mode shows up.

---

## 7. UI note

Assist UI was too large/sparse vs Aspen desktop density → compacted fonts/padding/chips/toolbar so Optimize dropdown and actions stay findable.

---

## 8. Repo / push notes from this session

- New standalone repo: `simple-column-assist-v1-new-intelligence`  
- Case description: `docs/CASE_SIMPLE_COLUMN_V1_NEW_INTELLIGENCE.md`  
- This discussion log: `docs/DISCUSSION_HISTORY_2026-07-22.md`  
- Intentionally **not** mixed: RR-only lab scripts, large `.hsc` binaries, old `simple-column-assist` repo content after revert of misplaced case commit  

---

## 9. Working rules to keep

1. Diagnose before optimizing.  
2. Never auto-save `.hsc`.  
3. Never auto-relax locked FINAL_TARGET.  
4. One major change per trial.  
5. Structural / condenser type = engineer knows and approves.  
6. Complementary docs must not declare “supersedes all.”  

---

*End of session discussion capture — 2026-07-22*
