# E8 — Reload time (extraction + explorer DB build)

| Save | size | in-game | players | extraction | `import_db.build` | total |
|---|---|---|---|---|---|---|
| Career - Rennes.fm (copy) | 183 MB | 21 Dec 2023 | 84,438 | 10–12 s | 2.6 s | ~14 s |
| Career - Tosu.fm (largest) | 601 MB | 30 Aug 2036 | 110,920 | 17.2 s | 1.0 s | ~18 s |

Target < 30 s: **PASS**. The first prototype took 223 s; the fix was replacing a per-player
byte scan with numpy-precomputed candidates. The save's checksum and mtime were unchanged
after the Tosu run (read-only check, task 4.5).

Layout differences found by running a second career (fixed in the parser):
- the first-name dictionary can be split into two runs (names added during a career);
- the player-header marker byte differs per save (0x58 in Rennes, 0x40 in Tosu); it is
  chosen per save by club-ref votes.

**Re-measured after the squad-check fixes** (more header variants and team layouts):
Rennes 87k players 14.7 s, Tosu (601 MB) 97.7k players 22.1 s + 1.0 s DB build ≈ 23 s:
still under 30 s.

**With height, contract and personality (fm24-player-details):** Rennes 18 s; Tosu (601 MB) 27.7 s + 1 s DB build ≈ 29 s: just under 30 s; the contract search is the main added cost and the first place to optimise if saves grow.
