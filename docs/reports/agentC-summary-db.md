# Agent C — summary.dat / basic_people_db.raw parsing report

Date: 2026 session. Scope: parse the uncompressed `summary.dat` and the
zstd-decompressed `basic_people_db.raw` into CSV (person id, names, numeric
fields) and cross-check against `work/FMdataExport/DataAnalyser/FM26_Example_data.csv`.

## TL;DR

* `summary.dat` is **not** zstd. It is a raw structured table. It contains
  **40,408 person records** (30,901 unique ids), each with first name, second
  name, a position bitmask, **Current Ability**, an 8-bit age and an unknown
  byte plus two unknown u32 ids.
* `basic_people_db.raw` is a table of **84-byte fixed records** (723,009
  records). Every record stores the person id **twice** at record offsets
  **16 and 20**. It contains no names.
* Cross-check vs the 71,745-row example CSV:
  * 71,260 / 71,745 example ids (99.3 %) are present in `basic_people_db.raw`.
  * 8,630 / 71,745 example ids (12.0 %) have a named record in `summary.dat`.
* Decoded reliably from `summary.dat`: person id, first/second name, position
  bitmask (and position labels), Current Ability (0–195), age (verified at
  99.9 % agreement with the example CSV). `summary.dat` age is the age at DB
  build time, so it can be 1 less than the in-game age.

## Inputs and checksum verification

| file | bytes | md5 |
|---|---|---|
| `…/2620_fm/summary.dat` (copied to `work/summary.raw`) | 5,236,844 | `f9965a2a4cce975e6c957d5d7fdda91c` |
| `…/2620_fm/basic_people_db.dat` → `work/basic_people_db.raw` | 60,147,370 | `e836c03ce6a65cdddc6c4d9f58292b7f` |

The raw files were re-derived/verified with:

```bash
GAME="$HOME/.steam/steam/steamapps/common/Football Manager 26/shared/data/database/db/2620/2620_fm"
# summary.dat is uncompressed: a plain copy is the raw table
cp "$GAME/summary.dat" work/summary.raw
# basic_people_db.dat is zstd behind the 12-byte "tad." header
python3 fmdb.py "$GAME/basic_people_db.dat" work/basic_people_db.raw
md5sum work/basic_people_db.raw   # e836c03ce6a65cdddc6c4d9f58292b7f
```

## `summary.dat` record format

Scanning `work/summary.raw` for the sequence `02 <u32 id> <u32 len1> <name1>
<u32 len2> <name2>` produces a stable, self-consistent stream. Record layout:

```
u8   tag = 0x02
u32  person_id
u32  len(first_name)          # 0 for people stored with a single full name
u8[len1] first_name (UTF-8)
u32  len(second_name)
u8[len2] second_name (UTF-8)
u8[16] tail
```

The 16-byte tail decodes (little endian, byte-packed) as:

| field | type | meaning | evidence |
|---|---|---|---|
| `summary_u32_a` | u32 | unknown id (216 distinct values) | dominant value per `Résidence` matches the country (France=769, England=765, Spain=796, Portugal=788, Argentina=1649) → very likely a **nation id** |
| `summary_u32_b` | u32 | unknown id (221 distinct values) | same shape as `a`, likely second-nation / club nation |
| `pos_flags` | u32 | position bitmask | see table below |
| `summary_ca` | u16 | **Current Ability** (range 0–195) | top values: Mbappé 195, Kane 188, Dembélé 186, Haaland 184, Rice 182, Salah/Courtois/Saka 181, Rodri 180, Van Dijk 179; distribution is the classic FM CA curve |
| `summary_age` | u8 | age at DB build time | equals example-CSV age or age−1 for **8,621 / 8,630 (99.9 %)** matched players |
| `summary_x` | u8 | unknown (values 1–5) | no clean correlation with club/position |

Examples (record bytes, `tail.hex()`):

```
Ronaldo  02 f0370b00 00000000 11000000 "Cristiano Ronaldo" ffffffff 14030000 00400000 9b00 28 05
         id=735216  first=""  second="Cristiano Ronaldo"  CA=155 age=40 x=5
Riyad    02 2a301205 05000000 "Riyad" 06000000 "Mahrez" 05000000 05000000 00080000 9100 22 01
         id=85078058 first="Riyad" second="Mahrez" CA=145 age=34 x=1
```

### Position bitmask (`pos_flags`)

Derived empirically from records whose flag is a single bit and comparing the
decoded value with the example CSV `Position` column:

| bit | label | bit | label |
|---|---|---|---|
| `0x0001` | GB | `0x0100` | M (D) |
| `0x0004` | D/AL (D) | `0x0200` | M (G) |
| `0x0008` | D/AL (G) | `0x0400` | M (C) |
| `0x0010` | D (C) | `0x0800` | MO (D) |
| `0x0020` | D/M (?) | `0x1000` | MO (G) |
| `0x0040` | AL (?) | `0x2000` | MO (C) |
| `0x0080` | MD | `0x4000` | BT (C) |
| `0x8000` | unknown | | |

For matched players the example position's base role is one of the decoded
summary roles in **6,877 / 8,596 (80 %)** of cases; the remainder are
multi-position or notation differences.

## `basic_people_db.raw` record format

The whole file is a table of **84-byte records** (the first ~0x41 bytes are a
small file header). Each record contains the person id twice, 4 bytes apart:

```
offset 0   u32 header word 0     (flags-like; 0 / 0x80000 / 0x1a040000 …)
offset 4   u32 header word 1     (0 or 0x1000)
offset 8   u32 always 0
offset 12  u32 per-record unique value (probably a record key/pointer)
offset 16  u32 person_id
offset 20  u32 person_id  (duplicate)
offset 24  u8  0x11  (constant tag)
offset 25  u8  subtype (1,2,3,4,5)
offset 26  payload, 58 bytes (packed numeric data)
```

Detected with the signature `d[i:i+4] == d[i+4:i+8] and d[i+8] == 0x11`:

* 723,009 records found (ids all unique within this table).
* Consecutive records are 84 bytes apart in 711,653 of cases; a small number of
  section boundaries produce gaps of 34/22/11/… bytes.

The payload is **not yet semantically decoded**: none of its u16/u32 fields
matches `summary.dat` Current Ability, age, nation or the example CSV columns.
It is exported verbatim so agent B / others can attack it with the schema from
the editor frames. Example payloads (u16 from offset 26):

```
Ronaldo  162,0, 788,0, 1289,0, 1485,0, ffff×8, 0,0,ffff,ffff, 60,110,110,110,126, 1982, 6,0,0
Mbappé   143,0, 769,0,  775,0,  881,0, ffff×4, 36,0,41,0, 0,0,ffff,ffff, 70,95,95,95,116, 1991, 0,0,0
```

Note: the value at u16 index 25 looks like a year for some players
(Militão 1998, Toney 1996, Cancelo 1994) but not for others (Kanté 1963), so it
is not simply the birth year.

## Cross-check with `FM26_Example_data.csv`

* example rows: **71,745** (44 columns, `Joueur`, `Unique ID`, `Âge`, `Club`, …).
* ids present in `basic_people_db` : **71,260** (99.3 %).
* ids present in `summary.dat`      : **8,630** (12.0 %).
* `summary.dat` unique ids: 30,901, of which 8,630 appear in the example CSV
  (the rest are retired legends, staff, free agents, non-playable people).

The example CSV is not the full database (the raw tables contain ~723 k people);
it is the set of players in the active game view and was only used as the
cross-check.

## Deliverables (all under `work/agentC_summary/`)

| file | rows | notes |
|---|---|---|
| `players_summary.csv` | 30,901 (+1 header) | one row per person in `summary.dat` (duplicates collapsed, `n_records` records); names, position, CA, age, unknown ids, tail hex, joined `basic_people` numeric fields and example-CSV columns |
| `basic_people_db_parsed.csv` | 723,009 (+1) | every 84-byte record: id, 4 header u32, subtype, 15 payload u32 |
| `example_players_crosscheck.csv` | 71,745 (+1) | every example player with summary name/CA/age/position + basic_people fields; `in_summary` flag |
| `parse.py` | — | the parser that produced all of the above |

Key columns of `players_summary.csv`:

```
person_id, first_name, second_name, display_name, n_records,
pos_flags, positions, summary_ca, summary_age, summary_x,
summary_u16_e, summary_u16_e_all, summary_u32_a, summary_u32_b,
summary_tail_hex, in_example_csv, example_name, example_age,
example_club, example_nation, example_position,
basic_present, basic_hdr0..3, basic_subtype, basic_w00..w14
```

## Reproduce

```bash
cd /home/dat/src/football_manager
python3 work/agentC_summary/parse.py
# -> work/agentC_summary/{players_summary,basic_people_db_parsed,example_players_crosscheck}.csv
```

## Caveats / next steps

1. `summary.dat` covers only 30,901 people; the other ~690 k names live in
   `people_db.raw` (agent B's stream). Joining this CA/position decode onto the
   full `people_db.raw` name table would give the complete player list.
2. `summary_u32_a` is almost certainly a nation id (strong per-country modes);
   `summary_u32_b` is a same-shaped second id. Cheap to confirm by building the
   nation id→name table from `natc` records / the editor schema.
3. The `basic_people_db` 58-byte payload is still opaque. It is packed (many
   `0xffff` runs and repeated value/0 u16 pairs). A bit-level schema from the
   editor frames (`editor.fmf.016/.076/.098.bin`, `db_field="pers,…"`) is the
   most promising route.
4. All writes were confined to `work/`; the game install and Steam were never
   modified (raw files were read-only copies / decompressions).
