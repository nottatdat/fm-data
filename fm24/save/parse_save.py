#!/usr/bin/env python3
"""FM24 (macOS) save file -> fm24_players.csv + fm24_meta.json.

Usage:
    python3 fm24/save/parse_save.py [--save PATH] [--out DIR]

Reads the newest career save (FM's "last save overwrite backup*" files are ignored)
from the FM24 macOS saves folder unless --save is given. The save is only read, never
written, and the game is never touched. Output replaces the previous CSV + metadata
atomically, and only after a complete extraction.

The save is a container of zstd frames: frame 2 is the Load-Game summary (manager,
club, in-game date), frame 3 the main data block of plaintext binary records. The record
layouts are the "layout" constants below; the evidence for each is in
fm24/experiments/E1..E11. To decode a new column: add its offset next to the record it
belongs to, read it in the matching decode_* function, and drop it from nothing else
(blank columns are derived from the output).
Requires: zstandard, numpy.
"""
import argparse
import bisect
import csv
import datetime
import importlib.util
import json
import os
import re
import struct
import sys
import time

try:
    import numpy as np
    import zstandard
except ImportError as e:            # the explorer imports this too: exit with the fix, not a traceback
    raise SystemExit(f"FM24 support needs the '{e.name}' package. Install with:\n"
                     "    python3 -m pip install zstandard numpy") from e

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SAVES = os.environ.get("FM24_SAVES") or os.path.expanduser(
    "~/Library/Application Support/Sports Interactive/Football Manager 2024/games")
OUT = os.path.join(ROOT, "fm24", "csv")
BACKUP_PREFIX = "last save overwrite backup"
ZSTD = b"\x28\xb5\x2f\xfd"
NONE = 0xFFFFFFFF

POS = ["GK", "SW", "DL", "DC", "DR", "DM", "ML", "MC", "MR", "AML", "AMC", "AMR", "ST", "WBL", "WBR"]
ATTR = ["Crossing", "Dribbling", "Finishing", "Heading", "LongShots", "Marking", "OffTheBall", "Passing",
        "PenaltyTaking", "Tackling", "Vision", "Handling", "AerialReach", "CommandOfArea", "Communication",
        "Kicking", "Throwing", "Anticipation", "Decisions", "OneOnOnes", "Positioning", "Reflexes", "FirstTouch",
        "Technique", "LeftFoot", "RightFoot", "Flair", "Corners", "Teamwork", "WorkRate", "LongThrows",
        "Eccentricity", "RushingOut", "Punching", "Acceleration", "FreeKicks", "Strength", "Stamina", "Pace",
        "JumpingReach", "Leadership", "Dirtiness", "Balance", "Bravery", "Consistency", "Aggression", "Agility",
        "ImportantMatches", "InjuryProneness", "Versatility", "NaturalFitness", "Determination", "Composure",
        "Concentration"]
HIDDEN = ["Dirtiness", "Consistency", "ImportantMatches", "InjuryProneness", "Versatility"]
FEET = ("LeftFoot", "RightFoot")          # decoded for `foot`, not exported as columns
NATURAL, ACCOMPLISHED = 18, 15             # position rating thresholds (FM: 20 natural)

# --------------------------------------------------------------------------- layout
# Byte offsets inside records of the main block. Every decoder below uses these names;
# the E-notes in fm24/experiments hold the evidence.
#
# Dates (everywhere): u16 day-of-year in the low 9 bits (high bits are flags), u16 year. (E5)
DOY_MASK = 0x1FF
# Name dictionary entry: [u32 id][u32 len][utf-8]. Three dictionaries (first names,
# surnames, common names) each start at the same low id. (E1, E8)
NAME_DICT_MIN_RUN = 1000                   # shorter runs of such entries are other strings
# Person record: [first id]00[surname id]00[common id]00[u32 len][full name][dob]...
PERSON_NAT = 9                             # u32 nation index, after the 4-byte dob (E1)
PERSON_PERSONALITY = 17                    # 8 hidden personality bytes, 1-20 (E15)
PERSONALITY = ["adaptability", "ambition", "loyalty", "pressure", "professionalism",
               "sportsmanship", "temperament", "controversy"]
# Nation record: [u32 index][u32 uid][u32 uid] 00, in index order. (E11)
NATION_MIN = 100                           # a real nation table has ~250 entries
MAX_INDEX = 200000                         # club/team/nation indices are small numbers
# Club record, relative to its u32 index: [index][uid][uid] 00 [nat] ffffffff [nat2][nat]
# [u32][4 bytes] ff ff [u32 len][full name]. (E11)
CLUB_ZERO, CLUB_NAT, CLUB_NAME_MARK = 12, 13, 37
MAX_NATION_INDEX = 2000
# Team record, relative to the first copy of the team uid: (E11)
TEAM_NO, TEAM_CLUB_INDEX = -4, -18         # u32 team number, u32 club index (senior teams)
TEAM_TAIL = 0x0A                           # first byte after the uid pair
# B/youth teams carry their own name instead: [u32 len][name] ff [team no][uid][uid] (squad check)
TEAM_NAME_END = TEAM_NO - 1                # the ff byte before the team number
# Teams created during the career (e.g. a loanee's "Clermont 2" registration) have no uid
# pair: [u32 club index][10 zero bytes][u32 team no][u32 uid][u32 ?] 0a (squad check).
CAREER_TEAM = re.compile(rb"(.{4})\x00{10}(.{4}).{8}\x0a", re.S)
# Player header, written after a player's person record, relative to its marker byte:
HDR_UID = 10                               # u32 FM unique id, written twice (+10, +14)
HDR_FLAG = 18                              # record-variant byte
HDR_FLAGS = {1, 2, 3, 4, 8, 16}            # values seen on real headers; 0/5/7/108 are noise
HDR_CLUB_REF = -12                         # u32 club ref = team number + 1 (E11)
NO_CLUB_REFS = {0, 0xFFFFFFFF, 0xFF02FF}   # free agents / retired (club shown blank)
HDR_NEXT_RATINGS = 48                      # flag 2/3: the NEXT player's ratings start here
# The first header byte is a record-variant bitfield: several values occur in one save
# (0x58 for players from the shipped database, 0x40 for players created during the career,
# also 0x18, 0x78, 0x42, 0xc0). Real variants carry a real team's club ref in 25-91 % of
# candidates, byte noise in under 10 % (E8, squad check).
MARKER_MIN_SHARE, MARKER_MIN_VOTES = 0.25, 100
# Ratings record, relative to its first position rating (E1 round 4):
RAT_CA, RAT_PA = -23, -21                  # u16 each (unverified: FM shows only stars)
RAT_CLUB_REF = -8                          # u32 club ref, followed by u32 0
RAT_ATTR = 15                              # 15 position ratings (1-20), then 54 attributes
RAT_LEN = RAT_ATTR + len(ATTR)             # raw 0-100, display = (raw + 2) // 5
RAT_HEIGHT = 99                            # u16 cm (u16 kg weight at +97, not exported) (E12)
RAT_VALUE = RAT_LEN                        # u32 £ base valuation right after the attributes;
NO_VALUE = 0xFFFFFFFF                      # FM adjusts it for display (E14, fm-open-scout)
# Contract record: [u32 expiry date][u32 start date] ... [u32 club ref][u32 0][u32 weekly
# wage £]; found through the player's own club ref, the date pair within CONTRACT_DATES of
# it. FM displays the wage rounded (8,675 -> £8.75K). (E13)
CONTRACT_WAGE, CONTRACT_DATES, CONTRACT_SEARCH = 8, 200, 3000
MAX_WAGE = 2_000_000                       # £/week; larger values are not wages
RATINGS_SEARCH = 20000                     # how far before a person its ratings may sit


class SaveChanged(Exception):
    pass


# --------------------------------------------------------------------------- save file
def career_saves(saves_dir=SAVES):
    """Career saves in the folder (FM's 'last save overwrite backup*' files excluded)."""
    if not os.path.isdir(saves_dir):
        return []
    return [os.path.join(saves_dir, f) for f in os.listdir(saves_dir)
            if f.endswith(".fm") and not f.startswith(BACKUP_PREFIX)]


def default_save(saves_dir=SAVES):
    cands = career_saves(saves_dir)
    if not cands:
        sys.exit(f"no career save (.fm) found in {saves_dir}")
    return max(cands, key=os.path.getmtime)


def read_frames(data, wanted=4):
    """Decompress the first `wanted` zstd frames (the last one is the main block)."""
    frames, pos = [], 0
    for _ in range(wanted):
        o = data.find(ZSTD, pos)
        if o < 0:
            raise ValueError("not an FM24 save: missing zstd frames")
        obj = zstandard.ZstdDecompressor().decompressobj()
        frames.append(obj.decompress(data[o:]))
        pos = o + (len(data) - o - len(obj.unused_data))
    return frames


def to_date(raw, year):
    try:
        return datetime.date(year, 1, 1) + datetime.timedelta((raw & DOY_MASK) - 1)
    except (ValueError, OverflowError):
        return None


def game_date(summary):
    """[u32 len][manager][u32 len][club][u16 doy|flags][u16 year] in the summary frame."""
    for i in range(4, len(summary) - 16):
        l1 = struct.unpack_from("<I", summary, i - 4)[0]
        if not 2 <= l1 <= 60:
            continue
        j = i + l1
        l2 = struct.unpack_from("<I", summary, j)[0] if j + 4 <= len(summary) else 0
        if not 2 <= l2 <= 80 or j + 8 + l2 > len(summary):
            continue
        try:
            summary[i:j].decode()
            club = summary[j + 4:j + 4 + l2].decode()
        except UnicodeDecodeError:
            continue
        raw, year = struct.unpack_from("<HH", summary, j + 4 + l2)
        d = to_date(raw, year) if 1900 < year < 2200 else None
        if d:
            return d, club
    return None, ""


# --------------------------------------------------------------------------- tables
def name_dictionaries(b):
    """The three name dictionaries (first names, surnames, common names), in file order.
    Each is a run of [u32 id][u32 len][utf-8] entries with consecutive ids; all three
    start at the same id, so a person's fields must be looked up in their own dictionary."""
    runs, cur = [], None
    for m in re.finditer(rb"(.{4})([\x01-\x7f])\x00\x00\x00", b, re.S):
        i = m.start()
        n = b[i + 4]
        nid = struct.unpack_from("<I", b, i)[0]
        if i + 12 + n > len(b) or struct.unpack_from("<I", b, i + 8 + n)[0] != nid + 1:
            continue
        try:
            text = b[i + 8:i + 8 + n].decode()
        except UnicodeDecodeError:
            continue
        if cur is not None and i == cur["next"] and nid == cur["last"] + 1:
            cur["names"][nid] = text
            cur["last"], cur["next"] = nid, i + 8 + n
        else:
            if cur is not None and len(cur["names"]) > NAME_DICT_MIN_RUN:
                runs.append(cur)
            cur = {"names": {nid: text}, "last": nid, "next": i + 8 + n}
    if cur is not None and len(cur["names"]) > NAME_DICT_MIN_RUN:
        runs.append(cur)
    # Every dictionary starts at the same low id; a run that continues with higher ids
    # (e.g. names added during the career, after one irregular entry) extends the previous one.
    dictionaries = []
    for r in runs:
        if dictionaries and min(r["names"]) > max(dictionaries[-1]):
            dictionaries[-1].update(r["names"])
        else:
            dictionaries.append(dict(r["names"]))
    if len(dictionaries) != 3:
        raise ValueError(f"expected 3 name dictionaries, found {len(dictionaries)}")
    return dictionaries


def nation_table(b, known_uids):
    """index -> nation uid. Several tables share the [k][uid][uid]00 layout, so walk every
    chain that starts at index 1 and keep the one whose uids are known nation uids."""
    best, best_score = {}, 0.0
    for m in re.finditer(re.escape(struct.pack("<I", 1)) + rb"(.{4})\1\x00", b, re.S):
        uid = struct.unpack("<I", m.group(1))[0]
        if uid not in known_uids:
            continue
        table, pos, k = {1: uid}, m.start(), 2
        while k < 1000:
            rx = re.compile(re.escape(struct.pack("<I", k)) + rb"(.{4})\1\x00", re.S)
            nxt = next((x for x in rx.finditer(b, pos + 16, pos + 30000)
                        if uid < struct.unpack("<I", x.group(1))[0] < 1 << 31), None)
            if not nxt:
                break
            pos, uid = nxt.start(), struct.unpack("<I", nxt.group(1))[0]
            table[k] = uid
            k += 1
        score = sum(u in known_uids for u in table.values()) / len(table)
        if len(table) >= NATION_MIN and score > best_score:
            best, best_score = table, score
    return best


def _u32_views(b):
    for al in range(4):
        yield al, np.frombuffer(b[al:al + (len(b) - al) // 4 * 4], dtype="<u4")


def clubs(b):
    """club index -> (name, uid)."""
    out = {}
    for al, a in _u32_views(b):
        for i in np.nonzero((a[1:-2] == a[2:-1]) & (a[1:-2] > 0) & (a[:-3] < MAX_INDEX))[0]:
            p = al + 4 * int(i)
            if b[p + CLUB_ZERO] != 0:
                continue
            nat, ff, n2, n3 = struct.unpack_from("<IIII", b, p + CLUB_NAT)
            q = p + CLUB_NAME_MARK
            # The nation fields can differ (Welsh clubs in the English league: 139, 175, 139).
            if ff != NONE or max(nat, n2, n3) > MAX_NATION_INDEX or b[q:q + 2] != b"\xff\xff":
                continue
            ln = struct.unpack_from("<I", b, q + 2)[0]
            if not 1 <= ln <= 100:
                continue
            try:
                name = b[q + 6:q + 6 + ln].decode()
            except UnicodeDecodeError:
                continue
            ci, uid = struct.unpack_from("<II", b, p)
            out.setdefault(ci, (name, uid))
    return out


def team_own_name(b, p):
    """Name stored in a B/youth team record ([u32 len][name] ff right before the team
    number), or None."""
    end = p + TEAM_NAME_END
    if end < 8 or b[end] != 0xFF:
        return None
    for n in range(2, 61):
        start = end - n
        if struct.unpack_from("<I", b, start - 4)[0] == n:
            try:
                return b[start:end].decode()
            except UnicodeDecodeError:
                return None
    return None


def teams(b, club_by_index):
    """player club ref -> team name: the club's name for senior teams, the team's own
    name (e.g. "Reims 2") for B and youth teams."""
    out = {}
    for al, a in _u32_views(b):
        mask = (a[1:-2] == a[2:-1]) & (a[1:-2] > 0) & (a[:-3] < MAX_INDEX) & ((a[3:] & 0xFF) == TEAM_TAIL)
        for i in np.nonzero(mask)[0]:
            p = al + 4 * (int(i) + 1)
            ref = struct.unpack_from("<I", b, p + TEAM_NO)[0] + 1
            if ref in out:
                continue
            c = club_by_index.get(struct.unpack_from("<I", b, p + TEAM_CLUB_INDEX)[0])
            name = c[0] if c and c[1] == a[int(i) + 1] else team_own_name(b, p)
            if name:
                out[ref] = name
    # Career-created teams (no uid pair), named after their club.
    for m in CAREER_TEAM.finditer(b):
        team_no = struct.unpack("<I", m.group(2))[0]
        c = club_by_index.get(struct.unpack("<I", m.group(1))[0])
        if c and 0 < team_no < MAX_INDEX and team_no + 1 not in out:
            out[team_no + 1] = c[0]
    return out


# --------------------------------------------------------------------------- people
PERSON = re.compile(rb"(.{4})\x00(.{4})\x00(.{4})\x00([\x00-\x63])\x00\x00\x00", re.S)


def persons(b, dictionaries, latest_year):
    """People with a valid date of birth up to `latest_year` (derived from the save's
    in-game year, so regens born during a long career are kept)."""
    first_names, surnames, common_names = dictionaries
    out = []
    for m in PERSON.finditer(b):
        first, sur, common = (struct.unpack("<I", m.group(k))[0] for k in (1, 2, 3))
        if first not in first_names or sur not in surnames:
            continue
        end = m.end() + m.group(4)[0]
        if end + PERSON_NAT + 4 > len(b):
            continue
        raw, year = struct.unpack_from("<HH", b, end)
        dob = to_date(raw, year) if 1900 < year <= latest_year else None
        if not dob:
            continue
        display = common_names[common] if common in common_names else f"{first_names[first]} {surnames[sur]}"
        traits = b[end + PERSON_PERSONALITY:end + PERSON_PERSONALITY + len(PERSONALITY)]
        out.append({"pos": m.start(), "end": end, "name": display, "dob": dob,
                    "nat": struct.unpack_from("<I", b, end + PERSON_NAT)[0],
                    "personality": dict(zip(PERSONALITY, traits)) if traits and 1 <= min(traits) and max(traits) <= 20 else {}})
    return out


def player_headers(b, team_refs):
    """Offsets of player headers (layout HDR_*). A candidate is an id pair with a known
    variant byte (HDR_FLAGS) whose club ref is a plausible team index or a "no club" value; a
    marker value is accepted when enough of
    its candidates point at a real team (MARKER_MIN_SHARE / MARKER_MIN_VOTES), which
    separates record variants from byte noise. Requiring a sane club ref also keeps
    records of other types (garbage at HDR_CLUB_REF) from being taken for headers."""
    cands, votes, totals = [], {}, {}
    for al, a in _u32_views(b):
        hit = np.nonzero((a[:-1] == a[1:]) & (a[:-1] > 1000) & (a[:-1] != NONE))[0]
        for i in hit.tolist():
            o = al + 4 * i                              # first copy of the id
            h = o - HDR_UID
            if h + HDR_CLUB_REF < 0 or h + HDR_FLAG >= len(b) or b[h + HDR_FLAG] not in HDR_FLAGS \
                    or not plausible_uid(struct.unpack_from("<I", b, o)[0]):
                continue
            ref = struct.unpack_from("<I", b, h + HDR_CLUB_REF)[0]
            m = b[h]
            totals[m] = totals.get(m, 0) + 1
            if ref in team_refs:
                votes[m] = votes.get(m, 0) + 1
                cands.append(h)
            elif ref < MAX_INDEX or ref in NO_CLUB_REFS:
                cands.append(h)             # a team we cannot name, or no club: club left blank
    markers = {m for m, v in votes.items() if v >= MARKER_MIN_VOTES and v / totals[m] >= MARKER_MIN_SHARE}
    return sorted(h for h in cands if b[h] in markers)


def plausible_uid(v):
    """Reject values that are byte patterns rather than ids: an encoded date such as FM's
    empty date 01 00 6c 07 (day 1, year 1900), or four identical bytes."""
    if v <= 1000 or v == NONE:
        return False
    if 1900 <= v >> 16 <= 2200 and (v & DOY_MASK) <= 366:
        return False
    return len(set(v.to_bytes(4, "little"))) > 1


def valid_ratings(b, s):
    """A plausible ratings record at s: every position 1-20 with a natural-ish best
    position, every raw attribute 0-100."""
    pos, attrs = b[s:s + RAT_ATTR], b[s + RAT_ATTR:s + RAT_LEN]
    return len(attrs) == len(ATTR) and min(pos) >= 1 and ACCOMPLISHED <= max(pos) <= 20 and max(attrs) <= 100


def find_ratings(b, lo, hi, club_ref):
    """Start of the player's ratings record: the last [club ref][u32 0] in [lo, hi) that is
    followed by valid ratings. Linking by club ref is what makes this robust: after a
    flag-1 header the ratings are not at a fixed distance (E1 round 4)."""
    key = struct.pack("<II", club_ref, 0)
    i = hi
    while True:
        i = b.rfind(key, lo, i)
        if i < 0:
            return None
        if valid_ratings(b, i - RAT_CLUB_REF):
            return i - RAT_CLUB_REF
        if i == lo:
            return None


def find_contract(b, lo, hi, club_ref, today=None):
    """{expires, wage} of the player's current contract with this club ref in [lo, hi), or
    None. The key [club ref][u32 0] also starts ratings records, which are skipped; a
    contract that ended before the in-game date or an implausible wage is not current."""
    if club_ref in NO_CLUB_REFS:
        return None
    key = struct.pack("<II", club_ref, 0)
    i = hi
    while True:
        i = b.rfind(key, lo, i)
        if i < 0:
            return None
        if not valid_ratings(b, i - RAT_CLUB_REF):
            for q in range(i - 8, max(lo, i - CONTRACT_DATES), -1):     # nearest date pair before
                (r1, y1), (r2, y2) = struct.unpack_from("<HH", b, q), struct.unpack_from("<HH", b, q + 4)
                expires, start = to_date(r1, y1), to_date(r2, y2)
                if expires and start and 1900 < y2 <= y1 < 2200 and start < expires:
                    wage = struct.unpack_from("<I", b, i + CONTRACT_WAGE)[0]
                    if wage <= MAX_WAGE and (today is None or expires >= today):
                        return {"expires": expires.isoformat(), "wage": wage}
                    break
        if i == lo:
            return None


def decode_header(b, h):
    return {"uid": struct.unpack_from("<I", b, h + HDR_UID)[0],
            "club_ref": struct.unpack_from("<I", b, h + HDR_CLUB_REF)[0],
            "flag": b[h + HDR_FLAG]}


def decode_ratings(b, r):
    """CSV fields from a ratings record starting at r."""
    ratings = dict(zip(POS, b[r:r + RAT_ATTR]))
    attrs = {a: (v + 2) // 5 for a, v in zip(ATTR, b[r + RAT_ATTR:r + RAT_LEN])}
    natural = [x for x in POS if ratings[x] >= NATURAL]
    accomplished = [x for x in POS if ratings[x] >= ACCOMPLISHED]
    row = {"ca": struct.unpack_from("<H", b, r + RAT_CA)[0], "pa": struct.unpack_from("<H", b, r + RAT_PA)[0],
           "height": struct.unpack_from("<H", b, r + RAT_HEIGHT)[0] or None,
           "value": None if (v := struct.unpack_from("<I", b, r + RAT_VALUE)[0]) == NO_VALUE else v,
           "pos": ", ".join(accomplished), "posArr": "; ".join(accomplished), "posNat": "; ".join(natural),
           "foot": foot(attrs["LeftFoot"], attrs["RightFoot"])}
    row.update({a: v for a, v in attrs.items() if a not in FEET})
    return row


# --------------------------------------------------------------------------- assembly
def importer_columns():
    """The explorer importer's source columns (loaded by path: no sys.path changes)."""
    path = os.path.join(ROOT, "fm27", "explorer", "import_db.py")
    spec = importlib.util.spec_from_file_location("fm27_explorer_import_db", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cols = [c for c in mod.ALL_COLS if c not in ("club_display", "club_search")]
    missing = set(ATTR) - set(FEET) - set(cols)
    if missing:
        raise ValueError(f"attribute names unknown to the explorer importer: {sorted(missing)}")
    return cols


def foot(left, right):
    if left >= ACCOMPLISHED and right >= ACCOMPLISHED:
        return "Both"
    return "Left" if left > right else "Right"


YOUNGEST_AGE = 13          # FM regens arrive at 14-16

# Coverage floors: well below what tested saves give (84k-111k players, 76-91 % rated,
# 250 nations, ~78 % with a club), so normal careers pass but a format change that breaks
# one decoder step fails loudly instead of publishing mostly blank data.
MIN_PLAYERS, MIN_RATED_SHARE, MIN_NATIONS, MIN_CLUB_SHARE = 5000, 0.5, 100, 0.4


def check_coverage(players, rated, nations, with_club):
    problems = []
    if players < MIN_PLAYERS:
        problems.append(f"only {players} players")
    elif rated / players < MIN_RATED_SHARE:
        problems.append(f"ratings for only {rated}/{players} players")
    if nations < MIN_NATIONS:
        problems.append(f"nation table has {nations} entries")
    if players and with_club / players < MIN_CLUB_SHARE:
        problems.append(f"club for only {with_club}/{players} players")
    if problems:
        raise ValueError("save layout not recognised (" + "; ".join(problems) + ")")


def extract(save_path):
    t0 = time.time()
    st = os.stat(save_path)
    with open(save_path, "rb") as fh:
        data = fh.read()
    summary, b = read_frames(data)[2:4]
    del data
    today, manager_club = game_date(summary)
    dictionaries = name_dictionaries(b)
    with open(os.path.join(HERE, "nations_en.json"), encoding="utf-8") as fh:
        nation_names = {int(k): v for k, v in json.load(fh).items()}
    nat_uid = nation_table(b, set(nation_names))
    team_refs = teams(b, clubs(b))
    # No footballer is younger than 13; later "births" are false matches on other records.
    people = persons(b, dictionaries, (today.year if today else 2200) - YOUNGEST_AGE)
    headers = player_headers(b, team_refs)

    rows, seen = [], set()
    prev_header = 0                    # the previous player's header: this player's data follows it
    for k, p in enumerate(people):
        next_pos = people[k + 1]["pos"] if k + 1 < len(people) else len(b)
        i = bisect.bisect_left(headers, p["end"])
        own = headers[i] if i < len(headers) and headers[i] < next_pos else None
        if own is None:
            continue                                   # not a player (staff, official ...)
        hdr = decode_header(b, own)
        uid, ref = hdr["uid"], hdr["club_ref"]
        if uid in seen:
            continue
        seen.add(uid)
        dob = p["dob"]
        age = None
        if today:
            age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        nuid = nat_uid.get(p["nat"])
        row = {
            "id": uid, "name": p["name"], "dob": dob.isoformat(), "age": age,
            "birthYear": dob.year, "birthDoy": dob.timetuple().tm_yday,
            "nat": nation_names.get(nuid, ""), "natId": nuid or "",
            "club": team_refs.get(ref, ""), "gender": "0",
        }
        r = find_ratings(b, max(prev_header, p["pos"] - RATINGS_SEARCH), p["pos"], ref)
        if r is None and prev_header and b[prev_header + HDR_FLAG] in (2, 3) \
                and valid_ratings(b, prev_header + HDR_NEXT_RATINGS):
            # Ratings carrying a different club ref (e.g. loanees) sit right after the
            # previous player's header when that header is variant 2/3.
            r = prev_header + HDR_NEXT_RATINGS
        if r is not None:
            row.update(decode_ratings(b, r))
        contract = find_contract(b, max(prev_header, p["pos"] - CONTRACT_SEARCH), p["pos"], ref, today)
        if contract:
            row.update(contract)
        row.update(p["personality"])
        rows.append(row)
        prev_header = own

    cols = importer_columns()
    rated = sum(1 for r in rows if r.get("ca") is not None)
    check_coverage(len(rows), rated, len(nat_uid), sum(1 for r in rows if r["club"]))
    if os.stat(save_path).st_mtime != st.st_mtime or os.stat(save_path).st_size != st.st_size:
        raise SaveChanged("the save was still being written; save again in FM and retry")
    meta = {
        "save": os.path.basename(save_path),
        "saved_at": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "in_game_date": today.isoformat() if today else None,
        "manager_club": manager_club,
        "rows": len(rows),
        "columns": {"unverified": ["ca", "pa", "value"] + HIDDEN + PERSONALITY,
                    "blank": [c for c in cols if all(r.get(c) in (None, "") for r in rows)]},
        "stats": {"people": len(people), "player_headers": len(headers), "nations": len(nat_uid),
                  "rated": rated, "rated_share": round(rated / len(rows), 3),
                  "club_refs": len(team_refs), "seconds": round(time.time() - t0, 1)},
    }
    return rows, meta


def output_paths(out_dir=OUT):
    return os.path.join(out_dir, "fm24_players.csv"), os.path.join(out_dir, "fm24_meta.json")


def stage(rows, meta, out_dir=OUT):
    """Write CSV + meta next to their final names with a .tmp suffix; returns the tmp paths."""
    os.makedirs(out_dir, exist_ok=True)
    cols = importer_columns()
    csv_path, meta_path = output_paths(out_dir)
    with open(csv_path + ".tmp", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c, "")) for c in cols})
    with open(meta_path + ".tmp", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1, ensure_ascii=False)
    return csv_path + ".tmp", meta_path + ".tmp"


def commit(staged):
    """Swap staged files in: CSV first, meta last, so the metadata never describes data
    that is not in place."""
    for tmp in staged:
        os.replace(tmp, tmp[:-len(".tmp")])


def discard(staged):
    for tmp in staged:
        if os.path.exists(tmp):
            os.remove(tmp)


def publish(rows, meta, out_dir=OUT):
    staged = stage(rows, meta, out_dir)
    commit(staged)
    return output_paths(out_dir)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--save", help="path to an FM24 .fm save (default: newest career save)")
    ap.add_argument("--out", default=OUT, help="output directory (default: fm24/csv)")
    args = ap.parse_args()
    save = args.save or default_save()
    print(f"reading {save}", flush=True)
    try:
        rows, meta = extract(save)
    except SaveChanged as e:
        sys.exit(str(e))
    except (ValueError, zstandard.ZstdError) as e:
        sys.exit(f"could not read {os.path.basename(save)} as an FM24 save: {e}")
    csv_path, _ = publish(rows, meta, args.out)
    print(f"{meta['rows']:,} players -> {csv_path} (in-game {meta['in_game_date']}, "
          f"{meta['stats']['seconds']} s)")


if __name__ == "__main__":
    main()
