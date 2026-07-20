# HYSYS Automation Studio

A clean-room reconstruction of a Python desktop dashboard observed in the
provided screenshots. It connects to Aspen HYSYS through Windows COM, inspects
the active case, edits supported stream inputs, solves the case, plots stream
data and exports results to Excel.

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

Click **Connect**. If attachment to the running instance is unavailable, the
program attempts to start HYSYS. Use **Open Case** to select a `.hsc` file.

## Notes

- AspenTech has changed some automation members between releases. The adapter
  tries common collection and solver variants and reports a useful error when
  the installed version differs.
- The application never saves the HYSYS case automatically.
- See `ARCHITECTURE.md` for the high-level and subsystem design.

