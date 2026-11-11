# FM27 Player Data Capture — Step-by-Step Guide

> All commands are run from the repository root.

Reproduces `fm27/csv/`: **106,770 players + 53,538 staff** with CA/PA, all attributes,
hidden personality, contracts, values and clubs, read from a loaded Football Manager 27 save.

Two routes are covered:

* **A. Offline** — mine the database shipped with FM27 (no game running). Gives names, DOB,
  nation refs, CA/age/position for ~31k people.
* **B. Live** — read the loaded save from memory with **FMSuperScout Scanner** (complete data).
  This is what produced the CSVs in `fm27/csv/`.

Tested on: **FM27 27.0.0+2493426**, Steam app `4530370`, Linux + Proton Experimental.
The scanner's offsets are pinned to `game_plugin.dll` **27.0.x**; a game update needs a
matching scanner release.

---

## A. Offline database extraction (no game needed)

The FM27 `.dat` files use the same zstd container as FM26.

```bash
GAME="/mnt/data/SteamLibrary/steamapps/common/Football Manager 27"
DB="$GAME/shared/data/database/db/2700/2700_fm"     # 2700 = FM27.0 database

cd ~/src/fm-data
python3 tools/fmdb.py "$DB/people_db.dat"       fm27/work/people_db.raw
python3 tools/fmdb.py "$DB/basic_people_db.dat" fm27/work/basic_people_db.raw
cp "$DB/summary.dat" fm27/work/summary.raw

# names + DOB + nation ref (211,880 people)
python3 fm27/offline/parse_people.py fm27/work/people_db.raw fm27/offline/players_people.csv

# CA / age / position from summary.dat (30,871 people)
SUMMARY_RAW=fm27/work/summary.raw BASIC_RAW=fm27/work/basic_people_db.raw \
  python3 fm27/offline/parse_summary.py
```

Outputs in `fm27/offline/`: `players_people.csv`, `players_summary.csv`,
`basic_people_db_parsed.csv`. The raw `.raw` files can be deleted afterwards.

---

## B. Live full extraction (the CSVs in `fm27/csv/`)

### B1. Prepare FM27

1. Install/launch FM27 normally through Steam. The first launch processes the shader cache
   (Steam shows *Processing shaders*; it can take several minutes — wait it out).
2. Load a career (or import an FM24/FM26 save via **Load Game**). Wait until the manager
   portal is fully loaded — the scanner only sees what is in memory.

### B2. Put the scanner inside the FM27 prefix

The scanner is a self-contained Windows `.exe` (`FMSuperScout.Scanner.exe`, ~10 MB).
Either run the FMSuperScout installer inside the FM27 prefix, or simply copy the exe:

```bash
PREFIX=/mnt/data/SteamLibrary/steamapps/compatdata/4530370/pfx
mkdir -p "$PREFIX/drive_c/FMSuperScout"
cp fm27/tools/FMSuperScout.Scanner.exe "$PREFIX/drive_c/FMSuperScout/"
```

(If installing from `FMSuperScout-Setup.exe`, run it with the same Proton prefix and
`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`.)

### B3. Run the scanner on Linux/Proton — important

Do **not** use `proton run` for the scanner: that starts a separate Wine session and the
scanner reports *"Football Manager is not running"*. Run the **host Proton Wine binary
outside the pressure-vessel container**; it then connects to the game's wineserver and sees
`fm.exe`:

```bash
PREFIX=/mnt/data/SteamLibrary/steamapps/compatdata/4530370/pfx
PROTON_DIR="/home/dat/.local/share/Steam/steamapps/common/Proton - Experimental"
export WINEPREFIX="$PREFIX" WINEDEBUG=-all
export LD_LIBRARY_PATH="$PROTON_DIR/files/lib/x86_64-linux-gnu:$PROTON_DIR/files/lib/i386-linux-gnu:$PROTON_DIR/files/lib"
"$PROTON_DIR/files/bin/wine" 'C:\FMSuperScout\FMSuperScout.Scanner.exe' scan
```

This is exactly what `fm27/scan.sh` does:

```bash
fm27/scan.sh
```

The scan reads ~2–3 GB and takes **3–4 minutes** on the reference machine (the Wine RPC
path is slower than native Windows; FM26's in-process plugin took ~6 s).

### B4. Check and collect the dump

Output lands in the FM27 prefix at:

```
<pfx>/drive_c/users/steamuser/AppData/Local/FMSuperScout/
├── status.json          {"state":"done","players":106770,"staff":53538,...}
├── dump.json            full database (~195 MB)
└── diagnostics.txt      scan regions, versions, timings
```

Wait for `"state":"done"` and copy the dump:

```bash
P=/mnt/data/SteamLibrary/steamapps/compatdata/4530370/pfx/drive_c/users/steamuser/AppData/Local/FMSuperScout
cp "$P/dump.json" fm27/work/fmsuperscout_dump.json
```

### B5. Convert to CSV

```bash
python3 tools/fmsuperscout_to_csv.py fm27/work/fmsuperscout_dump.json fm27/csv
```

The converter detects `meta.game == "FM27"` and writes `fm27_players.csv`,
`fm27_staff.csv`, `fm27_people.csv`. It includes every scalar field the dump has,
so FM27-only fields (`posNat`, `prefJob`, `jobPrefs`, `curRep`, `worldRep`) and the
new staff attribute (`Adaptability`) are preserved.

The delivered `fm27/csv/` CSVs have the human-manager rows removed.
This produces the imported-career set (106,770 players). For the **full FM27 database**
(516,038 players, both genders) see section E.

---

## C. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Steam hangs on **Processing shaders** | First-run shader cache. Wait; do not kill it. |
| Scanner log says *fm.exe draait niet* | Scanner was launched via `proton run` (separate wineserver), or FM is not running. Use the host Wine command in B3. |
| Scanner says game is running as administrator | Start FM normally (not elevated). |
| `status.json` = error / 0 players | No save loaded (main menu), or scan failed. Load the career and rerun. |
| `meta.versionOk` false / warning about layout | `game_plugin.dll` is not 27.0.x. Update FMSuperScout Scanner to the release pinned for your game version. |
| Women's players missing | Scanner defaults to men. Create `scan-config.json` in the FMSuperScout data dir: `{"db":"both"}` then rerun. |

## D. What changed vs the FM26 dump

The FM27 career was imported from FM26. The person set is identical (106,770 IDs;
CA/PA/attributes/height unchanged). FM27 only applied date/DB updates on import:
ages +1 for players whose birthday passed (13,172), re-valued 17,241 players,
35 club changes, and `pos` now includes accomplished positions (`posNat` = natural).
Details: `fm27/csv/README.md`.

## E. Full database capture (516,038 players)

This produced `fm27/csv_515k/` — a new FM27 career using the full custom database,
with both men's and women's players.

1. **New game → Advanced Setup.** Add the nations/leagues you want. In the reference
   run: England, 6 men's leagues + 2 women's leagues, both genders; the setup estimated
   **515,420 players**.
2. **Start the career** and wait until the manager portal is fully loaded.
3. **Tell the scanner to include both genders.** In the FMSuperScout data dir:

   ```bash
   P=/mnt/data/SteamLibrary/steamapps/compatdata/4530370/pfx/drive_c/users/steamuser/AppData/Local/FMSuperScout
   printf '{"db":"both"}' > "$P/scan-config.json"
   ```

4. **Scan.** `fm27/scan.sh` — reference run: **516,038 players + 179,289 staff**,
   ~10 minutes, 867 MB `dump.json`.
5. **Sanitize + convert.** `python3 fm27/make_final.py`:
   - removes the human manager profile (identified from `meta.manager` / `meta.managers`;
     extra names/ids can be supplied via `DROP_NAMES` / `DROP_IDS`) from players/staff,
   - clears `meta.manager` / `meta.managers`,
   - writes `fm27/work/fmsuperscout_dump_515k_sanitized.json` (no manager profile),
   - writes `fm27/csv_515k/fm27_{players,staff,people}.csv`.

   Edit the `names`/`ids` sets at the top of `make_final.py` if the manager name differs.

Columns and validation: `fm27/csv_515k/README.md`.
