# CDU Expert Modules — Starter (source templates)

**Canonical copies:** [`docs/expert/`](../docs/expert/)

---

## Domain modules (10–30)

Re-merge into `docs/expert/` with:

```powershell
python scripts/integrate_expert_modules.py
```

| Starter | Integrated |
|---------|------------|
| `10_Crude_Assay.md` | `docs/expert/10_Crude_Assay.md` |
| `20`–`30` | `docs/expert/20_*.md` … `30_*.md` |

---

## Platform intelligence (31–37, 90)

**Merged manually** into `docs/expert/` (do not overwrite via script):

| Starter | Integrated | Role |
|---------|------------|------|
| `31_HYSYS_Object_Map.md` | [`31_HYSYS_Object_Map.md`](../docs/expert/31_HYSYS_Object_Map.md) | COM abstraction |
| `32_State_Machine.md` | [`32_State_Machine.md`](../docs/expert/32_State_Machine.md) | Process flow + A–F |
| `33_Reasoning_Engine.md` | [`33_Reasoning_Engine.md`](../docs/expert/33_Reasoning_Engine.md) | Core loop |
| `34_Knowledge_Base.md` | [`34_Knowledge_Base.md`](../docs/expert/34_Knowledge_Base.md) | Rules + routing |
| `35_Experiment_Selection.md` | [`35_Experiment_Selection.md`](../docs/expert/35_Experiment_Selection.md) | One trial |
| `36_Learning_System.md` | [`36_Learning_System.md`](../docs/expert/36_Learning_System.md) | Memory |
| `90_Test_Cases.md` | [`90_Test_Cases.md`](../docs/expert/90_Test_Cases.md) | Validation |

Pseudocode: [`37_Expert_Pseudocode.md`](../docs/expert/37_Expert_Pseudocode.md)

Master architecture: [`00_System_Architecture.md`](../docs/expert/00_System_Architecture.md)

---

**Edit canonical copies in `docs/expert/`** for day-to-day PE authoring.
