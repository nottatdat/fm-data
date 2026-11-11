#!/usr/bin/env python3
"""Sanitize the FM27 515k dump (remove the human manager) and write CSVs."""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fmsuperscout_to_csv as conv

RAW = os.path.join(ROOT, "fm27/work/fmsuperscout_dump_515k.json")
SAN = os.path.join(ROOT, "fm27/work/fmsuperscout_dump_515k_sanitized.json")
OUT = os.path.join(ROOT, "fm27/csv_515k")
PREFIX = "fm27"

print("loading", RAW, "...")
d = json.load(open(RAW))
meta = d.get("meta", {})

# Names/ids that identify the human manager profile.
names = set()
if meta.get("manager"):
    names.add(meta["manager"])
for m in meta.get("managers", []):
    if m.get("name"):
        names.add(m["name"])
for n in os.environ.get("DROP_NAMES", "").split(","):
    if n.strip():
        names.add(n.strip())
ids = {x.strip() for x in os.environ.get("DROP_IDS", "").split(",") if x.strip()}

def is_manager(x):
    # manager person row; also drop the age-0/club-less manager placeholder
    placeholder = (x.get("job") in ("Staflid", "Staff") and x.get("age") in (0, None)
                   and not x.get("club"))
    return (x.get("name") in names) or (str(x.get("id")) in ids) or placeholder

bp, bs = len(d["players"]), len(d["staff"])
removed_p = [x for x in d["players"] if is_manager(x)]
removed_s = [x for x in d["staff"] if is_manager(x)]
d["players"] = [x for x in d["players"] if not is_manager(x)]
d["staff"] = [x for x in d["staff"] if not is_manager(x)]
print(f"manager names: {sorted(names)}")
print(f"removed players: {len(removed_p)}  staff: {len(removed_s)}")
for x in (removed_p + removed_s):
    print("  removed:", x.get("id"), repr(x.get("name")), x.get("job"), x.get("club"))

# Scrub manager metadata.
meta["manager"] = None
meta.pop("managers", None)
meta["myClub"] = None
meta["myClubRep"] = 0

print("writing sanitized dump", SAN, "...")
with open(SAN, "w", encoding="utf-8") as fh:
    json.dump(d, fh, ensure_ascii=False, separators=(",", ":"))
print("wrote", os.path.getsize(SAN), "bytes")

os.makedirs(OUT, exist_ok=True)
p, pn, pc = conv.write_players(d["players"], OUT, PREFIX)
print(f"wrote {p} ({pn} rows x {pc} cols)")
s, sn, sc = conv.write_staff(d["staff"], OUT, PREFIX)
print(f"wrote {s} ({sn} rows x {sc} cols)")
c = conv.write_combined(d["players"], d["staff"], OUT, PREFIX)
print(f"wrote {c}")
print(f"players {bp} -> {len(d['players'])}; staff {bs} -> {len(d['staff'])}")
