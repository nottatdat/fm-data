# Football Manager data extraction

Extracted player/staff data from Football Manager 26 and Football Manager 27,
kept in separate directories, plus a local profiles explorer.

| Directory | What it contains |
|---|---|
| [`fm26/`](fm26/) | **FM26**: 106,770-player career CSV set, offline DB extracts, capture guide, BepInEx plugin |
| [`fm27/`](fm27/) | **FM27**: full **516,038-player** database CSV set, career history, imported-FM26 career set, offline DB extracts, capture guide, scanner |
| [`fm27/explorer/`](fm27/explorer/) | **Profiles Explorer**: local web app — search/filter players, local face/logo packs, career history |
| [`tools/`](tools/) | Shared scripts: `fmdb.py` (decompress FM `.dat`), `fmsuperscout_to_csv.py` (dump→CSV), `extract_frames.py` (`.fmf` frames) |
| [`docs/reports/`](docs/reports/) | Research reports from the native DB reverse-engineering and tool survey |

## Data at a glance

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

516,038 players, full-text search, filters, local faces/club logos, and
season-by-season history (club, competition, appearances, goals). The SQLite
databases are built on first run (~1 min) and are gitignored.
See [`fm27/explorer/README.md`](fm27/explorer/README.md).

## Reproduce

* FM26: [`fm26/GUIDE.md`](fm26/GUIDE.md)
* FM27: [`fm27/GUIDE_FM27.md`](fm27/GUIDE_FM27.md)

The large sanitized raw dump (`fm27/work/fmsuperscout_dump_515k_sanitized.json`,
867 MB) is kept locally but excluded from git via `.gitignore`; the derived CSVs
are committed.
