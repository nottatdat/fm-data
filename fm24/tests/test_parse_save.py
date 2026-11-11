#!/usr/bin/env python3
"""Tests for fm24/save/parse_save.py against a real save.

The decoding tests need a local save copy at fm24/work/e5/rennes_21dec.fm (game data,
never committed) and are skipped without it; fm24/tests/test_layouts.py covers the
decoders with synthetic bytes."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from fm24.save import parse_save as P  # noqa: E402

SAMPLE = os.path.join(ROOT, "fm24", "work", "e5", "rennes_21dec.fm")


def read(path):
    with open(path, "rb") as fh:
        return fh.read()


class SaveSelection(unittest.TestCase):
    def test_newest_career_save_ignoring_backups(self):
        with tempfile.TemporaryDirectory() as d:
            for i, name in enumerate(["Old.fm", "Career.fm", "last save overwrite backup.fm"]):
                path = os.path.join(d, name)
                open(path, "w").close()
                os.utime(path, (1000 + i, 1000 + i))
            open(os.path.join(d, "notes.txt"), "w").close()
            self.assertEqual(os.path.basename(P.default_save(d)), "Career.fm")

    def test_no_save_names_the_folder(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit) as cm:
                P.default_save(d)
            self.assertIn(d, str(cm.exception))


class PublishAndFailure(unittest.TestCase):
    def test_failed_extraction_keeps_previous_output(self):
        with tempfile.TemporaryDirectory() as d:
            P.publish([{"id": 1, "name": "A"}], {"save": "x.fm"}, d)
            before = {f: read(os.path.join(d, f)) for f in os.listdir(d)}
            bad = os.path.join(d, "corrupt.fm")
            with open(bad, "wb") as fh:
                fh.write(b"not a save")
            with mock.patch.object(sys, "argv", ["parse_save.py", "--save", bad, "--out", d]):
                with self.assertRaises(SystemExit) as cm:
                    P.main()
            self.assertIn("could not read", str(cm.exception))
            after = {f: read(os.path.join(d, f)) for f in os.listdir(d) if f != "corrupt.fm"}
            self.assertEqual(before, after)
            self.assertFalse([f for f in os.listdir(d) if f.endswith(".tmp")])


@unittest.skipUnless(os.path.exists(SAMPLE), "needs a local FM24 save copy")
class Decoding(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.save = os.path.join(cls.tmp, "Rennes.fm")
        shutil.copy2(SAMPLE, cls.save)
        cls.rows, cls.meta = P.extract(cls.save)
        cls.by_name = {r["name"]: r for r in cls.rows}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_identity_fields(self):
        r = self.by_name["Steve Mandanda"]
        self.assertEqual((r["dob"], r["age"], r["nat"], r["club"]), ("1985-03-28", 38, "France", "Stade Rennais FC"))
        r = self.by_name["Erling Haaland"]
        self.assertEqual((r["nat"], r["club"], r["posNat"]), ("Norway", "Manchester City", "ST"))
        self.assertEqual(self.by_name["Giorgi Mamardashvili"]["club"], "Valencia")

    def test_attributes_and_metadata(self):
        r = self.by_name["Mathis Lambourde"]
        self.assertEqual((r["Dribbling"], r["Agility"], r["LongThrows"], r["foot"]), (13, 13, 4, "Left"))
        self.assertEqual(self.meta["in_game_date"], "2023-12-21")
        r = self.by_name["Désiré Doué"]
        self.assertEqual((r["height"], r["expires"], r["wage"]), (182, "2026-06-30", 8675))
        self.assertEqual(self.by_name["Steve Mandanda"]["professionalism"], 17)
        self.assertIn("professionalism", self.meta["columns"]["unverified"])
        self.assertEqual(self.by_name["Guela Doué"]["value"], 1_310_205)      # FM shows £1.3M
        self.assertIn("value", self.meta["columns"]["unverified"])
        self.assertEqual(len({r["id"] for r in self.rows}), len(self.rows))
        self.assertLessEqual(min(r["age"] for r in self.rows), 16)      # youngest regens kept

    def test_save_changing_during_read_is_rejected(self):
        real = P.read_frames

        def touching(data, wanted=4):
            t = time.time() + 5
            os.utime(self.save, (t, t))
            return real(data, wanted)

        with mock.patch.object(P, "read_frames", touching):
            with self.assertRaises(P.SaveChanged):
                P.extract(self.save)


if __name__ == "__main__":
    unittest.main()
