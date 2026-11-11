"""fm24/save/live.py: save settling, newer-save detection, background jobs (no game data)."""
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from fm24.save import live, parse_save  # noqa: E402


def read(path):
    with open(path) as fh:
        return fh.read()


def touch(path, mtime, size=10):
    with open(path, "wb") as fh:
        fh.write(b"x" * size)
    os.utime(path, (mtime, mtime))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saves = os.path.join(self.tmp.name, "games")
        self.out = os.path.join(self.tmp.name, "csv")
        os.makedirs(self.saves)
        os.makedirs(self.out)
        self.ds = live.SaveDataset(out_dir=self.out, saves_dir=self.saves)
        self.clock = 1000.0
        patcher = mock.patch.object(live.time, "monotonic", lambda: self.clock)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def loaded(self, save, saved_at):
        with open(self.ds.meta_path, "w") as fh:
            json.dump({"save": save, "saved_at": saved_at, "columns": {"unverified": ["ca"]}}, fh)
        with open(self.ds.csv_path, "w") as fh:
            fh.write("id\n1\n")

    def wait(self):
        for _ in range(200):
            if self.ds._current()["state"] != "running":
                return self.ds._current()
            time.sleep(0.01)
        self.fail("job did not finish")


class NewerSave(Fixture):
    def test_offered_only_after_settling_and_ignoring_backups(self):
        self.loaded("Career.fm", "2024-01-01T00:00:00")
        touch(os.path.join(self.saves, "Career.fm"), 1_800_000_000)
        touch(os.path.join(self.saves, "last save overwrite backup.fm"), 1_900_000_000)
        self.assertIsNone(self.ds.newer_save())          # first sighting: not settled yet
        self.clock += 0.5
        self.assertIsNone(self.ds.newer_save())
        self.clock += live.SETTLE_SECONDS
        self.assertEqual(self.ds.newer_save()["save"], "Career.fm")

    def test_still_growing_file_is_not_offered(self):
        self.loaded("Career.fm", "2024-01-01T00:00:00")
        path = os.path.join(self.saves, "Career.fm")
        for size in (10, 20, 30):
            touch(path, 1_800_000_000, size)
            self.assertIsNone(self.ds.newer_save())
            self.clock += live.SETTLE_SECONDS

    def test_the_loaded_save_is_not_offered_again(self):
        path = os.path.join(self.saves, "Career.fm")
        touch(path, 1_800_000_000)
        saved_at = live.datetime.datetime.fromtimestamp(1_800_000_000).isoformat(timespec="seconds")
        self.loaded("Career.fm", saved_at)
        self.ds.newer_save()
        self.clock += live.SETTLE_SECONDS
        self.assertIsNone(self.ds.newer_save())


class Jobs(Fixture):
    def setUp(self):
        super().setUp()
        self.loaded("Old.fm", "2024-01-01T00:00:00")
        touch(os.path.join(self.saves, "New.fm"), 1_800_000_000)
        self.ds.newer_save()
        self.clock += live.SETTLE_SECONDS

    def fake_extract(self, rows=None):
        def extract(path):
            return [{"id": 7, "name": "New"}], {"save": os.path.basename(path), "saved_at": "2027-01-01T00:00:00"}
        return mock.patch.object(parse_save, "extract", extract)

    def test_reload_swaps_data_and_refreshes(self):
        built, refreshed = [], []
        with self.fake_extract():
            self.ds.start_reload(lambda csv: built.append(read(csv)), lambda: refreshed.append(1))
            job = self.wait()
        self.assertEqual(job, {"state": "idle", "error": None, "save": "New.fm"})
        self.assertIn("New", built[0])
        self.assertEqual(refreshed, [1])
        self.assertEqual(self.ds.loaded()["save"], "New.fm")

    def test_failed_build_keeps_previous_data(self):
        before = read(self.ds.csv_path), read(self.ds.meta_path)
        def boom(csv):
            raise RuntimeError("disk full")
        with self.fake_extract():
            self.ds.start_reload(boom, lambda: None)
            job = self.wait()
        self.assertEqual((job["state"], job["error"]), ("error", "disk full"))
        self.assertEqual((read(self.ds.csv_path), read(self.ds.meta_path)), before)
        self.assertFalse([f for f in os.listdir(self.out) if f.endswith(".tmp")])

    def test_refresh_failure_says_the_data_is_loaded(self):
        def bad_refresh():
            raise RuntimeError("index")
        with self.fake_extract():
            self.ds.start_reload(lambda csv: None, bad_refresh)
            job = self.wait()
        self.assertIn("new data is loaded", job["error"])

    def test_one_job_at_a_time(self):
        gate = threading.Event()
        with self.fake_extract():
            first = self.ds.start_reload(lambda csv: gate.wait(5), lambda: None)
            second = self.ds.start_reload(lambda csv: None, lambda: None)
            self.assertEqual((first["state"], second["state"]), ("running", "running"))
            gate.set()
            self.wait()

    def test_stale_database_is_rebuilt_from_the_csv(self):
        db = os.path.join(self.tmp.name, "game.db")
        touch(db, 1_000_000_000)
        os.utime(self.ds.csv_path, (1_100_000_000, 1_100_000_000))
        self.assertTrue(self.ds.db_stale(db))
        built = []
        self.ds.start_rebuild(lambda csv: built.append(csv), lambda: None)
        self.wait()
        self.assertEqual(built, [self.ds.csv_path])


class FmRunning(unittest.TestCase):
    def test_pgrep_is_cached(self):
        calls = []
        cached = live._Cached(lambda: calls.append(1) or True, seconds=60)
        self.assertTrue(cached.get() and cached.get())
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
