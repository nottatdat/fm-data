#!/usr/bin/env python3
"""E6: log every change (create/delete/size/mtime) in the FM24 saves folder.

Usage: e6_watch.py <log_path> [seconds]   (polls every 0.1 s)
"""
import os
import sys
import time

GAMES = os.path.expanduser("~/Library/Application Support/Sports Interactive/Football Manager 2024/games")


def snap():
    out = {}
    for e in os.scandir(GAMES):
        try:
            st = e.stat()
            out[e.name] = (st.st_size, st.st_mtime)
        except FileNotFoundError:
            pass
    return out


def main():
    log = open(sys.argv[1], "a", buffering=1)
    end = time.time() + float(sys.argv[2] if len(sys.argv) > 2 else 900)
    prev = snap()
    log.write(f"{time.strftime('%H:%M:%S')} start, {len(prev)} entries\n")
    while time.time() < end:
        time.sleep(0.1)
        cur = snap()
        t = time.strftime('%H:%M:%S') + f".{int(time.time() * 10) % 10}"
        for n in cur.keys() - prev.keys():
            log.write(f"{t} CREATE {n} size={cur[n][0]}\n")
        for n in prev.keys() - cur.keys():
            log.write(f"{t} DELETE {n}\n")
        for n in cur.keys() & prev.keys():
            if cur[n] != prev[n]:
                log.write(f"{t} CHANGE {n} size={cur[n][0]} mtime={time.strftime('%H:%M:%S', time.localtime(cur[n][1]))}\n")
        prev = cur
    log.write(f"{time.strftime('%H:%M:%S')} end\n")


if __name__ == "__main__":
    main()
