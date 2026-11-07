#!/usr/bin/env python3
"""Build the SQLite database used by the FM27 profiles explorer.

Usage:
    python3 import_db.py [--force]

Reads ../csv_515k/fm27_players.csv (516,038 players, 94 columns) and writes
data/fm27.db.  Also builds an FTS5 index over name/club/nation/division.
"""
import argparse
import csv
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.abspath(os.path.join(HERE, "..", "csv_515k", "fm27_players.csv"))
DB = os.path.join(HERE, "data", "fm27.db")

TEXT_COLS = [
    "name", "dob", "nat", "club", "ownerClub", "div", "pos", "posArr", "posNat",
    "expires", "listed", "loanListed", "notForSale", "setForRelease",
    "ownerTeamType", "transferDate", "transferTo",
]
INT_COLS = [
    "age", "birthYear", "birthDoy", "natId", "ca", "pa", "height", "wage",
    "value", "askingPrice", "wageDemand", "clubRep", "worldRep",
    "adaptability", "ambition", "loyalty", "pressure", "professionalism",
    "sportsmanship", "temperament", "controversy",
]
# 52 attributes, kept in their own table?  No: flat columns are easier to query/sort.
ATTRS = [
    "Crossing", "Dribbling", "Finishing", "Heading", "LongShots", "Marking",
    "OffTheBall", "Passing", "PenaltyTaking", "Tackling", "Vision", "Handling",
    "AerialReach", "CommandOfArea", "Communication", "Kicking", "Throwing",
    "Anticipation", "Decisions", "OneOnOnes", "Positioning", "Reflexes",
    "FirstTouch", "Technique", "Flair", "Corners", "Teamwork", "WorkRate",
    "LongThrows", "Eccentricity", "RushingOut", "Punching", "Acceleration",
    "FreeKicks", "Strength", "Stamina", "Pace", "JumpingReach", "Leadership",
    "Balance", "Bravery", "Aggression", "Agility", "NaturalFitness",
    "Determination", "Composure", "Concentration", "Dirtiness", "Consistency",
    "ImportantMatches", "InjuryProneness", "Versatility",
]
ALL_COLS = ["id"] + TEXT_COLS + INT_COLS + ATTRS + ["foot", "gender"]

FOOT_EN = {"Rechts": "Right", "Links": "Left", "Beide": "Both"}


def _to_int(v):
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def _to_text(v):
    if v is None:
        return ""
    return str(v).strip()


def build(db_path=DB, csv_path=CSV, force=False):
    if os.path.exists(db_path) and not force:
        return db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    tmp = db_path + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)

    sql_cols = []
    for c in ALL_COLS:
        if c == "id":
            sql_cols.append('"id" INTEGER PRIMARY KEY')
        elif c in ("foot", "gender"):
            sql_cols.append(f'"{c}" TEXT')
        elif c in TEXT_COLS:
            sql_cols.append(f'"{c}" TEXT')
        else:
            sql_cols.append(f'"{c}" INTEGER')

    con = sqlite3.connect(tmp)
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("PRAGMA temp_store=MEMORY")
    con.execute(f'CREATE TABLE players ({", ".join(sql_cols)})')
    con.execute("CREATE INDEX idx_players_ca ON players(ca)")
    con.execute("CREATE INDEX idx_players_pa ON players(pa)")
    con.execute("CREATE INDEX idx_players_age ON players(age)")
    con.execute("CREATE INDEX idx_players_value ON players(value)")
    con.execute("CREATE INDEX idx_players_club ON players(club)")
    con.execute("CREATE INDEX idx_players_nat ON players(nat)")
    con.execute("CREATE INDEX idx_players_div ON players(div)")

    placeholders = ",".join("?" for _ in ALL_COLS)
    insert = f'INSERT INTO players ({",".join(ALL_COLS)}) VALUES ({placeholders})'

    n = 0
    t0 = time.time()
    batch = []
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            vals = []
            for c in ALL_COLS:
                if c == "id":
                    vals.append(_to_int(row.get(c)))
                elif c == "foot":
                    vals.append(FOOT_EN.get(_to_text(row.get(c)), _to_text(row.get(c))))
                elif c == "gender":
                    vals.append("Women" if _to_text(row.get(c)) == "1" else "Men")
                elif c in TEXT_COLS:
                    vals.append(_to_text(row.get(c)))
                else:
                    vals.append(_to_int(row.get(c)))
            batch.append(vals)
            n += 1
            if len(batch) >= 5000:
                con.executemany(insert, batch)
                batch.clear()
                if n % 50000 == 0:
                    print(f"  {n:,} rows ({time.time()-t0:.0f}s)", flush=True)
    if batch:
        con.executemany(insert, batch)
    con.commit()
    print(f"  inserted {n:,} players in {time.time()-t0:.0f}s", flush=True)

    print("  building FTS index...", flush=True)
    con.execute("CREATE VIRTUAL TABLE players_fts USING fts5(name, club, nat, div, content='players', content_rowid='id')")
    con.execute("INSERT INTO players_fts(rowid, name, club, nat, div) SELECT id, name, club, nat, div FROM players")
    con.commit()
    con.execute("VACUUM")
    con.close()
    os.replace(tmp, db_path)
    print(f"  wrote {db_path} ({os.path.getsize(db_path)/1e6:.0f} MB)", flush=True)
    return db_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--db", default=DB)
    ap.add_argument("--csv", default=CSV)
    args = ap.parse_args()
    if not os.path.exists(args.csv):
        sys.exit(f"CSV not found: {args.csv}")
    print(f"importing {args.csv} -> {args.db}")
    build(args.db, args.csv, force=args.force)


if __name__ == "__main__":
    main()
