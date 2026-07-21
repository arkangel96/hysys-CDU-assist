# Architecture — CDU Assist

External COM assist for **atmospheric crude distillation (CDU)** in Aspen HYSYS.
Simple-column stripper logic and VDU are out of scope (separate tools). See
`docs/SCOPE_CDU_ASSIST.md`.

## High level

The application is an external Windows desktop client for Aspen HYSYS. Aspen
HYSYS remains the simulation and thermodynamics engine; this application reads
and writes supported HYSYS objects through the Windows COM automation API.

```text
PyQt5 desktop UI
    -> application/service layer
        -> HYSYS COM adapter (pywin32)
            -> Aspen HYSYS case
```

## Subsystems

### 1. Desktop interface

- Connection toolbar: connect, refresh, solve, auto-refresh, export.
- Component setup: automatic detection with a manual-name fallback.
- Stream inspector: selector, property cards, editable inputs and composition.
- Operations table: operation name, type and solved state.
- Analytics: temperature, pressure and molar-flow charts.
- Column Assistant: CDU-oriented inspect / diagnose / specs / trial map.
- Activity log and visible error messages.

### 2. HYSYS adapter

- Attaches to a running HYSYS instance or starts one.
- Uses the active case, or opens a selected `.hsc` case.
- Enumerates fluid-package components, material streams and operations.
- Reads stream conditions and composition / petroleum properties (as available).
- Writes only explicitly supported specifications.
- Requests a case solve and reports COM errors without hiding them.

### 3. Application/service layer

- Converts COM objects into plain Python records for the UI.
- Keeps units and display formatting outside the COM adapter.
- Coordinates refresh, trial snapshot/restore, and export operations.
- Prevents UI code from depending directly on HYSYS COM objects.

### 4. Export

- Creates an Excel workbook with Streams, Composition and Operations sheets.

## Safety boundaries

- A write can fail when HYSYS calculates that property from another
  specification or unit operation. The application displays the failure and
  leaves the case unchanged.
- Automatic refresh only reads data.
- Editing and solving require an explicit user action.
- HYSYS files are not automatically saved or overwritten.
- First strategy family must not add Active specs when DOF is already zero.
- FINAL_TARGETs (cuts / ASTM / TBP) are never auto-relaxed to fake success.

## First-release scope (v0.1)

- Windows only for live HYSYS connectivity.
- Steady-state inspection and basic stream specification edits.
- Column Assistant: inspect specs/DOF/profiles, diagnose States A–F, and run
  bounded GoalValue trials with keep/reverse on Category-1 CDU MVs
  (draws, PA, reflux/OH, side-strip, overflash — after COM discovery).
- No silent structural edits, dynamic-mode controls, case persistence or bulk writes.

## Build phases

See `docs/SCOPE_CDU_ASSIST.md` — Phase 0 identity → Phase 1 COM discovery →
Phase 2 inspect/diagnose → Phase 3 Trial Map → Phase 4 intelligence → Phase 5 live validation.
