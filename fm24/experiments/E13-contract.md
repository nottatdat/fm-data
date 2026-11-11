# E13 — Contract: wage and expiry

**Method:** ground truth from the 8 profile screenshots ("£8.75K p/w until 30/6/2026").
Listed dates before each person record; searched a consistent wage/date relationship.
Script: `e13_contract.py`.

**Result:** the contract record holds `[u32 expiry date][u32 start date]` and, after a
variable gap (47–134 bytes), `[u32 club ref][u32 0][u32 weekly wage £]`. Linked to the
player through their own club ref (the header's), with the nearest date pair within 200
bytes before it. Stored wages are exact and FM rounds them for display (8,675 → £8.75K,
51,307 → £51K). 8/8: expiry exact, wage within display rounding, including a player at
another club (Mamardashvili, Valencia: started 1/1/2022, real signing date).

**Verdict:** PASS.
