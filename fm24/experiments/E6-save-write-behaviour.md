# E6 — How FM24 writes a save

**Method:** `e6_watch.py` polled the `games/` folder every 0.1 s while the user pressed ⌘S
twice (20 Dec 2023, then 21 Dec 2023 after advancing a day). Log: `fm24/work/e6/watch.log`.

**Result (both saves identical in shape):**
1. The previous save is **renamed** to `last save overwrite backup.fm` (same size, its old
   mtime preserved).
2. The new save is written **in place** under the career name, growing continuously from
   ~0.9 MB to its final size (~183 MB) over ~3 s, with no pause longer than 0.2 s.
3. Older backups are `last save overwrite backup (v02).fm`, `(v03)`, …; versioned career
   saves are `<career> (v02).fm`, `(v03)`, ….

**Verdict:** PASS. Decisions:
- Exclude `last save overwrite backup*.fm` from save selection and newer-save detection.
- Settled rule: size **and** mtime unchanged across two checks ≥ 1 s apart.
- The extractor still checks size/mtime before and after reading, since a partial file is
  a real possibility during those ~3 s.
