# FM27 Imported-Career Exports (106,770 players)

Source: **Football Manager 27** (`27.0.0+2493426`, Steam app `4530370`) running the
career imported from FM26 — the same Argentine national-team save. Read live from game
memory with **FMSuperScout Scanner v1.7.3**.

The human manager profile was **removed** from the exported data. The raw dump was
deleted after sanitization.

Stats: **106,770 players**, **53,536 staff** (2 manager rows removed).

## Files

| File | Rows | Cols | Description |
|---|---|---|---|
| `fm27_players.csv` | 106,770 | 93 | every player, CA/PA + 52 attributes |
| `fm27_staff.csv` | 53,536 | 53 | staff incl. 23 attributes + `prefJob/jobPrefs/curRep/worldRep` |
| `fm27_people.csv` | 160,306 | 122 | players + staff, union of both column sets, with a `kind` column |

UTF-8 with BOM, comma-delimited.

## Columns

Player basics: `id`, `name`, `age`, `dob`, `birthYear`, `birthDoy`, `nat`, `natId`,
`club`, `ownerClub`, `div`, `ca`, `pa`, `pos`, `posArr`, **`posNat`**, `foot`,
`height`, `wage`, `expires`, `value`, `askingPrice`, `wageDemand`, `listed`,
`loanListed`, `notForSale`, `setForRelease`, `clubRep`, `worldRep`, `teamType`,
`gender`; the 8 hidden personality attributes and 52 visible/hidden attributes.

Staff adds `job`, `jobId`, `prefJob`, `jobPrefs`, `curRep`, `worldRep` and 23
staff attributes (English labels).

## FM27 vs FM26 — same data

This is the same career as the FM26 export: 106,770 identical player IDs, names,
CA/PA, height and attributes. FM27 only applied import/date effects:

* `age` +1 for 13,172 players (game date advanced),
* 17,241 players re-valued,
* `pos` now includes accomplished positions; `posNat` holds natural positions,
* 35 club changes.

## Validation

| Player | CA | PA | Club |
|---|---|---|---|
| Kylian Mbappé | 195 | 197 | R. Madrid |
| Harry Kane | 188 | 190 | FC Bayern München |
| Erling Haaland | 184 | 195 | Manchester City |
| Jude Bellingham | 176 | 188 | R. Madrid |
| Lionel Messi | 172 | 200 | Inter Miami CF |
| Cristiano Ronaldo | 155 | 195 | Al-Nassr |

For the **full FM27 database** (516,038 players), see `../csv_515k/`.
