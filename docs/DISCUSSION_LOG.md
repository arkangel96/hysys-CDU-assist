# Discussion log (rolling — keep thin)

**Purpose:** Continuity of project ideas and decisions across chats.  
**Format:** Newest session first. Bullets only — not full transcripts.  
**Raw chats:** Cursor agent-transcripts + optional copies under `docs/transcripts/`.  
**Rule:** `.cursor/rules/discussion-continuity.mdc` (`alwaysApply`) — Assist updates this without being asked.

---

## 2026-07-23 (night) — architecture clean + live HYSYS + lessons

**Transcript id:** `19ca8612-b052-475a-a0c4-bc7e06fe7b9f`  
**History write-up:** [`DISCUSSION_HISTORY_2026-07-23_night.md`](DISCUSSION_HISTORY_2026-07-23_night.md)

### Decisions locked

- CDU-only product — no SW Stripper / NH₃ shell in runtime.
- **One brain:** `propose_action` only; complementary docs do not rival authority.
- Surgical fixes shipped: °F keep gate, SS Prod Flow naming, RR bias removed, State F family map.
- Learning: curated `docs/lessons/` now; **auto** learn/DB still HELD.
- T-100 = column tag / reference topology — **feeds will change**; lessons tag feed/assay + Reusable vs Case-specific.
- SWE trajectory: ~3 → 3.5 disciplined build-up; no need to chase “platform 4” before more PE IQ.
- Discussion continuity: this log + alwaysApply rule (user must not re-remind).

### Live HYSYS

- `stress_test_cdu_t100.py` exit 0; baseline E; wrong RR Active → B + `refresh_estimates`; restore OK.
- Naphtha+Kero **rates Active held** (~670.83 / ~271.25 USGPM). Hard D86/flash **on spec**; soft kero–diesel gap **~10 F vs 27 F** (soft miss only).

### Open / next

- Optional: push DISCUSSION_LOG + lessons to GitHub for other PC.
- Next PE intelligence via Inventory → one brain only.
- Bare `python` on PATH missing in Cursor — use sibling `.venv` (not a product bug).

---

## Older sessions

| Date | File |
|------|------|
| 2026-07-23 pm | [`DISCUSSION_HISTORY_2026-07-23_pm.md`](DISCUSSION_HISTORY_2026-07-23_pm.md) |
| 2026-07-23 | [`DISCUSSION_HISTORY_2026-07-23.md`](DISCUSSION_HISTORY_2026-07-23.md) |
| 2026-07-22 | [`DISCUSSION_HISTORY_2026-07-22.md`](DISCUSSION_HISTORY_2026-07-22.md) |
| Transcripts index | [`transcripts/README.md`](transcripts/README.md) |
