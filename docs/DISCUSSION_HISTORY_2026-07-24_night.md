# Discussion history — 2026-07-24 (night)

**Channel:** Cursor Agent + live Aspen HYSYS (T-100 open)  
**Transcript (repo):** [`transcripts/2026-07-24/b6250938-5cf2-45ff-9e57-d84b520ea4d6.jsonl`](transcripts/2026-07-24/b6250938-5cf2-45ff-9e57-d84b520ea4d6.jsonl)  
**Rolling log:** [`DISCUSSION_LOG.md`](DISCUSSION_LOG.md)

---

## What we did

1. Continued Campaign A energy studies: same-unit PA+CondQ re-score; PA_2 and PA_3 weaker-cooling runs → all **KEEP_SHIFT** (heat to CondQ, no utility save). Case restored each time.
2. Closed Campaign A PA weaker-cooling path (PA_1/2/3). Agreed stages not next; furnace/preheat is the real energy play.
3. Live COM confirmed flowsheet ops: Mixer, Crude Heater, PreFlash, T-100; energy Crude Duty / Atmos Cond / Q-Trim.
4. Integrated **PreFlash + Crude Heater Intelligence v0.1** (propose-only PE board): docs, Inventory `CDU-PFH-T100`, config knobs, `cdu_preflash_heater.py`, board wiring. No auto heater writes; study runner deferred to v0.2.

---

## Decisions locked

| Topic | Decision |
|-------|----------|
| PA cut energy | Heat shift ≠ save under N+K holds |
| Overflash | Liquid below flash / % fresh feed; band project-configurable (null ok) |
| Primary MV (PFH) | Crude Heater Duty; COT secondary |
| PFH v0.1 | Propose-only PE board; PE approval before execute |
| One brain | PFH advisory; `propose_action` remains column chooser |

---

## Open / next

- Configure overflash stream names + band when plant numbers known.
- PFH v0.2 study runner after multi-case validation.
- Optional: soft gap / diesel campaign (separate from PFH).
