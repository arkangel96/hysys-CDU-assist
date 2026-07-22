# Complementary CDU intelligence (`cdu_intel/`) — thin integration

**Policy:** Help Assist — do **not** supersede Inventory, States A–F, FINAL_TARGET lock,
no auto-save, or one-family trials. No second state machine.

| Package | Role |
|---------|------|
| [`../cdu_intel/`](../cdu_intel/CDU_Engineering_Intelligence_Package_Master_Architecture_v1.md) | CDU domain PE reading (D1–D10) |
| This Assist (`docs/` + `column_engine.py`) | Active runtime judgment |
| Coded hook | `cdu_reasoning.py` — PE-board labels + soft family hints |
| FINAL_TARGET config | `config/cdu_final_targets.example.json` → copy to `cdu_final_targets.json` |

**Coded now (minimal):**

- D1 problem-class label on PE board (mapped from State A–F)
- D1 priority reminder (validate / one family / no force specs)
- Soft preferred-family nudge when Active PA / side-draw / steam names are present
- D8 soft acceptance cues on PE board (advisory only)
- D6 neighbor-product reminder on PE board + after KEPT/REVERSED for draw/PA/steam/cut
- D3 interaction tip by preferred family
- Optional multi-product FINAL_TARGET load from `config/cdu_final_targets.json` (`cdu_targets.py`)

**Not coded (by design — avoid risk):** full assay validation, furnace auto-MV, hard D8 gates, auto-merge of D2–D10.
