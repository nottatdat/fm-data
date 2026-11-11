# Tasks

Every experiment writes `fm24/experiments/E<n>-<slug>.md` (method, result, pass/fail,
decision). An experiment that fails its criterion stops the dependent tasks until the
user decides how to proceed. Ground truth follows design D9: exact on-screen values of
the user's own players; CA/PA only sanity-checked.

## 1. Scaffolding and FM27 regression baseline

- [x] 1.1 Create `fm24/` with `GUIDE.md` (stub), `csv/README.md` (stub), `experiments/`, `save/`; add `fm24/work/` and `fm24/csv/*.json` to `.gitignore` (`*.csv` and `fm27/explorer/data/` are already covered); verify `git status` shows only the new stubs and `git diff --stat -- fm26 fm27 tools` is empty
- [x] 1.2 Build the FM27 regression fixture (D8): a few hundred rows in the `fm27_players.csv` column format plus a minimal `history.db` with the tables `server.py` checks, under `fm24/work/fm27-fixture/`, with the builder script now in `fm24/tests/fm27_fixture.py`; verify the current explorer starts on it and serves search and a profile without errors
- [x] 1.3 Capture the baseline from the pre-change commit in a temporary worktree under `.context/`: JSON for a fixed list of searches, filters and ≥5 profiles, plus screenshots of the search page and one profile, saved to `fm24/work/fm27-baseline/` with the capture script now in `fm24/tests/fm27_regression.py`; verify a second capture run gives byte-identical JSON

## 2. Cheap experiments (independent, run first)

- [x] 2.1 E7 process detection (≤10 min): with FM24 open via Epic and closed, find a process check that is reliably true/false; pass: one command distinguishes the two states
- [x] 2.2 E6 save writing and naming (≤30 min): watch `games/` during ⌘S of a large save (`fs_usage` or repeated stat) and note how `last save overwrite backup*.fm` and any autosave files are created; pass: note states in-place vs temp + rename, the settled-file rule, and the exact backup/autosave name patterns to exclude
- [x] 2.3 E5 in-game date (≤30 min): locate the current game date in a save, using 2 saves with known, different in-game dates; pass: both decoded, else record "mtime only, age blank"
- [x] 2.4 E4 save scope (≤30 min, after the id check in 3.1 if needed): count distinct people in 2 careers' saves vs the shipped DB (198,662); pass: counts and the loaded-league explanation recorded
- [x] 2.5 E9 importer behaviour (≤15 min): run `import_db.build()` into a temp DB from a CSV with the importer's source columns but only id/name/club/gender/a few attributes filled; pass: build succeeds, blank numbers are NULL, blank text is `""`, and a profile with blank CA/PA/attributes renders without errors in the explorer
- [x] 2.6 E10 face/logo ids (≤30 min): check whether the local face/logo packs' ids match FM24 person/club ids for 10 known players and clubs; pass: decision recorded to use them in FM24 mode or fall back to placeholders

## 3. Gate: player record decode

- [x] 3.1 E1 decode one own player (time box 2 days): first establish whether string-table ids are person ids or name-dictionary ids, then find one of the user's own players and decode DOB, nationality, club and ≥5 visible attributes; pass: DOB/age/nationality/club equal the in-game profile, attributes within ±1 (equal where no change arrow). On fail: stop and review options with the user
- [x] 3.2 E2 field encoding (within E1): determine whether records are tag/field-code encoded or fixed-layout structs, whether the shipped editor schema / field codes apply, and whether hidden attributes are stored like visible ones; pass: note states the encoding and how each decoded field is located
- [x] 3.4 E11 club/nation names (time box 1 day): map the player's club ref (uid − 22) and the nationality index to names; pass: the 7 screenshot players resolve to Rennes/France, plus Haaland/Foden → Man City, Saka → Arsenal, Mbappé → PSG, Jude Bellingham → Real Madrid; on fail: stop and review with the user
- [x] 3.3 E3 generalise (after E1): decode 20 of the user's own players across positions, ages and both feet; pass: ≥19/20 match on DOB/age/nationality/club, and attributes within ±1 for the players with screenshots; locate CA/PA and check they order consistently with coach star ratings; record which importer columns are verified, unverified or blank

## 4. Save extractor (fm24-save-extraction)

- [x] 4.1 Implement save selection in `fm24/save/parse_save.py` (newest career `.fm`, backups excluded per E6, explicit path option, clear error when none); verify with a temp directory holding career saves, a newer backup file, and an empty directory
- [x] 4.2 Implement record decoding per E1–E3 and write `fm24_players.csv` with the importer's source columns (`import_db.ALL_COLS` minus `club_display`/`club_search`), blanks for undecoded, explicit `gender`, and `age` from the in-game date or blank; verify the header matches that list and the 20 E3 players match their recorded values
- [x] 4.3 Write `fm24_meta.json` (save file, saved-at, in-game date or null, row count, verified/unverified columns); write CSV and meta to temp files and publish them only after success; add the consistent-snapshot check (size/mtime before vs after); verify that touching the save during a run discards the result and that a forced failure leaves the previous CSV and meta unchanged
- [x] 4.4 E8 reload time: on the largest save (~600 MB) time extraction + `import_db.build()` + FTS together; pass: < 30 s total, else record the bottleneck and optimise inside `fm24/` before continuing
- [x] 4.5 Verify read-only behaviour: the save's checksum and mtime are unchanged after extraction with FM running, and `git status` shows no generated data files
- [x] 4.6 Document the extractor in `fm24/GUIDE.md` and the verified/unverified/blank columns in `fm24/csv/README.md`; verify the guide's commands run as written in a clean shell

## 5. Explorer game selection (explorer-game-datasets)

- [x] 5.1 Add `--game {fm27,fm24}` to `server.py`, resolved once at startup (D5): FM24 passes its CSV and `data/fm24.db` paths explicitly, skips the history build, disables `player_club_id`, and exits with "run the FM24 save extractor first" if its CSV is missing; verify an unsupported value and a missing FM24 CSV both exit non-zero with the right message
- [x] 5.2 Add `/api/meta` (label, player count, panel availability, save-backed flag, unverified columns); make the UI take title/header from it, skip history/form requests and panels when unavailable, and mark unverified values; verify an FM24 profile, with an FM27 `history.db` present, shows no history/form panel, no FM27 club logo, an "unverified" marker on CA/PA, and no failed requests in the browser network log
- [x] 5.3 Run the D8 comparison against the 1.3 baseline with the default server on the fixture: identical JSON, matching UI screenshots with no banner or `/api/meta` polling, FM27 fixture DB/CSV mtimes unchanged after starting in FM24 mode, `git diff --stat -- fm26 fm27 tools ':!fm27/explorer'` empty, and only `server.py`, `static/*` and `README.md` changed in `fm27/explorer`

## 6. Freshness banner and reload (explorer-save-freshness)

- [x] 6.1 Extend `/api/meta` with provenance, FM-running state (E7) and newest-career-save detection with the settled rule (E6), backups excluded; verify that changing a career save's mtime shows the newer save within 10 s and changing only a backup file shows nothing
- [x] 6.2 Render the banner: provenance with relative age; ⌘S instruction only while FM runs; `New save detected: "<name>" (<time>)` with **Load it**; verify each state with FM open and closed and after a real ⌘S, with screenshots saved under `.context/`
- [x] 6.3 Implement `POST /api/reload` per D7 (temp outputs, DB build, publish CSV then meta, rebuild `CLUB_INDEX`, clear `_filter_cache`, one reload at a time) with a loading state in the UI; verify that a successful reload updates data, banner, filters and club search (using a save with a club absent from the previous one), that a second click during a reload starts nothing, and that a forced failure (corrupt save copy) keeps the previous data, banner and filters with the error shown
- [x] 6.4 Update `fm24/GUIDE.md` with the explorer flow (start with `--game fm24`, press ⌘S, click Load it) and add a short `--game` note to `fm27/explorer/README.md`; verify the documented steps reproduce the flow

## 8. Review fixes (maintainability review, after implementation)

- [x] 8.1 Fix decoder correctness found in review: keep regens born during long careers (birth-year bound from the in-game date, minimum age 13) and fail loudly on low coverage instead of publishing blank data; verify the 2036 save's youngest players are 15 and `test_layouts`/`test_parse_save` pass
- [x] 8.2 Name every record offset in `parse_save.py` (layout constants tied to E-notes), split `decode_header`/`decode_ratings`, derive the blank-column list, assert attribute names against the importer, load the importer by path; verify identical output on the Rennes save (84,437 rows, 292/294)
- [x] 8.3 Per-game `GAMES` dict in `server.py`, `fm24` as a package, `window.FM_GAME` panels read by `app.js`, `savemode.js`, startup check of the `index.html` injection, cache refresh order, Origin check, stale-DB rebuild, pgrep cache, correct reload error phases; verify FM24 browser flow and FM27 API + UI identical to the baseline
- [x] 8.4 Tests in `fm24/tests/` (layouts on synthetic bytes, live.py, server FM24 mode, FM27 unchanged vs `origin/master`); verify `python3 -m unittest discover -s fm24/tests -t .` passes with no resource warnings

## 7. Integration check

- [x] 7.1 End-to-end on the user's Mac: in FM24 make a change you control (sign or release a player, or change a contract), ⌘S, wait for the banner, Load it, and confirm the change appears in the explorer; then re-run the 5.3 comparison; verify both pass
