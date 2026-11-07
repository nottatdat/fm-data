# Agent E — Existing offline tools / libraries / datasets for FM26 `.dat` → CSV

**Date:** 2026-09-11
**Scope:** find existing offline tools, libraries or datasets that can parse FM26 `.dat`
or convert the FM26 database to CSV (GitHub, PyPI, fmscout, sortitoutsi, Steam). Try
candidates under `work/agentE_tools/`. Never modify the game.

---

## Bottom line (TL;DR)

1. **No public, working, offline parser for the FM26 *PC* `.dat` files
   (`people_db.dat`, `basic_people_db.dat`, `server_db.dat`, …) exists today.**
   Every search (GitHub repo + code, PyPI, crates.io, npm, NuGet, Sourcegraph,
   fmscout, sortitoutsi, Steam Workshop, Kaggle) is negative. The only authoritative
   FM26 community analysis we found states the same explicitly (see quote below).

2. **The closest existing offline `.dat` parser is `nyongrand/fmm-editor` (FMMLibrary)**,
   but it targets **Football Manager Mobile 26** — different, fixed-header layout.
   We ported its reader to Python and tested it against the decompressed PC files:
   it does **not** work (garbage `OtherNationalityCount=29696`, etc. See
   `fmm_people_parse.log`).

3. **Every full-data FM26 tool that exists is a *runtime* memory/UI reader**, not an
   offline `.dat` parser:
   - **FMSuperScout** (open source, BepInEx) — full attributes + CA/PA + hidden
     personality + value, dumps JSON. Best open-source candidate.
   - **FM Genie Scout 26**, **FM Live Editor 26**, **FMST 26** — closed source, Windows.
   - **MacScout26** — closed source, macOS, reads a save file directly, exports CSV.
   - **FM26 Player Export v5.1** / **fredGob/FMdataExport** — BepInEx UI scrapers that
     write CSV/HTML from the in-game list.

4. **Published FM26 data already matching this DB version** exists:
   - `FMdataExport/DataAnalyser/FM26_Example_data.csv` — **71,745 players**, 43 columns
     (name, Unique ID, age, club, position, wage, contract, per-90 stats). Cristiano
     Ronaldo ID `735216` matches `summary.dat` of installed DB `2620` → same database.
   - sortitoutsi.net FM26 person pages / wonderkid tables.
   - `mcanvrr/fm26-wonderkids` `wonderkids.txt` (603 lines, includes PA).

5. **Best reusable offline reverse-engineering assets** (not parsers):
   - `contatovinteset-wq/fm26-editor-workspace` — full IL2CPP dump (`dump.cs`,
     `il2cpp.h`, `stringliteral.json`), 347 in-game table/view JSON definitions,
     field dictionary.
   - `mavarobli/FMSuperScout` `plugin/Fields.cs` — verified memory offsets for
     FM26 **26.3.x** (installed `game_plugin.dll` is **26.3.2+2329565**, so these
     offsets match this install) incl. CA/PA, 46 attributes, hidden attrs, positions,
     wage, contract, value.
   - `mavarobli/FMSuperScout/docs/fmf-format.md` — proves `.fmf` payloads are
     per-file-encrypted; only the index is zstd. No offline FMF parser is feasible.

---

## Environment facts verified this run

| Fact | Value |
|---|---|
| Database path | `~/.steam/steam/steamapps/common/Football Manager 26/shared/data/database/db/2620/2620_fm/` |
| DB metadata version | `26.2.0` (`2620_fm.xml`, dated 13/3/2026) |
| DB folders present | `2300 2310 2320 2330 2340 2400 2430 2600 2620` (no `2630`) |
| `game_plugin.dll` version | **`26.3.2+2329565`** (game binary is 26.3.x; DB base is 2620) |
| Steam appid / buildid | `3551340` / `23583635` |
| `FMdataExport` example CSV | 71,745 rows, 71,745 unique IDs, 43 cols, 7,609 clubs, ages 16–55, IDs 352…2,002,040,995 |
| BepInEx presence | game dir already contains BepInEx 6 `changelog.txt`/`core.txt` (not placed by agent E) |

Why this matters: the **26.3-pinned memory tools are compatible with this install**,
even though the shipped DB folder is named 2620.

---

## 1. GitHub search — exact queries and results

GitHub REST repository search (`api.github.com/search/repositories`) and HTML search.
Full dumps saved under `work/agentE_tools/ghapi/`, `ghapi2/`, `ghapi3/`.

Commands (examples):

```bash
# helper (HTML, no rate limit) — work/agentE_tools/gh_search.py
python3 work/agentE_tools/gh_search.py "fm26 dat parser"

# API with backoff (search limit = 10 req/min unauthenticated)
curl -s -A "Mozilla/5.0" \
  "https://api.github.com/search/repositories?q=fm26+in:name,description,readme&per_page=30&sort=updated" \
  -o work/agentE_tools/ghapi2/q1.json
```

Queries executed (all results inspected):
`fm26 dat parser`, `football manager 2026 database`, `fm database csv`,
`football manager dat parser`, `fmgenie scout`, `football manager save editor`,
`fm26 editor`, `football manager fmf`, `fm database reader`, `football manager 26`,
`fm26 in:name,description,readme`, `football manager database in:name,description`,
`football manager parser in:name,description`, `football manager editor in:name,description`,
`football manager dat in:name,description,readme`, `football manager csv in:name,description`,
`fmm-editor`, `fmm26 in:name,description,readme`, `football manager mobile database`,
`fmm database`, `fmm editor`, `football manager mobile editor`.

**Representative relevant hits (none is an FM26 PC `.dat` parser):**

| Repo | Lang | Description | What it really does |
|---|---|---|---|
| [nyongrand/fmm-editor](https://github.com/nyongrand/fmm-editor) | C# | FMM 26 Database Editor, `FMMLibrary` parses/writes `.dat` | **FMM (mobile) 26 `.dat`** only. MIT. Tested → not PC-compatible |
| [mavarobli/FMSuperScout](https://github.com/mavarobli/FMSuperScout) | C#/JS | FM26 scouting, 45k+ players | BepInEx **memory** reader, JSON dump |
| [fredGob/FMdataExport](https://github.com/fredGob/FMdataExport) | C#/JS | BepInEx table→CSV export + analyser | In-game **UI** scrape; ships 71,745-player example CSV |
| [contatovinteset-wq/fm26-editor-workspace](https://github.com/contatovinteset-wq/fm26-editor-workspace) | C#/mixed | FM26 Ctrl+P / Player Export source | IL2CPP dump + in-game UI scrape, no `.dat` parser |
| [andrewcrawford131/FM26editor](https://github.com/andrewcrawford131/FM26editor) | Python | FM26 player generator, `fm26_db_extractor.py` | Parses **editor `db_changes` XML**, not `.dat` |
| [poi82999/fm26rte](https://github.com/poi82999/fm26rte) | Lua/Rust/TS | FM26 runtime player editor, IL2CPP RE | Memory editor |
| [JG1995/fm-valuescout](https://github.com/JG1995/fm-valuescout) | Rust/TS | FM26 offline-first companion | **BepInEx memory bridge**, Windows only |
| [KaliszS/fmforge](https://github.com/KaliszS/fmforge) | Rust/Svelte | FM regens editor | reads/writes `.edt` files, not `.dat`/`.fmf` |
| [Galdinowski/FM_Database](https://github.com/Galdinowski/FM_Database) | C# | FM26 market updater plan | Reads **editor XML**; document says no `.dat` parser |
| [sforde989-sudo/Fm-26-Squad-Hub-app](https://github.com/sforde989-sudo/Fm-26-Squad-Hub-app) | Python | FM26 squad dashboard | Consumes **CSV/XLSX exports** only |
| [AlbertShen31/FMScouter](https://github.com/AlbertShen31/FMScouter) | Python | FM26 role scorer | Consumes **attribute CSV** only |
| [hazhogg/fmwonderkidscouter](https://github.com/hazhogg/fmwonderkidscouter) | Python | FM26 wonderkid DB | Scrapes a **web table** into Postgres |
| [campbellchief-testy/retro-football-manager-data-parsing](https://github.com/campbellchief-testy/retro-football-manager-data-parsing) | Python | Parses a 1994 DOS `.DAT` | Not SI FM format at all |

Clones are in `work/agentE_tools/repos/`.

---

## 2. Package registries — all negative

```bash
# PyPI JSON (404 = does not exist)
for p in fmdb fmdat fm-dat fmdata footballmanager football-manager fm-parser \
         fmdatabase pyscoutfm fm26 fmscout; do
  curl -s -o /tmp/pypi_$p.json -w "%{http_code} $p\n" https://pypi.org/pypi/$p/json
done
# -> only pyscoutfm exists (1.1.1) and it consumes FM *HTML prints*, not .dat.

curl -s "https://crates.io/api/v1/crates?q=football+manager&per_page=20"
curl -s "https://crates.io/api/v1/crates?q=fm+database&per_page=20"
curl -s "https://registry.npmjs.org/-/v1/search?text=football%20manager&size=20"
curl -s "https://azuresearch-usnc.nuget.org/query?q=football+manager&take=20"
```

| Registry | Result |
|---|---|
| PyPI | `fmdb`, `fmdat`, `fm-dat`, `footballmanager`, `football-manager`, `fm-parser`, `fmdatabase`, `fm26`, `fmscout` → **404**. `fmdata` = FileMaker, `pyscoutfm` = HTML export consumer. |
| crates.io | nothing FM-related |
| npm | nothing usable (only match simulators / spam) |
| NuGet | no results |

**Conclusion:** there is no library to `pip install` / `cargo add` / `npm i` that reads FM `.dat`.

---

## 3. Sourcegraph code search — negative

Sourcegraph public-code stream API (`https://sourcegraph.com/.api/search/stream`), literal
queries. The exact FM26 filenames and native RTTI symbols return **zero** relevant matches:

```bash
enc(){ python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
for q in "people_db.dat" "basic_people_db" "server_db.dat" "VGAME_PERSON" "tad. file:\\.dat"; do
  curl -s "https://sourcegraph.com/.api/search/stream?q=$(enc "$q")&v=V3&t=literal&display=20"
done
```

| Query | Result |
|---|---|
| `people_db.dat` | 0 |
| `basic_people_db` | 0 |
| `server_db.dat` | 0 |
| `VGAME_PERSON` | 0 |
| `tad. file:\.dat` | 0 |
| `people_db` | only unrelated projects (lancedb/grafeo) |

Also tried `grep.app` (blocked by Vercel Security Checkpoint) and `searchcode.com` (404 API).

---

## 4. fmscout.com tools (FM26)

Fetched `https://www.fmscout.com/c-fm26-tools.html` (saved `/tmp/fmscout_tools.html`).

| Tool | URL | Reads | CSV? | Notes |
|---|---|---|---|---|
| **FM Genie Scout 26** | https://www.fmscout.com/a-fm-genie-scout-26.html | running game/save memory | own UI/export | closed source, Windows; supports FM26 26.0.0–26.3.2 |
| **FM Live Editor 26** | https://www.fmscout.com/a-fm-live-editor-26.html | live memory | editing focus | closed source, Windows |
| **FMST 26** | https://www.fmscout.com/a-fmst-26.html | live memory (read-only) | own UI | closed source, Windows/Mac? |
| **FM26 Player Export v5.1** | https://www.fmscout.com/a-fm26-player-csv-export.html | in-game UI list | **CSV + HTML** | free BepInEx plugin by "vinteset"; source is the `contatovinteset-wq` workspace |
| **MacScout26** | https://www.fmscout.com/a-macscout26.html | **FM26 save file** (no injection) | **CSV export** | closed source, macOS 14+, native |
| **FM26 Pre-Game Editor** | https://www.fmscout.com/a-fm26-official-pre-game-editor.html | editor DB | XML/FMF export | official SI tool |
| **FM XML Configurator / fmXML** | fmscout tools list | editor XML | XML | not `.dat` |

No fmscout tool parses `.dat` offline.

---

## 5. sortitoutsi.net — published FM26 data

| Page | URL | Content |
|---|---|---|
| FM26 DB portal | https://sortitoutsi.net/football-manager-2026/database | index of guides/teams/players "reflecting the official FM26 database" |
| Person page example | https://sortitoutsi.net/football-manager-2026/person/2000256231/lamine-yamal | UID, name, age, DOB, nationality, club, wage, contract, value, CA/PA stars, CA remaining |
| Men's wonderkids | https://sortitoutsi.net/best-football-manager-2026-wonderkids | table: Name, Age, Position, Wage, Value, Cost, Expires, Rating, Potential (≈700 person links) |
| FM26 Data Update | https://sortitoutsi.net/football-manager-data-update | downloadable editor-data update (FMF), not a raw DB dump |
| Club search / compare | https://sortitoutsi.net/football-manager-2026/club-search | club data |

Notes:
- Person pages are scrapeable/watchable and contain DOB/value/wage/contract/CA-PA-stars,
  but there is **no bulk CSV/API** documented; it is a web database with long "unique IDs"
  (e.g. Lamine Yamal `2000256231`), not the short in-game UID (e.g. Ronaldo `735216`).
- The Data Update is editor data applied on top of the shipped DB; useful as a dataset
  but not a parser.

---

## 6. Steam Workshop (appid 3551340)

Fetched the browse page and resolved all 30 items via the public Web API:

```bash
curl -s "https://steamcommunity.com/workshop/browse/?appid=3551340&browsesort=trend" -o /tmp/steam_ws.html
# unique filedetails ids -> ISteamRemoteStorage/GetPublishedFileDetails/v1/ (POST, no key)
```

30 items found, all are **editor-data / league / graphics packs** (e.g. "26.3 FM26
Transfers & Data Final Season (V4)", "FMUpdate – September 2026", "Norway Lower Leagues").
**No `.dat` parser, no CSV exporter, no database dump tool** on the Workshop.
Full list: `/tmp/ws_ids.txt` + the API output (not saved separately; rerun the snippet).

---

## 7. Kaggle / other datasets

```bash
curl -s "https://www.kaggle.com/api/v1/datasets/list?search=football%20manager"
curl -s "https://www.kaggle.com/api/v1/datasets/list?search=fm26"
```

- Kaggle has FM19, FM20, FM22, FM23 datasets only; **`fm26` returns nothing**.
- `fmdataba.com` still advertises FM21; `fminside.net` returns Cloudflare 403.

---

## 8. The single most useful negative evidence

`Galdinowski/FM_Database/docs/FM26-MARKET-UPDATER-ANALYSIS.md` (independent FM26 project,
written 2026-09-01, aligned to the same DB **2620**):

> “**Leitura:** não há biblioteca madura e fiável para FM26 destes `.dat`.
> Não vamos escrever um parser.”
> (“Reading: there is no mature, reliable library for FM26 `.dat`. We will not write a parser.”)

Same document records the write-path reality: FM26 DB is edited via the **Pre-Game Editor
XML → FMF** flow (the official SI door), and `.fmf`/`.dat` patching is explicitly out of
scope. This independently confirms our findings.

---

## 9. Candidate tools we actually tried

### 9.1 FMMLibrary (`nyongrand/fmm-editor`) — the only offline `.dat` parser

- Clone: `git clone --depth 1 https://github.com/nyongrand/fmm-editor`
- `FMMLibrary/PeopleParser.cs` etc. read: `[8-byte header][u32 count][records…]`
  with `ReadString() = int32 len + UTF-8`, `ReadDate() = (int16 day-of-year, int16 year)`.
- Our Python port + probe: `work/agentE_tools/fmm_people_parse.py`,
  output `work/agentE_tools/fmm_people_parse.log`.

Result on the decompressed PC files:

```
basic_people_db.raw: FMM header = 42 08 0b 00 00 11 01 83
                     FMM count  = -184549376 (0xf5000000)  -> implausible
people_db.raw:       FMM count  = 327691 (looks plausible)
                     first record OtherNationalityCount = 29696 (garbage)
```

**Verdict:** FMMLibrary is not directly usable on FM26 PC files. It remains valuable as a
structural reference (same length-prefixed UTF-8 and SI date encoding), and it is MIT
licensed, so its record definitions can inform a purpose-built parser.

### 9.2 `.fmf` offline parsing — proven infeasible

`mavarobli/FMSuperScout/docs/fmf-format.md`: the `.fmf` container is
`02 01 "afe."` + payloads, then `"fmf."` + **zstd index**. The index decompresses, but
payloads are **encrypted with a random per-file nonce** (identical default image bytes
differ in every file). Conclusion: cannot write/read payloads offline; only SI's Resource
Archiver can. This closes off the `.fmf` route for a parser.

### 9.3 PyPI / crates / npm / NuGet — tried, nothing to install (see §2).

### 9.4 Steam Workshop — enumerated, no parser (see §6).

---

## 10. Published FM26 data matching DB 2620 / game 26.3.2

### 10.1 `FMdataExport` example CSV (best bulk dataset)
Path: `work/FMdataExport/DataAnalyser/FM26_Example_data.csv` (21.8 MB, 71,745 rows)

```
,Joueur,Unique ID,Âge,Club,Résidence,Division,Position,Salaire,Expire le,Minutes,Note,
 enc/90,Arrêts/90,xG év/90,% Ra,Dég/90,Blq/90,Int/90,Tcl/90,Tcl D/90,Poss remp/90,
 Poss perd/90,Pres T/90,Pres E/90,Aér T/90,Têtes r/90,Ps T/90,Ps R/90,% pas.,
 Passes pr./90,PC-J/90,PdA/90,Occ. / 90 min.,Cts tent./90,Cts R/90,Drb/90,Tir/90,
 % cadrés,xG-HP/90,Buts par 90 min. de jeu,Dist/90,Sprints/90
```

- Row 1: `Cristiano Ronaldo, 735216, 41, Al Nassr, …`, matching `summary.dat` id `735216`
  (installed DB 2620). 71,745 unique IDs; includes contract and wage.
- **No CA/PA and no individual attribute columns** — it is an in-game list export, not a DB dump.
- Convert/validate command:

```bash
python3 - <<'PY'
import csv
p='work/FMdataExport/DataAnalyser/FM26_Example_data.csv'
with open(p, encoding='utf-8-sig', newline='') as f:
    r = csv.reader(f); hdr = next(r)
    print(len(hdr), hdr[:11])
    for i, row in enumerate(r):
        if i < 3: print(row[:11])
        else: break
PY
```

### 10.2 `mcanvrr/fm26-wonderkids/wonderkids.txt`
603-line human-readable FM26 wonderkid list (name, nation, position, club, age, value, **PA**),
Turkish headers. A small published dataset with real PA values.

### 10.3 sortitoutsi.com FM26 DB (see §5)
Web database with DOB/wage/value/contract/CA-PA-stars per person.

### 10.4 fmscout "FM26 Best Players / Wonderkids"
`https://www.fmscout.com/c-players26.html` and
`https://www.fmscout.com/a-football-manager-2026-wonderkids.html` — curated lists, not raw data.

---

## 11. Best reusable open-source assets for the offline parser effort

1. **`work/agentE_tools/repos/mavarobli_FMSuperScout/plugin/Fields.cs`**
   Verified FM 26.3.x memory offsets (game_plugin 26.3.0/26.3.2) from the community
   Cheat Engine tables (tdg6661). Includes:
   - CA `PLAO_CA=0x264`, PA `PLAO_PA=0x266`, 46 `PlayerAttrs` (stored ×5), 5 hidden attrs,
     15 position ratings, `PLAO_POSITIONS=0x150`, `PLAO_ATTRS=0x15F`
   - personality `PERO_*`, DOB `PERO_DOB=0x88`, nation/club pointers
   - contract wage `CON_WEEKLY_WAGE=0x20`, expiry `CON_EXPIRY=0x48`, status bits
   - value `PLAO_GUIDE_VALUE`, `PLAO_TRANSFER_VALUE`
   Since the installed `game_plugin.dll` is **26.3.2**, these offsets apply to this install.

2. **`work/agentE_tools/repos/contatovinteset-wq_fm26-editor-workspace/`**
   - `Arquivos gerados no dump/dump.cs`, `il2cpp.h`, `stringliteral.json` — IL2CPP dump
   - `extracted-tables/*.json` — **347** in-game table/view definitions with `m_columnID`s
     (e.g. `shirtnumber`) — directly useful to map any UI-scrape export to columns
   - `docs/dicionario-funcoes-fm26.md` — player-role/function dictionary
   - `SKILL FM26.md` — methodology for IL2CPP/BepInEx/memory/`.dat` approaches
   - `EXPORT-GUIDE.md` — documents the (failed) Ctrl+P / skin approaches

3. **`work/agentE_tools/repos/nyongrand_fmm-editor/FMMLibrary/`** (MIT)
   Reference record layouts and helper encodings (length-prefixed UTF-8, SI date
   `(u16 day-of-year, u16 year)`, RGB565 colors, personality bytes).

4. **`work/agentE_tools/repos/mavarobli_FMSuperScout/docs/fmf-format.md`**
   Definitive negative result on offline `.fmf` parsing.

5. **`work/agentE_tools/repos/Galdinowski_FM_Database/docs/`**
   Architecture/plan documents that name DB 2620 and the XML/FMF write-path, with sources.

---

## 12. Recommendation for the extraction pipeline

Given no offline `.dat` parser exists, the realistic options are:

- **A. Runtime memory dump → CSV (highest data quality, needs Windows).**
  Use the open-source, currently-compatible **FMSuperScout** (pinned to 26.3, matches our
  installed 26.3.2): install BepInEx 6 IL2CPP in a Windows/Proton prefix, load a save,
  press F9, then convert `%LOCALAPPDATA%\FMSuperScout\dump*.json` to CSV. Gives all
  attributes + CA/PA + hidden personality + value. It is the only open-source route to a
  *complete* CSV. (Alternatively the BepInEx UI exporters FM26 Player Export / FMdataExport
  give name/age/club/position/wage/contract + stats but no attributes/CA/PA.)

- **B. Fallback dataset, no game run needed.**
  Use `FMdataExport/DataAnalyser/FM26_Example_data.csv` (71,745 FM26 players, IDs + names +
  age + club + position + wage + contract + per-90 stats) as a ready-made CSV
  matching DB 2620. It lacks CA/PA/attributes.

- **C. Purpose-built offline parser (agent A/B work).**
  No shortcut exists. Reuse: `editor.fmf` field codes (already extracted by the team),
  `FMMLibrary` record/encoding references, `contatovinteset` IL2CPP dump and the 347 table
  JSONs, and `Fields.cs` as a cross-check for field semantics. The PC `.dat` container is
  `03 01 'tad.'` + zstd frame(s); `basic_people_db` is a near-exact 84-byte-record table
  (`60147370 = 716040×84 + 10`), `people_db` is variable-length with inline
  `[u32 len][utf-8]` names.

- **D. Do not pursue `.fmf`/`.slf` offline** (encrypted payloads) or `.edt` (regens only).

---

## 13. Files produced by agent E

```
work/agentE/REPORT.md                     # this report (also copied to agentE_tools/REPORT.md)
work/agentE_tools/
  REPORT.md                               # copy
  gh_search.py / gh_search.sh             # GitHub search helpers
  ghapi/ ghapi2/ ghapi3/                  # raw GitHub search JSON
  search/                                 # earlier FMSuperScout/PyScoutFM/etc. searches
  repos/                                  # 18 cloned candidate repos (see table)
  fmm_people_parse.py                     # Python port of FMMLibrary People reader (test)
  fmm_people_parse.log                    # test output: FMM parser incompatible with PC files
  ddg1.html ddg2.html                     # search-engine captures
  fmsuperscout_readme.md pyscoutfm_readme.md
  repo_fmsuperscout.json
```

### Exact commands used (condensed)

```bash
# GitHub API (search limit 10/min)
for q in "fm26+in:name,description,readme" "fmm-editor" "football+manager+dat+in:name,description,readme"; do
  curl -s -A "Mozilla/5.0" -o "ghapi2/$(echo $q|tr -d '+:,').json" \
    "https://api.github.com/search/repositories?q=${q}&per_page=30&sort=updated"
  sleep 8
done

# Sourcegraph
enc(){ python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))" "$1"; }
curl -s "https://sourcegraph.com/.api/search/stream?q=$(enc 'basic_people_db')&v=V3&t=literal&display=20"

# PyPI
for p in fmdb fmdat footballmanager fm-parser fm26 pyscoutfm; do
  curl -s -o /dev/null -w "%{http_code} $p\n" "https://pypi.org/pypi/$p/json"; done

# Web pages
curl -sL -A "Mozilla/5.0" https://www.fmscout.com/c-fm26-tools.html -o /tmp/fmscout_tools.html
curl -sL -A "Mozilla/5.0" https://www.fmscout.com/a-fm26-player-csv-export.html -o /tmp/fmscout_csv.html
curl -sL -A "Mozilla/5.0" https://sortitoutsi.net/football-manager-2026/database -o /tmp/sots_db.html
curl -sL -A "Mozilla/5.0" "https://steamcommunity.com/workshop/browse/?appid=3551340&browsesort=trend" -o /tmp/steam_ws.html

# Steam Workshop item details (no key)
curl -s "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/" --data "...publishedfileids[0]=..."

# Candidate tool test
python3 work/agentE_tools/fmm_people_parse.py | tee work/agentE_tools/fmm_people_parse.log

# Clone candidates (all read-only, under work/)
git clone --depth 1 https://github.com/nyongrand/fmm-editor
git clone --depth 1 https://github.com/mavarobli/FMSuperScout
git clone --depth 1 https://github.com/contatovinteset-wq/fm26-editor-workspace
git clone --depth 1 https://github.com/fredGob/FMdataExport   # already in work/
```

**No game files were modified. All work stayed under `work/`.**
