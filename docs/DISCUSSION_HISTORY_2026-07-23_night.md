# Discussion history — 2026-07-23 (night)

**Channel:** Cursor Agent + live Aspen HYSYS (T-100 open)  
**Transcript (Cursor cache):** `19ca8612-b052-475a-a0c4-bc7e06fe7b9f`  
**Rolling log:** [`DISCUSSION_LOG.md`](DISCUSSION_LOG.md)

---

## What we did

1. Code/intel audit (discussion): loose ends, contradictions, °F trap, draw-name split-brain, dual doc authority.
2. Shipped surgical fixes; scrubbed NH₃ from runtime `.py`/`.json`; deleted legacy stripper stress helpers.
3. Declared **CDU-only** + **one brain**; removed `sw_stripper` catalog path; unified expert into `propose_action`; demoted Decision Intel “authority” language.
4. Discussed architecture trajectory (~3 stable enough to build); agreed not to chase full platform “4” yet.
5. Live `stress_test_cdu_t100.py` against open HYSYS — pass + restore.
6. Explained PATH/`python` stub vs real `.venv` (not a product failure).
7. Learning: no auto-DB yet; added curated `docs/lessons/` (multi-feed aware).
8. Discussion continuity: alwaysApply rule + this log so ideas are not lost between sessions.

---

## Decisions locked

| Topic | Decision |
|-------|----------|
| Product | Atmospheric CDU Assist only |
| Chooser | Single `propose_action` brain |
| Docs | Complementary; Inventory = coded status |
| Memory | Lessons folder now; auto learn HELD |
| Column tag | T-100 reference; feeds will change |
| Continuity | Update DISCUSSION_LOG without user reminder |

---

## Ideas to not forget

- Lessons must tag **feed/assay** and split **Reusable vs Case-specific**.
- Quality MV order (draw-first) vs energy (PA order) — different objectives, same brain.
- CondQ rise on PA cut = heat shift; don’t confuse with net energy win.
- Future multi-feed: case pack vs CDU-class rules.

---

## Case / tooling notes

- Live stress restored T-100; not auto-saved.
- Python for scripts: `Documents\cdu tool\hysys-CDU-assist\.venv\Scripts\python.exe`
