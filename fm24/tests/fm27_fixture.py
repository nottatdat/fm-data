#!/usr/bin/env python3
"""Build a small, deterministic FM27-format fixture for explorer regression checks.

No FM27 data exists on the FM24 Mac, so the default (FM27) explorer is exercised
against synthetic data instead:

    fm27_fixture.py build  <fixture_dir>      # writes fm27_players.csv + history.db
    fm27_fixture.py install <fixture_dir> <repo_root>
        # copies them to <repo_root>/fm27/csv_515k/ and <repo_root>/fm27/explorer/data/
        # and deletes any fm27.db there so the explorer rebuilds it from the fixture.

`install` refuses to write into the main working copy: point it at a throwaway
worktree (e.g. under .context/) only.
"""
import csv
import os
import random
import shutil
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(MAIN_ROOT, "fm27", "explorer"))
import import_db  # noqa: E402  (column lists only; nothing is built here)

N_PLAYERS = 300
CLUBS = [("R. Madrid", "LaLiga EA Sports"), ("Man City", "Premier League"),
         ("Paris Saint-Germain", "Ligue 1"), ("FC Bayern München", "Bundesliga"),
         ("Inter", "Serie A"), ("Arsenal", "Premier League"), ("Everton", "Premier League"),
         ("Stade Rennais FC", "Ligue 1"), ("Sagan Tosu", "J1 League"), ("", "")]
NATS = [("England", 765), ("France", 772), ("Spain", 796), ("Brazil", 1649),
        ("Japan", 1362), ("Germany", 771)]
FIRST = ["Alex", "Bruno", "Carlos", "Daniel", "Erik", "Felix", "Hugo", "Ivan", "Jonas", "Kenji"]
LAST = ["Silva", "Muller", "Martin", "Tanaka", "Smith", "Garcia", "Rossi", "Dubois", "Kane", "Ito"]
POS = ["GK", "D (C)", "D (L)", "D (R)", "DM", "M (C)", "AM (C)", "AM (L)", "AM (R)", "ST (C)"]
FOOT = ["Rechts", "Links", "Beide"]


def source_columns():
    derived = {"club_display", "club_search"}
    return [c for c in import_db.ALL_COLS if c not in derived]


def build(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rnd = random.Random(2024)
    cols = source_columns()
    rows = []
    for i in range(N_PLAYERS):
        pid = 1000 + i * 7
        club, div = CLUBS[i % len(CLUBS)]
        nat, nat_id = NATS[i % len(NATS)]
        by = 1985 + (i % 20)
        ca = 60 + (i * 37) % 140
        r = {c: "" for c in cols}
        r.update({
            "id": pid, "name": f"{FIRST[i % 10]} {LAST[(i // 10) % 10]} {i}",
            "dob": f"{by}-{1 + i % 12:02d}-{1 + i % 28:02d}", "nat": nat, "natId": nat_id,
            "club": club, "ownerClub": club, "div": div, "pos": POS[i % len(POS)],
            "posNat": POS[i % len(POS)], "expires": f"{2026 + i % 4}-06-30",
            "age": 2027 - by, "birthYear": by, "birthDoy": 1 + (i * 11) % 365,
            "ca": ca, "pa": min(200, ca + (i * 13) % 60), "height": 165 + i % 35,
            "wage": 1000 * (1 + i % 90), "value": 50000 * (1 + (i * 3) % 400),
            "clubRep": 1000 + i, "worldRep": 500 + i,
            "foot": FOOT[i % 3], "gender": "1" if i % 9 == 0 else "0",
        })
        for c in import_db.ATTRS + ["adaptability", "ambition", "loyalty", "pressure",
                                     "professionalism", "sportsmanship", "temperament",
                                     "controversy"]:
            r[c] = rnd.randint(1, 20)
        rows.append(r)
    csv_path = os.path.join(out_dir, "fm27_players.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    hist_path = os.path.join(out_dir, "history.db")
    if os.path.exists(hist_path):
        os.remove(hist_path)
    con = sqlite3.connect(hist_path)
    con.execute("""CREATE TABLE history (person_id INTEGER NOT NULL, season_start INTEGER NOT NULL,
        season_end INTEGER NOT NULL, record_type TEXT, apps INTEGER, goals INTEGER, club_id INTEGER,
        club TEXT, parent_club_id INTEGER, parent_club TEXT, competition_id INTEGER, competition TEXT,
        parent_competition_id INTEGER, parent_competition TEXT, extra_hex TEXT)""")
    con.execute("CREATE TABLE clubs (club_id INTEGER PRIMARY KEY, name TEXT)")
    con.execute("CREATE TABLE competitions (comp_id INTEGER PRIMARY KEY, name TEXT)")
    con.execute("CREATE TABLE player_club (person_id INTEGER PRIMARY KEY, club_id INTEGER, competition_id INTEGER)")
    club_ids = {c: 100 + k for k, (c, _) in enumerate(CLUBS) if c}
    con.executemany("INSERT INTO clubs VALUES (?,?)", [(v, k) for k, v in club_ids.items()])
    con.execute("INSERT INTO competitions VALUES (1, 'Premier League')")
    for i, r in enumerate(rows):
        if not r["club"]:
            continue
        cid = club_ids[r["club"]]
        con.execute("INSERT INTO player_club VALUES (?,?,1)", (r["id"], cid))
        for s in range(3):
            con.execute("INSERT INTO history VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (r["id"], 2023 + s, 2024 + s, "Senior", 10 + (i + s) % 30, (i * s) % 15,
                         cid, r["club"], 0, "", 1, "Premier League", 0, "", ""))
    con.commit()
    con.close()
    print(f"fixture: {csv_path} ({len(rows)} players), {hist_path}")


def install(fixture_dir, repo_root):
    repo_root = os.path.abspath(repo_root)
    if repo_root == MAIN_ROOT:
        sys.exit("refusing to install the fixture into the main working copy; use a throwaway worktree")
    csv_dst = os.path.join(repo_root, "fm27", "csv_515k")
    data_dst = os.path.join(repo_root, "fm27", "explorer", "data")
    os.makedirs(csv_dst, exist_ok=True)
    os.makedirs(data_dst, exist_ok=True)
    shutil.copy2(os.path.join(fixture_dir, "fm27_players.csv"), csv_dst)
    shutil.copy2(os.path.join(fixture_dir, "history.db"), data_dst)
    stale = os.path.join(data_dst, "fm27.db")
    if os.path.exists(stale):
        os.remove(stale)
    print(f"installed fixture into {repo_root}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "build":
        build(sys.argv[2])
    elif len(sys.argv) == 4 and sys.argv[1] == "install":
        install(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
