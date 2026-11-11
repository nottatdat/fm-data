# E5 — In-game date

**Method:** two saves of the Rennes career with user-confirmed dates (20 Dec 2023 and
21 Dec 2023, `fm24/work/e5/`), searched for the encodings that differed only in the date.

**Result:**
- Dates are stored as `u16 day-of-year (1-based, low 9 bits; high bits are flags)` +
  `u16 year`, the same encoding as DOB and contract dates. 20 Dec → `62 01 e7 07`,
  21 Dec → `63 01 e7 07`; an older save `5d 5d e7 07` → 349 → 15 Dec 2023.
- Most robust location: the third zstd frame (save summary used by Load Game) holds
  `[u32 len][manager name][u32 len][club name][u16 doy|flags][u16 year]`. The fixed offset
  36 in the main block is *not* stable across saves.
- Decoded for all 30 career saves; every date is plausible and versioned saves of a
  career are ~1 week apart. Manager name differs between careers (two different
  names in the tested saves), so parse by structure, not by name.

**Verdict:** PASS. Age = in-game date − DOB. Also: `bf 1a e7 07` seen in every player
record is a date (10 Jul 2023), so it is not a valid record anchor across saves.
