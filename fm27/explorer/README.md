# FM27 Profiles Explorer

A local, dependency-free web app to browse the **516,038-player FM27 database** with:

- search by name / club / nation / division (SQLite FTS5)
- filters: gender, nation, club, division, position, age, CA, PA, sort
- player profiles with **photos fetched live from Wikipedia**
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

## Wikipedia photos

`/api/photo/<player-id>` queries the Wikipedia API live (no server-side cache):
exact title first, then an `intitle:"..." footballer` search; the page title must
contain the player's surname. Thumbnails are loaded directly from Wikimedia.
Players without a matching Wikipedia page (regens/newgens) get an initials
avatar. Photo credit and a Wikipedia link are shown on the profile.
Photos © their authors via Wikipedia/Wikimedia; check the linked page for the license.

## API

| Endpoint | Description |
|---|---|
| `GET /api/stats` | player/club/division/nation counts |
| `GET /api/filters` | nations, top clubs/divisions, position counts |
| `GET /api/players?q=&nat=&club=&div=&pos=&gender=&min_ca=&max_ca=&min_pa=&min_age=&max_age=&sort=&order=&page=&per=` | paginated search |
| `GET /api/player/<id>` | full player record (all 94 columns + attributes) |
| `GET /api/history/<id>` | career history records + totals |
| `GET /api/history/<id>.csv` | history CSV download |
| `GET /api/photo/<id>` | live Wikipedia photo lookup |

`sort` ∈ `ca, pa, age, name, value, wage, height, reputation, id`.

## Notes

- The history comes from the **shipped 2700 database**, not the live save. Real
  players have it; regens generally do not.
- Club/competition names are inferred from current data, so a few historical
  competitions may be labelled `Unknown`.
- The player database is the full FM27 custom DB (England, 6 men's + 2 women's
  leagues, both genders) exported earlier; see `../csv_515k/`.
