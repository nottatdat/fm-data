#!/usr/bin/env python3
"""E11: build player club ref -> club name from an FM24 save main block.

Club record:  [u32 club index][u32 uid][u32 uid] 00 [u32 nat] ffffffff [u32 nat][u32 nat]
              [u32 ?][4 bytes] ff ff [u32 len][full name][u32 len][short name]
Team record:  ... [u32 club index] (uid-18) ... [u32 team no][u32 uid][u32 uid] 0a 00 ...
Player:       club ref (uid-22) = team no + 1.
Usage: e11_clubs.py <main_block.bin>
"""
import struct
import sys

import numpy as np


def clubs(b):
    out = {}
    for al in range(4):
        A = np.frombuffer(b[al:al + (len(b) - al) // 4 * 4], dtype='<u4')
        # [ci][uid][uid] followed by 00 then nat,ffffffff,nat,nat (unaligned: check in python)
        idx = np.nonzero((A[1:-2] == A[2:-1]) & (A[1:-2] > 0) & (A[:-3] < 200000))[0]
        for i in idx:
            p = al + 4 * int(i)                      # club index position
            if b[p + 12] != 0:
                continue
            nat, ff, n2, n3 = struct.unpack_from('<IIII', b, p + 13)
            if ff != 0xFFFFFFFF or not (nat == n2 == n3) or nat > 2000:
                continue
            q = p + 13 + 16 + 8
            if b[q:q + 2] != b'\xff\xff':
                continue
            ln = struct.unpack_from('<I', b, q + 2)[0]
            if not 1 <= ln <= 100:
                continue
            try:
                name = b[q + 6:q + 6 + ln].decode()
            except UnicodeDecodeError:
                continue
            ci, uid = struct.unpack_from('<II', b, p)
            out.setdefault(ci, (name, uid, nat))
    return out


def teams(b, club_by_index):
    out = {}
    for al in range(4):
        A = np.frombuffer(b[al:al + (len(b) - al) // 4 * 4], dtype='<u4')
        idx = np.nonzero((A[1:-2] == A[2:-1]) & (A[1:-2] > 0) & (A[:-3] < 200000) & ((A[3:] & 0xFFFF) == 0x000A))[0]
        for i in idx:
            p = al + 4 * (int(i) + 1)                # first uid
            t = struct.unpack_from('<I', b, p - 4)[0]
            ci = struct.unpack_from('<I', b, p - 18)[0]
            uid = struct.unpack_from('<I', b, p)[0]
            c = club_by_index.get(ci)
            if c and c[1] == uid:                    # senior team: team uid == club uid
                out.setdefault(t + 1, c[0])
            elif c:
                out.setdefault(t + 1, c[0])
    return out


if __name__ == "__main__":
    data = open(sys.argv[1], 'rb').read()
    C = clubs(data)
    T = teams(data, C)
    print('clubs', len(C), 'team refs', len(T))
    for lab, ref in [('Man City', 557), ('Arsenal', 481), ('Sunderland', 600), ('PSG', 725), ('Rennes', 738),
                     ('Real Madrid', 1396), ('Valencia', 1420)]:
        print(f"{lab:12s} {ref} -> {T.get(ref)}")
