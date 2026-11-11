#!/usr/bin/env python3
"""E3 helper: compare fm24_players.csv with the screenshot ground truth.

Usage: check_csv.py <fm24_players.csv> <fm24/work/screens.json>  (ground truth stays local)"""
import csv
import json
import sys

rows = list(csv.DictReader(open(sys.argv[1])))
screens = json.load(open(sys.argv[2]))
names = {'Mandanda': 'Steve Mandanda', 'Doue_D': 'Désiré Doué', 'Omari': 'Warmed Omari',
         'Kalimuendo': 'Arnaud Kalimuendo', 'Winger06': 'Mathis Lambourde', 'Gallon': 'Gauthier Gallon',
         'Doue_G': 'Guela Doué', 'Mamardashvili': 'Giorgi Mamardashvili'}
by = {}
for r in rows:
    by.setdefault(r['name'], r)
tot = ok = 0
for key, nm in names.items():
    r = by.get(nm)
    sc = screens.get(key, {}).get('screen', {})
    if not r:
        print(nm, 'MISSING')
        continue
    good = sum(1 for a, v in sc.items() if r.get(a) not in (None, '') and int(r[a]) == v)
    near = sum(1 for a, v in sc.items() if r.get(a) not in (None, '') and abs(int(r[a]) - v) <= 1)
    tot += len(sc)
    ok += good
    print(f"{nm:21s} {r['id']:>11s} {r['dob']} age {r['age']:>2s} {r['nat']:8s} {r['club'][:18]:18s} "
          f"CA {r['ca']:>3s} PA {r['pa']:>3s} {r['posNat']:9s} {r['foot']:5s} exact {good}/{len(sc)} ±1 {near}/{len(sc)}")
print(f"attributes exact {ok}/{tot}")
ids = [r['id'] for r in rows]
print('rows', len(rows), 'duplicate ids', len(ids) - len(set(ids)),
      'with club', sum(1 for r in rows if r['club']), 'with nat', sum(1 for r in rows if r['nat']),
      'with attributes', sum(1 for r in rows if r['Finishing']))
