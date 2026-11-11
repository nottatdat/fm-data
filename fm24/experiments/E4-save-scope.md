# E4 — How many people a save holds

**Method:** counted person records (first/surname ids found in the save's name dictionary,
valid DOB) in two careers' main blocks; compared with the shipped FM24 database
(`people_db.dat`, 198,662 people via `fm27/offline/parse_people.py`).

| Save | in-game date | people in save |
|---|---|---|
| Career - Rennes.fm | 21 Dec 2023 | 149,867 |
| Career - Everton.fm | 17 Sep 2024 | 109,891 |
| shipped database | — | 198,662 |

**Result:** a save holds only the people FM loaded for that career (the nations/leagues
chosen at setup, plus regens created since), so counts differ per career and are below the
full database. The name dictionary itself is the full one (~545k entries) in both.
People include staff and non-playing persons; players are the subset with a player block.

**Verdict:** PASS (recorded, not a bug). The guide will say: "the explorer shows the
players loaded in your career, not the whole FM database".
