"""Integrate CDU_Expert_Modules_Starter domain modules (10-30) into docs/expert/.

Platform modules 31-37 and 90 are merged manually — do not overwrite from starter.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "CDU_Expert_Modules_Starter"
DST = ROOT / "docs" / "expert"

# Platform / merged manually — never overwrite from starter templates
SKIP = {
    "README.md",
    "31_HYSYS_Object_Map.md",
    "32_State_Machine.md",
    "33_Reasoning_Engine.md",
    "34_Knowledge_Base.md",
    "35_Experiment_Selection.md",
    "36_Learning_System.md",
    "90_Test_Cases.md",
}

HEADER = """\
**Module ID:** {mid}  
**Parent:** [`00_System_Architecture.md`](00_System_Architecture.md)  
**Status:** Starter framework — integrated from `CDU_Expert_Modules_Starter`  
**Reasoning loop:** [`33_Reasoning_Engine.md`](33_Reasoning_Engine.md)  
**Knowledge base:** [`34_Knowledge_Base.md`](34_Knowledge_Base.md)  
**HYSYS map:** [`31_HYSYS_Object_Map.md`](31_HYSYS_Object_Map.md)  
**Reference case:** T-100 — [`../cdu_com_discovery.md`](../cdu_com_discovery.md)

"""

T100_SECTIONS: dict[str, str] = {
    "20_Model_Validation.md": """
---

## T-100 reference hooks (live case)

| Check | T-100 evidence |
|-------|----------------|
| Column connectivity | Feeds: `Atm Feed`, steams; products: Naphtha → Residue |
| DOF | 0 at inspect — spec set closed |
| Convergence | Residuals tight; validate product streams not stripper OH/btms only |
| Sentinel duties | Stripper-style condenser read failed — use named energy streams |
| State A gate | Fail if feeds/products disconnected or DOF ≠ 0 without audit |

**Process flow:** Model Validation → State **A** / **B** — [`32_State_Machine.md`](32_State_Machine.md).
""",
    "21_Feed_Preparation.md": """
---

## T-100 reference hooks

| Object | Name |
|--------|------|
| Crude feed | `Atm Feed` → column ~stage 28 |
| Upstream | `Mixer`, `Crude Heater`, `PreFlash` |

**Automation:** Feed/case changes → `feed_or_case_change` Trial Map event (manual log).
""",
    "22_Fired_Heater.md": """
---

## T-100 reference hooks

| Object | Role |
|--------|------|
| `Crude Heater` | Upstream of column — COT / duty not on column specs |

**Automation:** Category-2 — `overflash_or_furnace_nudge` as manual map until COM mapped.
""",
    "23_Flash_Zone.md": """
---

## T-100 reference hooks

| Object | Role |
|--------|------|
| `PreFlash` | Upstream flash — overflash / flash-zone coupling |
| Feed stage | ~28 on `T-100` |

**Automation:** Category-2 — manual until flash/overflash specs discovered on case.
""",
    "24_Main_Fractionator.md": """
---

## T-100 reference hooks

| Item | Value / names |
|------|----------------|
| Column | `T-100`, 29 stages |
| Products | Naphtha, Kerosene, Diesel, AGO, Residue, Off Gas, Waste Water |
| Active draw specs | `Naphtha Prod Rate`, side-draw family via SS prod flows |
| Reflux / liquid | `Liquid Flow`, `Reflux Ratio` (estimate) |

**Hypothesis examples:**

| Symptom | Subsystem | Experiment (one family) |
|---------|-----------|-------------------------|
| Overall yield split wrong | Material split | `Naphtha Prod Rate` or draw rate nudge |
| OH / naphtha end-point | Top section | `Liquid Flow` or activate `Reflux Ratio` (DOF care) |
| Mid-T profile wrong | Fractionation + PA | See [`25_PumpArounds.md`](25_PumpArounds.md) |

**Trial Map:** `side_draw_rate_nudge`, `reflux_or_oh_nudge`.
""",
    "25_PumpArounds.md": """
---

## T-100 reference hooks

| PA | Active specs (COM) | Typical PE role |
|----|-------------------|-----------------|
| PA_1 | `PA_1_Rate(Pa)`, `PA_1_Duty(Pa)` | Upper tower heat removal — naphtha/kero zone |
| PA_2 | `PA_2_Rate(Pa)`, `PA_2_Duty(Pa)` | Mid tower — kero/diesel fractionation |
| PA_3 | `PA_3_Rate(Pa)`, `PA_3_Duty(Pa)` | Lower mid — diesel/AGO |

**Expert rules (to expand as Rule IDs in 34):**

1. Cut **quality** off with yields OK → PA duty in section **above** that cut.  
2. Cut **yield** wrong → draw / SS prod rate first.  
3. **One PA, one knob** per trial.  

**Selection:** [`35_Experiment_Selection.md`](35_Experiment_Selection.md) · **Trial Map:** `pa_duty_nudge`.
""",
    "26_Side_Strippers.md": """
---

## T-100 reference hooks

| Side stripper | Active spec | Steam feed |
|---------------|-------------|------------|
| Kero_SS | `Kero_SS Prod Flow` | TBD stream read |
| Diesel_SS | `Diesel_SS Prod Flow` | `Diesel Steam` |
| AGO_SS | `AGO_SS Prod Flow` | `AGO Steam` |
| Kero reboil | `Kero Reb Duty` | `Kero_SS_Energy` |

**Trial Map:** `side_strip_steam_nudge`, `side_draw_rate_nudge`.
""",
    "27_Product_Quality.md": """
---

## T-100 reference hooks

| Product | Quality (TBD from streams) |
|---------|--------------------------|
| Naphtha | RVP / end point |
| Kerosene | Flash / D86 |
| Diesel | D86 95% — FINAL_TARGET candidate |
| AGO | TBP / cut |
| Residue | Heavies / overlap |

**Policy:** FINAL_TARGETs locked — monitor on stream truth. See [`90_Test_Cases.md`](90_Test_Cases.md).
""",
}

FOOTER = """
---

## Automation hook (CDU Assist)

| Capability | Status |
|------------|--------|
| Evidence read | Partial — [`31_HYSYS_Object_Map.md`](31_HYSYS_Object_Map.md) |
| Hypothesis rules in this module | **To author** — [`34_Knowledge_Base.md`](34_Knowledge_Base.md) |
| Experiment selection | [`35_Experiment_Selection.md`](35_Experiment_Selection.md) |
| Execute + reversible | Yes — `column_engine` |
| Learning / memory | [`36_Learning_System.md`](36_Learning_System.md) |
"""

MODULE_IDS = {
    "10_Crude_Assay.md": "10",
    "20_Model_Validation.md": "20",
    "21_Feed_Preparation.md": "21",
    "22_Fired_Heater.md": "22",
    "23_Flash_Zone.md": "23",
    "24_Main_Fractionator.md": "24",
    "25_PumpArounds.md": "25",
    "26_Side_Strippers.md": "26",
    "27_Product_Quality.md": "27",
    "28_Yield_Optimization.md": "28",
    "29_Energy_Optimization.md": "29",
    "30_Hydraulic_Diagnostics.md": "30",
}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    count = 0
    for name in sorted(SRC.glob("*.md")):
        if name.name in SKIP:
            print("skip", name.name)
            continue
        body = name.read_text(encoding="utf-8")
        mid = MODULE_IDS.get(name.name, "?")
        lines = body.splitlines(keepends=True)
        if lines and lines[0].startswith("#"):
            out = lines[0] + "\n" + HEADER.format(mid=mid) + "".join(lines[1:])
        else:
            out = HEADER.format(mid=mid) + body
        out += T100_SECTIONS.get(name.name, "")
        out += FOOTER
        (DST / name.name).write_text(out, encoding="utf-8")
        print("wrote", DST / name.name)
        count += 1
    print("done", count, "domain modules (31-37, 90 merged separately)")


if __name__ == "__main__":
    main()
