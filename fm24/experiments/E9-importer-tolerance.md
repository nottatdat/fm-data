# E9 — Importer tolerance to blank columns

**Question:** can `fm27/explorer/import_db.build()` load an FM24 CSV in which most
columns are blank, and does the explorer render such players?

**Method:** wrote a 20-row CSV with exactly the importer's source columns
(`import_db.ALL_COLS` minus `club_display`/`club_search`), filling only `id`, `name`,
`club` (half blank), `gender` (one "1") and two attributes. Built it with
`import_db.build(test.db, csv, force=True)`, queried the result, then served it from a
throwaway worktree of the pre-change explorer and opened a profile in headless Chromium.

**Result:**
- Build succeeded (20 rows, FTS built).
- Blank numeric columns → `NULL` (`ca`, `pa`, `age`, attributes).
- Blank text columns → `""` (`nat`, `dob`, `foot`, `club`).
- `gender`: `"1"` → `Women`, blank/`"0"` → `Men`. FM24 output must write gender explicitly.
- Profile rendered every blank as "—" (CA, PA, age, DOB, attributes); filled attributes
  shown. Only console errors were 404s for face/club-logo images (no asset packs in this
  checkout), which the UI already tolerates (`onerror` removes the image).

**Verdict:** PASS. No importer change needed. Decisions: write `gender` explicitly
(design D4); blank club displays as "Free agent", which is acceptable.
