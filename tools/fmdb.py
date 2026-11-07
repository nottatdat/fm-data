#!/usr/bin/env python3
"""Football Manager 26 database (.dat) extraction helpers.

The FM .dat files are zstd frames located at a fixed offset (12) behind a
small proprietary header.  This module locates and decompresses them.
"""
import os
import sys
import zstandard as zstd

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"


def read_raw(path):
    with open(path, "rb") as fh:
        return fh.read()


def find_frame(data):
    """Return offset of the first zstd frame (magic) in data."""
    off = data.find(ZSTD_MAGIC)
    if off < 0:
        raise ValueError("no zstd frame found")
    return off


def decompress(path):
    data = read_raw(path)
    off = find_frame(data)
    dctx = zstd.ZstdDecompressor()
    # Some files contain extra trailing frames; stream all of it.
    return dctx.stream_reader(data[off:]).read()


def main():
    if len(sys.argv) < 2:
        print("usage: fmdb.py <file.dat> [out.raw]")
        raise SystemExit(2)
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    blob = decompress(src)
    if out:
        with open(out, "wb") as fh:
            fh.write(blob)
        print(f"{src} -> {out} ({len(blob)} bytes)")
    else:
        print(f"{src}: {len(blob)} bytes")


if __name__ == "__main__":
    main()
