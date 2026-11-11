# FM26 Player Data — CSV exports

> Schema documentation only: the CSV files themselves are generated locally and not committed.

Source: a saved Argentine national-team career loaded in Football Manager **26.3.2**,
read from live game memory with **FMSuperScout v0.1.46** (BepInEx).
The human manager profile was **removed** from the exported data.

Stats: **106,770 players**, **53,536 staff** (2 manager rows removed).
The raw dump was deleted after sanitization; the CSVs are the deliverable.
See `../GUIDE.md` for the capture procedure.

## Files

| File | Rows | Cols | Description |
|---|---|---|---|
| `fm26_players.csv` | 106,770 | 89 | Every player found in the loaded save |
| `fm26_staff.csv` | 53,536 | 39 | Every non-playing staff member |
| `fm26_people.csv` | 160,306 | 114 | Players + staff with a `kind` column |

Encoding UTF-8 with BOM (Excel-friendly), comma delimiter.

## Player columns

Basics: `id` (FM unique ID), `name`, `age`, `dob`, `birthYear`, `birthDoy`,
`nat` (nationalities, `;`-separated), `natId`, `club`, `ownerClub` (loan parent
when on loan), `div` (division), `ca`, `pa`, `pos` (text), `posArr`,
`foot`, `height` (cm), `wage`, `expires`, `value`, `askingPrice`,
`wageDemand`, `listed`, `loanListed`, `notForSale`, `setForRelease`,
`clubRep`, `worldRep`, `teamType`.

Hidden personality: `adaptability`, `ambition`, `loyalty`, `pressure`,
`professionalism`, `sportsmanship`, `temperament`, `controversy`.

52 visible/hidden attributes (1–20), including `Acceleration`, `Pace`,
`Finishing`, `Passing`, `Tackling`, `Vision`, `Determination`, `Composure`,
`Consistency`, `ImportantMatches`, `InjuryProneness`, `Versatility`, plus
goalkeeping (`Handling`, `Reflexes`, `OneOnOnes`, …).

## Staff columns

Basics as above plus `job`, `jobId`, `gender`, `clubRep` and 22 staff attributes
(English FM labels: `Attacking`, `Defending`, `Fitness`, `Possession`,
`Technical`, `Tactical`, `Set Pieces`, `Determination`, `Man Management`,
`Motivating`, `Judging Player Ability`, `Judging Player Potential`,
`Judging Staff Ability`, `Negotiating`, `Tactical Knowledge`, `Physiotherapy`,
`Sports Science`, `Data Analysis`, `Working With Youngsters`,
`Goalkeeping Distribution`, `Goalkeeping Handling`, `Goalkeeping Shot Stopping`).

## Validation

| Player | CA | PA | Club |
|---|---|---|---|
| Kylian Mbappé | 195 | 197 | R. Madrid |
| Harry Kane | 188 | 190 | FC Bayern München |
| Ousmane Dembélé | 186 | 188 | Paris Saint-Germain |
| Erling Haaland | 184 | 195 | Manchester City |
| Jude Bellingham | 176 | 188 | R. Madrid |
| Lionel Messi | 172 | 200 | Inter Miami CF |
