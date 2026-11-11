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
import importlib
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
# Optional Sofascore data for the Form panel (kept outside this repo). Point
# FM_MATCH_DATA at a directory holding links.db + matches.db to enable it.
MATCH_DATA = os.environ.get("FM_MATCH_DATA", os.path.join(ROOT, "matches", "data"))
FORM_DB = os.path.join(MATCH_DATA, "links.db")
MATCH_DB = os.path.join(MATCH_DATA, "matches.db")
CSV = os.path.join(ROOT, "fm27", "csv_515k", "fm27_players.csv")
# Datasets the explorer can serve, chosen once at startup with --game (see configure()).
# FM27 is the default and keeps the paths above unchanged. A save-backed game names its
# database file and the module providing its SaveDataset (provenance, reload); its
# `panels` say which FM27-only features (career history, Sofascore form, face/logo packs)
# exist. Adding a game = one entry here plus its own package.
GAMES = {
    "fm27": {"label": "FM27", "panels": {"history": True, "form": True, "images": True}},
    "fm24": {"label": "FM24", "db": "fm24.db", "dataset": "fm24.save.live",
             "panels": {"history": False, "form": False, "images": False},
             "missing": "Save in FM24 (Cmd+S), then run: python3 fm24/save/parse_save.py"},
}
GAME = "fm27"
PANELS = GAMES["fm27"]["panels"]
SAVE_DATASET = None        # SaveDataset of a save-backed game
INDEX_SCRIPT_TAG = b'<script src="/static/app.js">'   # save-backed games inject before it
LEAGUE_NAMES = {
    "PL": "Premier League", "PD": "La Liga", "SA": "Serie A",
    "BL1": "Bundesliga", "FL1": "Ligue 1",
}
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


def configure(game):
    """Point the module-level paths at the chosen game's dataset (called once at startup)."""
    global GAME, PANELS, DB, CSV, SAVE_DATASET
    cfg = GAMES[game]
    GAME, PANELS = game, cfg["panels"]
    if "dataset" not in cfg:
        return
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    SAVE_DATASET = importlib.import_module(cfg["dataset"]).SaveDataset()
    DB = os.path.join(HERE, "data", cfg["db"])
    CSV = SAVE_DATASET.csv_path
    if not os.path.exists(CSV):
        sys.exit(f"no {cfg['label']} data yet ({CSV}).\n{cfg['missing']}")
    with open(os.path.join(STATIC, "index.html"), "rb") as fh:
        if INDEX_SCRIPT_TAG not in fh.read():
            sys.exit("static/index.html no longer loads app.js the expected way; "
                     "update INDEX_SCRIPT_TAG in server.py")


def game_config_script():
    """<script> tags a save-backed game adds to index.html: its settings for app.js
    (window.FM_GAME) and the save banner (static/savemode.js)."""
    cfg = {"game": GAME, "label": GAMES[GAME]["label"], "panels": PANELS}
    return (b"<script>window.FM_GAME = " + json.dumps(cfg).encode() + b";</script>\n"
            b'<script src="/static/savemode.js"></script>\n')


def ensure_db():
    sys.path.insert(0, HERE)
    if SAVE_DATASET:
        import import_db
        if not os.path.exists(DB) or os.path.getmtime(DB) < os.path.getmtime(CSV):
            print(f"building {GAME.upper()} player database...", flush=True)
            import_db.build(DB, CSV, force=True)
        _build_club_index()
        return
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
    if not PANELS["images"]:
        return None              # FM27 history must not label another game's players
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
    if not PANELS["history"] or not os.path.exists(HIST_DB):
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
# Sofascore form (matches/data/links.db + matches.db)
# --------------------------------------------------------------------------
def get_form(pid, limit=10):
    empty = {"player_id": pid, "linked": False, "matches": [],
             "summary": {"matches": 0, "minutes": 0, "goals": 0,
                         "assists": 0, "xg": None, "xa": None,
                         "rating_avg": None}, "form": []}
    if not PANELS["form"] or not (os.path.exists(FORM_DB) and os.path.exists(MATCH_DB)):
        return empty
    try:
        limit = max(1, min(50, int(limit)))
    except (TypeError, ValueError):
        limit = 10

    lcon = sqlite3.connect(FORM_DB, timeout=30)
    lcon.row_factory = sqlite3.Row
    try:
        link = lcon.execute(
            "SELECT * FROM player_links WHERE fm27_id=? "
            "ORDER BY confidence DESC, sofascore_player_id LIMIT 1", (pid,)
        ).fetchone()
    finally:
        lcon.close()
    if not link:
        return empty

    sid = link["sofascore_player_id"]
    mcon = sqlite3.connect(MATCH_DB, timeout=30)
    mcon.row_factory = sqlite3.Row
    try:
        pcols = {r[1] for r in mcon.execute("PRAGMA table_info(player_match_stats)")}
        xg = 'pms."expectedGoals"' if "expectedGoals" in pcols else "NULL"
        xa = 'pms."expectedAssists"' if "expectedAssists" in pcols else "NULL"
        rows = [dict(r) for r in mcon.execute(f"""
            SELECT m.match_id, m.match_date, m.league_code, m.season_label, m.round,
                   m.home_team_id, m.home_team, m.away_team_id, m.away_team,
                   m.home_score, m.away_score,
                   l.team_id, l.side, l.is_starter, l.minutes_played,
                   l.rating, l.goals, l.assists,
                   {xg} AS xg, {xa} AS xa
            FROM lineups l
            JOIN matches m ON m.match_id = l.match_id
            LEFT JOIN player_match_stats pms
              ON pms.match_id = l.match_id AND pms.player_id = l.player_id
            WHERE l.player_id = ? AND m.status = 'finished'
              AND COALESCE(l.minutes_played, 0) > 0
            ORDER BY m.match_date DESC, m.match_id DESC
            LIMIT ?
        """, (sid, limit))]
    finally:
        mcon.close()

    matches = []
    for r in rows:
        is_home = int(r["team_id"]) == int(r["home_team_id"])
        team_score = r["home_score"] if is_home else r["away_score"]
        opp_score = r["away_score"] if is_home else r["home_score"]
        if team_score is None or opp_score is None:
            continue
        result = "W" if team_score > opp_score else "D" if team_score == opp_score else "L"
        matches.append({
            "match_id": r["match_id"],
            "date": r["match_date"],
            "season": r["season_label"],
            "league": LEAGUE_NAMES.get(r["league_code"], r["league_code"]),
            "round": r["round"],
            "opponent": r["away_team"] if is_home else r["home_team"],
            "home": is_home,
            "team_score": team_score,
            "opp_score": opp_score,
            "result": result,
            "rating": r["rating"],
            "minutes": r["minutes_played"],
            "goals": r["goals"] or 0,
            "assists": r["assists"] or 0,
            "xg": round(float(r["xg"]), 2) if r["xg"] is not None else None,
            "xa": round(float(r["xa"]), 2) if r["xa"] is not None else None,
        })

    ratings = [m["rating"] for m in matches if m["rating"] is not None]
    summary = {
        "matches": len(matches),
        "minutes": int(sum(m["minutes"] or 0 for m in matches)),
        "goals": int(sum(m["goals"] for m in matches)),
        "assists": int(sum(m["assists"] for m in matches)),
        "xg": round(sum(m["xg"] for m in matches if m["xg"] is not None), 2)
              if any(m["xg"] is not None for m in matches) else None,
        "xa": round(sum(m["xa"] for m in matches if m["xa"] is not None), 2)
              if any(m["xa"] is not None for m in matches) else None,
        "rating_avg": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }
    return {
        "player_id": pid,
        "linked": True,
        "sofascore_id": sid,
        "sofascore_name": link["sofascore_name"],
        "confidence": link["confidence"],
        "matches": matches,
        "summary": summary,
        "form": [m["result"] for m in matches[:5]],
        "xg_available": any(m["xg"] is not None for m in matches),
        "xa_available": any(m["xa"] is not None for m in matches),
    }


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
        if SAVE_DATASET and filename == "index.html":
            body = body.replace(INDEX_SCRIPT_TAG, game_config_script() + INDEX_SCRIPT_TAG)
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
            if path == "/api/meta":
                self.send_json(get_meta())
            elif path == "/api/stats":
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
            elif path.startswith("/api/form/"):
                pid = path.rsplit("/", 1)[-1]
                self.send_json(get_form(pid, params.get("limit", 10)))
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

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        origin = self.headers.get("Origin")
        if origin and urllib.parse.urlparse(origin).netloc != self.headers.get("Host"):
            self.send_error(403)                 # only the explorer's own page may reload
        elif path == "/api/reload" and SAVE_DATASET:
            self.send_json(SAVE_DATASET.start_reload(build_db, refresh_caches))
        else:
            self.send_error(404)


def get_meta():
    """Dataset description for a save-backed game's banner; FM27's frontend does not call it."""
    if SAVE_DATASET and SAVE_DATASET.db_stale(DB):
        SAVE_DATASET.start_rebuild(build_db, refresh_caches)   # CSV rewritten by the CLI
    meta = {"game": GAME, "label": GAMES[GAME]["label"], "save_backed": bool(SAVE_DATASET),
            "players": get_filters()["stats"]["players"], "panels": PANELS}
    if SAVE_DATASET:
        meta.update(SAVE_DATASET.status())
    return meta


def build_db(csv_path):
    """Build the current game's player database from csv_path (atomic swap)."""
    import import_db
    import_db.build(DB, csv_path, force=True)


def refresh_caches():
    """Rebuild data derived from the player DB after it was replaced. The club index is
    rebuilt before the filter cache is dropped, so a request in between cannot cache
    filters computed from the old index."""
    global _filter_cache
    _build_club_index()
    with _filter_lock:
        _filter_cache = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--game", choices=list(GAMES), default="fm27",
                    help="dataset to serve (default fm27; fm24 = FM24 save files, see fm24/GUIDE.md)")
    args = ap.parse_args()
    configure(args.game)
    ensure_db()
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"{GAMES[GAME]['label']} Profiles Explorer: http://{args.host}:{args.port}")
    print("Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
