# E3 — Generalise to the user's squad

**Ground truth:** the user's Rennes squad list (27 players, in-game Jan 2024: name,
nationality, age, team) plus profile screenshots of 8 players and in-game confirmations
(Lembet and Nagida play for Reims 2; Jacquet is on loan at Clermont).

**Result (save of 21 Jan 2024):**
- 25/27 decoded; the 2 others (Antonin Leon, Fabio Geffroy) are greyed out in FM with no
  value and have no person record in the save.
- 25/25 correct nationality and club or loan club (Alemdar → ESTAC Troyes, Gomis → FC Lorient,
  Assignon → Burnley, Jacquet → Clermont Foot 63, Lembet/Nagida → Reims 2, the rest
  Stade Rennais FC); ages correct at the screenshot date.
- Attributes: 292/294 on-screen values equal for the 8 screenshot players, both misses
  within ±1 on a rounding boundary.

Fixes this needed are in E11 (header variants, variant byte, club-ref sanity, B teams,
career-created teams, Welsh clubs). **Verdict:** PASS (criterion ≥19/20).
