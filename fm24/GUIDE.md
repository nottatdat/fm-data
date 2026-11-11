# FM24 (macOS) — Save-File Capture Guide

> **Scope: Football Manager 24 on macOS only.** FM26/FM27 use the live-memory route in
> `fm26/` and `fm27/`; this folder does not support them, nor FM24 on Windows/Linux.

> All commands are run from the repository root.

FM24 on macOS is read from your **save files** (`.fm`), not from game memory, so nothing
is injected into the game and SIP stays untouched. The data is **"as of your last save"**:
press **⌘S** in FM for fresh data.

Tested on: **FM24 24.4.2** (Epic, Apple Silicon), saves written by 24.3–24.4.

## 1. Requirements

```bash
python3 -m pip install zstandard numpy
```

`zstandard` is already used by `tools/`; `numpy` makes extraction take seconds instead of
minutes (≈ 10–17 s for a 180–600 MB save).

## 2. Save in FM24

Saves live in:

```
~/Library/Application Support/Sports Interactive/Football Manager 2024/games/
```

(Set `FM24_SAVES=/path/to/games` if yours are elsewhere.)

Press **⌘S** in FM and wait for "Game saved". FM renames the previous save to
`last save overwrite backup.fm` and writes the new one in place (~3 s); the extractor
ignores the backup files.

## 3. Extract

```bash
python3 fm24/save/parse_save.py                  # newest career save
python3 fm24/save/parse_save.py --save "<path>.fm"   # a specific save
```

Output (local only, gitignored):

| File | Content |
|---|---|
| `fm24/csv/fm24_players.csv` | one row per player, same columns as `fm27_players.csv` |
| `fm24/csv/fm24_meta.json` | save file, saved-at, in-game date, verified/unverified/blank columns |

The CSV and metadata are replaced together, and only after a complete extraction; a
failed run (or a save that changed while being read) leaves the previous output intact.

What a save contains: only the people loaded for that career (the nations/leagues chosen at
setup, plus regens), e.g. ~84k players in a 2023 Rennes career and ~111k in a 2036 one,
not the whole FM database.

## 4. Browse in the Profiles Explorer

```bash
cd fm27/explorer
python3 server.py --game fm24        # open http://127.0.0.1:8770
```

A banner shows which save the data came from and when it was saved. While FM is running
it reminds you to press **⌘S** for fresh data; after you save, it shows
**New save detected → Load it** within ~10 s. Load it re-extracts the save and refreshes
the page (≈ 15–20 s); if anything fails, the previous data stays and the banner says why.
CA/PA and hidden attributes carry a **?** marker (decoded but not shown as numbers in FM).

## 5. Column notes

See [`csv/README.md`](csv/README.md): which columns are exact, which are unverified
(CA/PA, hidden attributes) and which stay blank.

## Tests

```bash
python3 -m unittest discover -s fm24/tests -t .
```

See [`tests/README.md`](tests/README.md); none of them touch your saves or the game.

## How it works

The save is a container of zstd frames; the main frame holds plaintext binary records.
The record layouts (people, name dictionaries, nations, clubs, teams, player ratings) and
the evidence for each are in [`experiments/`](experiments/) (E1–E11).
