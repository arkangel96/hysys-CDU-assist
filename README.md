# CDU Assist

External desktop assist for **atmospheric Crude Distillation Units (CDU)** in
Aspen HYSYS (Windows COM). Not an AspenTech product.

> **Scope:** atmospheric crude towers — side draws, pumparounds, cut/ASTM/TBP targets.  
> **Not for:** simple stripper purity chasing, or VDU (later).  
> Full boundary notes: [`docs/SCOPE_CDU_ASSIST.md`](docs/SCOPE_CDU_ASSIST.md)

## What it does

- Connect to a running HYSYS case
- Inspect streams, edit supported specs, solve, chart, export Excel
- **Column Assistant:** Inspect / Diagnose / Specs Summary Active·Estimate /
  Connections READ / PE board / Trial Map / Assist trials (CDU Category-1 MVs)

## Requirements

- Windows 10/11
- Aspen HYSYS installed and licensed
- 64-bit Python 3.11 or 3.12 matching the installed HYSYS architecture

## Install

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Open a HYSYS case first, then run:

```powershell
python main.py
```

Or double-click `Open CDU Assist.bat`.

Click **Connect**. Use **Open Case** to select a `.hsc` file if needed.

## Notes

- AspenTech COM members vary by release; the adapter tries common variants.
- The application never saves the HYSYS case automatically.
- See `ARCHITECTURE.md` and `docs/SCOPE_CDU_ASSIST.md`.
- COM discovery for draws / PAs / cut specs is Phase 1 — do not invent APIs.
