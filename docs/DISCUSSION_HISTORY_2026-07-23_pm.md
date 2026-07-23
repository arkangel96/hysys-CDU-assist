# Discussion history — 2026-07-23 (PM / office continuation)

**Channel:** Cursor Agent + live Aspen HYSYS (T-100)  
**Transcript (raw):** [`transcripts/2026-07-23/bddd93c2-4585-45e8-9d9f-aa4985ecbe79.jsonl`](transcripts/2026-07-23/bddd93c2-4585-45e8-9d9f-aa4985ecbe79.jsonl)  
**Related morning notes:** [`DISCUSSION_HISTORY_2026-07-23.md`](DISCUSSION_HISTORY_2026-07-23.md)  
**Trial map:** [`T100_SESSION_TRIAL_MAP.md`](T100_SESSION_TRIAL_MAP.md)

---

## What we did

1. Opened CDU Assist / verified HYSYS live — T-100 **converged**, DOF=0, easy numerical solve (~6 iters).
2. Raised AI identity to **expert** CDU PE + **Oil Manager assay** specialist; user also expert PE (expert-to-expert).
3. Locked **naphtha + kero rates** (Goal←Current); clarified that is **flow**, not quality.
4. Declared plant-like **FINAL_TARGETs in Field °F** (not °C); wired COM D86/flash reads via HYSYS display units (no Assist conversion).
5. Live quality: hard D86/flash **ON**; soft kero–diesel gap **OFF** (~10 vs ≥27 F).
6. Specs page vs stream quality: quality is **calculated** on streams; Cold Props / Boiling Point Curves — don’t Add quality Specs with DOF=0.
7. Discussed optimize vs trays: **operating** → energy first; **design** → trays early. Manual tray estimate: empirical ~26–44; model **29** OK lean first guess. Sharp Fenske ~110 rejected for CDU overlaps.
8. Nozzle entry: manual ρv² — need real nozzle ID; Atm Feed 2-phase likely needs vapor horn; location @28 OK.
9. Added `new_intelligence/CDU_T100_Decision_Intelligence_v1.md` (complementary decision authority) — **DOCS**, not required to code yet.
10. HYSYS Help = **lookup shelf** only (not core brain); local Help mostly `.hh` headers under `Aspen HYSYS V14.0\Help`.
11. **Trial T3:** PA_1 −5% |duty| (−55.0 → −52.25 MMBtu/hr). KEEP on rates/quality/converge; CondQ **+~2.75** MMBtu/hr → heat **shift**, not clear net energy save.
12. Created session **trial map** (`docs/T100_SESSION_TRIAL_MAP.md` + Cursor canvas) for MV tracking.

---

## Decisions locked (this session)

| Topic | Decision |
|-------|----------|
| AI role | Expert HYSYS CDU PE + Oil Manager assay; user = expert PE |
| Units | **HYSYS display / Field (°F)** — no Assist °C conversion |
| Primary | Naphtha + kero **rates** + hard **quality** FINAL_TARGETs |
| Soft gap | Track; may accept with PE approval |
| Energy order | PA_1 → PA_2 → PA_3; judge **net** (PA + CondQ), not PA alone |
| Trays (operate) | Last / approval-only; 29 OK as initial guess |
| Decision Intel | Complementary DOCS authority; code later optional |
| Help | Lookup shelf only |

---

## Case state left on HYSYS (after T3)

- PA_1_Duty = **−52.25e6 Btu/hr** (was −55e6) — **KEPT**
- PA_2 / PA_3 = −35e6 each (unchanged)
- Naphtha / Kero rates locked Active
- Hard qualities on-spec; soft gap still miss
- Condenser ~**112** MMBtu/hr (was ~109)

---

## Next (from trial map backlog)

1. Fork on T3: **reverse** (protect preheat) **or** stop PA_1 cuts and move on  
2. Then PA_2 / PA_3 if energy path continues  
3. Steam / kero reb only after PA flatten  
4. Trays still approval-only last  

---

## End-of-day addendum (going home)

- **Hindsight heading:** operating PE campaign on T-100 — hold naphtha/kero (rate+quality) → honest net energy (PA+Cond) → log MVs → structure only with approval. Not Help-dump, not auto-trays.
- **Next product need (discussed, no code yet):** program a **Trial Ledger** (JSONL/SQLite) so many trials auto-record before/after, quality, CondQ/PA, KEEP/REVERSE — trial map reads ledger; chat notes won’t scale.
- Raw transcript refreshed in `transcripts/2026-07-23/bddd93c2-…jsonl` for home handoff.

---

## Commits this afternoon (approx.)

- `38878a1` — Field units quality + Decision Intelligence  
- `6648aa4` — T-100 session trial map  
- `0210e62` — discussion script + raw transcript archive  
- *(this)* — transcript refresh + home handoff note  
