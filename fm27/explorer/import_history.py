#!/usr/bin/env python3
"""Build the FM27 player-history database for the profiles explorer.

Reads the shipped FM27 history files:
  2700_fm/pl_hist_index.dat  -> count + (person_id, block_index)
  2700_fm/pl_hist_id.dat     -> (start, start_of_last_record) offsets per block
  2700_fm/pl_hist_dt.dat     -> blocks of 44-byte season records

44-byte season record (decoded against known careers):
  0  u16 season_start
  2  u16 season_end
  4  u8  record type (0x40 senior, 0x42 youth)
  5  u8  appearances
  6  u8  goals
  7  u8  extra (unknown)
  8  u8[3] extra
  11 u32 club id
  15 u32 parent club id (differs on loans)
  19 u32 competition id
  23 u32 parent competition id
  27 u16 flags
  29 date (u16 day, u16 year) x3, usually null (1/1900)
  41 u8[3] extra

Club and competition IDs are mapped to names by voting with the current
club/division of the players in fm27/csv_515k/fm27_players.csv.

Outputs data/history.db (~500 MB) with a `history` table.
"""
import csv
import os
import sqlite3
import struct
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
from fmdb import decompress

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CSV = os.path.join(ROOT, "fm27", "csv_515k", "fm27_players.csv")
GAME_DB = os.environ.get("FM27_DB", "/mnt/data/SteamLibrary/steamapps/common/Football Manager 27/shared/data/database/db/2700/2700_fm")
OUT = os.path.join(HERE, "data", "history.db")

REC = 44
NULL_ID = 0xFFFFFFFF


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


def main():
    t0 = time.time()
    print("loading current players (id -> club/division)...", flush=True)
    meta = {}
    with open(CSV, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                pid = int(r["id"])
            except (KeyError, ValueError):
                continue
            try:
                ca = int(float(r.get("ca") or 0))
            except ValueError:
                ca = 0
            meta[pid] = ((r.get("club") or "").strip(), (r.get("div") or "").strip(), ca)
    print(f"  {len(meta):,} players", flush=True)

    print("loading history index/data...", flush=True)
    idx = decompress(os.path.join(GAME_DB, "pl_hist_index.dat"))
    ids = decompress(os.path.join(GAME_DB, "pl_hist_id.dat"))
    dt = decompress(os.path.join(GAME_DB, "pl_hist_dt.dat"))
    count = struct.unpack_from("<I", idx, 0)[0]
    offsets = struct.unpack_from(f"<{count * 2}I", ids, 0)
    print(f"  {count:,} players with history, {len(dt):,} bytes", flush=True)

    def blocks():
        for i in range(count):
            pid, rec = struct.unpack_from("<II", idx, 4 + i * 8)
            start = offsets[2 * rec]
            end = offsets[2 * rec + 1]
            nxt = offsets[2 * (rec + 1)] if rec + 1 < count else len(dt)
            yield pid, start, nxt

    # ---- pass 1: club id -> current club name + player's current club id ----
    print("mapping club IDs...", flush=True)
    club_votes = defaultdict(Counter)
    player_club = {}
    for pid, start, nxt in blocks():
        best = None
        best_senior = None
        for pos in range(start, nxt, REC):
            r = dt[pos:pos + REC]
            if len(r) < REC:
                break
            y2 = struct.unpack_from("<H", r, 2)[0]
            if best is None or y2 > best[0]:
                best = (y2, r)
            if r[4] == 0x40 and r[5] > 0 and (best_senior is None or y2 > best_senior[0]):
                best_senior = (y2, r)
        chosen = best_senior or best
        if chosen:
            r = chosen[1]
            cid = struct.unpack_from("<I", r, 11)[0]
            cp = struct.unpack_from("<I", r, 19)[0]
            if cid not in (0, NULL_ID):
                player_club[pid] = (cid, None if cp in (0, NULL_ID) else cp)
        if pid in meta and best:
            club, _, _ = meta[pid]
            cid = struct.unpack_from("<I", best[1], 11)[0]
            if club and cid not in (0, NULL_ID):
                club_votes[cid][club] += 1
    club_map = {cid: votes.most_common(1)[0][0] for cid, votes in club_votes.items()}
    print(f"  {len(club_map):,} club IDs mapped", flush=True)

    # ---- pass 2: competition id -> division name (latest senior record) ----
    print("mapping competition IDs...", flush=True)
    comp_votes = defaultdict(Counter)
    for pid, start, nxt in blocks():
        if pid not in meta:
            continue
        club, div, ca = meta[pid]
        if not div or ca < 100:
            continue
        maxy = -1
        recs = []
        for pos in range(start, nxt, REC):
            r = dt[pos:pos + REC]
            if len(r) < REC:
                break
            y2 = struct.unpack_from("<H", r, 2)[0]
            maxy = max(maxy, y2)
            recs.append(r)
        for r in recs:
            if struct.unpack_from("<H", r, 2)[0] != maxy:
                continue
            if r[4] != 0x40 or r[5] == 0:
                continue
            cid = struct.unpack_from("<I", r, 11)[0]
            if club_map.get(cid) != club:
                continue
            cp = struct.unpack_from("<I", r, 19)[0]
            if cp not in (0, NULL_ID):
                comp_votes[cp][div] += max(1, r[5]) * max(1, ca)
            break
    comp_map = {cp: votes.most_common(1)[0][0] for cp, votes in comp_votes.items()}
    print(f"  {len(comp_map):,} competition IDs mapped", flush=True)

    # ---- pass 3: write the history DB ----
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = sqlite3.connect(tmp)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("""
        CREATE TABLE history (
            person_id INTEGER NOT NULL,
            season_start INTEGER NOT NULL,
            season_end INTEGER NOT NULL,
            record_type TEXT,
            apps INTEGER,
            goals INTEGER,
            club_id INTEGER,
            club TEXT,
            parent_club_id INTEGER,
            parent_club TEXT,
            competition_id INTEGER,
            competition TEXT,
            parent_competition_id INTEGER,
            parent_competition TEXT,
            extra_hex TEXT
        )
    """)
    con.execute("CREATE INDEX idx_history_pid ON history(person_id, season_end, season_start)")
    con.execute("CREATE TABLE clubs (club_id INTEGER PRIMARY KEY, name TEXT)")
    con.execute("CREATE INDEX idx_clubs_name ON clubs(name)")
    con.execute("CREATE TABLE competitions (comp_id INTEGER PRIMARY KEY, name TEXT)")
    con.execute("CREATE TABLE player_club (person_id INTEGER PRIMARY KEY, club_id INTEGER, competition_id INTEGER)")
    ins = "INSERT INTO history VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"

    def name(mapping, cid, kind):
        if cid in (0, NULL_ID):
            return ""
        v = mapping.get(cid)
        return v if v else f"Unknown {kind} #{cid}"

    n = 0
    batch = []
    print("writing history rows...", flush=True)
    for pid, start, nxt in blocks():
        for pos in range(start, nxt, REC):
            r = dt[pos:pos + REC]
            if len(r) < REC:
                break
            y1, y2 = struct.unpack_from("<HH", r, 0)
            b4, apps, goals = r[4], r[5], r[6]
            cid = struct.unpack_from("<I", r, 11)[0]
            pcid = struct.unpack_from("<I", r, 15)[0]
            cp = struct.unpack_from("<I", r, 19)[0]
            pcp = struct.unpack_from("<I", r, 23)[0]
            rtype = "Senior" if b4 == 0x40 else ("Youth" if b4 == 0x42 else f"0x{b4:02x}")
            batch.append((
                pid, y1, y2, rtype, apps, goals,
                cid, name(club_map, cid, "club"),
                pcid, name(club_map, pcid, "club"),
                cp, name(comp_map, cp, "competition"),
                pcp, name(comp_map, pcp, "competition"),
                r[7:11].hex() + r[41:44].hex(),
            ))
            n += 1
            if len(batch) >= 10000:
                con.executemany(ins, batch)
                batch.clear()
                if n % 500000 == 0:
                    print(f"  {n:,} rows ({time.time()-t0:.0f}s)", flush=True)
    if batch:
        con.executemany(ins, batch)
    print(f"  writing club/competition/player-club maps...", flush=True)
    con.executemany("INSERT INTO clubs(club_id,name) VALUES(?,?)", club_map.items())
    con.executemany("INSERT INTO competitions(comp_id,name) VALUES(?,?)", comp_map.items())
    con.executemany("INSERT INTO player_club(person_id,club_id,competition_id) VALUES(?,?,?)",
                    ((pid, c, cp) for pid, (c, cp) in player_club.items()))
    con.commit()
    con.execute("VACUUM")
    con.close()
    os.replace(tmp, OUT)
    print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.0f} MB, {n:,} rows, {time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
