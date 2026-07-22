# Test Cases

**Module ID:** 90  
**Parent:** [`00_System_Architecture.md`](00_System_Architecture.md)  
**Reference column:** `T-100` — [`../cdu_com_discovery.md`](../cdu_com_discovery.md)

Integrated from `CDU_Expert_Modules_Starter/90_Test_Cases.md` + T-100 baseline.

Each module requires validation scenarios. Each test documents: initial condition, expected diagnosis, expected experiment, expected response, acceptance criteria.

---

## Scenario library (generic — all modules)

| Scenario | Expected diagnosis area | Expected experiment family |
|----------|-------------------------|----------------------------|
| Wrong crude assay | State A / module 10 | Fix assay — no MV |
| Heater outlet too low | 22 / flash feed | Furnace / feed (Cat-2) |
| Heater outlet too high | 22 / coke risk | Furnace (Cat-2) |
| Flash-zone pressure too high | 23 | Flash / pressure |
| Flooding | 30 | Hydraulics — no blind MV |
| Poor diesel endpoint | 27 + 25 | PA or draw per rule |
| Excess furnace duty | 29 + 22 | Energy optimization |

---

## T-100 — baseline (2026-07-21)

| Item | Value |
|------|--------|
| Column | T-100, 29 stages, feed ~28 |
| DOF | 0 |
| Converged (residuals) | Yes |
| Physical (CDU gates) | **Not verified** — product stream reads pending |
| Active families | SS prod flows, PA rate+duty, naphtha rate, liquid flow, kero reboil |

### FINAL_TARGETs (PE to fill)

| Product | Target | Source | Locked |
|---------|--------|--------|--------|
| Naphtha | TBD | ASTM / RVP | Yes |
| Kerosene | TBD | Flash / D86 | Yes |
| Diesel | TBD | D86 95% | Yes |
| AGO | TBD | TBP / cut | Yes |
| Residue | TBD | Yield / property | Yes |

### Test case template (per scenario)

```text
Test ID:
Initial condition:
Engineering state (A-F):
Process state (1-10):
Expected hypotheses (rule IDs):
Expected experiment (strategy_id):
Predicted response:
Actual response (after live run):
Acceptance criteria:
Pass/Fail:
```

### Successful PE path to State E (to record)

1. Starting state: …  
2. FINAL_TARGETs: …  
3. Trials (strategy_id, keep/reverse): …  
4. End state definition: …  

---

## Validation workflow

1. Run scenario on T-100 (or dedicated test case file)  
2. Compare diagnosis + selected experiment to expected  
3. Log in Trial Map — feeds [`36_Learning_System.md`](36_Learning_System.md)  
4. Update domain module rules if PE disagrees with automation  

---

*Test cases · CDU Expert System*
