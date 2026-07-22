# Discussion history — 2026-07-23 (home session)

**Channel:** Cursor Agent + live Aspen HYSYS (T-100)  
**Transcript (raw):** [`transcripts/2026-07-23/82fbe4d7-c1ae-4dac-b2ee-e376cec45714.jsonl`](transcripts/2026-07-23/82fbe4d7-c1ae-4dac-b2ee-e376cec45714.jsonl)  
**Purpose:** Human-readable review for office PC (same day chat).

---

## What we did

1. Set up `.venv`, launched CDU Assist, verified live HYSYS connect + smoke test (T-100 converged).
2. Honest PE assessment: Assist is co-pilot, not senior PE yet; build-up via thin layers.
3. Locked intelligence direction: clone PE judgment, interactive-first, quality keep/reverse, diesel tree first.
4. Default AI role: senior Aspen HYSYS CDU PE — `.cursor/rules/cdu-hysys-senior-pe.mdc` (`alwaysApply`).
5. Discussed assay/lab→simulation: **separate program** later; CDU Assist stays tower-focused.
6. Live Specs: 13 Fixed Active (draws + PA rate/duty + kero reb…); RR Estimate only; ITER noted.
7. Corrected “normal CDU Active set”: sample is converge-first, not necessarily plant energy philosophy.
8. Tower-only optimize: **PA_1 first** (largest |duty|); not PreFlash/furnace.
9. Live trials: PA_1 |duty| −3% then another −3% (to ~−51.75e6 Btu/hr); still DOF=0 converged. Cond duty rose (heat shift, not clear energy win).
10. Production hierarchy: **fix naphtha + kerosene flows primary**; PA energy secondary.
11. Clarified: no main column reboiler; **Kero Reb** = side-stripper; energy metric should be PA+Condenser total.

---

## Decisions locked

| Topic | Decision |
|-------|----------|
| AI role | Senior HYSYS CDU PE, always on |
| Scope tonight | Atmospheric **tower only** |
| Primary products | **Naphtha + Kerosene** flow rates |
| Energy order | **PA_1 → PA_2 → PA_3** |
| Energy success (next) | Lower **Σ\|PA\| + \|Cond\|**, not PA alone |
| Assay conversion | Separate program (tomorrow+) |

---

## Case state left on HYSYS (home)

- PA_1_Duty ≈ **−51.75e6 Btu/hr** (was −55e6)  
- Naphtha / Kero rates still held  
- Converged, DOF = 0  

---

## Tomorrow (office) suggested start

1. Pull `main` from GitHub.  
2. Read this note + raw transcript if needed.  
3. Continue: define total tower heat metric; next PA_1 step or reverse if desired.  
4. Optional: start separate assay-assist planning.

---

*Pushed so home ↔ office can stay in sync.*
