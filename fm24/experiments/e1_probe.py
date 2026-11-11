#!/usr/bin/env python3
"""E1 research helper: locate FM24 person records by (part of) full name.

Person record layout found so far (see E1-record-decode.md):
  ... u32 person_index @ name-36 ... u32 first_id,00, u32 surname_id,00, u32 common_id,00,
  u32 len, utf-8 full name, u16 dob_day_of_year (1-based), u16 dob_year, ...
Usage: e1_probe.py <main_block.bin> <name substring>...
"""
import re
import struct
import sys


def find_person(d, sub):
    b = sub.encode()
    out = []
    for m in re.finditer(re.escape(b), d):
        i = m.start()
        for st in range(i, max(i - 80, 4), -1):
            ln = struct.unpack_from('<I', d, st - 4)[0]
            if not (len(b) <= ln < 100 and st + ln >= i + len(b)):
                continue
            end = st + ln
            yr = struct.unpack_from('<H', d, end + 2)[0]
            if 1940 < yr < 2025 and d[st - 5] == 0 and d[st - 10] == 0:
                out.append(dict(pos=st, name=d[st:end].decode('utf-8', 'replace'),
                                doy=struct.unpack_from('<H', d, end)[0], year=yr,
                                index=struct.unpack_from("<I", d, st - 36)[0]))
                break
    return out


if __name__ == "__main__":
    data = open(sys.argv[1], 'rb').read()
    for s in sys.argv[2:]:
        for r in find_person(data, s):
            print(s, r)
