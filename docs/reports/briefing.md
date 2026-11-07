# FM26 Player Data Extraction — Shared Briefing

## Goal
Extract ALL players from the installed Football Manager 26 database into `.csv` files.

## Environment
- Working dir: `/home/dat/src/football_manager`
- Game: `~/.steam/steam/steamapps/common/Football Manager 26` (Steam app 3551340)
- GUI available: `DISPLAY=:0`, Wayland session, Steam already running.
- Steam Proton prefix for FM26 DOES NOT exist yet (`~/.local/share/Steam/steamapps/compatdata/3551340` missing) -> game has never been launched. No save games exist.
- Tools available: python3 (3.14), `zstandard` python pkg, zstd CLI, objdump/nm/readelf/llvm-nm. No pandas.
- Network works.

## Key files
- DB dir: `~/.steam/steam/steamapps/common/Football Manager 26/shared/data/database/db/2620/2620_fm/`
  - `people_db.dat` (76MB) -> zstd -> 451MB raw (master person table, names etc.)
  - `basic_people_db.dat` (12.8MB) -> zstd -> 60MB raw (looks like fixed ~84-byte records)
  - `server_db.dat` (68MB), `client_db.dat` (15MB), `lang_update_db.dat` (88MB)
  - `pl_hist_dt.dat`/`pl_hist_id.dat`/`pl_hist_index.dat` (player history)
  - `non_pl_hist_*` (non-player history)
  - `summary.dat` (5.2MB) — **NOT zstd**; appears to be an uncompressed structured table with person IDs + names + some attributes.
  - `db/2620/dbc/*.dbc` — encrypted.
  - `db/2620/lnc/*.lnc` — plain text name changes.
- Editor schema/config (text SGML): extract frames of
  `~/.steam/steam/steamapps/common/Football Manager 26/shared/data/editor.fmf`
  -> frames `editor.fmf.016.bin`, `.076.bin`, `.098.bin` contain `<record db_field="pers,PnRV">` style entries mapping short field codes to human names:
    `pers,PnRV`=name, `pers,Pfna`=first name, `pers,Psna`=second name, `pers,Pcna`=common name,
    `pers,Page`=age, `pers,Pcbi`=city of birth, `pers,Pnbi`=nation of birth, `pers,Pcti`=club,
    `pers,PCJO`=club primary job, `pers,PSJO`=club secondary job, `pers,Ncra`=current ability,
    `pers,Npta`=potential ability, `pers,Pnti`=nation, `pers,Ppsr`=position, `pers,Pcwg`=wage, etc.
  There are ~2100 unique db_field codes across tables `pers, club, comp, natc, stad, team, weat, awar, inju, nati, city, agrm`.
- Native code: `~/.steam/steam/steamapps/common/Football Manager 26/fm_Data/Plugins/x86_64/game_plugin.dll`
  (PE32+ x86-64, 514MB). Contains the DB reader + editor + simulation. Retains MSVC RTTI (class names like
  `VGAME_PERSON@@`, `VGAME_PLAYER@@`, `VGAME_DATABASE_RECORD@db@@`, `VDATABASE_SUMMARY@db@@`) and ~6200
  mangled symbol strings. C++ source paths embedded, e.g.
  `...\shared\libraries\fm\database\code\database.cpp`.
  `fm.exe` is just the Unity launcher stub; the DB code is in this DLL.
- C# IL2CPP metadata: `fm_Data/il2cpp_data/Metadata/global-metadata.dat` (15MB), `GameAssembly.dll` (53MB).
- Community tool: GitHub `fredGob/FMdataExport` (already cloned to `work/FMdataExport`) — a BepInEx plugin that
  exports the in-game table to CSV (F9/F10). Its example CSV `work/FMdataExport/DataAnalyser/FM26_Example_data.csv`
  has 71,746 rows and 44 columns (Joueur, Unique ID, Age, Club, etc.).
- The official game also supports Ctrl+A then Ctrl+P -> "Web Page" export of a player list.

## Findings so far
- FM `.dat` = small header (`03 01 'tad.'`) + zstd frame(s) starting at offset 12.
  Use `python3 fmdb.py <file.dat> <out.raw>` (in this dir) to decompress.
- `people_db.raw` starts with real person records. Name strings appear as `[u32 len][utf8 name]`.
  Known: Ronaldo full-name record has DOB encoded as (u16 day-of-year, u16 year) right after the name,
  then several small fields, then attributes. Person IDs do NOT appear adjacent to the names, so the
  record layout is not yet cracked.
- `summary.dat` contains records like: `[u32 person_id][u32 ...][u32 name_len][name]...`
  e.g. Cristiano Ronaldo id=735216, and fields 788, 155, 40 near it. No DOB found in summary.dat.
- `basic_people_db.raw` showed a strong ~84-byte periodicity at the file start but the layout is unclear.

## Deliverables wanted
- A parser / pipeline that outputs one or more CSVs containing all players with as many meaningful columns
  as possible (at minimum: unique id, name, age/DOB, nationality, club, position, CA/PA).
- Write findings and artifacts under `/home/dat/src/football_manager/work/`.

## Rules
- Do NOT modify the game install or Steam. Work read-only on the game, write only under `work/`.
- Prefer evidence (hexdumps, decoded records) over speculation. Save intermediate artifacts.
- Keep a concise markdown report of what you did, what worked, and exact commands.
