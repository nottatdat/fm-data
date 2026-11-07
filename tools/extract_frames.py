#!/usr/bin/env python3
"""Scan a (possibly multi-frame) zstd container and dump each frame.

FM's .dat/.fmf files concatenate several zstd frames.  Each frame is
self-contained, so we can recover every logical block without fully
understanding the outer container header.
"""
import os
import sys
import zstandard as zstd

ZMAGIC = b"\x28\xb5\x2f\xfd"


def extract(path, outdir, max_bytes=None):
    data = open(path, "rb").read()
    if max_bytes:
        data = data[:max_bytes]
    os.makedirs(outdir, exist_ok=True)
    base = os.path.basename(path)
    pos = 0
    idx = 0
    results = []
    while True:
        off = data.find(ZMAGIC, pos)
        if off < 0:
            break
        obj = zstd.ZstdDecompressor().decompressobj()
        try:
            out = obj.decompress(data[off:])
        except zstd.ZstdError as exc:
            pos = off + 4
            continue
        consumed = (len(data) - off) - len(obj.unused_data)
        fn = os.path.join(outdir, f"{base}.{idx:03d}.bin")
        with open(fn, "wb") as fh:
            fh.write(out)
        results.append((idx, off, consumed, len(out), fn))
        pos = off + consumed if consumed > 0 else off + 4
        idx += 1
    return results


def main():
    src = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "work/frames"
    rows = extract(src, outdir)
    for idx, off, consumed, size, fn in rows:
        print(f"frame {idx}: off=0x{off:x} comp={consumed} decomp={size} -> {fn}")
    print(f"total frames: {len(rows)}")


if __name__ == "__main__":
    main()
