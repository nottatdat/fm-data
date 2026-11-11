# E2 — Field encoding

**Result:** fixed-layout binary records, not tag/field-code encoded.
- Name dictionary: `[u32 id][u32 len][utf-8]`, sequential ids.
- Person: `[u32 first id]00[u32 surname id]00[u32 common id]00[u32 len][full name or empty]`
  `[u16 doy|flags][u16 year]` (DOB), then 5 bytes, `[u32 nationality index]`, …,
  8 bytes that look like hidden personality (unverified).
- Player: FM unique id written twice; club ref at uid − 22, league-nation ref at uid − 30.
  Record lengths vary per person, so fields are located via anchors, not fixed offsets.
- Attribute history: 71-byte records before the person record, 47 attributes on 1–100.
- Dates everywhere: `u16 (day-of-year & 0x1FF)`, `u16 year`.
- The editor field codes (`field_dict.csv`) were not needed and do not appear in the save.

**Hidden attributes:** not located with evidence (no on-screen ground truth); they stay
blank, as design D9 allows.

**Verdict:** PASS.
