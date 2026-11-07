# Football Manager 27 — extracted data

Source: Football Manager **27.0.0+2493426** (Steam app `4530370`), read from the
loaded game with the external **FMSuperScout Scanner v1.7.3**, plus the shipped
`2700` database's player-history files. Human manager profiles were removed from
the exports.

## Datasets

| Path | Players | Staff | Contents |
|---|---|---|---|
| **`csv_515k/`** | **516,038** | 179,287 | **Full FM27 custom database** (England, 6 men's + 2 women's leagues, both genders), 94 player columns |
| `csv/` | 106,770 | 53,536 | The career imported from FM26, running on FM27 — same player IDs as FM26, FM27 values/positions |
| `csv_515k/fm27_player_history.csv` | — | — | **5,718,899 season records**: season, club, competition, apps, goals, senior/youth, loan parent |

Both player sets include CA/PA, all 52 attributes, hidden personality, positions
(`pos` / `posArr` / `posNat`), contracts, wages, values, clubs and divisions.
Manager profiles (`meta.manager`) were stripped.

| Path | Contents |
|---|---|
| `explorer/` | Local **Profiles Explorer** web app (search, filters, Wikipedia photos, career history) |
| `offline/` | Offline extracts from the shipped `2700` database: 211,880 people name+DOB, 30,871 with CA/age/position, field codes, parsers |
| `work/` | Sanitized raw dump `fmsuperscout_dump_515k_sanitized.json` (867 MB, **local only — excluded from git**) and status files |
| `tools/` | `FMSuperScout.Scanner.exe` (v1.7.3, Windows/Proton) |
| `GUIDE_FM27.md` | Step-by-step capture procedure, including the full-database/both-genders route |
| `scan.sh` | Runs the scanner against the running FM27 |
| `make_final.py` | Removes the manager profile and writes `csv_515k/` from a raw dump |

See [`csv_515k/README.md`](csv_515k/README.md), [`csv/README.md`](csv/README.md)
and [`explorer/README.md`](explorer/README.md).
For FM26 data see [`../fm26/`](../fm26/).
