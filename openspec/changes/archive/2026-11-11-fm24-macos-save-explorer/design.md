# Design

## Context

See proposal.md (Why). Facts already established during exploration (no experiment needed):

- FM24 macOS (Epic, 24.4.2) stores saves in
  `~/Library/Application Support/Sports Interactive/Football Manager 2024/games/*.fm`,
  alongside FM's own `last save overwrite backup*.fm` files and saves of several careers.
- A save is an `fmf.` container of ~9.5k zstd frames; all tested frames decompress to
  plaintext `tad.` blocks. The main block (~234 MB) decompresses in ~0.35 s and contains
  `[id u32][len u32][utf-8]` string tables (names; whether ids are person ids or
  name-dictionary ids is not yet known) and club records in the clear.
- FM24 shipped DB `.dat` files use the same container as FM26/27: `tools/fmdb.py` and
  `fm27/offline/parse_people.py` already extract 198,662 names/DOB from them.
- Explorer today (`fm27/explorer/`):
  - `server.py` hardcodes `DB = data/fm27.db`, `HIST_DB`, Sofascore `FORM_DB`. Its `CSV`
    constant is unused: `ensure_db()` calls `import_db.build()` with defaults, which take
    the CSV path from `import_db.CSV`.
  - Module-level caches built once: `CLUB_INDEX` (`_build_club_index()`) and
    `_filter_cache` (filter options, totals).
  - `player_club_id()` reads `HIST_DB` whenever the file exists (club logos).
  - `import_db.build(db_path, csv_path, force)` reads rows with `row.get(col)`: missing
    numeric columns become NULL, missing text columns become `""`, a blank `gender`
    becomes `"Men"`. It writes `<db>.tmp` and swaps with `os.replace` (atomic).
  - `static/app.js` always requests `/api/history/<id>` (no error handling) and
    `/api/form/<id>`; `index.html` hardcodes FM27 branding and the 516,038 count.
  - `run.sh` already forwards its arguments to `server.py`.
  - `fm27/explorer/data/` and `*.csv` are already gitignored.
- No FM27 data exists on this Mac (`fm27/explorer/data/` absent, `fm27/csv_515k/` has
  only its README), so FM27 regression proof needs a fixture.
- FM24 shows exact 1–20 attributes for the user's own players, but never shows CA, PA or
  hidden attributes as numbers. The user has no editor/scout tool to read them.
- The person/player record layout inside the save is **unknown**.

## Goals / Non-Goals

**Goals:**
- Every unknown is retired by a cheap experiment with a written pass/fail result before
  dependent work starts; the record-decode experiment gates the whole build.
- FM24 code lives under `fm24/`; FM26/FM27 code paths keep their current behaviour.
- The explorer change is additive and switchable only at startup.

**Non-Goals:**
- Decoding every column. Name, DOB, nation, club, positions and visible attributes are
  the verified target; CA/PA and hidden attributes are best-effort and unverified.
- Generalising the explorer into a multi-game platform (no plugin registry, no runtime
  switcher). Exactly two values: `fm27` (default) and `fm24`.

## Decisions

### D1. Save-file parsing over memory reading
Read the `.fm` save offline in Python. Alternatives: an injected dylib
(`DYLD_INSERT_LIBRARIES` is permitted by FM24's entitlements) gives true live data but
needs native C++ reverse engineering, launch changes and risks crashing the game; an
external memory reader is blocked by hardened runtime + SIP. The user accepted
"as of last save" plus a manual ⌘S, which the save route satisfies with far less risk.

### D2. Experiment-first, evidence in the repo
Each experiment (tasks.md group 2–3 and 4.4) is time-boxed, has a pass/fail criterion, and
leaves a short note in `fm24/experiments/` (method, result, decision). Experiment scripts
live there too and are not part of the product path. If E1 fails its time box, stop and
revisit D1 with the user rather than widening scope silently.

### D3. Layout of FM24 code
```
fm24/                      a Python package (imported as fm24.save.*; no name clashes)
  GUIDE.md                 macOS steps: where saves are, ⌘S, run explorer --game fm24
  csv/README.md            column notes: exact / unverified / blank
  experiments/             E1..E11 notes + throwaway research scripts
  save/parse_save.py       save -> fm24_players.csv + fm24_meta.json (CLI + library)
  save/live.py             the explorer's save-backed dataset (provenance, reload)
  save/nations_en.json     nation UID -> English name
  tests/                   unit, server and FM27-unchanged tests (README lists them)
  work/ (gitignored)       decompressed blocks, ground truth, regression baseline
```
`parse_save.py` keeps its own small frame reader; `tools/` is unchanged. Record layouts are
named constants next to the decoders (`HDR_*`, `RAT_*`, `TEAM_*`, …), each tied to an
E-note; a new column is one constant plus one line in `decode_header`/`decode_ratings`, and
the metadata's blank-column list is derived from the output. It loads the explorer's
importer by file path (no `sys.path` changes) and asserts its attribute names exist there.

### D4. CSV schema = the importer's source columns
The output contract is `import_db.ALL_COLS` minus the columns `build()` derives itself
(`club_display`, `club_search`): those are exactly what the importer reads, so
`build()` works unchanged. Undecoded columns are written blank, which the importer turns
into NULL (numbers) or `""` (text). `gender` is written explicitly (FM24 careers can hold
both) rather than relying on the importer's blank → "Men" default. `age` is computed from
the in-game date, and left blank if E5 cannot decode it.
`fm24_meta.json` carries provenance: save file, saved-at mtime, in-game date or null, row
count, and `columns: {verified: [...], unverified: [...]}`.
Alternative (own schema + adapter in the explorer) adds a second code path for no gain.

### D5. Explorer: one startup option, resolved once
`server.py` gains `--game {fm27,fm24}` (default `fm27`), resolved once at startup from a
`GAMES` dict: label, `panels` (history, form, images), and for save-backed games the DB
file name and the module that provides its `SaveDataset` (`fm24.save.live`, imported with
`importlib`). Adding a game is one entry plus its own package. FM27 resolves to today's
exact values and keeps calling `import_db.build()` with its defaults. FM24 passes both paths explicitly:
`fm24/csv/fm24_players.csv` → `fm27/explorer/data/fm24.db` (the explorer's existing,
gitignored data directory; deleting it removes both games' DBs). In FM24 mode
`ensure_db()` skips the history build, `player_club_id()` returns nothing, face and
logo routes serve nothing (E10: no FM24 packs; FM27-era packs may mismatch newgen ids), and startup
fails with a clear message if the FM24 CSV does not exist yet. `run.sh` needs no change.
Alternatives: copying the explorer to `fm24/` (fixes made twice) or moving it to a shared
directory (larger diff touching FM27 paths). Rejected per user decision (option A).

### D6. UI learns capabilities from the server
For a save-backed game the server injects `window.FM_GAME = {game, label, panels}` and
`static/savemode.js` before `app.js` (it checks at startup that `index.html` still has the
expected `app.js` tag, so the injection cannot silently stop working). `app.js` reads the
panels (default: all on) to skip history/form requests, the history panel and face/logo
images. `savemode.js` owns the save banner: it polls `/api/meta` (label, player count,
provenance, unverified columns, FM running, newer save, reload state), sets title/footer,
and marks unverified values via the `data-k` key on attribute rows. FM27 gets no injection
and never calls `/api/meta`, so its page and requests are unchanged (D8).

### D7. Freshness and reload
- *Running detection*: process check by name (exact command from E7).
- *Save candidates*: career `.fm` files only; `last save overwrite backup*.fm` excluded.
- *Newer save*: `/api/meta` compares the newest candidate's mtime with the loaded save's;
  the UI polls every 5 s (meets the 10 s spec). Stat only; the game is never touched.
- *Settled file*: ready once size and mtime are unchanged across two checks; exact rule
  from E6 (in-place write vs temp + rename).
- *Reload* (`POST /api/reload`, background thread, one at a time; a second request returns
  the running state):
  1. extract to `fm24_players.csv.tmp` + `fm24_meta.json.tmp`;
  2. `import_db.build(fm24.db, csv.tmp, force=True)` (its own `.tmp` + atomic swap);
  3. `os.replace` the CSV, then the meta; rebuild `CLUB_INDEX` and clear `_filter_cache`;
  4. on any failure, delete temp files and record the error; the old DB, CSV, meta and
     caches stay in place and consistent.
  Meta is published last, so the banner never names a save whose data is not served.
  If refreshing the caches fails after the swap, the error says the new data is loaded.
- *CSV written by the CLI*: when `fm24_players.csv` is newer than `fm24.db`, the next
  `/api/meta` starts the same background job to rebuild the DB from it.
- `fm24/save/live.py` owns this state (one lock for the job and the settle bookkeeping);
  `pgrep` runs at most every 5 s; `POST /api/reload` rejects foreign `Origin`s.

### D8. Regression proof for FM27 default
No FM27 data exists on this Mac, so the baseline uses a fixture: a few hundred
`fm27_players.csv`-format rows (synthetic or sampled from a real FM27 export) plus a
minimal `history.db` with the tables `server.py` checks. The baseline is captured by
running the **pre-change commit** of the explorer against the fixture in a temporary
worktree (`.context/`), then compared with the changed explorer on the same fixture:
- API: fixed search/filter/profile requests return byte-identical JSON.
- UI: screenshots of the search page and one profile match (same panels, labels, content;
  no banner, no `/api/meta` polling).
- Files: `git diff --stat -- fm26 fm27 tools ':!fm27/explorer'` is empty; within
  `fm27/explorer` only `server.py`, `static/*` and `README.md` change.
The baseline outputs live under `fm24/work/` (gitignored). `fm24/tests/test_fm27_unchanged.py`
automates the API half on every run (explorer at the branch point with `origin/master`
vs the working tree, via `git archive`); `fm24/tests/fm27_regression.py` captures the UI
half with a browser for manual comparison.

### D9. Ground truth for decoding
Exact: DOB, age (in-game date − DOB), nationality and club of the user's own players, as
shown on their profiles. Attributes come from the player's **live block** (layout per
barak14/fm-editor `docs/fm24`: 15 position ratings, then 54 attributes, display =
(raw + 2) // 5): 292/294 on-screen values equal across 8 players, the 2 misses at rounding
boundaries on attributes with change arrows. The 5-entry attribute history (FM's progress
baseline) is not used. CA/PA are sanity-checked against coach star ratings and stay
unverified; hidden attributes from the live block are exported as unverified.

## Risks / Trade-offs

- [Record layout is undecodable within the time box] → E1 is the gate; stop and decide
  with the user (dylib route, or reduced scope such as names/clubs only).
- [String-table ids are name-dictionary ids, not person ids] → E1 checks this first; E4's
  person count depends on the answer.
- [Fields are tag-encoded per the editor schema rather than fixed structs] → E2 detects
  it early; that may simplify decoding via field codes.
- [CA/PA decoded wrongly but plausibly] → labelled unverified in data and UI (D9).
- [Save contains only loaded leagues] → E4 measures it; documented, not a bug.
- [Face/logo packs keyed by FM27 ids show the wrong person/club for FM24] → E10 checks id
  validity; if invalid, faces/logos fall back to placeholders in FM24 mode.
- [Reload too slow] → E8 measures save parse + DB build + FTS together; target < 30 s.
- [Reading a save while FM writes it] → settled-file rule (E6) plus the extractor's own
  size/mtime check before and after reading.
- [Shared explorer edits regress FM27] → additive changes, settings resolved once, D8
  API + UI + file-diff checks before merge.

## Migration Plan

No data migration. FM27 users see no change. Rollback is reverting the change. FM24 data
is local and can be deleted (`fm24/work/`, `fm24/csv/*.csv`, `fm24/csv/*.json`,
`fm27/explorer/data/fm24.db`).
