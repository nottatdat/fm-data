#!/usr/bin/env python3
"""E13: contract = [expiry date][start date] ... [u32 club ref][u32 0][u32 weekly wage £],
located through the player's own club ref (explicit link). Usage: e13_contract.py <save.fm>"""
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from fm24.save import parse_save as P  # noqa: E402
from fm24.experiments.e12_details import NAMES  # noqa: E402
from fm24.experiments.e12_ratings_rel import ratings_of  # noqa: E402

DATES_BEFORE = 200


def contract(b, lo, hi, club_ref):
    key = struct.pack("<II", club_ref, 0)
    i = hi
    while True:
        i = b.rfind(key, lo, i)
        if i < 0:
            return None
        for q in range(i - 8, max(lo, i - DATES_BEFORE), -1):        # nearest date pair before
            (r1, y1), (r2, y2) = struct.unpack_from("<HH", b, q), struct.unpack_from("<HH", b, q + 4)
            d1, d2 = P.to_date(r1, y1), P.to_date(r2, y2)
            if d1 and d2 and 1990 < y2 <= y1 < 2100 and d2 < d1:
                return {"expires": d1, "start": d2, "wage": struct.unpack_from("<I", b, i + 8)[0], "at": i}
        if i == lo:
            return None


def main():
    b, recs = ratings_of(sys.argv[1])
    truth = json.load(open(os.path.join(ROOT, "fm24", "work", "screens.json")))
    ok = 0
    for key, name in NAMES.items():
        r, own, p = recs[name]
        t = truth[key]["details"]
        c = contract(b, p["pos"] - 3000, p["pos"], P.decode_header(b, own)["club_ref"])
        good = c and str(c["expires"]) == t["expires"] and abs(c["wage"] / t["wage"] - 1) < 0.03
        ok += bool(good)
        print(f"{'OK ' if good else 'BAD'} {name:20s} {c and (str(c['expires']), c['wage'], c['at'] - p['pos'])} want {t['expires']} {t['wage']}")
    print(f"{ok}/{len(NAMES)}")


if __name__ == "__main__":
    main()
