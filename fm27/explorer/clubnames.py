#!/usr/bin/env python3
"""Club display names, aliases and fuzzy search for the FM27 explorer.

FM27 uses short/licensing-friendly club names ("R. Madrid", "A. Madrid",
"Casciavit Milano", "FC Bayern München").  This module:

  * gives each club a human display name ("Real Madrid", "Atlético Madrid",
    "AC Milan", "Bayern Munich"),
  * generates search aliases (prefixes, acronyms, city exonyms, nicknames),
  * resolves a user query to one or more FM club names for the SQL filter.

No third-party dependencies.
"""
import difflib
import re
import unicodedata

# Curated display names for clubs whose FM name is abbreviated / unlicensed.
DISPLAY = {
    "R. Madrid": "Real Madrid",
    "A. Madrid": "Atlético Madrid",
    "A. Bilbao": "Athletic Bilbao",
    "FC Bayern München": "Bayern Munich",
    "Casciavit Milano": "AC Milan",
    "Blu-neri Milano": "Inter Milan",
    "Sport Lisboa e Benfica": "Benfica",
    "Futebol Clube do Porto": "FC Porto",
    "Sporting Clube de Portugal": "Sporting CP",
    "Sporting Clube de Braga": "Braga",
    "Associazione Sportiva Roma": "AS Roma",
    "AFC Ajax": "Ajax",
    "PSV": "PSV Eindhoven",
    "Feyenoord Rotterdam": "Feyenoord",
    "Wolverhampton Wanderers": "Wolves",
    "Brighton & Hove Albion": "Brighton",
    "1. FC Köln": "FC Köln",
    "Bayer 04 Leverkusen": "Bayer Leverkusen",
    "FC St. Gallen 1879": "St. Gallen",
    "FC Basel 1893": "Basel",
    "FC Luzern": "Luzern",
    "FC Zürich": "Zürich",
    "Sparta Prague": "Sparta Prague",
    "RSC Anderlecht": "Anderlecht",
    "U.S. Sassuolo Calcio": "Sassuolo",
    "FC Ingolstadt 04": "Ingolstadt",
    "Coruña": "Deportivo La Coruña",
    "Mamelodi Sundowns Football Club": "Mamelodi Sundowns",
    "S.S. Lazio Women 2015": "Lazio Women",
    "Club Atlético Boca Juniors": "Boca Juniors",
    "Club Atlético River Plate": "River Plate",
    "Racing Club de Avellaneda": "Racing Club",
    "Club Atlético Rosario Central": "Rosario Central",
    "Club Atlético Vélez Sarsfield": "Vélez Sarsfield",
    "Club Atlético San Lorenzo de Almagro": "San Lorenzo",
    "Club Atlético Independiente": "Independiente",
    "Club Atlético Newell's Old Boys": "Newell's Old Boys",
    "Club Atlético Talleres de Córdoba": "Talleres",
    "Club Atlético Huracán": "Huracán",
    "Club Atlético Lanús": "Lanús",
    "Club Atlético Belgrano": "Belgrano",
    "Club Estudiantes de La Plata": "Estudiantes",
    "Club de Gimnasia y Esgrima La Plata": "Gimnasia",
    "Club Social y Deportivo Defensa y Justicia": "Defensa y Justicia",
    "Asociación Atlética Argentinos Juniors": "Argentinos Juniors",
    "Club Atlético Tigre": "Tigre",
    "Club Atlético Colón": "Colón",
    "Club Atlético Unión": "Unión Santa Fe",
    "Club Atlético Banfield": "Banfield",
    "Club Atlético Patronato": "Patronato",
    "Club Atlético Central Córdoba": "Central Córdoba",
    "Club Atlético Sarmiento": "Sarmiento",
    "Club Atlético Platense": "Platense",
    "Club Atlético Barracas Central": "Barracas Central",
    "Club Atlético Arsenal": "Arsenal de Sarandí",
}

# Query aliases -> FM club name(s).  Keys are normalized (see normalize()).
CURATED = {
    "real madrid": ["R. Madrid"],
    "r madrid": ["R. Madrid"],
    "atletico madrid": ["A. Madrid"],
    "atletico": ["A. Madrid"],
    "atleti": ["A. Madrid"],
    "athletic bilbao": ["A. Bilbao"],
    "athletic": ["A. Bilbao"],
    "bayern munich": ["FC Bayern München"],
    "bayern munchen": ["FC Bayern München"],
    "bayern": ["FC Bayern München"],
    "psg": ["Paris Saint-Germain"],
    "paris sg": ["Paris Saint-Germain"],
    "paris saint germain": ["Paris Saint-Germain"],
    "ac milan": ["Casciavit Milano"],
    "milan": ["Casciavit Milano"],
    "inter": ["Blu-neri Milano"],
    "inter milan": ["Blu-neri Milano"],
    "internazionale": ["Blu-neri Milano"],
    "benfica": ["Sport Lisboa e Benfica"],
    "sl benfica": ["Sport Lisboa e Benfica"],
    "porto": ["Futebol Clube do Porto"],
    "fc porto": ["Futebol Clube do Porto"],
    "sporting": ["Sporting Clube de Portugal"],
    "sporting cp": ["Sporting Clube de Portugal"],
    "sporting lisbon": ["Sporting Clube de Portugal"],
    "roma": ["Associazione Sportiva Roma"],
    "as roma": ["Associazione Sportiva Roma"],
    "ajax": ["AFC Ajax"],
    "psv": ["PSV"],
    "psv eindhoven": ["PSV"],
    "feyenoord": ["Feyenoord Rotterdam"],
    "wolves": ["Wolverhampton Wanderers"],
    "wolverhampton": ["Wolverhampton Wanderers"],
    "spurs": ["Tottenham Hotspur"],
    "tottenham": ["Tottenham Hotspur"],
    "brighton": ["Brighton & Hove Albion"],
    "gladbach": ["Borussia Mönchengladbach"],
    "monchengladbach": ["Borussia Mönchengladbach"],
    "leverkusen": ["Bayer 04 Leverkusen"],
    "bayer leverkusen": ["Bayer 04 Leverkusen"],
    "cologne": ["1. FC Köln"],
    "koln": ["1. FC Köln"],
    "fc koln": ["1. FC Köln"],
    "boca": ["Club Atlético Boca Juniors"],
    "boca juniors": ["Club Atlético Boca Juniors"],
    "river": ["Club Atlético River Plate"],
    "river plate": ["Club Atlético River Plate"],
    "racing": ["Racing Club de Avellaneda"],
    "racing club": ["Racing Club de Avellaneda"],
    "velez": ["Club Atlético Vélez Sarsfield"],
    "velez sarsfield": ["Club Atlético Vélez Sarsfield"],
    "san lorenzo": ["Club Atlético San Lorenzo de Almagro"],
    "newells": ["Club Atlético Newell's Old Boys"],
    "newells old boys": ["Club Atlético Newell's Old Boys"],
    "talleres": ["Club Atlético Talleres de Córdoba"],
    "huracan": ["Club Atlético Huracán"],
    "lanus": ["Club Atlético Lanús"],
    "belgrano": ["Club Atlético Belgrano"],
    "estudiantes": ["Club Estudiantes de La Plata"],
    "gimnasia": ["Club de Gimnasia y Esgrima La Plata"],
    "defensa y justicia": ["Club Social y Deportivo Defensa y Justicia"],
    "argentinos juniors": ["Asociación Atlética Argentinos Juniors"],
    "tigre": ["Club Atlético Tigre"],
    "colon": ["Club Atlético Colón"],
    "union santa fe": ["Club Atlético Unión"],
    "banfield": ["Club Atlético Banfield"],
    "patronato": ["Club Atlético Patronato"],
    "central cordoba": ["Club Atlético Central Córdoba"],
    "sarmiento": ["Club Atlético Sarmiento"],
    "platense": ["Club Atlético Platense"],
    "barracas central": ["Club Atlético Barracas Central"],
    "arsenal sarandi": ["Club Atlético Arsenal"],
    "deportivo": ["Coruña"],
    "depor": ["Coruña"],
    "dep deportivo": ["Coruña"],
    "man city": ["Manchester City"],
    "manchester city": ["Manchester City"],
    "man utd": ["Manchester United"],
    "man united": ["Manchester United"],
    "manchester united": ["Manchester United"],
    "barcelona": ["Barcelona"],
    "juventus": ["Juventus"],
    "dortmund": ["Borussia Dortmund"],
    "lazio": ["S.S. Lazio Women 2015"],
    "napoli": ["Napoli Women"],
    "sevilla": ["Sevilla"],
    "villarreal": ["Villarreal"],
    "valencia": ["Valencia"],
    "newcastle": ["Newcastle United"],
    "aston villa": ["Aston Villa"],
    "liverpool": ["Liverpool"],
    "arsenal": ["Arsenal"],
    "chelsea": ["Chelsea"],
    "tottenham hotspur": ["Tottenham Hotspur"],
    "braga": ["Sporting Clube de Braga"],
    "anderlecht": ["RSC Anderlecht"],
    "basel": ["FC Basel 1893"],
    "zurich": ["FC Zürich"],
    "luzern": ["FC Luzern"],
    "st gallen": ["FC St. Gallen 1879"],
    "sparta prague": ["Sparta Prague"],
    "sassuolo": ["U.S. Sassuolo Calcio"],
    "ingolstadt": ["FC Ingolstadt 04"],
    "coruna": ["Coruña"],
    "deportivo la coruna": ["Coruña"],
}

CITY_EQUIV = {
    "munchen": ["munich"],
    "munich": ["munchen"],
    "milano": ["milan"],
    "milan": ["milano"],
    "lisboa": ["lisbon"],
    "lisbon": ["lisboa"],
    "koln": ["cologne"],
    "cologne": ["koln"],
    "roma": ["rome"],
    "rome": ["roma"],
    "napoli": ["naples"],
    "naples": ["napoli"],
    "torino": ["turin"],
    "turin": ["torino"],
    "wien": ["vienna"],
    "vienna": ["wien"],
    "zurich": ["zuerich"],
    "zuerich": ["zurich"],
}

# Tokens that are too generic to use as single-token aliases / acronym letters.
STOPWORDS = {
    "fc", "cf", "afc", "ac", "as", "ss", "ssc", "sc", "sl", "sv", "rsc",
    "us", "cd", "ca", "club", "atletico", "athletic", "real", "sport",
    "sporting", "futebol", "clube", "de", "do", "da", "e", "and", "the",
    "city", "united", "town", "county", "football", "calcio", "milan",
    "milano", "madrid", "juniors", "club",
}
PREFIX_TOKENS = {
    "club", "atletico", "athletic", "real", "fc", "cf", "afc", "ac", "as",
    "ss", "ssc", "sc", "sl", "sv", "rsc", "us", "cd", "ca", "1", "04",
    "futebol", "clube", "sport",
}

_EXTRA = {}
for alias, names in CURATED.items():
    for n in names:
        _EXTRA.setdefault(n, set()).add(alias)


def strip_accents(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c))


def normalize(s):
    s = strip_accents(s).lower().replace("&", " and ")
    s = re.sub(r"[.'’`]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def tokens(s):
    return normalize(s).split()


def display_name(name):
    if name in DISPLAY:
        return DISPLAY[name]
    d = name
    d = re.sub(r"^R\.\s+", "Real ", d)
    d = re.sub(r"^Club Atlético\s+", "", d, flags=re.I)
    d = re.sub(r"^Club Atletico\s+", "", d, flags=re.I)
    d = re.sub(r"^Club\s+", "", d, flags=re.I)
    d = re.sub(r"^Futebol Clube do\s+", "FC ", d, flags=re.I)
    d = re.sub(r"^Sport Lisboa e\s+", "", d, flags=re.I)
    d = re.sub(r"^Sporting Clube de\s+", "Sporting ", d, flags=re.I)
    d = re.sub(r"^Associazione Sportiva\s+", "AS ", d, flags=re.I)
    d = re.sub(r"^AFC\s+", "", d, flags=re.I)
    d = re.sub(r"^1\.\s*FC\s+", "FC ", d, flags=re.I)
    return d.strip() or name


def _strip_prefixes(norm):
    out = set()
    toks = norm.split()
    while toks:
        out.add(" ".join(toks))
        if toks[0] in PREFIX_TOKENS and len(toks) > 1:
            toks = toks[1:]
        else:
            break
    return out


def _acronym(toks):
    sig = [t for t in toks if t not in STOPWORDS and not t.isdigit()]
    if len(sig) >= 2:
        return "".join(t[0] for t in sig)
    return ""


def _city_variants(alias):
    out = set()
    toks = alias.split()
    for i, t in enumerate(toks):
        for eq in CITY_EQUIV.get(t, []):
            v = list(toks)
            v[i] = eq
            out.add(" ".join(v))
    return out


def aliases_for(name):
    out = set(_EXTRA.get(name, set()))
    for base in (name, display_name(name)):
        n = normalize(base)
        if not n:
            continue
        out.add(n)
        out |= _strip_prefixes(n)
        # leading "R." -> Real
        if n.startswith("r ") and len(n) > 2:
            out.add("real " + n[2:])
        # token aliases (distinctive words only)
        for t in n.split():
            if len(t) >= 4 and t not in STOPWORDS and not t.isdigit():
                out.add(t)
        a = _acronym(n.split())
        if len(a) >= 2:
            out.add(a)
    # city-exonym variants of every alias
    for a in list(out):
        out |= _city_variants(a)
    return {a for a in out if a}


def search_text(name):
    return " ".join(sorted(aliases_for(name)))


class ClubIndex:
    """Resolve user club queries to FM club names."""

    def __init__(self, rows):
        """rows: iterable of (club_name, player_count)."""
        self.items = []
        self.counts = {}
        self.exact = {}
        for name, count in rows:
            count = int(count or 0)
            disp = display_name(name)
            aliases = aliases_for(name)
            item = {
                "name": name,
                "display": disp,
                "count": count,
                "norm": normalize(name),
                "display_norm": normalize(disp),
                "toks": tokens(disp) or tokens(name),
                "aliases": aliases,
                "acronym": _acronym(tokens(disp)),
            }
            self.items.append(item)
            self.counts[name] = count
            for a in aliases | {item["norm"], item["display_norm"]}:
                self.exact.setdefault(a, set()).add(name)
        self.by_norm = {}
        for it in self.items:
            self.by_norm.setdefault(it["norm"], it["name"])

    def top(self, n=500):
        items = sorted(self.items, key=lambda it: (-it["count"], it["display"]))[:n]
        return [{"club": it["name"], "display": it["display"], "count": it["count"]}
                for it in items]

    def resolve(self, query, limit=40):
        q = normalize(query)
        if not q:
            return []
        # Curated aliases win (PSG, Man City, Milan, Inter, ...).
        if q in CURATED:
            names = sorted(set(CURATED[q]), key=lambda n: (-self.counts.get(n, 0), n))
            return names[:limit]
        exact = self.exact.get(q)
        if exact:
            return sorted(exact, key=lambda n: (-self.counts.get(n, 0), n))[:12]
        qt = q.split()
        scored = []
        for it in self.items:
            score = 0.0
            if q == it["norm"] or q == it["display_norm"]:
                score = 100
            elif q in it["aliases"]:
                score = 100
            elif q in it["norm"] or q in it["display_norm"]:
                score = 80
            else:
                matched = 0.0
                for t in qt:
                    best = 0.0
                    for ct in it["toks"]:
                        if t == ct:
                            best = max(best, 1.0)
                        elif len(t) >= 2 and (ct.startswith(t) or t.startswith(ct)):
                            best = max(best, 0.8)
                    matched += best
                ratio = matched / max(1, len(qt))
                if ratio >= 1.0:
                    score = 75
                elif ratio >= 0.5:
                    score = 40 + 30 * ratio
                if it["acronym"] and q == it["acronym"]:
                    score = max(score, 70)
            if score > 0:
                scored.append((score, it["count"], it["name"]))
        scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
        if not scored:
            if len(q) >= 4:
                for norm in difflib.get_close_matches(q, list(self.by_norm), n=limit, cutoff=0.8):
                    n = self.by_norm[norm]
                    if n not in scored:
                        scored.append((50, self.counts.get(n, 0), n))
            if not scored:
                return []
        max_score = scored[0][0]
        if max_score < 70:
            return []
        threshold = max(70, max_score - 5)
        names = []
        for score, _, n in scored:
            if score < threshold:
                break
            if n not in names:
                names.append(n)
            if len(names) >= 12:
                break
        return names[:limit]
