#!/usr/bin/env python3
"""Export the full player-history database to CSV.

Usage:
    python3 export_history.py [out.csv]

Reads data/history.db (built by import_history.py) and writes ~5.7M rows.
"""
import csv
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "data", "history.db")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "fm27_player_history.csv")

if not os.path.exists(DB):
    sys.exit(f"history database not found: {DB}\nRun: python3 import_history.py")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
n = 0
with open(OUT, "w", encoding="utf-8-sig", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["person_id", "season", "club", "parent_club", "competition",
                "apps", "goals", "type"])
    cur = con.execute(
        "SELECT person_id, season_start, season_end, club, parent_club, "
        "competition, apps, goals, record_type FROM history "
        "ORDER BY person_id, season_end, season_start")
    for r in cur:
        y1, y2 = r["season_start"], r["season_end"]
        season = str(y1) if y1 == y2 else f"{y1}-{y2}"
        w.writerow([r["person_id"], season, r["club"], r["parent_club"],
                    r["competition"], r["apps"], r["goals"], r["record_type"]])
        n += 1
        if n % 500000 == 0:
            print(f"  {n:,} rows", flush=True)
con.close()
print(f"wrote {OUT} ({n:,} rows, {os.path.getsize(OUT)/1e6:.0f} MB)")
