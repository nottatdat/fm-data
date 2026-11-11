#!/usr/bin/env python3
"""E1: locate own players by DOB (+ nation, club ref) and solve the attribute order
from on-screen ground truth. Usage: e1_solve.py <main_block.bin>"""
import collections
import datetime
import struct
import sys

b = open(sys.argv[1], 'rb').read()
FRANCE, RENNES = 143, 738

T = ['Corners', 'Crossing', 'Dribbling', 'Finishing', 'FirstTouch', 'FreeKicks', 'Heading', 'LongShots',
     'LongThrows', 'Marking', 'Passing', 'PenaltyTaking', 'Tackling', 'Technique']
M = ['Aggression', 'Anticipation', 'Bravery', 'Composure', 'Concentration', 'Decisions', 'Determination',
     'Flair', 'Leadership', 'OffTheBall', 'Positioning', 'Teamwork', 'Vision', 'WorkRate']
P = ['Acceleration', 'Agility', 'Balance', 'JumpingReach', 'NaturalFitness', 'Pace', 'Stamina', 'Strength']
GK = ['AerialReach', 'CommandOfArea', 'Communication', 'Eccentricity', 'FirstTouch', 'Handling', 'Kicking',
      'OneOnOnes', 'Passing', 'Punching', 'Reflexes', 'RushingOut', 'Throwing']
GKM = M
GKP = P
GKT = ['FreeKicks', 'PenaltyTaking', 'Technique']


def outfield(t, m, p):
    return {**dict(zip(T, t)), **dict(zip(M, m)), **dict(zip(P, p))}


# Screenshot ground truth (user's own players) is game data: kept locally, never committed.
import json as _json
import os as _os
_SCREENS = _os.path.join(_os.path.dirname(_os.path.abspath(globals().get("__file__", "fm24/experiments/e1_solve.py"))), "..", "work", "screens.json")
PLAYERS = {k: (tuple(v["dob"]), v["screen"]) for k, v in _json.load(open(_SCREENS)).items()}


def persons_by_dob(y, mo, d):
    doy = (datetime.date(y, mo, d) - datetime.date(y, 1, 1)).days + 1
    out = []
    i = 0
    while True:
        i = b.find(struct.pack('<H', y), i)
        if i < 0:
            return out
        if (struct.unpack_from('<H', b, i - 2)[0] & 0x1ff) == doy and struct.unpack_from('<I', b, i + 7)[0] == FRANCE:
            # name end = i-2; walk back to a u32 length that fits
            for ln in range(0, 100):
                if struct.unpack_from('<I', b, i - 2 - ln - 4)[0] == ln and b[i - 2 - ln - 5] == 0:
                    out.append(i - 2 - ln)
                    break
        i += 1


def uid_after(st):
    for o in range(40, 4000):
        a = struct.unpack_from('<I', b, st + o)[0]
        if a > 1000 and a == struct.unpack_from('<I', b, st + o + 4)[0] \
                and struct.unpack_from('<I', b, st + o - 22)[0] == RENNES:
            return st + o


def rnd(v):
    return int(v / 5 + 0.5)


def locate_history(st, screen):
    """Latest record of the attribute-history chain before the person record:
    71-byte records, byte 47 of each == 6, at least two chained. Returns (multiset overlap, start)."""
    S = collections.Counter(screen.values())
    chain_ends = [s for s in range(st - 8000, st - 47)
                  if b[s + 47] == 6 and b[s + 47 - 71] == 6 and all(1 <= x <= 100 for x in b[s:s + 47])]
    if not chain_ends:
        return 0, None
    s = chain_ends[-1]
    c = collections.Counter(rnd(x) for x in b[s:s + 47])
    return sum((c & S).values()), s


found = {}
for name, (dob, screen) in PLAYERS.items():
    for st in persons_by_dob(*dob):
        u = uid_after(st)
        if u:
            ov, s = locate_history(st, screen)
            found[name] = (st, u, s, screen)
            print(f"{name:10s} person@{st} uid={struct.unpack_from('<I', b, u)[0]} hist@{s - st:+d} "
                  f"multiset {ov}/{len(screen)} height@uid+112={b[u + 112]}")
            break
    else:
        print(name, 'NOT FOUND')

attrs = sorted({a for _, _, _, sc in found.values() for a in sc})
cands = {}
for a in attrs:
    cands[a] = [p for p in range(47) if all(rnd(b[s + p]) == sc[a] for _, _, s, sc in found.values() if a in sc)]
for a in sorted(attrs, key=lambda a: (cands[a][0] if cands[a] else 99)):
    print(f"{a:15s} {cands[a]}")
