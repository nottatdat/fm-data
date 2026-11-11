# E1 — Decode one player from an FM24 save  (PASS, revised criteria)

Save used so far: `Career - Rennes.fm` (FM24 24.3.0 save format). Main `tad.` block =
the zstd frame at offset 7558 (234,012,579 bytes decompressed, ~0.35 s).

## Findings so far (reference player: Erling Haaland, values not yet screen-verified)

1. **String-table ids are a name dictionary, not person ids.** Entries are
   `[id u32][len u32][utf-8]`, sequential ids; "Erling" exists under 6 ids, "Haaland" is
   id 414204. (Answers the first question of E1; E4 must count person records instead.)
2. **Person record** (found by searching the u32 surname id):
   ```
   ... c7 74 02 00            u32 160967  internal person index (referenced 81x in block)
   98 00 e6 07 ...            (u16 doy?, u16 year 2022 ...)  unknown
   ce 43 03 00 | 00           u32 first-name id 213966 ("Erling") + 1 byte
   fc 51 06 00 | 00           u32 surname id 414204 ("Haaland") + 1 byte
   ff ff ff ff | 00           u32 common-name id (none) + 1 byte
   14 00 00 00 "Erling Braut Haaland"   u32 length + full name
   cb 00 d0 07                DOB: u16 day-of-year 203 (1-based), u16 year 2000 = 21 Jul 2000 ✔
   ff 00 07 01 02 a0 ...      unknown
   10 14 0f 12 11 0a 0c 0b    8 bytes 16 20 15 18 17 10 12 11 — candidate hidden personality
   ```
3. **FM unique id** 29179241 (sortitoutsi/FMRTE id) appears as u32 twice, ~636 bytes after
   the name, followed by what looks like the player block.
4. **Candidate attribute block** ~689 bytes after the name: 54 bytes on a 1–100 scale
   (displayed value ≈ round(v/5)); contains 100 (→20, likely Finishing) and a run of 1–3
   values consistent with goalkeeping attributes on an outfield player.

## Nationality, club, age (follow-up, same save)

5. **Nationality** = u32 at *name end + 9* (after DOB + 5 bytes): Haaland 160, Foden 139.
   Club records carry the club's nation the same way (Man City/Arsenal/Sunderland 139,
   PSG/Rennes 143) → nation index 139 = England, 143 = France, 160 = Norway. Index → name
   mapping not done yet.
6. **Player block anchor**: every player has the 4-byte marker `bf 1a e7 07` followed 16
   bytes later by the FM unique id written twice (`uid uid`). 152,378 such records in the
   block. Record offsets vary per person, so decoding goes via this anchor, not a fixed
   offset from the name.
7. **Club reference** = u32 at *uid − 22*. Teammates agree: Haaland & Foden 557
   (Man City), Kylian & Ethan Mbappé 725 (PSG), Saka 481 (Arsenal), Jobe Bellingham 600
   (Sunderland), Jude Bellingham 1396. Counts per value look like club squads (first team
   + reserves + youth): 557→60, 481→68, 725→64, 600→60. u32 at *uid − 30* behaves like
   the club's league nation (638 for English clubs, 642 for French).
8. **Club ref → club name** is not yet a direct lookup: club records (found by a
   name-record signature) have a field at record −13 with ref = field + 127 for the English
   clubs tested and + 179 for PSG; Rennes' field 559 + 179 = 738 has 59 players, which is
   consistent. A per-nation offset is a hypothesis, not the final mapping; next step is to
   find the table the ref actually indexes.
9. **Age** = in-game date − DOB. DOB is decoded; the in-game date is E5.

## Ground-truth round 1 (user's own players, save `rennes_21dec.fm`, 21 Dec 2023)

Screenshots: Steve Mandanda (GK) and Désiré Doué (MC). Neither has a full-name string
(stored only when it differs from first name + surname), so they were found via the
surname dictionary id → person record (`[first id]00[surname id]00[common id]00[len=0]`).

| Field | Mandanda | Doué | Verdict |
|---|---|---|---|
| DOB | 28 Mar 1985 ✔ | 3 Jun 2005 ✔ | verified |
| Nationality index | 143 (France) ✔ | 143 ✔ | verified (index; name lookup open) |
| Club ref (uid − 22) | 738 | 738 | **Rennes = 738**, matches the prediction from the club table |
| League nation (uid − 30) | 642 | 642 | France |
| FM unique id | 8428461 | 2000115202 | |
| Height | — | 182 found 112 bytes after the uid ✔ | to confirm on Mandanda |

Notes:
- The "UID written twice" anchor alone gives false hits (first Mandanda attempt); pairing it
  with a valid club ref at uid − 22 fixed it. The parser needs a stricter anchor.
- **Attributes**: FM keeps a per-player *attribute history* (one 71-byte record per update)
  shortly before the person record: 47 attributes = 11 goalkeeping + 36 outfield, stored on
  a 1–100 scale (display ≈ value / 5). Doué's latest record matches all 36 visible values;
  Mandanda's latest matches 45/47; both misses are internal 48 shown as 9, so the latest
  history snapshot may lag the live values. The live values must live elsewhere (still to
  find).
- Order solved so far (two players): position 3 Eccentricity, 4 Handling, 5 Kicking,
  8 Punching, 14 Heading, 16 Long Throws, 18 Passing, 24 Corners, 33 Off The Ball,
  36 Work Rate; the remaining positions narrow to 2–7 candidates and need more players.

## Ground-truth round 2 (6 own players)

Players: Mandanda (GK), Désiré Doué, Warmed Omari, Arnaud Kalimuendo, Mathis Lambourde,
Guéla Doué. All located by DOB + nation 143 + club ref 738, and names confirmed by
decoding first/surname ids through the name dictionary. Solver: `e1_solve.py`.

**Attribute history record** (47 bytes, 1–100 scale, display = round(v/5)), 5 snapshots
per player in 71-byte records before the person record:
- 0–10: goalkeeping (Eccentricity 3, Handling 4, Kicking 5, Punching 8 fixed; the rest
  only partly fixed, since Mandanda is the only goalkeeper so far)
- 11–24 technical: Crossing, Dribbling, Finishing, Heading, Long Shots, Long Throws,
  Marking, Passing, Penalty Taking, Free Kicks, Tackling, Technique, First Touch, Corners
- 25–38 mental: Aggression, Anticipation, Bravery, Vision, Decisions, Determination, Flair,
  Leadership, Off The Ball, Positioning, Teamwork, Work Rate, Composure, Concentration
- 39–46 physical: Acceleration, Agility, Balance, Pace, Stamina, Strength, Jumping Reach,
  Natural Fitness

**The latest snapshot is not the live value.** Mismatches are exactly the attributes
with change arrows on screen: +1 where the arrow is up (Lambourde 14 attrs, Omari 3),
−1 where it is down (Guéla Doué 4, Kalimuendo 1). Players without recent changes match
36/36 (Désiré Doué). The snapshot is the baseline FM draws the arrows from.

**Live values not found yet.** Searched for the exact ordered vector (×5 and raw, u8 and
u16, /5, /10) in the whole main block and in all 1,271 decodable frames, plus multiset
windows of 36–70 bytes around each record: no exact match. Hypothesis: live values are
stored as per-attribute progress (e.g. fractional deltas) on top of the snapshot.

## Round 3: goalkeeping order + live-value hunt

**Goalkeeping (Mandanda + Gauthier Gallon, both exact on the latest snapshot):**
0 Aerial Reach, 1 Command Of Area, 2 Communication, 3 Eccentricity, 4 Handling,
5 Kicking, 6 Reflexes, 7/10 One On Ones / Rushing Out (still ambiguous: equal values for
both keepers), 8 Punching, 9 Throwing.

**Live-value hunt (all negative):**
- Exact ordered vector, u8 ×5 and raw, whole main block + 1,271 decodable frames: none.
- Order-agnostic multiset, 36/47-byte windows over the whole main block: best 35/36
  (other players' snapshots), never 36/36.
- u16 (both alignments) ×5 / raw / ÷10 over the whole block: ≤ 23/36.
- f32 arrays near the records: none.
- One-day diff (20 → 21 Dec) of Omari's records: changes are daily counters (+1/day,
  fitness/sharpness-like) and decaying ~10000-scale relationship values (−128/day),
  not attributes.
Conclusion: live attributes are not stored as a block of 36/47 values in any simple
encoding. Most likely FM derives them from the snapshot plus progress kept in another form.

## Verdict

**PASS** under the revised spec (attributes = latest snapshot, within ±1 of the screen):
7 own players decoded with exact DOB/age, nationality index 143 = France, club ref 738 =
Rennes, and the full 47-attribute order (One On Ones / Rushing Out still ambiguous between
positions 7 and 10). Turning club/nation refs into **names** is not solved yet → new
experiment E11.

## Leftovers (moved out of E1)
- Ground truth from the user's own players (DOB, nationality, club, ≥5 visible attributes
  from the in-game profile) to fix the attribute order and confirm the scale/rounding.
- Locate nationality and club references (likely internal ids → nation/club records).

## Round 4: live attribute block (supersedes the snapshot fallback)

Hint from barak14/fm-editor `docs/fm24/memory-layout.md` + `src/fields/fm24/player.rs`
(FM24 24.4.2 memory): positions 0x208..0x216 (15: GK SW DL DC DR DM ML MC MR AML AMC AMR
ST WBL WBR) then 54 encoded attributes 0x217..0x24C, display = (raw + 2) // 5. The same
byte order exists in the save (`e1_live_block.py`), ~2–3.5 KB before the person record.

| Player | matches | positions (≥10) |
|---|---|---|
| Mamardashvili (Valencia GK, no history) | 38/38 | GK20 |
| Mandanda / Gallon | 38/38 / 38/38 | GK20 |
| Désiré Doué | 36/36 | MC20 AMC18 AML16 |
| Lambourde (snapshot was 22/36) | 36/36 | AMR20 ST18 AML13 |
| Guéla Doué | 36/36 | DR20 DC16 WBR10 |
| Omari / Kalimuendo | 35/36 / 35/36 | DC20 DM15 / ST20 |

Total 292/294; both misses sit on a rounding boundary (raw 48 → 9, raw 28 → 5) and have
change arrows. Left/right foot (1–20) and hidden attributes (consistency, important
matches, injury proneness, versatility, dirtiness) are in the same block. CA/PA are not at
the memory-adjacent offset in the save (read 0) and are still to locate. The attribute
history exists only for some players (e.g. own squad), the live block for all checked.
