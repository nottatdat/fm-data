#!/usr/bin/env python3
"""Agent C: parse FM26 summary.dat (uncompressed) and basic_people_db.raw.

Outputs (in work/agentC_summary):
  players_summary.csv              - one row per person found in summary.dat,
                                     joined with basic_people numeric fields and
                                     cross-checked against FM26_Example_data.csv.
  basic_people_db_parsed.csv       - every detected basic_people_db record.
  example_players_crosscheck.csv   - every example-CSV player, annotated with
                                     summary + basic_people data.

Evidence for the formats (see REPORT.md):
  summary.dat  : sequence of records
                   u8 tag=0x02 | u32 person_id | u32 len1 | utf8 first
                   | u32 len2 | utf8 second | 16-byte tail
                 tail = u32 a, u32 b, u32 pos_flags, u16 ca_like, u16 e
  basic_people : fixed 84-byte records with the person id stored twice at
                 record offsets 16 and 20.  Payload starts at record offset 24.
"""
import csv
import os
import re
import struct
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)
SUM = os.environ.get("SUMMARY_RAW", os.path.join(WORK, "summary.raw"))
BAS = os.environ.get("BASIC_RAW", os.path.join(WORK, "basic_people_db.raw"))
EX = os.environ.get("EXAMPLE_CSV", os.path.join(WORK, "FMdataExport", "DataAnalyser", "FM26_Example_data.csv"))
OUT = HERE

# ---------------------------------------------------------------------------
# summary.dat
# ---------------------------------------------------------------------------
_ALLOWED_PUNCT = set("'\u2019\u2032.-[](),")


def name_like(b: bytes) -> bool:
    """True if b looks like a UTF-8 personal name.

    Permissive enough for Vietnamese/Azerbaijani/Romanian names (which use
    letters such as \u0259, \u0219, \u021b and combining marks) while still
    rejecting binary payloads.
    """
    if len(b) == 0:
        return True
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        return False
    if not s:
        return False
    has_alpha = False
    for c in s:
        cat = unicodedata.category(c)
        if cat[0] == "C":          # control / format / private-use
            return False
        if c.isspace() or c.isalpha() or c.isdigit():
            has_alpha = has_alpha or c.isalpha()
            continue
        if cat[0] == "M":          # combining mark
            continue
        if c in _ALLOWED_PUNCT:
            continue
        return False
    return has_alpha


def parse_summary(path=SUM):
    """Yield (offset, person_id, first, second, tail16)."""
    d = open(path, "rb").read()
    n = len(d)
    i = 0
    while i < n - 9:
        if d[i] == 0x02:
            pid = struct.unpack_from("<I", d, i + 1)[0]
            if 1 <= pid < 2_200_000_000:
                l1 = struct.unpack_from("<I", d, i + 5)[0]
                if l1 <= 64:
                    s1 = d[i + 9:i + 9 + l1]
                    if name_like(s1):
                        p2 = i + 9 + l1
                        if p2 + 4 <= n:
                            l2 = struct.unpack_from("<I", d, p2)[0]
                            if l2 <= 64:
                                s2 = d[p2 + 4:p2 + 4 + l2]
                                if name_like(s2) and (l1 or l2):
                                    end = p2 + 4 + l2
                                    if end + 16 <= n:
                                        yield (i, pid,
                                               s1.decode("utf-8", "replace"),
                                               s2.decode("utf-8", "replace"),
                                               d[end:end + 16])
                                        i = end + 16
                                        continue
        i += 1


# position bitmask -> label.  Derived empirically by matching single-bit flags
# against the Position column of FM26_Example_data.csv (see REPORT.md).
POS_BITS = [
    (0x0001, "GB"),
    (0x0004, "D/AL (D)"),
    (0x0008, "D/AL (G)"),
    (0x0010, "D (C)"),
    (0x0020, "D/M (?)"),
    (0x0040, "AL (?)"),
    (0x0080, "MD"),
    (0x0100, "M (D)"),
    (0x0200, "M (G)"),
    (0x0400, "M (C)"),
    (0x0800, "MO (D)"),
    (0x1000, "MO (G)"),
    (0x2000, "MO (C)"),
    (0x4000, "BT (C)"),
    (0x8000, "?"),
]


def decode_positions(flags: int) -> str:
    if flags == 0:
        return ""
    out = []
    known = 0
    for bit, label in POS_BITS:
        known |= bit
        if flags & bit:
            out.append(label)
    if flags & ~known:
        out.append("0x%x" % (flags & ~known))
    return "/".join(out)


# ---------------------------------------------------------------------------
# basic_people_db.raw
# ---------------------------------------------------------------------------
def parse_basic(path=BAS):
    """Fixed 84-byte records: id duplicated at offsets 16 and 20."""
    d = open(path, "rb").read()
    n = len(d)
    i = 0
    while i < n - 10:
        if d[i + 8] == 0x11:
            if d[i:i + 4] == d[i + 4:i + 8]:
                pid = struct.unpack_from("<I", d, i)[0]
                if (1 <= pid < 2_200_000_000 and i >= 16
                        and i + 68 <= n):
                    yield pid, d[i - 16:i + 68]
        i += 1


BASIC_COLS = (["basic_present", "basic_hdr0", "basic_hdr1", "basic_hdr2",
               "basic_hdr3", "basic_subtype"]
              + ["basic_w%02d" % k for k in range(15)])


def basic_fields(rec):
    if not rec:
        return [0] + [""] * 4 + [""] + [""] * 15
    hdr = struct.unpack_from("<4I", rec, 0)
    words = struct.unpack_from("<15I", rec, 24)
    return [1, *hdr, rec[25], *words]


def load_example():
    rows = {}
    if not os.path.exists(EX):
        return rows
    with open(EX, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            try:
                pid = int(row["Unique ID"])
            except (KeyError, ValueError):
                continue
            rows[pid] = row
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)

    # --- basic table -------------------------------------------------------
    basic = {}
    with open(os.path.join(OUT, "basic_people_db_parsed.csv"), "w", newline="",
              encoding="utf-8") as fh:
        cols = (["person_id", "hdr0", "hdr1", "hdr2", "hdr3", "subtype"]
                + ["w24_%02d" % k for k in range(15)])
        w = csv.writer(fh)
        w.writerow(cols)
        nbasic = 0
        for pid, rec in parse_basic():
            basic.setdefault(pid, rec)
            hdr = struct.unpack_from("<4I", rec, 0)
            words = struct.unpack_from("<15I", rec, 24)
            w.writerow([pid, *hdr, rec[25], *words])
            nbasic += 1
        print("basic records:", nbasic, "unique:", len(basic))

    # --- example -----------------------------------------------------------
    example = load_example()
    print("example rows:", len(example))

    # --- summary -----------------------------------------------------------
    from collections import defaultdict
    per_id = defaultdict(list)
    all_sum = list(parse_summary())
    for _off, pid, first, second, tail in all_sum:
        per_id[pid].append((first, second, tail))
    print("summary records:", len(all_sum), "unique ids:", len(per_id))

    def pick(recs):
        def key(r):
            _a, _b, _flags, ca, e = struct.unpack("<IIIHH", r[2])
            return (ca, e, len(r[0]) + len(r[1]))
        return max(recs, key=key)

    reps = {}
    with open(os.path.join(OUT, "players_summary.csv"), "w", newline="",
              encoding="utf-8") as fh:
        cols = [
            "person_id", "first_name", "second_name", "display_name",
            "n_records", "pos_flags", "positions",
            "summary_ca", "summary_age", "summary_x", "summary_u16_e",
            "summary_u16_e_all",
            "summary_u32_a", "summary_u32_b", "summary_tail_hex",
            "in_example_csv", "example_name", "example_age", "example_club",
            "example_nation", "example_position",
        ] + BASIC_COLS
        w = csv.writer(fh)
        w.writerow(cols)
        for pid, recs in per_id.items():
            first, second, tail = pick(recs)
            reps[pid] = (first, second, tail)
            a, b, flags, ca_like, efield = struct.unpack("<IIIHH", tail)
            e_all = ";".join(str(x) for x in
                             sorted({struct.unpack("<IIIHH", r[2])[4]
                                     for r in recs}))
            row = [
                pid, first, second, (first + " " + second).strip(),
                len(recs), flags, decode_positions(flags),
                ca_like, efield & 0xff, efield >> 8, efield, e_all,
                a, b, tail.hex(),
            ]
            ex = example.get(pid)
            if ex:
                row += [1, ex.get("Joueur", ""), ex.get("Âge", ""),
                        ex.get("Club", ""), ex.get("Résidence", ""),
                        ex.get("Position", "")]
            else:
                row += [0, "", "", "", "", ""]
            row += basic_fields(basic.get(pid))
            w.writerow(row)
        print("players_summary.csv rows:", len(reps))

    # --- cross-check file: every example player ----------------------------
    with open(os.path.join(OUT, "example_players_crosscheck.csv"), "w",
              newline="", encoding="utf-8") as fh:
        cols = ["person_id", "example_name", "example_age", "example_club",
                "example_nation", "example_division", "example_position",
                "example_wage", "in_summary", "first_name", "second_name",
                "summary_ca", "summary_age", "summary_positions"] + BASIC_COLS
        w = csv.writer(fh)
        w.writerow(cols)
        n = 0
        for pid, ex in example.items():
            rec = reps.get(pid)
            if rec:
                first, second, tail = rec
                _a, _b, flags, ca_like, e = struct.unpack("<IIIHH", tail)
                row = [pid, ex.get("Joueur", ""), ex.get("Âge", ""),
                       ex.get("Club", ""), ex.get("Résidence", ""),
                       ex.get("Division", ""), ex.get("Position", ""),
                       ex.get("Salaire", ""), 1, first, second,
                       ca_like, e & 0xff, decode_positions(flags)]
            else:
                row = [pid, ex.get("Joueur", ""), ex.get("Âge", ""),
                       ex.get("Club", ""), ex.get("Résidence", ""),
                       ex.get("Division", ""), ex.get("Position", ""),
                       ex.get("Salaire", ""), 0, "", "", "", "", ""]
            row += basic_fields(basic.get(pid))
            w.writerow(row)
            n += 1
        print("example_players_crosscheck.csv rows:", n)

    # --- stats -------------------------------------------------------------
    ex_ids = set(example)
    print("example ids found in basic  :", len(ex_ids & set(basic)))
    print("example ids found in summary:", len(ex_ids & set(reps)))
    print("summary ids also in example :", len(set(reps) & ex_ids))


if __name__ == "__main__":
    main()
