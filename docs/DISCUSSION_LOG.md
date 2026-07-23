# Discussion log (rolling — keep thin)

**Purpose:** Continuity of project ideas and decisions across chats.  
**Format:** Newest session first. Bullets only — not full transcripts.  
**Raw chats:** Cursor agent-transcripts + optional copies under `docs/transcripts/`.  
**Rule:** `.cursor/rules/discussion-continuity.mdc` (`alwaysApply`) — Assist updates this without being asked.

---

## 2026-07-24 — PreFlash + Crude Heater IQ v0.1 integrate (propose-only)

- Locked: overflash = liquid below flash / % fresh feed; band **project-configurable** (null ok); primary MV = **heater duty**, COT secondary.
- v0.1 = PE Decision Board propose-only; v0.2 study runner later. No auto furnace writes.
- Docs: `new_intelligence/CDU_PreFlash_Crude_Heater_Intelligence_v0.1.md`; Inventory `CDU-PFH-T100`; code `cdu_preflash_heater.py`.
- Live ops confirmed: PreFlash, Crude Heater, Mixer, T-100; energy Crude Duty.
- **Transcript:** [`transcripts/2026-07-24/b6250938-5cf2-45ff-9e57-d84b520ea4d6.jsonl`](transcripts/2026-07-24/b6250938-5cf2-45ff-9e57-d84b520ea4d6.jsonl)
- **History:** [`DISCUSSION_HISTORY_2026-07-24_night.md`](DISCUSSION_HISTORY_2026-07-24_night.md)

---

## 2026-07-24 — discuss furnace/preheat Assist IQ (no code yet)

- User: don’t expand Assist casually; **first design intelligence** for heaters + related upstream equipment; discuss before build. Sees it as fairly simple.
- Locked so far: tower PA Campaign A closed; furnace/preheat **not coded** (Category-2 / Manual map). → superseded by PFH v0.1 integrate above.

---

## 2026-07-24 — after Campaign A close: next recommendation

- PE lean: **don’t open trays next.** Document Campaign A closed; pick either soft-gap/diesel campaign or reframe energy (preheat/furnace), not more PA cuts.
- Stages = design/structural; column already E + hard Q + N+K holds.

---

## 2026-07-24 — PA_3 energy study (Campaign A PA series complete)

- Ran 2× PA_3 |duty| −3% with N+K holds; rates + hard Q OK both steps.
- Same-unit display: **KEEP_SHIFT** both (~1:1 CondQ rise); not a utility win.
- Case restored. Docs: `docs/studies/energy_pa3_run_20260723_152208.md`.
- **Campaign A weaker-PA path done (PA_1/2/3):** all heat-shift, no save under N+K holds.

---

## 2026-07-24 — PA_2 energy study (same protocol)

- Ran 2× PA_2 |duty| −3% with N+K holds; rates + hard Q OK both steps.
- Same-unit display score: **KEEP_SHIFT** both (~1:1 CondQ rise); tiny dnet (~−3e4 Btu/hr) not a declared utility win.
- Case restored. Docs: `docs/studies/energy_pa2_run_20260723_151214.md`.
- **Same lesson as PA_1:** weaker mid PA → heat moves to condenser; practically no energy save.

---

## 2026-07-24 — PA_1 same-unit re-score; path closed

- Re-scored `energy_pa1_run_20260723_144800`: mixed PA Btu/hr + Cond COM was a false “net KEEP.”
- Same-unit COM `|PA1_goal|+|Cond|` ≈ **flat** both steps → **KEEP_SHIFT** (~1:1); Cond ≈ 109→112 MMBtu/hr.
- N+K + hard Q held; **not** a utility win. Campaign A **PA_1 save path closed**.
- Runner fixed: same-unit display/COM scoring in `scripts/run_energy_study_pa1.py`.
- **Fork open:** (1) PA_2 next, (2) reverse/hold PA_1, (3) strengthen PA_1 only if CondQ↓ is the objective.
- One brain unchanged: study scripts log; `propose_action` remains sole chooser.

---

## 2026-07-23 (late) — Campaign A PA_1 energy study run

- Ran 2× PA_1 |duty| −3% with N+K holds; rates + hard Q OK; CondQ rose both steps (heat shift).
- Case restored to PA1 −55e6. Docs: `docs/studies/energy_pa1_run_20260723_144800.md`.
- Do not treat runner “net KEEP” as utility win until CondQ is same-unit as PA.
- **Lesson:** weaker top PA cooling → CondQ up (yin–yang); NHT naphtha/kero rate holds survive these steps; heat **shift ≠** utility save.

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
| 2026-07-24 night | [`DISCUSSION_HISTORY_2026-07-24_night.md`](DISCUSSION_HISTORY_2026-07-24_night.md) |
| 2026-07-23 pm | [`DISCUSSION_HISTORY_2026-07-23_pm.md`](DISCUSSION_HISTORY_2026-07-23_pm.md) |
| 2026-07-23 | [`DISCUSSION_HISTORY_2026-07-23.md`](DISCUSSION_HISTORY_2026-07-23.md) |
| 2026-07-22 | [`DISCUSSION_HISTORY_2026-07-22.md`](DISCUSSION_HISTORY_2026-07-22.md) |
| Transcripts index | [`transcripts/README.md`](transcripts/README.md) |
