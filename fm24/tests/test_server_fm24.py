"""The Profiles Explorer in `--game fm24` mode, run from a temporary copy with a tiny CSV.

No game data and no FM24 saves folder are used: FM24_SAVES points at an empty folder.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from fm24.save import parse_save  # noqa: E402

EXPLORER_FILES = ["server.py", "import_db.py", "import_history.py", "clubnames.py", "static"]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def make_tree(dest):
    """Copy the explorer and the fm24 package into dest (a stand-in repository root)."""
    os.makedirs(os.path.join(dest, "fm27", "explorer"))
    for name in EXPLORER_FILES:
        src = os.path.join(ROOT, "fm27", "explorer", name)
        dst = os.path.join(dest, "fm27", "explorer", name)
        (shutil.copytree if os.path.isdir(src) else shutil.copy2)(src, dst)
    shutil.copytree(os.path.join(ROOT, "fm24", "save"), os.path.join(dest, "fm24", "save"),
                    ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(os.path.join(ROOT, "fm24", "__init__.py"), os.path.join(dest, "fm24", "__init__.py"))


def publish(dest, names, save="Career.fm"):
    rows = [{"id": 100 + i, "name": n, "club": "Stade Rennais FC", "nat": "France", "age": 20,
             "gender": "0", "ca": 120, "Finishing": 12} for i, n in enumerate(names)]
    meta = {"save": save, "saved_at": "2024-01-07T12:00:00", "in_game_date": "2024-01-07",
            "manager_club": "Rennes", "columns": {"unverified": ["ca", "pa"]}}
    parse_save.publish(rows, meta, os.path.join(dest, "fm24", "csv"))


class ExplorerFm24(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.root = os.path.join(cls.tmp, "repo")
        make_tree(cls.root)
        cls.saves = os.path.join(cls.tmp, "games")
        os.makedirs(cls.saves)
        cls.env = dict(os.environ, FM24_SAVES=cls.saves)
        cls.explorer = os.path.join(cls.root, "fm27", "explorer")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def start(self):
        port = free_port()
        proc = subprocess.Popen([sys.executable, "server.py", "--game", "fm24", "--port", str(port)],
                                cwd=self.explorer, env=self.env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.terminate)
        base = f"http://127.0.0.1:{port}"
        for _ in range(300):
            try:
                urllib.request.urlopen(base + "/api/stats", timeout=1)
                return base
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.1)
        self.fail("server did not start")

    def get(self, base, path):
        with urllib.request.urlopen(base + path, timeout=10) as r:
            body = r.read()
        return json.loads(body) if path.startswith("/api") else body.decode()

    def post(self, base, path, origin=None):
        req = urllib.request.Request(base + path, data=b"", method="POST")
        if origin:
            req.add_header("Origin", origin)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, None

    def test_1_missing_csv_exits_with_instructions(self):
        p = subprocess.run([sys.executable, "server.py", "--game", "fm24"], cwd=self.explorer,
                           env=self.env, capture_output=True, text=True, timeout=60)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("parse_save.py", p.stderr)

    def test_2_fm24_mode(self):
        publish(self.root, ["Mathis Lambourde", "Désiré Doué"])
        base = self.start()
        meta = self.get(base, "/api/meta")
        self.assertEqual((meta["label"], meta["players"], meta["save"]["save"]), ("FM24", 2, "Career.fm"))
        self.assertEqual(meta["panels"], {"history": False, "form": False, "images": False})
        page = self.get(base, "/")
        self.assertLess(page.index("window.FM_GAME"), page.index('src="/static/savemode.js"'))
        self.assertLess(page.index('src="/static/savemode.js"'), page.index('src="/static/app.js"'))
        self.assertEqual(self.get(base, "/api/history/100")["records"], [])
        self.assertFalse(self.get(base, "/api/form/100")["linked"])
        self.assertEqual(self.post(base, "/api/reload")[1]["state"], "idle")     # nothing newer
        self.assertEqual(self.post(base, "/api/reload", origin="http://evil.example")[0], 403)

        # The CLI rewrites the CSV while the server runs: the next status poll rebuilds the DB.
        time.sleep(1.1)                                                   # newer mtime than the DB
        publish(self.root, ["Mathis Lambourde", "Désiré Doué", "Guela Doué"])
        self.get(base, "/api/meta")
        for _ in range(100):
            if self.get(base, "/api/meta")["reload"]["state"] == "idle" and \
                    self.get(base, "/api/stats")["players"] == 3:
                break
            time.sleep(0.1)
        self.assertEqual(self.get(base, "/api/players?q=Guela")["total"], 1)


if __name__ == "__main__":
    unittest.main()
