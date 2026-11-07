# FM27 Profiles Explorer

A local, dependency-free web app to browse the **516,038-player FM27 database** with:

- search by name / club / nation / division (SQLite FTS5)
- filters: gender, nation, club, division, position, age, CA, PA, sort
- player profiles with **local faces** (sortitoutsi cutout megapack) and **club / competition / nation logos** (FMG Standard Logos)
- **career / league history**: season, club, competition, appearances, goals,
  senior/youth, loan parent club
- per-player history CSV download and a full-history CSV exporter

Built with Python's standard library only (`http.server`, `sqlite3`, `urllib`).
No Node/npm needed.

## Run

```bash
cd fm27/explorer
python3 server.py --port 8770
# or: ./run.sh
# open http://127.0.0.1:8770
```

First run builds two SQLite databases from the data in this repo / the FM27 install:

| Database | Size | Built from | Time |
|---|---|---|---|
| `data/fm27.db` | ~230 MB | `../csv_515k/fm27_players.csv` (516,038 players) | ~25 s |
| `data/history.db` | ~950 MB | FM27 `2700_fm/pl_hist_{index,id,dt}.dat` (5,718,899 season records) | ~30 s |

They are `.gitignore`d. If the game is not at the default Steam path, point the
history importer at the DB folder:

```bash
FM27_DB="/path/to/Football Manager 27/shared/data/database/db/2700/2700_fm" \
  python3 server.py
```

## Profile view

Clicking a player opens a full-screen, FM-style dashboard:

**Hero row** — portrait · facts + personality · attribute radar · position pitch
**Second row** — attribute columns · career history

- hero portrait at its native 250×250 resolution (no upscaling blur), on a
  club-colour gradient, with nation flag, club logo and division
- key facts (DOB, age, height, foot, contract, wage, value, asking price, reputation)
- CA/PA, position chips and personality bars
- 8-axis **attribute radar** (technique, mental, physical, defending, attacking, speed, aerial, goalkeeping)
- **position pitch** showing natural and accomplished positions
- Technical / Mental / Physical attribute columns with coloured bars
- full **career history** with club and competition logos + CSV download

Morale, condition, training, form and per-match stats are not present in the
exported database; the profile shows everything the data has.

## Club names and search

FM27 ships short/licensing-friendly club names. The explorer shows a canonical
display name and accepts many query forms:

| FM27 name | Display | Also matches |
|---|---|---|
| `R. Madrid` | Real Madrid | `madrid`, `r madrid`, `rm` |
| `A. Madrid` | Atlético Madrid | `atletico`, `atleti` |
| `A. Bilbao` | Athletic Bilbao | `athletic` |
| `FC Bayern München` | Bayern Munich | `bayern`, `bayern munchen` |
| `Casciavit Milano` | AC Milan | `milan`, `ac milan` |
| `Blu-neri Milano` | Inter Milan | `inter`, `internazionale` |
| `Paris Saint-Germain` | Paris Saint-Germain | `psg` |
| `Manchester City` | Manchester City | `man city` |
| `Manchester United` | Manchester United | `man utd`, `man united` |
| `Wolverhampton Wanderers` | Wolves | `wolverhampton` |
| `Tottenham Hotspur` | Tottenham Hotspur | `spurs` |
| `1. FC Köln` | FC Köln | `koln`, `cologne` |

Matching is accent-insensitive, accepts prefixes (`dortmund`),
city exonyms (`munich`/`münchen`, `lisbon`/`lisboa`), acronyms (`psg`, `rm`)
and common nicknames. The Club dropdown lists the 500 most-populated clubs;
typing any other club still resolves against all 30,387 clubs. The global
search box (`q`) uses the same alias text, so `Real Madrid` also finds the
club's players there.

## Career history

The shipped FM27 database stores a 44-byte record per player-season. Decoded layout:

| Offset | Field |
|---|---|
| 0 | season start year (u16) |
| 2 | season end year (u16) |
| 4 | record type: `0x40` senior, `0x42` youth |
| 5 | appearances (u8) |
| 6 | goals (u8) |
| 11 | club ID (u32) |
| 15 | parent club ID (u32; differs on loans) |
| 19 | competition ID (u32) |
| 23 | parent competition ID (u32) |
| 29 | 3 × date (u16 day, u16 year; usually null `1/1900`) |

Club and competition IDs are mapped to names by voting with the current
club/division of the players in `fm27/csv_515k/fm27_players.csv`
(weighted by appearances and CA, so senior league names win over youth leagues).
Old clubs/competitions with no current players show as `Unknown club #ID` /
`Unknown competition #ID`. Assists and match-level stats are **not** present in
`pl_hist` — the game only stores appearances and goals there.

Export the complete history (all 5.7M records, ~490 MB CSV):

```bash
python3 export_history.py ../csv_515k/fm27_player_history.csv
```

## Faces and logos (local packs)

No web crawling: the explorer reads two local packs.

* **Faces** — sortitoutsi Cutout Megapack 2027:
  `sortitoutsi/faces/face_<player_id>.png` (558,430 images).
* **Logos** — FMG Standard Logos 2026:
  `Clubs/Normal/<club_id>_club.png`, `Competitions/Normal/<competition_id>_comp.png`,
  `Nations/Normal/<nation_id>_nation.png`.

Extract them under `fm27/explorer/assets/`:

```bash
mkdir -p assets
unrar x -o+ -y -idq "../sortitoutsi_cutout_megapack_2027.00.rar" "sortitoutsi/faces/*" assets/
unzip -q -o "../FMG Standard Logos 2026.00.zip" \
  "FMG Standard Logos 2026.00/Clubs/Normal/*" \
  "FMG Standard Logos 2026.00/Competitions/Normal/*" \
  "FMG Standard Logos 2026.00/Nations/Normal/*" \
  "FMG Standard Logos 2026.00/Confederations/Normal/*" \
  "FMG Standard Logos 2026.00/Default/*" -d assets/logos/
```

The `assets/` tree (~21 GB) and the archives are gitignored. Missing faces fall back
to initials; missing logos are hidden. Faces © their authors via sortitoutsi;
logos © their authors via FMG.

## API

| Endpoint | Description |
|---|---|
| `GET /api/stats` | player/club/division/nation counts |
| `GET /api/filters` | nations, top clubs/divisions, position counts |
| `GET /api/players?q=&nat=&club=&div=&pos=&gender=&min_ca=&max_ca=&min_pa=&min_age=&max_age=&sort=&order=&page=&per=` | paginated search |
| `GET /api/player/<id>` | full player record (all 94 columns + attributes) |
| `GET /api/history/<id>` | career history records + totals |
| `GET /api/history/<id>.csv` | history CSV download |
| `GET /api/face/<id>` | player face from the cutout pack |
| `GET /api/player-club-logo/<id>` | current club logo |
| `GET /api/club-logo/<id>` | club logo by club ID |
| `GET /api/comp-logo/<id>` | competition logo by competition ID |
| `GET /api/nation-logo/<id>` | nation logo by nation ID |

`sort` ∈ `ca, pa, age, name, value, wage, height, reputation, id`.

## Notes

- The history comes from the **shipped 2700 database**, not the live save. Real
  players have it; regens generally do not.
- Club/competition names are inferred from current data, so a few historical
  competitions may be labelled `Unknown`.
- The player database is the full FM27 custom DB (England, 6 men's + 2 women's
  leagues, both genders) exported earlier; see `../csv_515k/`.
