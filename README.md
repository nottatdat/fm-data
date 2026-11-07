# Football Manager data extraction

Extracted player/staff data from Football Manager 26 and Football Manager 27,
kept in separate directories.

| Directory | What it contains |
|---|---|
| [`fm26/`](fm26/) | **FM26**: 106,770-player career CSV set, offline DB extracts, capture guide, BepInEx plugin |
| [`fm27/`](fm27/) | **FM27**: full **516,038-player** database CSV set, the imported-FM26 career set, offline DB extracts, capture guide, scanner |
| [`tools/`](tools/) | Shared scripts: `fmdb.py` (decompress FM `.dat`), `fmsuperscout_to_csv.py` (dump→CSV), `extract_frames.py` (`.fmf` frames) |
| [`docs/reports/`](docs/reports/) | Research reports from the native DB reverse-engineering and tool survey |

## Data at a glance

| Dataset | Players | Staff | Location |
|---|---|---|---|
| FM26 career | 106,770 | 53,536 | `fm26/csv/` |
| FM27 full database | 516,038 | 179,287 | `fm27/csv_515k/` |
| FM27 imported FM26 career | 106,770 | 53,536 | `fm27/csv/` |

CSVs are UTF-8 with BOM, comma-delimited. Player rows include unique ID, name,
DOB/age, nationality, club, division, CA/PA, positions, foot, height, wage,
contract, value, 8 hidden personality attributes and 52 attributes.

Human manager profiles were removed from all exported CSVs.

## Reproduce

* FM26: [`fm26/GUIDE.md`](fm26/GUIDE.md)
* FM27: [`fm27/GUIDE_FM27.md`](fm27/GUIDE_FM27.md)

The large sanitized raw dump (`fm27/work/fmsuperscout_dump_515k_sanitized.json`,
867 MB) is kept locally but excluded from git via `.gitignore`; the derived CSVs
are committed.
