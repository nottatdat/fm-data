#!/usr/bin/env python3
"""E12-E14: find height/weight/wage/expiry/value of the 8 ground-truth players at a
consistent offset from an occurrence of their FM uid. Usage: e12_details.py <save.fm>"""
import collections
import datetime
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from fm24.save import parse_save as P  # noqa: E402

NAMES = {'Doue_D': 'Désiré Doué', 'Omari': 'Warmed Omari', 'Kalimuendo': 'Arnaud Kalimuendo',
         'Winger06': 'Mathis Lambourde', 'Doue_G': 'Guela Doué', 'Mandanda': 'Steve Mandanda',
         'Gallon': 'Gauthier Gallon', 'Mamardashvili': 'Giorgi Mamardashvili'}


def load(save):
    with open(save, "rb") as fh:
        summary, b = P.read_frames(fh.read())[2:4]
    rows, _ = P.extract(save)
    return b, {r["name"]: r for r in rows}


def occurrences(b, v):
    pat, i, out = struct.pack("<I", v), 0, []
    while True:
        i = b.find(pat, i)
        if i < 0:
            return out
        out.append(i)
        i += 1


def main():
    save = sys.argv[1]
    b, rows = load(save)
    truth = json.load(open(os.path.join(ROOT, "fm24", "work", "screens.json")))
    hits = collections.defaultdict(set)              # (field, occurrence rank, offset) -> players
    for key, name in NAMES.items():
        t, uid = truth[key]["details"], int(rows[name]["id"])
        exp = datetime.date.fromisoformat(t["expires"])
        exp_key = (exp.timetuple().tm_yday, exp.year)
        for rank, o in enumerate(occurrences(b, uid)):
            for d in range(-600, 600):
                q = o + d
                if q < 0 or q + 8 > len(b):
                    continue
                if b[q] == t["height"]:
                    hits[("height", d)].add(key)
                if b[q] == t["weight"]:
                    hits[("weight", d)].add(key)
                raw, yr = struct.unpack_from("<HH", b, q)
                if (raw & P.DOY_MASK, yr) == exp_key:
                    hits[("expires", d)].add(key)
                v = struct.unpack_from("<I", b, q)[0]
                for unit in (1, 52, 4, 12):
                    for fx in (1.0, 1.15, 1.17, 1.18, 1.2):        # GBP, EUR-ish rates
                        if v and abs(v - t["wage"] * fx * unit / (4 if unit == 12 else 1)) <= 0.02 * v:
                            hits[(f"wage x{unit} fx{fx}", d)].add(key)
                lo, hi = t["value_range"]
                if lo * 0.9 <= v <= hi * 1.4 and v > 10000:
                    hits[("value", d)].add(key)
    best = collections.defaultdict(list)
    for (field, d), ks in hits.items():
        best[field.split(" ")[0]].append((len(ks), d, field))
    for field, lst in best.items():
        lst.sort(reverse=True)
        print(field, lst[:5])


if __name__ == "__main__":
    main()
