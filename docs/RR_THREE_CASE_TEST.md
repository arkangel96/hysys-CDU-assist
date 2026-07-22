# RR-only 3-case test (with popup/Messages capture)

> **Legacy simple-column validation:** RR ladder on SW Stripper — historical COM / Messages capture under **CDU Assist** product naming.

| Case | Action | State | Family | Propose | NH3 ppmw | RR | Physical | Popups | Messages |
|------|--------|-------|--------|---------|----------|----|----------|--------|----------|
| `RR_1_2.5` | Set RR Goal=2.5, Btms=12500 Active, solve | `E_acceptable` | `-` | `none` | 0.853 | 2.5 | True | - | [hysys_message|com:Trace] <bound method Trace of <COMObject <unknown>>> |
| `RR_2_1.2` | Set RR Goal=1.2, Btms=12500 Active, solve | `E_acceptable` | `-` | `none` | 3.53 | 1.2 | True | - | [hysys_message|com:Trace] <bound method Trace of <COMObject <unknown>>> |
| `RR_3_0.6` | Set RR Goal=0.6, Btms=12500 Active, solve | `E_acceptable` | `-` | `none` | 14.8 | 0.6 | True | - | [hysys_message|com:Trace] <bound method Trace of <COMObject <unknown>>> |
| `RESTORE` | Restore RR=2.5, Btms=12500 | `E_acceptable` | `-` | `none` | 0.853 | 2.5 | True | - | - |
