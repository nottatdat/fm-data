# Agent B — `people_db.raw` record layout & player extraction

**Deliverable:** `work/agentB_parse/parse_people.py` → `work/agentB_parse/players_people.csv`
**Raw input:** `work/people_db.raw` (451,072,539 bytes; zstd-decompressed `people_db.dat`)
**Game:** FM26 `26.2.0` (unmodified; read-only)

---

## 1. TL;DR

* I cracked the **person record layout** used by the large section of
  `people_db.raw`.
* Every person owns a **full-name string + date-of-birth** record:

  ```
  [u32 nation_ref] [ff ff ff ff] [00] [u32 name_len] [utf8 full name]
  [u16 day_of_year] [u16 year]
  ```

* The table is **grouped by `nation_ref`** (all Algerians first, then the next
  nation, …). 2,079 distinct `nation_ref` values are present.
* A parser extracts **216,348 people** with full legal name and a decoded ISO
  date of birth. Known players validate exactly (see §4).
* The parser optionally joins the FMdataExport example roster to attach the
  in-game **unique id / club / position** for recognised players
  (29,123 rows in the current run).
* The `[u32 id][u32 id]` player-link pair was located and documented (§5) but
  is **not unique enough to use as a name→id anchor from `people_db.raw`
  alone** (see §7 limitations).

---

## 2. How the raw file is laid out

`fmdb.py` decompresses `people_db.dat` to `people_db.raw`. The first bytes are
a small table of person-name records:

```
00000000  00 00 42 08 0b 00 74 05 0b 00 05 00 00 00 00 0d  ......t.........
00000010  00 00 00 4c 61 64 69 73 6c 61 76 20 4b 75 6e 61  ...Ladislav Kuna
```

Records in the first ~69 KB use a compact layout
`[u32 id][05 00 00 00][00][u32 len][name][8 zeros][u32 id][ptr][ptr]`
(1,478 records, ids `721528..723009`). From ~`0x10dd8` onward the file switches
to the **large person records** that are the subject of this task.

### 2.1 The full-name field

The overwhelming majority (`203,751 / 205,866`) of full names are preceded by a
fixed 20-byte struct plus a `ff ff ff ff` sentinel. For **Amoura**:

```
0001106f  01 00 6c 07 01 00 6c 07 ff ff ff ff ff ff ff ff   ................
0001107f  01 00 6c 07 00 00 70 80 00 00 00 08 00 62 ce 00   ......p......b..
0001108f  00 00 11 02 00 00 ff ff ff ff 00 17 00 00 00 4d   ...............M
0001109f  6f 68 61 6d 65 64 20 45 6c 20 41 6d 69 6e 65 20   ohamed El Amine
000110af  41 6d 6f 75 72 61 82 00 d0 07 01 02 10 06 07 00   Amoura..........
```

Field breakdown (name starts at `0x1109f`):

| offset (rel. name) | bytes | meaning |
|---|---|---|
| `-13..-10` | `11 02 00 00` | `nation_ref` = **529** (Algeria group) |
| `-9..-5`   | `ff ff ff ff 00` | inline-string sentinel |
| `-4..-1`   | `17 00 00 00` | name length = 23 UTF-8 bytes |
| `0..22`    | `Mohamed El Amine Amoura` | full name |
| `+23..+24` | `82 00` | day-of-year = 130 |
| `+25..+26` | `d0 07` | year = 2000 |

`(doy=130, year=2000)` → **2000-05-09**, Amoura's real DOB.

### 2.2 Compact record prefix

The 39 bytes immediately before a full name are extremely regular:

```
01 00 6c 07  01 00 6c 07  ff ff ff ff ff ff ff ff  01 00 6c 07  <19 field bytes>
```

`01 00 6c 07` = `(doy=1, year=1900)`, FM's **null date**. The 19 trailing field
bytes end with the `nation_ref`. This prefix was found at exactly `name-39` for
203,751 of the 205,866 `ff`-prefixed names; the residual names (e.g. Ronaldo)
use a non-null reference before the string and are still captured by the
generic name scan.

### 2.3 Player attribute block

Immediately after the DOB the person record continues with a small header and
then a run of 1..20 attribute bytes. Amoura's record:

```
Mohamed El Amine Amoura 82 00 d0 07   01 02 10 06 07 00 00 00
03 00 00 00 00 05 00 00 00   10 10 04 0a 05 03 04 10 6d 38 00 00 ...
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ FM-style attributes
```

Haaland's record shows the same shape with his known physical stats
(`10 14 0f 12 11 0a 0c 0b ...` = 16,20,15,18,17,10,12,11). This block is where
club/CA/PA eventually live, but the surrounding records contain variable-length
nested lists (contracts / history / relationships), so field offsets behind it
are **not fixed** (see §7).

---

## 3. Parser

`parse_people.py` (self-contained, no third-party modules):

1. Reads `people_db.raw`.
2. Scans for `[u32 len][utf8 name][u16 doy][u16 year]` where
   `2 <= len <= 70`, the bytes decode as UTF-8, the first char is a letter and
   ≥70 % of chars are name characters.
3. Rejects FM's null date `(1, 1900)` and day-of-year overflow.
4. Records `nation_ref` when the `ff ff ff ff 00` sentinel precedes the string.
5. (optional) Loads `FMdataExport/DataAnalyser/FM26_Example_data.csv` as a
   roster of known players and attaches `unique_id`, `common_name`, `club`,
   `position`, `age` by requiring every ≥3-char token of the common name to
   occur in the full name, with the closest age breaking ties.
6. Writes `players_people.csv`.

Run:

```bash
cd /home/dat/src/football_manager/work/agentB_parse
python3 parse_people.py            # ~21 s
# or: python3 parse_people.py <people_db.raw> <out.csv>
```

### Output columns

`unique_id, common_name, full_name, date_of_birth, age, club, position,
nation_ref, dob_year, dob_day_of_year, record_offset`

---

## 4. Known-player validation

| person | unique id | full name extracted | DOB (decoded) | age | club (roster) | nation_ref |
|---|---|---|---|---|---|---|
| Cristiano Ronaldo | 735216 | Cristiano Ronaldo dos Santos Aveiro | 1985-02-05 | 41 | Al Nassr | (no sentinel) |
| Erling Haaland | 29179241 | Erling Braut Haaland | 2000-07-21 | 25 | Man City | 1715 |
| Jude Bellingham | 29232937 | Jude Victor William Bellingham | 2003-06-29 | 22 | R. Madrid | 945 |
| Kylian Mbappé | 85139014 | Kylian Mbappé Lottin | 1998-12-20 | 27 | R. Madrid | 1291 |
| Mohamed Amoura | 2000069643 | Mohamed El Amine Amoura | 2000-05-09 | 25 | VfL Wolfsburg | 529 |
| Riyad Mahrez | 85078058 | Riyad Karim Mahrez | 1991-02-21 | 35 | Al Ahli | 535 |

All six line up with the real-world facts, confirming the DOB encoding
(`day_of_year`,`year`) and the field order.

---

## 5. Player link found inside the record

A player's in-game unique id appears once, as an **adjacent duplicate u32
pair**, later in the same record region:

```
... 00 00 00 00 00 00 00 00 87 93 05 00 0b a4 36 77 0b a4 36 77 ca da 00 00 ...
                                ^^^^^^^^^^^ ^^^^^^^^^^^ ^^^^^^^^^^^
                                A           person id   person id (Amoura)
```

Structure observed for every validated player:

```
p-8 : u32  0 or 1
p-4 : u32  A          (per-record id)
p   : u32  unique_id  \
p+4 : u32  unique_id  /  the player/person link
p+8 : u32  B          (unique per player, not the club)
p+12: u8   C          (1..4)
p+13: u16  position-ish list (values are multiples of 5)
```

Raw offsets for the known players:

| player | name offset | id-pair offset | Δ |
|---|---|---|---|
| Ronaldo | `0x1100793d` | `0x11007c92` | 853 |
| Haaland | `0x1034b964` | `0x1034bb7a` | 534 |
| Bellingham | `0x092bdc32` | `0x092bde72` | 576 |
| Amoura | `0x0001109f` | `0x000111d4` | 313 |
| Mahrez | `0x00011caf` | `0x00011e43` | 404 |

Δ is variable because variable-length nested lists sit between the name and the
link.

---

## 6. Results

```
$ python3 parse_people.py
reading .../people_db.raw ...
  451,072,539 bytes
  extracted 216,348 person name+DOB records
  loaded 71,745 known players for enrichment
  -> .../players_people.csv (216,348 rows, 29,123 enriched with a known unique id)
```

* `216,348` people with full name + ISO DOB.
* `203,568` carry a `nation_ref` (2,079 distinct values; table is nation-grouped).
* DOB years span `1928..2009` (null-date 1900 hits removed).
* `29,123` rows got an in-game `unique_id`, `club` and `position` through the
  known-player roster.

---

## 7. Limitations / not fully cracked

1. **Unique id from raw alone.** The `[id][id]` link is real but the value is
   not structurally distinguishable from coincidental 4-byte repeats that sit
   near names. `p-8 ∈ {0,1}` is necessary but not sufficient (it matches
   ~28 M positions). Therefore the in-game unique id is taken from the known
   player roster instead of being derived purely from `people_db.raw`.
2. **Player vs staff.** The big section is the **master person table**: it
   contains staff as well (e.g. `Josep Guardiola Sala`, doy=18 year=1971, is
   present). The CSV is therefore a *person* superset; the `unique_id` column
   is populated only for rows matched to the player roster.
3. **`nation_ref` naming.** Values such as `529/535` (Algeria) and `945`
   (England) are nation/representative-team references, but they are
   *team-level* (a nation has several nearby ids, e.g. women's teams use
   `2248/2286/2297`). Mapping every id to a nation name needs the separate
   `natc`/nation table and was not done here.
4. **CA/PA, height, club inside the raw record.** The attribute block was
   located but the field offsets behind it are not fixed because of
   variable-length nested lists (histories/contracts). These columns are therefore
   taken from the known-player roster when available.
5. The `FMdataExport` example CSV is from a user save (it contains newgens), so
   only the real players overlap the shipped database; that caps the roster join
   at ~29 k rows.

---

## 8. Exact commands / artifacts

```bash
# decompress (already done by agent A)
python3 work/fmdb.py "$GAME/shared/data/database/db/2620/2620_fm/people_db.dat" work/people_db.raw

# run the parser
cd work/agentB_parse && python3 parse_people.py

# spot checks
xxd -s 0x1106f -l 0x60 work/people_db.raw          # Amoura record
xxd -s 0x1034b930 -l 0xc0 work/people_db.raw       # Haaland record
```

Artifacts:
* `work/agentB_parse/parse_people.py`
* `work/agentB_parse/players_people.csv`
* `work/agentB_parse/_name_cands.pkl`, `_id_pairs.pkl` (intermediate scans)
* `work/agentB/REPORT.md` (this file; copy under `work/agentB_parse/`)
