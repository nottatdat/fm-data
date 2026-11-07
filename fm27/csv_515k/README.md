# FM27 Full Database — CSV exports (516,038 players)

Source: **Football Manager 27** (`27.0.0+2493426`, Steam app `4530370`), new career with the
full custom database (England: 6 men's + 2 women's leagues, **both genders**), read live from
game memory with **FMSuperScout Scanner v1.7.3** (read-only; offsets pinned to `game_plugin.dll`
27.0.x). The setup screen estimated 515,420 players; the scan found 516,038.

**The human manager profile was removed from these exports** (the human-manager rows were
stripped and `meta.manager` was cleared). A sanitized raw dump is kept locally at
`../work/fmsuperscout_dump_515k_sanitized.json` (no manager profile; excluded from git).

## Files

| File | Rows | Cols | Description |
|---|---|---|---|
| `fm27_players.csv` | 516,038 | 94 | every player, CA/PA + 52 attributes |
| `fm27_staff.csv` | 179,287 | 53 | every staff member incl. 23 attributes |
| `fm27_people.csv` | 695,325 | 123 | players + staff, union of both column sets, `kind` column |
| `fm27_player_history.csv` | 5,718,899 | 8 | season-by-season history: season, club, competition, apps, goals, type |

Encoding UTF-8 with BOM (Excel-friendly), comma-delimited.

## Player columns

`id`, `name`, `age`, `dob`, `birthYear`, `birthDoy`, `nat`, `natId`, `club`,
`ownerClub`, `div`, `ca`, `pa`, `pos`, `posArr`, **`posNat`** (natural positions),
`foot`, `height`, `wage`, `expires`, `value`, `askingPrice`, `wageDemand`,
`listed`, `loanListed`, `notForSale`, `setForRelease`, `clubRep`, `worldRep`,
`teamType`, `gender`, `ownerTeamType`, the 8 hidden personality attributes
(`adaptability`…`controversy`) and 52 attributes (1–20) such as `Acceleration`,
`Pace`, `Finishing`, `Passing`, `Tackling`, `Vision`, `Determination`,
`Composure`, `Consistency`, `ImportantMatches`, `InjuryProneness`, `Versatility`,
plus goalkeeping.

## Staff columns

Basics plus `job`, `jobId`, `prefJob`, `jobPrefs`, `curRep`, `worldRep`, hidden
personality and 23 staff attributes in English (`Attacking`, `Defending`,
`Fitness`, `Possession`, `Technical`, `Tactical`, `Set Pieces`, `Determination`,
`Man Management`, `Motivating`, `Judging Player Ability`, `Judging Player
Potential`, `Judging Staff Ability`, `Negotiating`, `Tactical Knowledge`,
`Physiotherapy`, `Sports Science`, `Data Analysis`, `Working With Youngsters`,
`Goalkeeping Distribution`, `Goalkeeping Handling`, `Goalkeeping Shot Stopping`,
`Adaptability`).

## Career history

`fm27_player_history.csv` is decoded from FM27's `pl_hist_*` files: one row per
player-season with **season, club, competition, appearances, goals, senior/youth**
and loan parent club. Club/competition IDs were mapped to names using current
clubs/divisions; old clubs/competitions without current players show as
`Unknown … #ID`. Assists and match-level stats are not stored in these files.

For the interactive view (and per-player history CSV downloads), run the
`../explorer/` app.

## Validation (FM27-native database values)

| Player | CA | PA | Club |
|---|---|---|---|
| Kylian Mbappé | 192 | 197 | R. Madrid |
| Erling Haaland | 187 | 195 | Manchester City |
| Jude Bellingham | 181 | 188 | R. Madrid |
| Lionel Messi | 172 | 200 | Inter Miami CF |
| Cristiano Ronaldo | 145 | 195 | Al-Nassr |

These are FM27's own database values; the imported FM26 career had different
numbers (e.g. Haaland 184/195, Mbappé 195/197) — see `../csv/`.

## Reproduce

1. New game → Advanced Setup → Custom Setup: include all players (both genders),
   add the desired leagues. The count here was **515,420**.
2. Start the career and wait for the manager portal.
3. Enable both genders for the scanner:
   `<prefix>/drive_c/users/steamuser/AppData/Local/FMSuperScout/scan-config.json`
   → `{"db":"both"}`
4. Run `../scan.sh` (≈10 minutes, ~867 MB dump).
5. Sanitize and convert:
   ```bash
   python3 ../make_final.py
   ```
   This removes the manager rows, writes `fmsuperscout_dump_515k_sanitized.json`,
   and regenerates the three player/staff CSVs.
6. Build and export career history:
   ```bash
   python3 ../explorer/import_history.py
   python3 ../explorer/export_history.py fm27_player_history.csv
   ```

Full procedure and troubleshooting: `../GUIDE_FM27.md`.
