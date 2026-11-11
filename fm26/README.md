# Football Manager 26 — extracted data

Source: Football Manager **26.3.2** (Steam app `3551340`), read from a loaded
career with FMSuperScout (BepInEx plugin). The human manager profile was removed
from the exports.

> The CSVs listed here are **generated locally and not committed** (`*.csv` is
> gitignored). The figures describe what the guide produces.

| Path | Contents |
|---|---|
| `csv/` | **106,770 players**, **53,536 staff** — CA/PA, 52 attributes, hidden personality, contracts, values, clubs (`fm26_players.csv`, `fm26_staff.csv`, `fm26_people.csv`) |
| `offline/` | Offline extracts from the shipped `2620` database: 216,348 people with name+DOB, 30,901 with CA/age/position, 2,103 editor field codes, parser scripts |
| `tools/` | `FMSuperScout.dll` (FM26 BepInEx plugin) and `xtest.py` (X11 input helper) |
| `GUIDE.md` | Step-by-step capture procedure |
| `fmsuperscout_status.json` | Dump status (106,770 players / 53,538 staff before sanitization) |

See [`csv/README.md`](csv/README.md) for columns and validation.
For FM27 data see [`../fm27/`](../fm27/).
