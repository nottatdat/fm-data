# Agent A — Reverse engineering the native FM26 DB reader (`game_plugin.dll`)

Scope: the native `.dat` database reader in
`~/.steam/steam/steamapps/common/Football Manager 26/fm_Data/Plugins/x86_64/game_plugin.dll`.
The game install was **never modified**; all writes are under `work/agentA_re/`.
The report requested at `work/agentA/REPORT.md` exists via symlink
`work/agentA -> work/agentA_re`.

## TL;DR

* `game_plugin.dll` is a 514,894,848-byte PE32+ DLL for **x86-64**, image base
  `0x180000000`. Despite the odd section names, the real code is in
  `.rdata` (VA 0x1000) and `.rodata` (VA 0x5039000); `.edata`/`.trace` hold
  RTTI + string tables. `objdump -d` refuses the file, so I disassemble byte
  windows extracted with `dd` and `objdump -D -b binary -m i386:x86-64`.
* MSVC RTTI is intact. The DB record classes and their inheritance / vtable
  slots are recovered (`rtti2.py`, `rtti2_out.txt`).
* The DB is a **named-property** system: each persistent class exposes named
  properties (`first_name`, `common_name`, `current_ability`, …) and the
  persistence/copy code keys values by those names. The string blobs and the
  descriptor tables live in `.edata`.
* The editor schema (`editor.fmf`) gives the authoritative **field-code
  dictionary**: 2103 `db_field` codes with human labels, 739 of them for the
  `pers` (person) table → `field_dict.csv`.
* `.dat` container format nailed down across all 14 files → `header_probe.py`.
  `people_db.dat` = 12-byte header `03 01 "tad." a0 0f 90 0e 07 00` then a
  raw zstd frame (`28 b5 2f fd`) that decompresses to 451 MB of person
  records; the game reads that frame through its internal `sicompression::
  ZSTD_*_STREAM` classes (no `zstd` import — the codec is statically linked).

## Tools / commands used

```bash
DLL=~/.steam/steam/steamapps/common/Football\ Manager\ 26/fm_Data/Plugins/x86_64/game_plugin.dll
python3 rtti2.py > rtti2_out.txt          # RTTI walker (COL sig==1)
python3 header_probe.py                   # .dat headers
python3 extract_field_dict.py             # editor.fmf -> field_dict.csv
python3 extract_props.py                  # DLL snake_case property strings
python3 extract_person_fieldmap.py        # correlate names with obj reads
gcc -O2 -o xref xref.c                    # 1-second whole-image xref scanner
./xref "$DLL" <target_rva> ...            # RIP-relative xrefs
# targeted disassembly (objdump chokes on the real sections):
dd if="$DLL" bs=1 skip=$((0x4d7300)) count=$((0x1600)) of=/tmp/win.bin
objdump -D -b binary -m i386:x86-64 --adjust-vma=0x1804d7f00 /tmp/win.bin
```

Artifacts in this directory: `pe.py`, `rtti.py` (first, buggy pass),
`rtti2.py` + `rtti2_out.txt`, `exports.py`, `xref.c`/`xref`,
`header_probe.py`, `extract_field_dict.py` + `field_dict.csv`,
`extract_props.py` + `dll_property_names.txt` / `dll_person_props.txt`,
`extract_person_fieldmap.py` + `person_field_offsets.csv`,
`database_load_disasm.txt`, `persistence_copy_disasm.txt`,
`all_strings*.txt`, `database_strings.txt`, `db_mangled.txt`,
`rtti_classes.txt`, `source_paths.txt`.

## 1. Container / serialization format of `.dat`

`header_probe.py` output (file size, 16-bit version, 4-char magic, zstd offset):

```
basic_people_db.dat   ver=0x0103 magic=b'tad.' zstd@12  hdr=03017461642ea00f900e070028b52ffd...
people_db.dat         ver=0x0103 magic=b'tad.' zstd@12  hdr=03017461642ea00f900e070028b52ffd...
(non_)pl_hist_index   ver=0x0103 magic=b'tad.' zstd@12  hdr=03017461642ea00f900e070028b52ffd...
server_db.dat         ver=0x0103 magic=b'tad.' zstd@38  (nested "fmf." at offset 14)
client_db.dat         ver=0x0103 magic=b'tad.' zstd@38  (nested "fmf." at offset 14)
lang_update_db.dat    ver=0x0103 magic=b'tad.' zstd@38  (nested "fmf." at offset 14)
pl_hist_dt.dat        ver=0x0103 magic=b'tadc' zstd@8   hdr=...74616463030028b52ffd...
non_pl_hist_dt.dat    ver=0x0103 magic=b'tadc' zstd@8
non_pl_hist_id.dat    ver=0x0103 magic=b'tadc' zstd@8
pl_hist_id.dat        ver=0x0103 magic=b'tadc' zstd@9   hdr=...7461646303010028b52ffd...
summary.dat           ver=0x0103 magic=b'tad.' no zstd (uncompressed)
```

Facts:

* Bytes 0–1 `03 01` = little-endian `0x0103` version (same in every file).
* Bytes 2–5 are `"tad."` (i.e. `".dat"` byte-reversed) for table files, or
  `"tadc"` for the history files.
* For `"tad."` table files the fixed 6 bytes `a0 0f 90 0e 07 00`
  (`0x0FA0`, `0x0E90`, `0x0007`) precede the zstd frame at offset 12.
  For `"tadc"` files the payload follows after 2–3 more bytes.
* `summary.dat` is not compressed and uses a different TLV-ish body.
* There is **no literal `"tad."`, `".dat"` magic check string, and no `zstd`
  import in the DLL** (`strings`/grep). The codec is statically linked; the
  class names `VZSTD_INPUT_STREAM@sicompression@@`,
  `VZSTD_OUTPUT_STREAM@sicompression@@`,
  `VZSTD_SEEKABLE_INPUT_STREAM@sicompression@@`,
  `VZSTD_SEEKABLE_FORMAT_OUTPUT_STREAM@sicompression@@` prove the reader goes
  through SI's own seekable-zstd streams.

Related error strings (file offsets in the DLL):
`0x4416e66 zstd compress error`, `0x4416e7a zstd decode error`,
`0x4416e8c zstd decompress error`, `0x4416ea2 zstd not supported`.

## 2. Record classes (MSVC RTTI) and layout offsets

`rtti2.py` implements the x64 RTTI walk (the crucial detail is that the
`_RTTICompleteObjectLocator.signature` is **1**, not 0, on x64). Full output in
`rtti2_out.txt`. Vtable RVAs are image-relative.

Class map (base-class `mdisp` = sub-object displacement inside the derived
object; `COL offset` = offset of that vtable inside the complete object):

```
DATABASE_RECORD@db                       vt 0x434bad8   : PROPERTIED            (mdisp 0)
PERSON@db          : DATABASE_RECORD      vt 0x44d2ae8   (mdisp 0)  + data
PLAYER@db          : virtual PERSON       vt 0x450a718 offset 0, vt 0x450ac08 offset 24
   (vbases: PERSON mdisp 0 pdisp 8 vdisp 4)
BASIC_PERSON@db    : PERSON               vt 0x473f5c8
ACTUAL_PERSON_BASE@db : PERSON            vt 0x46a90f8 offset 0, vt 0x46a9128 offset 120
ACTUAL_PERSON@db   : ACTUAL_PERSON_BASE   vt 0x4571168 offset 0, vt 0x45711b8 offset 288
ACTUAL_PLAYER@db   : ACTUAL_PERSON,PLAYER vt 0x4509828 offset 0, 0x4509d18 off 688, 0x4509d68 off 648
ACTUAL_NON_PLAYER@db : ACTUAL_PERSON      vt 0x4565018 off 256, 0x4564fc8 off 296
ACTUAL_PLAYER_AND_NON_PLAYER : ACTUAL_PLAYER, ACTUAL_NON_PLAYER (mdisp 640) 3 vtables
HUMAN_NON_PLAYER@db  : ACTUAL_NON_PLAYER  vt 0x44a51e8 off 0, 0x44a5238 off 1104, 0x44a5ab0 off 1144
GAME_PERSON         : EXTERN_PERSON@db -> PERSISTENT_PROPERTIED  vt 0x4487078 off 0, 0x4487278 off 8
GAME_PLAYER         : EXTERN_PLAYER@db -> PERSISTENT_PROPERTIED  vt 0x4487848 off 0, 0x4487958 off 8
GAME_PERSON_BIOPIC_BASE: EXTERN_PERSON_BIOPIC_BASE  vt 0x4489728/0x4489768
GAME_PLAYER_BIO     : EXTERN_PLAYER_BIO            vt 0x4489148/0x44891a8
GAME_PERSON_STATUS_FLAGS : EXTERN_PERSON_STATUS_FLAGS vt 0x4487658/0x4487698
INTERNATIONAL_PLAYER_DATA@db : BASE_INTERNATIONAL_PERSON_DATA@db  vt 0x450b468
DATABASE_TABLE_BASE@db vt 0x46db048 ; DATABASE_SUMMARY@db vt 0x44d6158
CLASS_INFO_TEMPLATE<GAME_PERSON> vt 0x4486ff8 : PERSISTENT_CLASS_INFO@sicore
CLASS_INFO_TEMPLATE<GAME_PLAYER> vt 0x44877c8 : PERSISTENT_CLASS_INFO@sicore
```

Interpretation for record layout work:

* `DATABASE_RECORD` and `PERSON` are **single-inheritance** with the record
  vtable at offset 0; the `PERSON` data members start immediately after the
  `DATABASE_RECORD` sub-object (which itself is just a vtable + the
  `PROPERTIED`/`PERSISTENT` machinery).
* `ACTUAL_PERSON_BASE` adds a second vtable at object offset **120**; then
  `ACTUAL_PERSON` adds one at **288**. `PLAYER` puts its second vtable at
  **24**. `ACTUAL_PLAYER` combines both, with vtables at 0, 648, 688.
  These offsets are the strongest hard evidence for where the sub-objects and
  their extra data begin.
* `GAME_*` classes (game-plugin runtime wrappers) hold a pointer/sub-object at
  offset 8 (`PERSISTENT@sicore` base, mdisp 8); the actual persisted data lives
  in the corresponding `ACTUAL_*` / `PERSON` objects.

Complete-object-locator / class-hierarchy data (including the `mdisp/pdisp/
vdisp` triples and vtable RVAs) is in `rtti2_out.txt`; the same script can be
pointed at any other mangled name to extend the map, e.g.

```bash
python3 rtti2.py '?AVGAME_PLAYER@@' '?AVACTUAL_PLAYER@db@@' '?AVHUMAN_NON_PLAYER@db@@'
```

## 3. Field definitions / named properties

The binary is a **named-property object system**:

* `sicore` base classes `PROPERTIED`, `PERSISTENT_PROPERTIED`,
  `PERSISTENT_CLASS_INFO`, `CLASS_INFO_TEMPLATE<T>`, `PERSISTENT_SUBCLASS_INFO`
  are present in RTTI (`rtti_classes.txt`, `db_mangled.txt`).
* String blobs of property names exist in `.edata`. Example cluster at file
  `0x46a8cb0` (RVA `0x46a98b0`), immediately after an 86-entry table of
  accessor function pointers:
  `first_name, second_name, common_name, adaptability, ambition, loyalty,
   pressure, professionalism, sportsmanship, temperament, controversy`.
  Each name is loaded by `lea rdx,[rip+…]` and handed to the persistence setter
  `call 0x1835c4ea0` in the copy/persist routine that starts at file
  `0x2cec1e0` (VA `0x182cec1e0`) — see `persistence_copy_disasm.txt`.
* 7,455 snake_case identifier strings were extracted from the DLL
  (`extract_props.py` → `dll_property_names.txt`), 2,838 keyword-filtered to
  person/player terms (`dll_person_props.txt`). Examples with RVAs:
  `first_name 0x46a98b0`, `second_name 0x46a98bb`, `common_name 0x46a98c7`,
  `current_ability 0x4748e57`, `potential_ability 0x451ba17`,
  `max_current_ability 0x4491ab4`, `min_current_ability 0x4491ac8`.
* The **editor schema** (`editor.fmf` frames in `work/frames/editor/`) is the
  authoritative short-code → meaning dictionary for the on-disk DB. It uses
  `db_field="pers,PnRV"` style codes. `extract_field_dict.py` produced
  `field_dict.csv` with **2103 entries** (table, db_field, label, source),
  **739 of them `pers`**. Selected person fields:

  | db_field | label | | db_field | label |
  |---|---|---|---|---|
  | `pers,duni` | unique id | | `pers,Ncra` | current ability |
  | `pers,PnRV` | name | | `pers,Npta` | potential ability |
  | `pers,Pfna` | first name | | `pers,Pnti` | nation |
  | `pers,Psna` | second name | | `pers,Pcti` | club |
  | `pers,Pcna` | common name | | `pers,Ppsr` | position |
  | `pers,Page` | age | | `pers,Pcwg` | wage |
  | `pers,Pcbi` | city of birth | | `pers,PMsq` | squad status |
  | `pers,Pnbi` | nation of birth | | `pers,Pcex` | contract expires |

  (The full list is the deliverable `field_dict.csv`; the same file covers
  `club, comp, natc, stad, team, weat, awar, inju, nati, city, agrm` …)

## 4. The load pipeline (native)

The `DATABASE::load` logging path was located by xref'ing the log strings with
`./xref` and disassembled into `database_load_disasm.txt` (window starting at
VA `0x1804d7f00`):

* `"Loading database: "` @ RVA `0x437886a` is loaded at VA `0x1804d8033`
  (`lea 0x3ea0830(%rip),%rdx`).
* `"Loaded database: "` @ RVA `0x4378898` at VA `0x1804d82ec`.
* `"load_database"` @ RVA `0x437885c` at VA `0x1804d801e`.
* The function is prologue'd at VA `0x1804d7ef0`
  (`mov %r9b,0x4971d6b(%rip)` … `cmpb $0,0x100(%rsp)`), and it opens the
  database file (`mov $0x666f6c64,%edx` = the 4-char code `"fold"`/`"dlof"`
  used by `file_llist.cpp`), wraps the stream, then iterates tables
  (`mov 0xae30(%rsi)`, `0xacd8/0xace0` vector of table pointers) and calls the
  per-table virtual `*0x88(%rax)`.
* Other located DB entry points:
  `"Could not load the database"` RVA `0x449817c`,
  `"Failed to load database"` RVA `0x4382745`,
  `"database_folder"` RVA `0x448cc80`,
  `"Loading database:"` chain also references RVA `0x437887d` and
  `0x43788aa`.

The persistence/copy routine that maps **property name → value** starts at
VA `0x182cec1e0` (file `0x2cec1e0`). It walks a vector of 16-byte descriptors
at `[r14+0x50]` (element stride 16; discriminator at element `+0xb`, threshold
at `+0xc`), and for each selected descriptor reads the object field and calls
`0x1835c4ea0(obj, property_name, value, ctx)` then a virtual store
`*0x10(%rax)`. Disassembly: `persistence_copy_disasm.txt` (window from
VA `0x182cecb00`). This confirms the serialization is name/id-keyed rather
than a raw positional struct dump, and that the on-disk field ordering is
driven by the compiled descriptor tables + the `.dbc` schema, not by a
hardcoded struct memcpy.

## 5. What is proven vs. still open

Proven (with artifacts/commands above):

* exact `.dat` header layouts for all files (`header_probe.py`);
* zstd payload and the SI seekable-zstd reader classes;
* record class hierarchy with vtable and base-subobject offsets (`rtti2.py`);
* that the DB uses named properties and the descriptor/accessor machinery;
* the editor's field-code dictionary (2103 codes) as the field-definition
  reference;
* the native load function and the property-copy routine addresses.

Still open (handoff / next steps) — I deliberately did **not** cross into
Agent B's raw-record cracking task:

1. Exact per-field byte encoding/order inside `people_db.raw`. The native
   reader is schema-driven; the schema lives in the encrypted
   `db/2620/dbc/*.dbc` (or is regenerated at runtime from
   `CLASS_INFO_TEMPLATE<T>`). A promising next step is to dump the live
   descriptor vector at `[r14+0x50]` (16-byte entries) in an external debugger,
   or to decrypt the `.dbc` files.
2. The 6 header bytes `a0 0f 90 0e 07 00` were not fully decoded (candidate
   meaning: table format/size hints, `0x0FA0`, `0x0E90`, `7`). They are
   constant across all four `"tad."` table families, so they can be skipped
   safely when decompressing.
3. `summary.dat`'s uncompressed TLV body was only inspected, not decoded.

## 6. Reproduction

```bash
cd work/agentA_re
python3 rtti2.py > rtti2_out.txt
python3 header_probe.py
python3 extract_field_dict.py
python3 extract_props.py
python3 extract_person_fieldmap.py
gcc -O2 -o xref xref.c && ./xref "$DLL" 0x437886a 0x4378898 0x437885c 0x449817c
```
