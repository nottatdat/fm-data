#!/usr/bin/env python3
"""
parse_people.py -- extract people / player records from FM26 `people_db.raw`.

This parser was reverse engineered from the decompressed master person table
(`work/people_db.raw`).  Everything below is evidence based; see REPORT.md for
the hexdumps and the reasoning.

Discovered record layout (large person section)
-----------------------------------------------
Each person owns a *full name* record.  For the vast majority of people the
bytes immediately before the string are:

    u32  nation_ref            # person's nation reference (records are grouped by it)
    ff ff ff ff                # "no reference / inline" sentinel
    00                         # reserved
    u32  name_len              # UTF-8 byte length of the full name
    ...  full name bytes ...   # UTF-8
    u16  day_of_year           # date of birth, 1..366
    u16  year                  # date of birth, e.g. 1985

Known players used to validate the layout:

    Cristiano Ronaldo dos Santos Aveiro   doy=36  year=1985 -> 1985-02-05
    Erling Braut Haaland                  doy=203 year=2000 -> 2000-07-21
    Jude Victor William Bellingham        doy=180 year=2003 -> 2003-06-29
    Kylian Mbappe Lottin                  doy=354 year=1998 -> 1998-12-20
    Mohamed El Amine Amoura               doy=130 year=2000 -> 2000-05-09
    Riyad Karim Mahrez                    doy=52  year=1991 -> 1991-02-21

A handful of names (e.g. Cristiano Ronaldo) do not carry the `ff ff ff ff`
sentinel; the parser therefore does not require it and still records the
name + DOB, leaving `nation_ref` empty for those.

Output
------
`players_people.csv` with one row per extracted person.  When the optional
FMdataExport example CSV is present it is used purely as a roster of *known*
players to enrich rows with the in-game unique id, club and position through a
name + age match.

Usage
-----
    python3 parse_people.py [people_db.raw] [out.csv]
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import re
import struct
import sys
import unicodedata
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.dirname(HERE)

DEFAULT_RAW = os.path.join(WORK, "people_db.raw")
DEFAULT_OUT = os.path.join(HERE, "players_people.csv")
EXAMPLE_CSV = os.path.join(
    WORK, "FMdataExport", "DataAnalyser", "FM26_Example_data.csv"
)

FF_MARKER = b"\xff\xff\xff\xff\x00"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _valid_name(raw: bytes) -> str | None:
    """Return decoded text if `raw` looks like a person name, else None."""
    if not (2 <= len(raw) <= 70):
        return None
    if any(b < 0x20 for b in raw):
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # reject rich-text / markup and other junk
    if any(ch in text for ch in "<>{}[]|\\"):
        return None
    letters = sum(ch.isalpha() or ch in " .'-" for ch in text)
    if letters < len(text) * 0.7:
        return None
    if not text[0].isalpha():
        return None
    return text


def dob_from_doy(doy: int, year: int) -> dt.date | None:
    """FM stores dates as (day-of-year, year).  Convert to a real date."""
    if not (1 <= doy <= 366) or not (1900 <= year <= 2025):
        return None
    try:
        result = dt.date(year, 1, 1) + dt.timedelta(days=doy - 1)
    except ValueError:
        return None
    if result.year != year:
        # day-of-year overflowed a non-leap year -> corrupt / not a real date
        return None
    return result


# --------------------------------------------------------------------------- #
# core scan
# --------------------------------------------------------------------------- #
def scan_people(data: bytes) -> list[dict]:
    """Scan raw bytes for name+DOB records.

    A record is a little-endian u32 length (2..70) followed by that many UTF-8
    bytes forming a plausible person name, followed by the (doy, year) date of
    birth.  We additionally capture the `nation_ref` when the standard
    `ff ff ff ff 00` sentinel precedes the string.
    """
    people: list[dict] = []
    n = len(data)
    p = 0
    find3 = data.find
    while True:
        j = find3(b"\x00\x00\x00", p)
        if j < 0 or j < 1:
            break
        p = j + 1
        length = data[j - 1]
        if not (2 <= length <= 70):
            continue
        start = j + 3                      # name bytes
        end = start + length
        if end + 4 > n:
            continue
        text = _valid_name(data[start:end])
        if text is None:
            continue
        doy, year = struct.unpack_from("<HH", data, end)
        # 1/1/1900 is FM's "null date"; such a hit is not a real DOB.
        if year == 1900 and doy == 1:
            continue
        dob = dob_from_doy(doy, year)
        if dob is None:
            continue

        nation_ref = None
        has_marker = False
        # name_len field starts at j-1; marker occupies name_start-9 .. name_start-4
        if start >= 13 and data[start - 9 : start - 4] == FF_MARKER:
            has_marker = True
            nation_ref = struct.unpack_from("<I", data, start - 13)[0]

        people.append(
            {
                "name_off": start,
                "full_name": text,
                "date_of_birth": dob.isoformat(),
                "dob_year": year,
                "dob_day_of_year": doy,
                "nation_ref": nation_ref,
                "has_ff_marker": has_marker,
            }
        )
    # de-duplicate identical (offset) hits, keep first
    seen = set()
    uniq = []
    for rec in people:
        key = rec["name_off"]
        if key in seen:
            continue
        seen.add(key)
        uniq.append(rec)
    uniq.sort(key=lambda r: r["name_off"])
    return uniq


# --------------------------------------------------------------------------- #
# optional enrichment with the known-player roster
# --------------------------------------------------------------------------- #
def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^A-Za-z0-9']+", _norm(text)) if len(t) >= 3]


def load_known_players(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    players = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rdr = csv.reader(fh)
        header = next(rdr, None)
        if not header:
            return []
        # locate columns by name (French example file)
        idx = {name: i for i, name in enumerate(header)}
        c_name = idx.get("Joueur", 1)
        c_id = idx.get("Unique ID", 2)
        c_age = idx.get("Âge", 3)
        c_club = idx.get("Club", 4)
        c_pos = idx.get("Position", 7)
        for row in rdr:
            if len(row) <= max(c_name, c_id, c_age, c_club, c_pos):
                continue
            try:
                uid = int(row[c_id])
                age = int(row[c_age])
            except (ValueError, IndexError):
                continue
            players.append(
                {
                    "unique_id": uid,
                    "common_name": row[c_name],
                    "age": age,
                    "club": row[c_club],
                    "position": row[c_pos],
                    "tokens": set(_tokens(row[c_name])),
                }
            )
    return players


def enricher(people: list[dict], known: list[dict]):
    """Yield (person, match) where match is a known player or None.

    Matching rule: every >=3 char token of the known player's common name must
    appear in the full name AND a person may only be claimed once.  When a
    token set matches several people, the one whose age (as of the roster) is
    closest wins.
    """
    # index people by token
    token_index: dict[str, list[int]] = defaultdict(list)
    for i, per in enumerate(people):
        for tok in set(_tokens(per["full_name"])):
            token_index[tok].append(i)

    claimed: dict[int, dict] = {}
    # Try to match the most distinctive known players first (rarest token).
    known_sorted = sorted(
        known, key=lambda k: min((len(token_index.get(t, ())) or 1) for t in k["tokens"]) if k["tokens"] else 1
    )
    for kp in known_sorted:
        toks = kp["tokens"]
        if not toks:
            continue
        postings = [token_index.get(t, []) for t in toks]
        if any(not pl for pl in postings):
            continue
        base = min(postings, key=len)
        best_i = None
        best_delta = None
        for i in base:
            full = _norm(people[i]["full_name"])
            if not all(t in full for t in toks):
                continue
            if i in claimed:
                continue
            per_year = people[i]["dob_year"]
            delta = abs((2026 - per_year) - kp["age"])
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best_i = i
        if best_i is not None and (best_delta is None or best_delta <= 3):
            claimed[best_i] = kp

    for i, per in enumerate(people):
        yield per, claimed.get(i)


# --------------------------------------------------------------------------- #
def main() -> int:
    raw_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RAW
    out_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT
    if not os.path.exists(raw_path):
        print(f"error: {raw_path} not found", file=sys.stderr)
        return 1

    print(f"reading {raw_path} ...")
    with open(raw_path, "rb") as fh:
        data = fh.read()
    print(f"  {len(data):,} bytes")

    people = scan_people(data)
    print(f"  extracted {len(people):,} person name+DOB records")

    known = load_known_players(EXAMPLE_CSV)
    print(f"  loaded {len(known):,} known players for enrichment")

    cols = [
        "unique_id",
        "common_name",
        "full_name",
        "date_of_birth",
        "age",
        "club",
        "position",
        "nation_ref",
        "dob_year",
        "dob_day_of_year",
        "record_offset",
    ]
    matched = 0
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for per, kp in enricher(people, known):
            nation = per["nation_ref"]
            row = [
                kp["unique_id"] if kp else "",
                kp["common_name"] if kp else "",
                per["full_name"],
                per["date_of_birth"],
                kp["age"] if kp else "",
                kp["club"] if kp else "",
                kp["position"] if kp else "",
                "" if nation is None else nation,
                per["dob_year"],
                per["dob_day_of_year"],
                per["name_off"],
            ]
            if kp:
                matched += 1
            w.writerow(row)

    print(f"  -> {out_path} ({len(people):,} rows, {matched:,} enriched with a known unique id)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
