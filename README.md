# Football Manager data extraction

Tools and guides for extracting player/staff data from Football Manager 26 and
Football Manager 27, plus a local profiles explorer.

**This repository contains no game data.** The extracted CSVs are gitignored;
regenerate them from your own copy of the game with the guides below. The
`csv*/README.md` files document each CSV's schema.

| Directory | What it contains |
|---|---|
| [`fm26/`](fm26/) | **FM26**: capture guide, offline DB parsers, BepInEx plugin, CSV schema docs |
| [`fm27/`](fm27/) | **FM27**: capture guide, offline DB parsers, scanner, `make_final.py` (dump → CSVs), CSV schema docs |
| [`fm27/explorer/`](fm27/explorer/) | **Profiles Explorer**: local web app — search/filter players, local face/logo packs, career history |
| [`tools/`](tools/) | Shared scripts: `fmdb.py` (decompress FM `.dat`), `fmsuperscout_to_csv.py` (dump→CSV), `extract_frames.py` (`.fmf` frames) |
| [`docs/reports/`](docs/reports/) | Research reports from the native DB reverse-engineering and tool survey |

## What the guides produce (local only)

| Dataset | Rows | Location |
|---|---|---|
| FM26 career players / staff | 106,770 / 53,536 | `fm26/csv/` |
| FM27 full database players / staff | 516,038 / 179,287 | `fm27/csv_515k/` |
| FM27 imported FM26 career players / staff | 106,770 / 53,536 | `fm27/csv/` |
| FM27 career history (season records) | 5,718,899 | `fm27/csv_515k/fm27_player_history.csv` |

Player CSVs include unique ID, name, DOB/age, nationality, club, division,
CA/PA, positions, foot, height, wage, contract, value, 8 hidden personality
attributes and 52 attributes. Human manager profiles were removed from all
exported CSVs.

## Profiles explorer

```bash
cd fm27/explorer
python3 server.py --port 8770     # or ./run.sh
# open http://127.0.0.1:8770
```

516,038 players, full-text search, filters, smart club aliases
(Real Madrid ↔ R. Madrid, PSG, Man City…), local faces/club logos, and
season-by-season history (club, competition, appearances, goals). It needs
`fm27/csv_515k/fm27_players.csv` (and `fm27_player_history.csv` for history)
generated locally; the SQLite databases are built from them on first run
(~1 min) and are gitignored.
See [`fm27/explorer/README.md`](fm27/explorer/README.md).

## How the data was pulled

Two routes, documented step by step in the guides below:

1. **Live (complete data; produces the CSVs above).** Read the loaded save
   from the running game's memory with FMSuperScout — the BepInEx plugin for
   FM26 (`fm26/tools/FMSuperScout.dll`) and the FMSuperScout Scanner for FM27
   (`fm27/tools/FMSuperScout.Scanner.exe`) — then convert the JSON dump with
   `tools/fmsuperscout_to_csv.py`.
2. **Offline (partial: names, DOB, nation, CA/age/position).** Decompress the
   shipped database with `tools/fmdb.py` and decode it with
   `fm2*/offline/parse_people.py` / `parse_summary.py` (field map in
   `field_dict.csv`). Used to cross-check the live dump.

The reverse-engineering notes and tool survey are in
[`docs/reports/`](docs/reports/). The step-by-step guides are below.

## Reproduce

* FM26: [`fm26/GUIDE.md`](fm26/GUIDE.md)
* FM27: [`fm27/GUIDE_FM27.md`](fm27/GUIDE_FM27.md)

Raw dumps (`fm27/work/*.json`), extracted CSVs, explorer databases and
face/logo packs all stay local and are excluded via `.gitignore`.

Bundled FMSuperScout binaries are MIT-licensed third-party software; see
[`THIRD_PARTY.md`](THIRD_PARTY.md).
