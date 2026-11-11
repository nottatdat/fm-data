# E12 — Height and weight

**Method:** for the 8 ground-truth players, searched for their on-screen height and weight
at a fixed offset from each decoded anchor (uid occurrences, person record, header,
ratings record). Scripts: `e12_details.py`, `e12_ratings_rel.py`.

**Result:** relative to the ratings record (first position rating): **u16 weight at +97,
u16 height at +99** (cm, kg), 8/8 exact. Same order as the memory layout in
barak14/fm-editor (weight 0x14C, height 0x14E). Nothing consistent near the uid or header.

**Verdict:** PASS. Weight is decoded too but the explorer CSV has no weight column, so it
is not exported (proposal: only without a schema change).
