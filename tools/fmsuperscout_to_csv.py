#!/usr/bin/env python3
"""Flatten an FMSuperScout dump.json into CSV files.

Usage: python3 fmsuperscout_to_csv.py <dump.json> <outdir>
Produces:
  fm26_players.csv  - one row per player, all scalar fields + 52 attributes
  fm26_staff.csv    - one row per staff member, all scalar fields + staff attrs
  fm26_people.csv   - players + staff with a 'kind' column
"""
import csv
import json
import os
import sys

# Stable, human-friendly column order for players.
PLAYER_FIELDS = [
    "id", "name", "age", "dob", "birthYear", "birthDoy",
    "nat", "natId", "club", "ownerClub", "div",
    "ca", "pa", "pos", "posArr", "posNat", "foot", "height",
    "wage", "expires", "value", "askingPrice", "wageDemand",
    "listed", "loanListed", "notForSale", "setForRelease",
    "clubRep", "worldRep", "teamType",
    "adaptability", "ambition", "loyalty", "pressure", "professionalism",
    "sportsmanship", "temperament", "controversy",
]

STAFF_FIELDS = [
    "id", "name", "age", "dob", "birthYear", "birthDoy",
    "nat", "natId", "club", "div", "ca", "pa",
    "wage", "expires", "job", "jobId", "prefJob", "jobPrefs",
    "curRep", "worldRep",
]

PERSONALITY = ["adaptability", "ambition", "loyalty", "pressure",
               "professionalism", "sportsmanship", "temperament", "controversy"]

# The FMSuperScout plugin emits staff attributes with Dutch keys (its internal
# labels).  Rename them to the standard Football Manager English labels.
STAFF_ATTR_EN = {
    "Aanvallen": "Attacking",
    "Verdedigen": "Defending",
    "Fitheid": "Fitness",
    "Balbezit": "Possession",
    "Technisch": "Technical",
    "Tactisch": "Tactical",
    "Standaardsituaties": "Set Pieces",
    "Vastberadenheid": "Determination",
    "Man-management": "Man Management",
    "Motiveren": "Motivating",
    "Oordeel_vermogen": "Judging Player Ability",
    "Oordeel_potentie": "Judging Player Potential",
    "Oordeel_staf": "Judging Staff Ability",
    "Onderhandelen": "Negotiating",
    "Tactische_kennis": "Tactical Knowledge",
    "Fysiotherapie": "Physiotherapy",
    "Sportwetenschap": "Sports Science",
    "Data_analyse": "Data Analysis",
    "Jeugd": "Working With Youngsters",
    "KV_distributie": "Goalkeeping Distribution",
    "KV_vangen": "Goalkeeping Handling",
    "KV_reflexen": "Goalkeeping Shot Stopping",
    "Aanpassingsvermogen": "Adaptability",
}


def flat(value):
    if isinstance(value, list):
        return "; ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None:
        return ""
    return value


def collect_attr_keys(rows, attr_field):
    keys = []
    seen = set()
    for r in rows:
        for k in (r.get(attr_field) or {}):
            if k not in seen:
                seen.add(k)
                keys.append(k)
    return keys


def write_players(players, outdir, prefix="fm26"):
    attr_keys = collect_attr_keys(players, "attrs")
    base = [f for f in PLAYER_FIELDS if any(f in p for p in players)]
    extra = sorted({k for p in players for k in p
                    if k not in base and k != "attrs"})
    header = base + extra + attr_keys
    path = os.path.join(outdir, f"{prefix}_players.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for p in players:
            row = {f: flat(p.get(f)) for f in base}
            row.update({k: flat(p.get(k)) for k in extra})
            row.update({k: flat((p.get("attrs") or {}).get(k))
                        for k in attr_keys})
            w.writerow(row)
    return path, len(players), len(header)


def write_staff(staff, outdir, prefix="fm26"):
    raw_keys = collect_attr_keys(staff, "staffAttrs")
    # Translate Dutch plugin keys to English FM labels (keep unknown keys as-is).
    renamed = {k: STAFF_ATTR_EN.get(k, k) for k in raw_keys}
    base = [f for f in STAFF_FIELDS if any(f in s for s in staff)]
    extra = sorted({k for s in staff for k in s
                    if k not in base and k != "staffAttrs"})
    header = base + extra + [renamed[k] for k in raw_keys]
    path = os.path.join(outdir, f"{prefix}_staff.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for s in staff:
            row = {f: flat(s.get(f)) for f in base}
            row.update({k: flat(s.get(k)) for k in extra})
            attrs = s.get("staffAttrs") or {}
            row.update({renamed[k]: flat(attrs.get(k)) for k in raw_keys})
            w.writerow(row)
    return path, len(staff), len(header)


def write_combined(players, staff, outdir, prefix="fm26"):
    hpath = os.path.join(outdir, f"{prefix}_players.csv")
    with open(hpath, "r", encoding="utf-8-sig", newline="") as fh:
        player_header = next(csv.reader(fh))
    spath = os.path.join(outdir, f"{prefix}_staff.csv")
    with open(spath, "r", encoding="utf-8-sig", newline="") as fh:
        staff_header = next(csv.reader(fh))
    combined_header = ["kind"] + player_header + [
        h for h in staff_header if h not in player_header]
    path = os.path.join(outdir, f"{prefix}_people.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as out:
        w = csv.writer(out)
        w.writerow(combined_header)
        for kind, src in (("player", hpath), ("staff", spath)):
            with open(src, "r", encoding="utf-8-sig", newline="") as fh:
                r = csv.reader(fh)
                head = next(r)
                for rec in r:
                    row = {"kind": kind}
                    row.update(dict(zip(head, rec)))
                    w.writerow([row.get(h, "") for h in combined_header])
    return path


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    dump_path, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    print(f"loading {dump_path} ...")
    with open(dump_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    players = data.get("players", [])
    staff = data.get("staff", [])
    meta = data.get("meta", {})
    print(f"players={len(players)} staff={len(staff)} gameVersion={meta.get('gameVersion')}")

    prefix = "fm27" if str(meta.get("game", "")).upper() == "FM27" else "fm26"
    p, pn, pc = write_players(players, outdir, prefix)
    print(f"wrote {p} ({pn} rows x {pc} cols)")
    s, sn, sc = write_staff(staff, outdir, prefix)
    print(f"wrote {s} ({sn} rows x {sc} cols)")
    c = write_combined(players, staff, outdir, prefix)
    print(f"wrote {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
