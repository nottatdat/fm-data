# E15 — Personality (hidden)

**Method:** read the 8 bytes after the person record's 4 zero bytes following nationality
(person end + 17..24), in fm-editor's memory order (adaptability, ambition, loyalty,
pressure, professionalism, sportsmanship, temperament, controversy), and compared with
the personality labels on the 8 profiles.

**Result:** all values 1–20. Labels agree: Mandanda professionalism 17 (his highest) →
"Fairly Professional"; Gallon loyalty 15 (highest) → "Fairly Loyal"; "Balanced" players
have no label-driving trait ≥ 15; the four "Fairly Determined" players have Determination
15 (a visible attribute that drives that label).

**Verdict:** PASS, exported as **unverified** (FM never shows the numbers).
