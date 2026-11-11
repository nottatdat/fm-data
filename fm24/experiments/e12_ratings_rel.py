#!/usr/bin/env python3
"""E12-E14: search height/weight/wage/expiry/value at a fixed offset from each ground-truth
player's ratings record (where CA/PA/positions/attributes are). Usage: e12_ratings_rel.py <save.fm>"""
import bisect
import collections
import datetime
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from fm24.save import parse_save as P  # noqa: E402
from fm24.experiments.e12_details import NAMES  # noqa: E402


def ratings_of(save):
    """name -> (ratings record offset, header offset) using the parser's own linking."""
    with open(save, "rb") as fh:
        summary, b = P.read_frames(fh.read())[2:4]
    today, _ = P.game_date(summary)
    people = P.persons(b, P.name_dictionaries(b), today.year - P.YOUNGEST_AGE)
    teams = P.teams(b, P.clubs(b))
    headers = P.player_headers(b, teams)
    want, out, prev = set(NAMES.values()), {}, 0
    for k, p in enumerate(people):
        nxt = people[k + 1]["pos"] if k + 1 < len(people) else len(b)
        i = bisect.bisect_left(headers, p["end"])
        own = headers[i] if i < len(headers) and headers[i] < nxt else None
        if own is None:
            continue
        if p["name"] in want:
            ref = P.decode_header(b, own)["club_ref"]
            r = P.find_ratings(b, max(prev, p["pos"] - P.RATINGS_SEARCH), p["pos"], ref)
            out[p["name"]] = (r, own, p)
        prev = own
    return b, out


def main():
    b, recs = ratings_of(sys.argv[1])
    truth = json.load(open(os.path.join(ROOT, "fm24", "work", "screens.json")))
    hits = collections.defaultdict(set)
    for key, name in NAMES.items():
        t = truth[key]["details"]
        r, own, p = recs[name]
        exp = datetime.date.fromisoformat(t["expires"])
        exp_key = (exp.timetuple().tm_yday, exp.year)
        for anchor, base in (("ratings", r), ("header", own), ("person", p["pos"])):
            for d in range(-3000, 3000):
                q = base + d
                if b[q] == t["height"]:
                    hits[(anchor, "height u8", d)].add(key)
                if struct.unpack_from("<H", b, q)[0] == t["height"]:
                    hits[(anchor, "height u16", d)].add(key)
                if b[q] == t["weight"]:
                    hits[(anchor, "weight u8", d)].add(key)
                raw, yr = struct.unpack_from("<HH", b, q)
                if (raw & P.DOY_MASK, yr) == exp_key:
                    hits[(anchor, "expires", d)].add(key)
    for field in ("height u8", "height u16", "weight u8", "expires"):
        best = sorted(((len(v), a, d) for (a, f, d), v in hits.items() if f == field), reverse=True)[:4]
        print(field, best)


if __name__ == "__main__":
    main()
