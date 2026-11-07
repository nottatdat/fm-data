#!/usr/bin/env python3
"""FM27 Profiles Explorer — stdlib-only web server.

Serves a searchable/filterable browser over the 516,038-player FM27 database
(fm27/csv_515k/fm27_players.csv, loaded into SQLite), with local face/logo packs
(sortitoutsi Cutout Megapack + FMG Standard Logos) and career history from the
shipped pl_hist_* files.

Usage:
    python3 server.py [--port 8770]

The SQLite database is built automatically on first run (~25 s, ~230 MB).
"""
import argparse
import csv
import io
import json
import os
import re
import sqlite3
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import clubnames
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(HERE, "data", "fm27.db")
HIST_DB = os.path.join(HERE, "data", "history.db")
CSV = os.path.join(ROOT, "fm27", "csv_515k", "fm27_players.csv")
STATIC = os.path.join(HERE, "static")

ASSETS = os.path.join(HERE, "assets")
FACE_DIR = os.path.join(ASSETS, "faces", "sortitoutsi", "faces")
LOGO_ROOT = os.path.join(ASSETS, "logos", "FMG Standard Logos 2026.00")
CLUB_LOGO_DIR = os.path.join(LOGO_ROOT, "Clubs", "Normal")
COMP_LOGO_DIR = os.path.join(LOGO_ROOT, "Competitions", "Normal")
NATION_LOGO_DIR = os.path.join(LOGO_ROOT, "Nations", "Normal")

LIST_COLS = ("p.id,p.name,p.age,p.nat,p.natId,p.club,p.div,p.ca,p.pa,p.pos,p.posNat,"
             "p.foot,p.height,p.value,p.gender,p.club_display")
SORT_COLS = {
    "ca": "p.ca", "pa": "p.pa", "age": "p.age", "name": "p.name",
    "value": "p.value", "wage": "p.wage", "height": "p.height",
    "reputation": "p.worldRep", "id": "p.id",
}
POSITIONS = ["GK", "DC", "DL", "DR", "WBL", "WBR", "DM", "MC", "ML", "MR",
             "AMC", "AML", "AMR", "ST"]



# --------------------------------------------------------------------------
# database
# --------------------------------------------------------------------------
CLUB_INDEX = None


def _build_club_index():
    global CLUB_INDEX
    con = connect()
    rows = con.execute("SELECT club, COUNT(*) FROM players WHERE club<>'' GROUP BY club").fetchall()
    con.close()
    CLUB_INDEX = clubnames.ClubIndex([(r[0], r[1]) for r in rows])


def ensure_db():
    sys.path.insert(0, HERE)
    if not os.path.exists(DB):
        import import_db
        print("building player database (first run)...", flush=True)
        import_db.build()
    if os.path.exists(HIST_DB):
        try:
            con = sqlite3.connect(HIST_DB)
            ok = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='player_club'").fetchone()
            con.close()
            if not ok:
                os.remove(HIST_DB)
        except Exception:
            pass
    if not os.path.exists(HIST_DB):
        import import_history
        print("building history database (first run)...", flush=True)
        import_history.main()
    _build_club_index()


def connect():
    con = sqlite3.connect(DB, timeout=30)
    con.row_factory = sqlite3.Row
    return con


# --------------------------------------------------------------------------
# search
# --------------------------------------------------------------------------
def fts_query(q):
    tokens = re.findall(r"[0-9A-Za-zÀ-ÿ]+", q)
    if not tokens:
        return None
    parts = []
    for i, t in enumerate(tokens):
        t = t.replace('"', "")
        parts.append(f'"{t}"' + ("*" if i == len(tokens) - 1 else ""))
    return " AND ".join(parts)


def build_search(params, use_fts=True):
    q = (params.get("q") or "").strip()
    where = []
    args = []
    match = fts_query(q) if (q and use_fts) else None
    if match:
        from_clause = "players p JOIN players_fts ON players_fts.rowid=p.id"
        where.append("players_fts MATCH ?")
        args.append(match)
    else:
        from_clause = "players p"
        if q:
            where.append("(p.name LIKE ? OR p.club LIKE ? OR p.nat LIKE ? OR p.div LIKE ?)")
            args += [f"%{q}%"] * 4

    def add(col, val, op="="):
        where.append(f"{col} {op} ?")
        args.append(val)

    nat = (params.get("nat") or "").strip()
    club = (params.get("club") or "").strip()
    div = (params.get("div") or "").strip()
    pos = (params.get("pos") or "").strip().upper()
    gender = (params.get("gender") or "").strip()
    if nat:
        add("p.nat", f"%{nat}%", "LIKE")
    if club:
        matches = CLUB_INDEX.resolve(club) if CLUB_INDEX else []
        if matches:
            where.append("p.club IN (" + ",".join("?" * len(matches)) + ")")
            args.extend(matches)
        else:
            add("p.club", f"%{club}%", "LIKE")
    if div:
        add("p.div", f"%{div}%", "LIKE")
    if pos in POSITIONS:
        where.append("(p.posArr LIKE ? OR p.posArr LIKE ? OR p.posArr LIKE ? OR p.posArr = ?)")
        args += [f"{pos};%", f"%; {pos}", f"%; {pos};%", pos]
    if gender in ("Men", "Women"):
        add("p.gender", gender)
    for key, col, op in (("min_ca", "p.ca", ">="), ("max_ca", "p.ca", "<="),
                         ("min_pa", "p.pa", ">="), ("max_pa", "p.pa", "<="),
                         ("min_age", "p.age", ">="), ("max_age", "p.age", "<="),
                         ("min_value", "p.value", ">="), ("max_value", "p.value", "<=")):
        v = params.get(key)
        if v not in (None, ""):
            try:
                add(col, int(v), op)
            except ValueError:
                pass
    sort_key = (params.get("sort") or "ca").lower()
    sort = SORT_COLS.get(sort_key, "p.ca")
    order = "ASC" if (params.get("order") or "desc").lower() == "asc" else "DESC"
    try:
        page = max(1, int(params.get("page") or 1))
    except ValueError:
        page = 1
    try:
        per = min(100, max(10, int(params.get("per") or 36)))
    except ValueError:
        per = 36
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = (f"SELECT {LIST_COLS} FROM {from_clause}{where_sql} "
           f"ORDER BY {sort} {order}, p.id ASC LIMIT ? OFFSET ?")
    count_sql = f"SELECT COUNT(*) FROM {from_clause}{where_sql}"
    return sql, count_sql, args, page, per, sort_key, order


def _execute(params, use_fts):
    sql, count_sql, args, page, per, sort_key, order = build_search(params, use_fts)
    con = connect()
    try:
        total = con.execute(count_sql, args).fetchone()[0]
        rows = con.execute(sql, args + [per, (page - 1) * per]).fetchall()
    finally:
        con.close()
    return {"total": total, "page": page, "per": per,
            "pages": max(1, (total + per - 1) // per),
            "sort": sort_key, "order": order,
            "players": [dict(r) for r in rows]}


def run_search(params):
    try:
        return _execute(params, True)
    except sqlite3.OperationalError:
        return _execute(params, False)


# --------------------------------------------------------------------------
# filters / stats
# --------------------------------------------------------------------------
_filter_cache = None
_filter_lock = threading.Lock()


def get_filters():
    global _filter_cache
    with _filter_lock:
        if _filter_cache is not None:
            return _filter_cache
        con = connect()
        nations = set()
        for (nat,) in con.execute("SELECT nat FROM players WHERE nat<>''"):
            for n in str(nat).split(";"):
                n = n.strip()
                if n:
                    nations.add(n)
        clubs = CLUB_INDEX.top(500) if CLUB_INDEX else []
        divs = [dict(r) for r in con.execute(
            "SELECT div, COUNT(*) c FROM players WHERE div<>'' "
            "GROUP BY div ORDER BY c DESC, div LIMIT 500")]
        total = con.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        women = con.execute("SELECT COUNT(*) FROM players WHERE gender='Women'").fetchone()[0]
        men = total - women
        n_clubs = con.execute("SELECT COUNT(DISTINCT club) FROM players WHERE club<>''").fetchone()[0]
        n_divs = con.execute("SELECT COUNT(DISTINCT div) FROM players WHERE div<>''").fetchone()[0]
        # position counts
        pos_counts = {p: 0 for p in POSITIONS}
        for (arr,) in con.execute("SELECT posArr FROM players WHERE posArr<>''"):
            for p in str(arr).split(";"):
                p = p.strip().upper()
                if p in pos_counts:
                    pos_counts[p] += 1
        con.close()
        _filter_cache = {
            "nations": sorted(nations),
            "clubs": clubs,
            "divisions": divs,
            "positions": [{"pos": p, "count": pos_counts[p]} for p in POSITIONS],
            "stats": {"players": total, "men": men, "women": women,
                      "clubs": n_clubs, "divisions": n_divs,
                      "nations": len(nations)},
        }
        return _filter_cache


# --------------------------------------------------------------------------
# local face / logo assets
# --------------------------------------------------------------------------
def player_club_id(pid):
    """Club id for a player, from history (preferred) or the clubs name map."""
    if os.path.exists(HIST_DB):
        con = sqlite3.connect(HIST_DB, timeout=30)
        try:
            row = con.execute("SELECT club_id FROM player_club WHERE person_id=?", (pid,)).fetchone()
            if row:
                return row[0]
        finally:
            con.close()
    con = sqlite3.connect(DB, timeout=30)
    try:
        row = con.execute("SELECT club FROM players WHERE id=?", (pid,)).fetchone()
    finally:
        con.close()
    if not row or not row[0] or not os.path.exists(HIST_DB):
        return None
    con = sqlite3.connect(HIST_DB, timeout=30)
    try:
        row = con.execute("SELECT club_id FROM clubs WHERE name=? ORDER BY club_id LIMIT 1", (row[0],)).fetchone()
        return row[0] if row else None
    finally:
        con.close()


# --------------------------------------------------------------------------
# career / league history
# --------------------------------------------------------------------------
def _season_label(y1, y2):
    return str(y1) if y1 == y2 else f"{y1}-{str(y2)[-2:].zfill(2)}"


def get_history(pid):
    empty = {"person_id": pid,
             "totals": {"apps": 0, "goals": 0, "clubs": 0, "seasons": 0},
             "records": []}
    if not os.path.exists(HIST_DB):
        return empty
    con = sqlite3.connect(HIST_DB, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in con.execute(
            "SELECT season_start,season_end,record_type,apps,goals,club_id,club,"
            "parent_club_id,parent_club,competition_id,competition,"
            "parent_competition_id,parent_competition,extra_hex FROM history "
            "WHERE person_id=? ORDER BY season_end, season_start, apps DESC", (pid,))]
    finally:
        con.close()
    for r in rows:
        r["season"] = _season_label(r["season_start"], r["season_end"])
        r["club_display"] = clubnames.display_name(r["club"]) if r.get("club") else ""
        r["parent_club_display"] = clubnames.display_name(r["parent_club"]) if r.get("parent_club") else ""
        if r.get("parent_club") == r.get("club"):
            r["parent_club"] = ""
        if r.get("parent_competition") == r.get("competition"):
            r["parent_competition"] = ""
    senior = [r for r in rows if r["record_type"] == "Senior"]
    clubs = {r["club"] for r in rows if r["club"] and not r["club"].startswith("Unknown")}
    seasons = {(r["season_start"], r["season_end"]) for r in rows}
    return {"person_id": pid,
            "totals": {"apps": sum(r["apps"] or 0 for r in senior),
                       "goals": sum(r["goals"] or 0 for r in senior),
                       "clubs": len(clubs), "seasons": len(seasons)},
            "records": rows}


def history_csv(pid):
    data = get_history(pid)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["season", "club", "parent_club", "competition", "parent_competition",
                "apps", "goals", "type"])
    for r in data["records"]:
        w.writerow([r.get("season"), r.get("club"), r.get("parent_club"),
                    r.get("competition"), r.get("parent_competition"),
                    r.get("apps"), r.get("goals"), r.get("record_type")])
    return buf.getvalue()


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml",
        ".png": "image/png", ".ico": "image/x-icon"}


class Handler(BaseHTTPRequestHandler):
    server_version = "FM27Profiles/1.0"

    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith(("GET /api/face", "GET /api/player-club-logo",
                                             "GET /api/club-logo", "GET /api/comp-logo",
                                             "GET /api/nation-logo", "GET /api/player")):
            return
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, filename):
        path = os.path.realpath(os.path.join(STATIC, filename))
        if not path.startswith(os.path.realpath(STATIC) + os.sep) or not os.path.isfile(path):
            self.send_error(404)
            return
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def send_csv(self, text, filename):
        body = ("\ufeff" + text).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_image(self, path):
        if not path or not os.path.isfile(path):
            self.send_error(404)
            return
        ext = os.path.splitext(path)[1].lower()
        ctype = "image/png" if ext == ".png" else "image/jpeg" if ext in (".jpg", ".jpeg") else "application/octet-stream"
        with open(path, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        path = parsed.path
        try:
            if path == "/api/stats":
                self.send_json(get_filters()["stats"])
            elif path == "/api/filters":
                self.send_json(get_filters())
            elif path == "/api/players":
                self.send_json(run_search(params))
            elif path.startswith("/api/history/"):
                rest = path[len("/api/history/"):]
                if rest.endswith(".csv"):
                    pid = rest[:-4]
                    self.send_csv(history_csv(pid), f"player_{pid}_history.csv")
                else:
                    self.send_json(get_history(rest))
            elif path.startswith("/api/player/"):
                pid = path.rsplit("/", 1)[-1]
                con = connect()
                row = con.execute("SELECT * FROM players WHERE id=?", (pid,)).fetchone()
                con.close()
                if not row:
                    self.send_json({"error": "not found"}, 404)
                else:
                    self.send_json(dict(row))
            elif path.startswith("/api/face/"):
                pid = path.rsplit("/", 1)[-1]
                self.send_image(os.path.join(FACE_DIR, f"face_{pid}.png"))
            elif path.startswith("/api/player-club-logo/"):
                pid = path.rsplit("/", 1)[-1]
                cid = player_club_id(pid)
                self.send_image(os.path.join(CLUB_LOGO_DIR, f"{cid}_club.png") if cid else None)
            elif path.startswith("/api/club-logo/"):
                cid = path.rsplit("/", 1)[-1]
                self.send_image(os.path.join(CLUB_LOGO_DIR, f"{cid}_club.png"))
            elif path.startswith("/api/comp-logo/"):
                cid = path.rsplit("/", 1)[-1]
                self.send_image(os.path.join(COMP_LOGO_DIR, f"{cid}_comp.png"))
            elif path.startswith("/api/nation-logo/"):
                nid = path.rsplit("/", 1)[-1]
                self.send_image(os.path.join(NATION_LOGO_DIR, f"{nid}_nation.png"))
            elif path in ("", "/", "/index.html"):
                self.send_static("index.html")
            elif path.startswith("/static/"):
                self.send_static(path[len("/static/"):])
            else:
                self.send_static(path.lstrip("/"))
        except BrokenPipeError:
            pass
        except Exception as e:
            self.send_json({"error": str(e)}, 500)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    ensure_db()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"FM27 Profiles Explorer: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
