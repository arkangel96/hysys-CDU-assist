# Simple Column Assist

External desktop assist for **simple distillation and stripping columns** in
Aspen HYSYS (Windows COM). Not an AspenTech product.

> **Scope:** simple 2-product columns (e.g. sour-water stripper).  
> **Not for:** CDU or VDU — those will be separate tools.  
> Full boundary notes: [`docs/SCOPE_SIMPLE_COLUMN_ASSIST.md`](docs/SCOPE_SIMPLE_COLUMN_ASSIST.md)

## What it does

- Connect to a running HYSYS case
- Inspect streams, edit supported specs, solve, chart, export Excel
- **Column Assistant:** Inspect / Diagnose / Specs Summary Active·Estimate /
  Connections READ / PE board / Trial Map / Assist trials

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

Click **Connect**. Use **Open Case** to select a `.hsc` file if needed.

## Notes

- AspenTech COM members vary by release; the adapter tries common variants.
- The application never saves the HYSYS case automatically.
- See `ARCHITECTURE.md` and `docs/SCOPE_SIMPLE_COLUMN_ASSIST.md`.
