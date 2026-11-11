# Tasks

Ground truth: the 8 profile screenshots already used (`fm24/work/screens.json`, local) plus
one contract-tab screenshot per player. Each experiment writes `fm24/experiments/E<n>-*.md`.

## 1. Ground truth

- [x] 1.1 Record height, weight, value range, personality label, wage and expiry of the 8 players from the existing profile screenshots (they show wage and contract end too), in `fm24/work/screens.json`; verify all 8 have every field

## 2. Experiments (time box ½ day each)

- [x] 2.1 E12 height/weight: locate them for all 8 players through an explicit link; pass: 8/8 exact
- [x] 2.2 E13 contract: locate wage and expiry for all 8; pass: 8/8 expiry exact, wage within display rounding; record unit/currency
- [x] 2.3 E14 market value: locate the stored value; pass: 8/8 inside the displayed range — FAIL (not stored; requirement removed, see E14 note)
- [x] 2.4 E15 personality: confirm the 8 bytes after nationality are the personality attributes (1–20, ordering consistent with the personality labels); pass: plausible for 8/8, recorded as unverified

## 4. Stored base valuation (after the E14 research lead)

- [x] 4.1 Read the u32 £ after the attributes (`RAT_VALUE`), export as `value` (blank for 0xFFFFFFFF), list as unverified; mark it with "?" on profiles and search cards; verify Guéla Doué = 1,310,205 (FM "£1.3M"), tests pass, FM27 API unchanged, browser shows the markers with no console errors

## 3. Extractor

- [x] 3.1 Add layout constants and decoders for the passed experiments to `parse_save.py`, write `height`, `wage`, `expires` and personality columns, unverified ones in metadata; verify on the Rennes save that the 8 players match and coverage is reported in `meta.stats`
- [x] 3.2 Synthetic-byte tests for each new decoder in `fm24/tests/test_layouts.py` and real-save checks in `test_parse_save.py`; verify the full suite passes
- [x] 3.3 Update `fm24/csv/README.md` (column status) and the explorer check: a profile shows height, wage and contract expiry, with "?" on personality; verify in the browser with no console errors
