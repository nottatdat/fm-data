# Proposal

## Why

The repository extracts full player data only for FM26/FM27, and only on Windows/Linux
(FMSuperScout is a Windows binary pinned to those games). The user plays **FM24 on macOS**
and wants to browse that career in the Profiles Explorer. Exploration showed a viable,
low-risk route: FM24 `.fm` saves are zstd frames over **plaintext** `tad.` blocks (not
encrypted like FM26's), and FM24 is final at 24.4.2, so a decoded layout never breaks.

## What Changes

- New `fm24/` directory owning everything FM24-specific: a save parser that turns an FM24
  `.fm` save into `fm24_players.csv` (same column schema as `fm27_players.csv`, undecoded
  columns left blank), a guide, a CSV schema README, and experiment notes.
- Experiment-first delivery: every open assumption (record layout, field encoding, save
  scope, in-game date, save write behaviour, process detection, parse time, importer
  tolerance) is resolved by a short, time-boxed experiment with a pass/fail criterion
  before the dependent build work starts. Decoding one of the user's own players (E1) is
  the gate. Ground truth is what FM24 shows on screen; CA/PA and hidden attributes, which
  the game never shows as numbers, are exported and displayed as **unverified**.
- Explorer gains an additive `--game fm24` option: FM24 uses its own database file and
  hides FM27-only panels (career history, Sofascore form). Without the option the explorer
  behaves exactly as today.
- In FM24 mode the explorer shows which save the data came from and when it was saved,
  tells the user to press ⌘S in FM when the game is running, detects a newer save, and
  offers **[Load it]** to re-parse and reload.

Non-goals: live memory reading (dylib injection), automating ⌘S or any interaction with
the game process, FM24 career history / Sofascore panels, an in-app game or save picker,
Windows/Linux support for FM24, any change to FM26/FM27 extraction.

## Capabilities

### New Capabilities
- `fm24-save-extraction`: reading an FM24 save file and producing a player CSV in the
  shared explorer schema, with provenance (save file, saved-at, in-game date if known).
- `explorer-game-datasets`: choosing which game's dataset the explorer serves at startup,
  with per-game database isolation and unchanged default (FM27) behaviour.
- `explorer-save-freshness`: in save-backed mode, showing data provenance and staleness,
  detecting newer saves, and reloading on user request.

### Modified Capabilities
- None (no existing specs in `openspec/specs/`).

## Impact

- New: `fm24/` (parser, guide, experiments, `csv/README.md`); `.gitignore` entries for
  FM24 CSVs/work files.
- Modified (additive only): `fm27/explorer/server.py` (startup option, freshness and reload
  endpoints), `fm27/explorer/static/app.js` (panels from `window.FM_GAME`), new `static/savemode.js` (banner). `import_db.py` is unchanged (E9).
- Untouched: `fm26/`, `fm27/` extraction, `tools/` (reused read-only: `fmdb.py`,
  `extract_frames.py` logic).
- Dependencies: `zstandard` (already required by `tools/`) and `numpy` (new; makes a
  600 MB save take ~17 s instead of minutes). macOS only for the guide; the parser itself
  is plain Python.
- No game data is committed; outputs stay local as with FM26/FM27.
