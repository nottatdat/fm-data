# FM26 Player Data Capture — Step-by-Step Guide

> All commands are run from the repository root.

> For **Football Manager 27**, see [`../fm27/GUIDE_FM27.md`](../fm27/GUIDE_FM27.md) and the
> generated data in `../fm27/csv/` (full database: `../fm27/csv_515k/`).

This guide reproduces the extraction in `fm26/csv/`: **106,770 players + 53,538 staff**
from a loaded Football Manager 26 save, including CA/PA, all 52 attributes,
hidden personality, contracts, values and clubs.

Primary method: **FMSuperScout** — a BepInEx plugin that reads the database from
the running game's memory and writes `dump.json`. No save-file decryption is
needed, and no GUI clicking (the dump can be triggered with a file).

---

## 0. What you need

| Item | Details |
|---|---|
| Football Manager 26 | Steam app **3551340**, game version **26.3.2** (plugin offsets are pinned to **26.3.x**) |
| BepInEx 6 | The FM26 build: `BepInExPack_FootballManager26` from Thunderstore |
| FMSuperScout | Plugin `FMSuperScout.dll` v0.1.46 — `github.com/mavarobli/FMSuperScout` (a copy is kept in `fm26/tools/FMSuperScout.dll`) |
| Python 3 | For the JSON→CSV step (no third-party packages needed) |
| A loaded save | The plugin only dumps what is currently in game memory |

> **Version rule:** the plugin's memory offsets are pinned per game patch.
> `dump.json` → `meta.versionOk` tells you whether the game version matched.
> If FM/`game_plugin.dll` updates past 26.3.x, wait for a plugin update or
> re-pin the offsets before trusting the numbers.

---

## 1. Install BepInEx into FM26

1. Download the FM26 BepInEx pack:
   `https://new.thunderstore.io/c/football-manager-26/p/BepInEx/BepInExPack_FootballManager26/`
2. Close FM26. Unzip the pack directly into the game folder so you get:

   ```
   Football Manager 26/
   ├── BepInEx/
   ├── dotnet/
   ├── winhttp.dll
   ├── doorstop_config.ini
   ├── .doorstop_version
   ├── changelog.txt
   └── fm.exe
   ```

   * Windows default: `C:\Program Files (x86)\Steam\steamapps\common\Football Manager 26\`
   * Linux/Proton:
     `~/.local/share/Steam/steamapps/common/Football Manager 26/`
3. **Linux only** — set the Steam launch option for FM26
   (right-click FM26 → Properties → Launch Options):

   ```
   WINEDLLOVERRIDES="winhttp=n,b" %command%
   ```

4. Launch FM26 once. The first start takes **1–3 minutes longer** (BepInEx
   generates IL2CPP interop bindings; a black console window is normal).
   Quit the game afterwards. Confirm `BepInEx/plugins/` now exists.

---

## 2. Install the FMSuperScout plugin

With the game closed, copy `FMSuperScout.dll` into the plugins folder:

```bash
# Linux/Proton
cp fm26/tools/FMSuperScout.dll \
   ~/.local/share/Steam/steamapps/common/"Football Manager 26"/BepInEx/plugins/
```

```powershell
# Windows
copy FMSuperScout.dll "C:\Program Files (x86)\Steam\steamapps\common\Football Manager 26\BepInEx\plugins\"
```

If you do not have the DLL, get it from the repo (`plugin/dist/FMSuperScout.dll`)
or build it with `dotnet build plugin/FMSuperScout.csproj -c Release`.

Verify the plugin loads: start the game and check `BepInEx/LogOutput.log` for

```
[Info :FMSuperScout] FMSuperScout 0.1.46 geladen. Druk in de game op F9 om te dumpen.
```

---

## 3. Load the save you want to capture

Start FM26 and load the career. Wait until the game world is fully loaded
(main menu / loading screens are not enough — `game_plugin.dll` must be active).
The dump captures **all** players and staff in the loaded database, not just
your squad.

---

## 4. Trigger the dump

### Option A — in-game hotkey
Press **F9** in the game. A dump of ~100k players takes several seconds
(6 s on the reference machine). The log reports progress.

### Option B — scripted (no clicking, recommended for automation)
The plugin polls a request file once per second. Write the current Unix time in
milliseconds into it:

```bash
# Linux/Proton path (maps to C:\users\steamuser\AppData\Local\FMSuperScout)
D=~/.local/share/Steam/steamapps/compatdata/3551340/pfx/drive_c/users/steamuser/AppData/Local/FMSuperScout
mkdir -p "$D"
date +%s%3N > "$D/request.flag"
```

```powershell
# Windows path
$d = "$env:LOCALAPPDATA\FMSuperScout"
New-Item -ItemType Directory -Force $d | Out-Null
[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() | Set-Content "$d\request.flag"
```

The flag is consumed and deleted automatically. A flag older than 2 minutes is
ignored (stale-request protection).

### Check the result

The plugin writes into the same folder:

| File | Meaning |
|---|---|
| `status.json` | `{"state":"done","players":106770,"staff":53538,"at":"..."}` |
| `dump.json` | the full database (hundreds of MB) |
| `diagnostics.txt` | scan details, version check, phase timings |

Wait until `status.json` says `"state":"done"` and `dump.json` stops growing.

**Optional — include the women's database.** The default scan is men only.
Create `scan-config.json` next to the flags:

```json
{"db":"both"}
```

Allowed values: `"men"` (default), `"women"`, `"both"` (or `{"includeWomen":true}`).

---

## 5. Convert `dump.json` to CSV

```bash
python3 tools/fmsuperscout_to_csv.py <dump.json> <outdir>
# example:
mkdir -p fm26/work
cp <prefix>/AppData/Local/FMSuperScout/dump.json fm26/work/fmsuperscout_dump.json
python3 tools/fmsuperscout_to_csv.py fm26/work/fmsuperscout_dump.json fm26/csv
```

Output (UTF-8 BOM, comma-separated, Excel-friendly). The delivered CSVs in
`fm26/csv/` have the human-manager rows removed.

| File | Rows | Cols | Contents |
|---|---|---|---|
| `fm26/csv/fm26_players.csv` | 106,770 | 89 | every player + 52 attributes |
| `fm26/csv/fm26_staff.csv` | 53,536 | 39 | every staff member + 22 staff attributes (English labels) |
| `fm26/csv/fm26_people.csv` | 160,306 | 114 | both, with a `kind` column |

Player columns: `id, name, age, dob, birthYear, birthDoy, nat, natId, club,
ownerClub, div, ca, pa, pos, posArr, foot, height, wage, expires, value,
askingPrice, wageDemand, listed, loanListed, notForSale, setForRelease,
clubRep, worldRep, teamType`, the 8 hidden personality attributes
(`adaptability…controversy`) and the 52 attributes (`Acceleration`, `Pace`,
`Finishing`, `Passing`, `Tackling`, `Determination`, `Consistency`,
`ImportantMatches`, `InjuryProneness`, `Versatility`, goalkeeping, …).

Staff columns: the basics plus `job, jobId` and `Attacking, Defending, Fitness,
Possession, Technical, Tactical, Set Pieces, Determination, Man Management,
Motivating, Judging Player Ability, Judging Player Potential, Judging Staff
Ability, Negotiating, Tactical Knowledge, Physiotherapy, Sports Science,
Data Analysis, Working With Youngsters, Goalkeeping Distribution,
Goalkeeping Handling, Goalkeeping Shot Stopping`.

---

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| No `FMSuperScout` line in `BepInEx/LogOutput.log` | DLL not in `BepInEx/plugins/`, or the game was not restarted after copying it. |
| `status.json` says `error`, log says *game_plugin.dll niet geladen* | You triggered the dump before a save was loaded. Load the career first. |
| *0 spelers en 0 staf gevonden — dump niet weggeschreven* | Scan found nothing; an existing good `dump.json` is deliberately **not** overwritten. Trigger again with a fully loaded save. |
| `meta.versionOk` is `false` in `dump.json` | Game `game_plugin.dll` no longer matches the plugin's pinned offsets (26.3.x). Update FMSuperScout or re-pin `plugin/Fields.cs`. |
| Dump aborts with memory errors / Win32 1450 | Not enough free RAM. Close other apps; the plugin already retries with a memory snapshot. |
| Women missing | Expected by default — set `scan-config.json` to `{"db":"both"}` (§4). |

---

## Appendix A — Alternative captures (no memory plugin)

* **Official game export:** in a player list, select rows
  (`Ctrl+A` / `⌘+A`) then `Ctrl+P` / `⌘+P` → **Web Page**, save the HTML and
  convert it to CSV. Columns are whatever the current view shows.
* **FMDataExport (BepInEx):** `github.com/fredGob/FMdataExport` — press
  **F10** on a table; it auto-scrolls large lists and writes a CSV to
  `Documents/Sports Interactive/Football Manager 26/exports/`.
* **FM26 Player Export v5.1** (fmscout.com) — F9 exports CSV + HTML.

These read the on-screen table, so configure the view columns first, and they
cannot give hidden attributes/CA/PA the way the memory dump does.

## Appendix B — Offline look at the shipped database (no game running)

Useful for inspecting the base database shipped with the game (people, names,
DOBs, hidden attributes), not the live game state. `tools/fmdb.py`
decompresses the zstd payload behind the FM `.dat` header:

```bash
GAME=~/.steam/steam/steamapps/common/"Football Manager 26"
DB="$GAME/shared/data/database/db/2620/2620_fm"

# 216k people with full name + DOB + nation ref from the shipped DB
mkdir -p fm26/work
python3 tools/fmdb.py "$DB/people_db.dat" fm26/work/people_db.raw
python3 fm26/offline/parse_people.py fm26/work/people_db.raw fm26/offline/players_people.csv

# ~31k people with current ability / age / position from the uncompressed summary.dat
cp "$DB/summary.dat" fm26/summary.raw
python3 tools/fmdb.py "$DB/basic_people_db.dat" fm26/basic_people_db.raw
python3 fm26/offline/parse_summary.py   # -> fm26/offline/players_summary.csv
```

`fm26/offline/` keeps those parsers, the pre-generated `players_people.csv` and
`players_summary.csv`, and `field_dict.csv` (2,103 editor field codes such as
`pers,Ncra` = current ability). The summary parser's community-CSV cross-check
only runs if the file exists; point `EXAMPLE_CSV=/path/to/FM26_Example_data.csv`
at it to enable it.

The full positional schema of the `.dat` format is schema-driven (compiled
descriptor tables / encrypted `.dbc`), so the live memory dump above remains
the complete route. Background: `docs/reports/agentA-native-re.md` and
`docs/reports/agentB-people-db.md`.

## Appendix C — Reference results (validation)

| Player | CA | PA | Club |
|---|---|---|---|
| Kylian Mbappé | 195 | 197 | R. Madrid |
| Harry Kane | 188 | 190 | FC Bayern München |
| Ousmane Dembélé | 186 | 188 | Paris Saint-Germain |
| Erling Haaland | 184 | 195 | Manchester City |
| Jude Bellingham | 176 | 188 | R. Madrid |
| Lionel Messi | 172 | 200 | Inter Miami CF |
| Cristiano Ronaldo | 155 | 195 | Al-Nassr |

These CA values match an independent decode of the shipped `summary.dat`
(`fm26/offline/players_summary.csv`), confirming the dump.
