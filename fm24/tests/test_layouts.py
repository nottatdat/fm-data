"""Decoders in fm24/save/parse_save.py on synthetic bytes built from its layout constants.

These pin the record layouts documented in parse_save.py (evidence: fm24/experiments)
without any game data. If FM changes a layout, decoding a real save fails the coverage
check; these tests show which decoder's assumptions were broken.
"""
import datetime
import os
import struct
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from fm24.save import parse_save as P  # noqa: E402

u32 = lambda v: struct.pack("<I", v)  # noqa: E731
u16 = lambda v: struct.pack("<H", v)  # noqa: E731


def name_run(start_id, names):
    out = b""
    for i, n in enumerate(names):
        raw = n.encode()
        out += u32(start_id + i) + u32(len(raw)) + raw
    return out


def date(d):
    return u16(d.timetuple().tm_yday | 0x8000) + u16(d.year)      # high bits are flags


class Dates(unittest.TestCase):
    def test_day_of_year_ignores_flag_bits(self):
        self.assertEqual(P.to_date(355 | 0xFE00, 2023), datetime.date(2023, 12, 21))


class NameDictionaries(unittest.TestCase):
    def test_three_dictionaries_and_split_run_merged(self):
        n = P.NAME_DICT_MIN_RUN + 5
        first = [f"First{i}" for i in range(n)]
        blob = (name_run(128, first) + b"\xff" * 9                   # irregular entry
                + name_run(128 + n + 1, [f"Late{i}" for i in range(n)])   # continues first names
                + b"\x00" * 7 + name_run(128, [f"Sur{i}" for i in range(n)])
                + b"\x00" * 7 + name_run(128, [f"Com{i}" for i in range(n)]) + b"\x00" * 16)
        f, s, c = P.name_dictionaries(blob)
        self.assertEqual((f[128], s[128], c[128]), ("First0", "Sur0", "Com0"))
        self.assertEqual(f[128 + n + 1], "Late0")                    # merged continuation

    def test_wrong_number_of_dictionaries_fails_loudly(self):
        with self.assertRaises(ValueError):
            P.name_dictionaries(name_run(128, [f"N{i}" for i in range(P.NAME_DICT_MIN_RUN + 5)]))


class Nations(unittest.TestCase):
    def test_chain_with_known_uids_wins_over_decoy(self):
        known = set(range(5000, 5000 + 3 * 400, 3))
        def chain(uids):
            return b"".join(u32(k) + u32(u) + u32(u) + b"\x00" + b"\x11" * 20 for k, u in enumerate(uids, 1))
        decoy = chain(range(10, 10 + 2 * 150, 2))                   # same layout, unknown uids
        real = chain(sorted(known)[:150])
        table = P.nation_table(decoy + b"\x00" * 64 + real, known)
        self.assertEqual(len(table), 150)
        self.assertEqual(table[1], min(known))


def club_record(index, uid, nat, name, nat2=None):
    raw = name.encode()
    return (u32(index) + u32(uid) + u32(uid) + b"\x00" + u32(nat) + u32(P.NONE) + u32(nat2 or nat) + u32(nat)
            + u32(7) + b"\x02\x00\x00\x00" + b"\xff\xff" + u32(len(raw)) + raw)


def team_record(club_index, team_no, uid):
    filler = b"\x01" * (-P.TEAM_CLUB_INDEX - 4 + P.TEAM_NO)          # up to the team number
    return u32(club_index) + filler + u32(team_no) + u32(uid) + u32(uid) + u16(P.TEAM_TAIL) + b"\x00\x00"


class ClubsAndTeams(unittest.TestCase):
    def test_career_created_team_named_after_its_club(self):
        clubs = {1400: ("Clermont Foot 63", 1991)}
        rec = u32(1400) + b"\x00" * 10 + u32(41713) + u32(2000341239) + u32(6650) + bytes([P.TEAM_TAIL, 0x10])
        self.assertEqual(P.teams(b"\x01" * 5 + rec + b"\x01" * 8, clubs), {41714: "Clermont Foot 63"})

    def test_b_team_uses_its_own_name(self):
        name = b"Rennes 2"
        rec = u32(len(name)) + name + b"\xff" + u32(25795) + u32(48038850) * 2 + bytes([P.TEAM_TAIL, 0x10, 0, 0])
        self.assertEqual(P.teams(b"\x00" * 8 + rec + b"\x00" * 16, {}), {25796: "Rennes 2"})

    def test_player_club_ref_is_team_number_plus_one(self):
        blob = (b"\x00" * 3 + club_record(430, 678, 139, "Manchester City") + b"\x00" * 17
                + club_record(559, 881, 143, "Stade Rennais FC") + b"\x00" * 40
                + club_record(362, 624, 139, "Cardiff City", nat2=175) + b"\x00" * 40   # Welsh club, English league
                + team_record(430, 556, 678) + b"\x00" * 9 + team_record(559, 737, 881) + b"\x00" * 16)
        clubs = P.clubs(blob)
        self.assertEqual(clubs[430], ("Manchester City", 678))
        self.assertEqual(clubs[362], ("Cardiff City", 624))
        teams = P.teams(blob, clubs)
        self.assertEqual((teams[557], teams[738]), ("Manchester City", "Stade Rennais FC"))


def header(marker, uid, club_ref, flag=2):
    h = bytearray(64)
    h[0] = marker
    h[P.HDR_UID:P.HDR_UID + 8] = u32(uid) * 2
    h[P.HDR_FLAG] = flag
    return u32(club_ref) + b"\x00" * (-P.HDR_CLUB_REF - 4) + bytes(h)


class PlayerHeaders(unittest.TestCase):
    def test_record_variants_accepted_noise_rejected(self):
        refs = {557: "Manchester City", 738: "Stade Rennais FC"}
        n = P.MARKER_MIN_VOTES
        real = b"".join(header(0x58, 29_000_000 + i, 557) for i in range(n))      # shipped-DB players
        career = b"".join(header(0x40, 2_000_100_000 + i, 738) for i in range(n))  # created in-career
        noise = b"".join(header(0x07, 31_000_000 + i, 9000 + i) for i in range(3 * n))
        noise += header(0x58, 32_000_000, 1_743_847_440)        # other record type: garbage club ref
        found = P.player_headers(real + noise + career, refs)
        blob = real + noise + career
        self.assertEqual({blob[h] for h in found}, {0x58, 0x40})
        self.assertEqual(len(found), 2 * n)                       # garbage-ref record rejected
        self.assertEqual(P.decode_header(blob, found[0]), {"uid": 29_000_000, "club_ref": 557, "flag": 2})

    def test_byte_patterns_are_not_uids(self):
        self.assertFalse(P.plausible_uid(0x076C0001))      # FM's empty date, 1/1900
        self.assertFalse(P.plausible_uid(0x01010101))
        self.assertTrue(P.plausible_uid(29179241))


def ratings_record(club_ref, ca, pa, positions, raw_attrs, height=180):
    pre = bytearray(-P.RAT_CA)
    pre[0:2], pre[2:4] = u16(ca), u16(pa)                  # at RAT_CA / RAT_PA
    pre[P.RAT_CLUB_REF - P.RAT_CA:] = u32(club_ref) + u32(0)
    post = bytearray(P.RAT_HEIGHT + 2 - P.RAT_LEN)
    post[P.RAT_VALUE - P.RAT_LEN:P.RAT_VALUE - P.RAT_LEN + 4] = u32(13_239_000)
    post[P.RAT_HEIGHT - P.RAT_LEN:] = u16(height)
    return bytes(pre) + bytes(positions) + bytes(raw_attrs) + bytes(post)


class Ratings(unittest.TestCase):
    def test_find_by_club_ref_and_decode(self):
        positions = [1] * 15
        positions[P.POS.index("AMR")], positions[P.POS.index("ST")] = 20, 18
        raw = [50] * len(P.ATTR)
        raw[P.ATTR.index("Dribbling")] = 62                 # display (62 + 2) // 5 = 12
        raw[P.ATTR.index("LeftFoot")] = 100                 # foot ratings drive `foot`
        raw[P.ATTR.index("RightFoot")] = 40
        decoy = ratings_record(600, 1, 1, positions, raw)  # another club's record
        rec = ratings_record(738, 116, 156, positions, raw)
        blob = b"\x00" * 10 + decoy + b"\x00" * 30 + rec + b"\x00" * 40
        r = P.find_ratings(blob, 0, len(blob), 738)
        row = P.decode_ratings(blob, r)
        self.assertEqual((row["ca"], row["pa"]), (116, 156))
        self.assertEqual((row["posNat"], row["posArr"], row["foot"]), ("AMR; ST", "AMR; ST", "Left"))
        self.assertEqual(row["Dribbling"], 12)
        self.assertEqual(row["height"], 180)
        self.assertEqual(row["value"], 13_239_000)
        self.assertNotIn("LeftFoot", row)

    def test_invalid_ratings_are_skipped(self):
        bad = ratings_record(738, 1, 1, [0] * 15, [50] * len(P.ATTR))     # position 0 is invalid
        self.assertIsNone(P.find_ratings(bad, 0, len(bad), 738))


class Contracts(unittest.TestCase):
    def contract(self, club_ref, expires, start, wage, gap=60):
        return date(expires) + date(start) + b"\x03" * gap + u32(club_ref) + u32(0) + u32(wage) + b"\x00" * 8

    def test_current_contract_found_through_club_ref(self):
        blob = (b"\x00" * 16 + self.contract(738, datetime.date(2026, 6, 30), datetime.date(2021, 7, 1), 8675)
                + b"\x00" * 32)
        c = P.find_contract(blob, 0, len(blob), 738, today=datetime.date(2023, 12, 21))
        self.assertEqual(c, {"expires": "2026-06-30", "wage": 8675})

    def test_expired_or_implausible_contract_is_not_current(self):
        today = datetime.date(2023, 12, 21)
        old = self.contract(738, datetime.date(2022, 6, 30), datetime.date(2019, 7, 1), 5000)
        bad = self.contract(738, datetime.date(2026, 6, 30), datetime.date(2021, 7, 1), 0xFFFFFFFF)
        for blob in (old, bad):
            self.assertIsNone(P.find_contract(b"\x00" * 8 + blob, 0, len(blob) + 8, 738, today))

    def test_free_agents_have_no_contract(self):
        self.assertIsNone(P.find_contract(b"\x00" * 64, 0, 64, 0))


class People(unittest.TestCase):
    def test_person_record_and_age_cap(self):
        dicts = ({200: "Mathis"}, {300: "Lambourde"}, {})
        traits = bytes([13, 13, 13, 12, 13, 14, 11, 5])
        def person(dob, nat):
            return (u32(200) + b"\x00" + u32(300) + b"\x00" + u32(P.NONE) + b"\x00" + u32(0)
                    + date(dob) + b"\x00" * (P.PERSON_NAT - 4) + u32(nat)
                    + b"\x00" * (P.PERSON_PERSONALITY - P.PERSON_NAT - 4) + traits + b"\x00" * 8)
        blob = b"\x00" + person(datetime.date(2006, 1, 9), 143) + person(datetime.date(2036, 1, 1), 143)
        people = P.persons(blob, dicts, latest_year=2023 - P.YOUNGEST_AGE)
        self.assertEqual([(p["name"], p["dob"], p["nat"]) for p in people],
                         [("Mathis Lambourde", datetime.date(2006, 1, 9), 143)])
        self.assertEqual(people[0]["personality"]["sportsmanship"], 14)


class Coverage(unittest.TestCase):
    def test_broken_decodes_fail_loudly(self):
        P.check_coverage(80000, 70000, 250, 60000)
        for args in [(100, 90, 250, 80), (80000, 1000, 250, 60000), (80000, 70000, 3, 60000)]:
            with self.assertRaises(ValueError):
                P.check_coverage(*args)

    def test_attribute_names_match_the_explorer_importer(self):
        cols = P.importer_columns()
        self.assertTrue(set(P.ATTR) - set(P.FEET) <= set(cols))


if __name__ == "__main__":
    unittest.main()
