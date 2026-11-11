# FM24 CSVs (generated locally, never committed)

Produced by `fm24/save/parse_save.py` from an FM24 save (see `../GUIDE.md`).

`fm24_players.csv` has exactly the source columns of `fm27/csv_515k/fm27_players.csv`
(the explorer importer's columns), so the Profiles Explorer loads it unchanged.
`fm24_meta.json` records the save, its saved-at time, the in-game date and the column
status below.

| Status | Columns | Notes |
|---|---|---|
| **Exact** (checked against in-game profiles) | `id` (FM unique id), `name`, `dob`, `age`, `birthYear`, `birthDoy`, `nat`, `natId` (nation UID), `club`, `pos`/`posArr`/`posNat`, `foot`, `height`, `wage`, `expires`, 36 outfield + 11 goalkeeping attributes | attributes: 292/294 on-screen values equal across 8 players (2 misses within ±1 on a rounding boundary); height, contract end and wage 8/8 (`wage` is the exact weekly £, FM rounds it for display) |
| **Unverified** (decoded, not shown numerically in FM) | `ca`, `pa`, `value`, `Dirtiness`, `Consistency`, `ImportantMatches`, `InjuryProneness`, `Versatility`, 8 personality attributes | CA/PA agree with coach star ratings; personality agrees with FM's personality labels; `value` is FM's stored base valuation (£), which FM adjusts for display (see below) |
| **Blank** (not decoded) | `ownerClub`, `div`, `askingPrice`, `wageDemand`, `clubRep`, `worldRep`, `listed`, `loanListed`, `notForSale`, `setForRelease`, `ownerTeamType`, `transferDate`, `transferTo` | |

- `club` is blank for free agents and retired players, and for the few teams whose name
  is not decoded (some loan clubs); B/youth teams use their own name (e.g. "Rennes 2").
- `gender` is always `0`: FM24 has no women's football.
- `age` is computed from the save's in-game date, not today's date.
- Positions: `posNat` = rating 18–20 (natural), `posArr`/`pos` = rating 15+ (accomplished).
- `foot`: `Both` when both feet are 15+, otherwise the stronger foot.
- `nat` uses English names from `../save/nations_en.json` (nation UIDs from FMSuperScout,
  MIT; see `THIRD_PARTY.md`). 99.7 % of people in a tested save get a name.
- `wage`/`expires` are the player's current contract (~75 % of players with a club); blank
  for free agents and where no current contract is found.
- `value` is in the right range but is not FM's displayed transfer value: e.g. £1.31M vs
  "£1.3M", £38.6M vs "£26M–£39M", but £13.2M vs "£27M–£35M" for a 17-year-old prospect.
  Exactly 300,000,000 is a cap FM stores for top stars. Use it to compare players.
- Known gaps: ~2 % of active players have no ratings decoded yet (attributes/CA/PA blank),
  and FM keeps player records for some retired players without ratings.
