#!/usr/bin/env python3
"""Capture and compare FM27 (default mode) explorer behaviour for regression checks.

    fm27_regression.py capture <base_url> <out_dir>
        Saves JSON/CSV for a fixed request list to <out_dir>/api/, page/profile text,
        the list of API paths the page requested, and screenshots to <out_dir>/ui/.
    fm27_regression.py compare <baseline_dir> <candidate_dir>
        Exits non-zero if any API response or UI text/request list differs.

Run against an explorer started on the fixture (see fm27_fixture.py), with
FM_MATCH_DATA pointing at a non-existent directory so results are deterministic.
UI capture uses the gstack `browse` CLI (headless Chromium).
"""
import json
import os
import subprocess
import sys
import urllib.request

BROWSE = os.path.expanduser("~/.claude/skills/gstack/browse/dist/browse")
PROFILE_IDS = [1000, 1007, 1063, 1700, 3093]   # first, mid, women (i=9), late, last
REQUESTS = [
    "/api/stats", "/api/filters",
    "/api/players", "/api/players?q=silva&per=10", "/api/players?q=R.%20Madrid",
    "/api/players?club=Arsenal&sort=age&order=asc", "/api/players?pos=ST&min_ca=120",
    "/api/players?gender=Women", "/api/players?nat=Japan&page=2&per=10",
    "/api/players?div=Ligue%201&sort=value",
] + [f"/api/player/{i}" for i in PROFILE_IDS] \
  + [f"/api/history/{i}" for i in PROFILE_IDS] \
  + [f"/api/form/{i}" for i in PROFILE_IDS] \
  + [f"/api/history/{PROFILE_IDS[1]}.csv", "/api/player/999999"]


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def safe_name(path):
    return path.strip("/").replace("/", "_").replace("?", "__").replace("&", "_").replace("%20", "+")


def browse(*args):
    return subprocess.run([BROWSE, *args], capture_output=True, text=True, timeout=60).stdout


def capture(base, out):
    api_dir = os.path.join(out, "api")
    ui_dir = os.path.join(out, "ui")
    os.makedirs(api_dir, exist_ok=True)
    os.makedirs(ui_dir, exist_ok=True)
    for p in REQUESTS:
        status, body = fetch(base + p)
        with open(os.path.join(api_dir, safe_name(p)), "wb") as fh:
            fh.write(f"{status}\n".encode() + body)

    browse("viewport", "1400x1000")
    browse("goto", base + "/")
    browse("wait", "--networkidle")
    browse("network", "--clear")
    browse("goto", base + "/")
    browse("wait", "#grid .card:first-child")
    browse("wait", "--networkidle")
    with open(os.path.join(ui_dir, "search.txt"), "w") as fh:
        fh.write(browse("text"))
    browse("screenshot", os.path.join(ui_dir, "search.png"))
    browse("js", "document.querySelector('#grid .card').click()")
    browse("wait", "#profile .pblock:first-child")
    browse("wait", "--networkidle")
    with open(os.path.join(ui_dir, "profile.txt"), "w") as fh:
        fh.write(browse("js", "document.querySelector('#profile').innerText"))
    browse("screenshot", os.path.join(ui_dir, "profile.png"))
    # API paths requested by the page (deduplicated, sorted; images/static excluded)
    net = browse("network")
    paths = sorted({tok.split(base, 1)[1].split()[0] for tok in net.split()
                    if base in tok and "/api/" in tok
                    and not any(k in tok for k in ("face", "logo"))})
    with open(os.path.join(ui_dir, "requests.txt"), "w") as fh:
        fh.write("\n".join(paths) + "\n")
    print(f"captured {len(REQUESTS)} API responses + UI into {out}")


def normalized(path):
    """File bytes without the browse tool's wrapper lines (they contain the server port)."""
    lines = open(path, "rb").read().splitlines()
    return [ln for ln in lines if not ln.startswith((b"--- BEGIN UNTRUSTED", b"--- END UNTRUSTED"))]


def compare(a, b):
    diffs = []
    for sub in ("api", "ui"):
        da, db = os.path.join(a, sub), os.path.join(b, sub)
        for name in sorted(set(os.listdir(da)) | set(os.listdir(db))):
            if name.endswith(".png"):
                continue   # screenshots are for human review; text + requests are compared
            pa, pb = os.path.join(da, name), os.path.join(db, name)
            if not (os.path.exists(pa) and os.path.exists(pb)):
                diffs.append(f"missing: {sub}/{name}")
            elif normalized(pa) != normalized(pb):
                diffs.append(f"differs: {sub}/{name}")
    for d in diffs:
        print(d)
    print("IDENTICAL" if not diffs else f"{len(diffs)} difference(s)")
    return 1 if diffs else 0


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "capture":
        capture(sys.argv[2].rstrip("/"), sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == "compare":
        sys.exit(compare(sys.argv[2], sys.argv[3]))
    else:
        sys.exit(__doc__)
