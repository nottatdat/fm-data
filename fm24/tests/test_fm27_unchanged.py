"""FM27 mode is unchanged: the explorer at the branch point with origin/master and the
explorer in this working tree return identical API responses on a synthetic FM27 fixture.

The UI half (page text, requested API paths, screenshots) needs a browser; run
`fm27_regression.py capture/compare` by hand for that.
"""
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from fm24.tests import fm27_fixture, fm27_regression  # noqa: E402


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def base_ref():
    try:
        return git("merge-base", "HEAD", "origin/master")
    except subprocess.CalledProcessError:
        return None


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@unittest.skipUnless(base_ref(), "needs origin/master in the git history")
class Fm27Unchanged(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.fixture = os.path.join(self.tmp, "fixture")
        fm27_fixture.build(self.fixture)

    def tree_from_git(self, name):
        dest = os.path.join(self.tmp, name)
        os.makedirs(dest)
        archive = subprocess.run(["git", "archive", base_ref(), "fm27/explorer"], cwd=ROOT,
                                 capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", dest], input=archive, check=True)
        return dest

    def tree_from_worktree(self, name):
        dest = os.path.join(self.tmp, name)
        shutil.copytree(os.path.join(ROOT, "fm27", "explorer"), os.path.join(dest, "fm27", "explorer"),
                        ignore=shutil.ignore_patterns("data", "assets", "shots", "__pycache__"))
        return dest

    def responses(self, root):
        fm27_fixture.install(self.fixture, root)
        port = free_port()
        env = dict(os.environ, FM_MATCH_DATA=os.path.join(self.tmp, "no-match-data"))
        proc = subprocess.Popen([sys.executable, "server.py", "--port", str(port)],
                                cwd=os.path.join(root, "fm27", "explorer"), env=env,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(600):
                try:
                    urllib.request.urlopen(base + "/api/stats", timeout=1)
                    break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.1)
            return {p: fm27_regression.fetch(base + p) for p in fm27_regression.REQUESTS}
        finally:
            proc.terminate()
            proc.wait()

    def test_api_responses_identical(self):
        before = self.responses(self.tree_from_git("before"))
        after = self.responses(self.tree_from_worktree("after"))
        for path in fm27_regression.REQUESTS:
            self.assertEqual(after[path], before[path], path)


if __name__ == "__main__":
    unittest.main()
