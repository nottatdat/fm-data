# E11 — Club / nation refs → names  (PASS)

## Nationality (SOLVED)

- **Nation table in the save** (~20.7–20.9 MB of the main block): records
  `[u32 nation index][u32 nation UID][u32 nation UID] 00 …` in index order, UIDs rising.
  250 nations (index 1–250) in the Rennes save. Walked record by record from Morocco
  (29/34); anchors England 139/765, France 143/769, Georgia 144/770, Norway 160/786,
  Argentina 187/1649 all match.
- **Person nationality = nation index → UID (from the save's own table) → English name.**
- **Names:** English country names are not in the save or in plaintext in the shipped DB.
  `fm24/save/nations_en.json` maps nation UID → English name: the 228 UIDs from
  mavarobli/FMSuperScout `tools/nation-ids.json` (MIT; Dutch names, translated), plus
  215446 → Soviet Union (inferred from its 7 Soviet-era players).
- Of the 23 nations in the save that the list lacks, 22 have no people in this save.
- Check (person-record scan, 149,867 people): Rennes players France, Haaland Norway,
  Foden England, Mamardashvili Georgia, Messi Argentina, Hakimi Morocco, Parfait Mandanda
  DR Congo; **99.75 %** of people get a name (unnamed: index 0 = 320 people, plus scan noise).

## Club (SOLVED)

Hint: barak14/fm-editor `docs/fm24/memory-layout.md`: player → team → club, a club's
senior team shares the club UID (facts only; fm-editor is GPL-3.0, no code reused).

- **Club record:** `[u32 club index][u32 uid][u32 uid] 00 [u32 nat] ffffffff [nat][nat]
  [u32][4 bytes] ff ff [u32 len][full name][u32 len][short name]`. Anchoring on the
  `index, uid, uid` triple also catches records the earlier regex missed (Real Madrid is
  stored as "R. Madrid", FM24's unlicensed name). 30,864 clubs.
- **Team record (table around 40 MB in the main block):** `… [u32 club index] (uid − 18)
  … [u32 team no][u32 uid][u32 uid] 0a 00 …`.
- **Player club ref = team no + 1.**
- Anchors (`e11_clubs.py`): 557 Manchester City, 481 Arsenal, 600 Sunderland,
  725 Paris Saint-Germain, 738 Stade Rennais FC, 1396 R. Madrid, 1420 Valencia: 7/7.
- Coverage across all players: to be measured by the real parser (task 4.2); the quick
  scan used here also counts non-player byte pairs, so its percentage is not meaningful.
- National teams (uid − 30 values 638/642/669) are not club teams; not needed for the CSV.

## Squad check (27 players from the user's Rennes squad list) and follow-up fixes

24/27 decoded with correct age and nationality (2 greyed-out players have no person record
in the save; FM shows them without a value). Fixes driven by the check:
- **Two header variants per save** (0x58 shipped-DB players, 0x40 players created during the
  career; also 0x18, 0x78, 0x42, 0xc0): accept every marker whose candidates resolve to a real
  team often enough, not one marker per save. +20k players in the Rennes save.
- **Header variant byte** (`HDR_FLAG`) takes 1, 2, 3, 4, 8, 16 on real headers (16 is common
  in 2036 saves); 0/5/7/108 are noise. William Saliba's header has 16.
- **Club refs must be plausible**: a team index (< MAX_INDEX) or a no-club value
  (0, 0xFFFFFFFF, 0xFF02FF); garbage refs mark other record types and are rejected. Before
  this, a player whose own header was filtered out got the next record's id and club.
- **B/youth teams** (e.g. "Rennes 2", "Reims 2") store their own name before the team
  number, and their tail byte after 0x0a varies (0x00/0x10).
- **Club records can carry two nations** (Welsh clubs in the English league: 139/175/139).
- **Free agents / retired**: club ref 0, 0xFFFFFFFF or 0xFF02FF → club blank ("Free agent").
  Teams that cannot be named (some loan clubs) also give a blank club, the player is kept.

Verified: Lembet and Nagida resolve to "Reims 2" (ref = team number + 1, as for senior
teams); the user confirmed in-game that both play only for Reims 2. Squad check result:
25/27 correct (age, nationality, club or loan club), 2 greyed-out players without a
person record in the save.

**Career-created teams** (user check: Jérémy Jacquet on loan at Clermont, history shows
"Clermont" and "Clermont 2"): his club ref 41714 is a team FM created during the career,
stored without a uid pair: `[u32 club index][10 zero bytes][u32 team no][u32 uid][u32] 0a`.
Named after its club, it resolves to Clermont Foot 63 (ref = team no + 1). This layout
names ~14.7k more players' clubs in the Rennes save; 50 of 67.7k such team numbers point at
two clubs (first match kept, senior/B teams take precedence).
