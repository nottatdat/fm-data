"""FM24 save-backed dataset for the Profiles Explorer (used only with `server.py --game fm24`).

Owns everything that is specific to reading FM24 from save files while the explorer runs:
which save the data came from, whether FM is running, whether a newer save exists, and
rebuilding the explorer's database from a newer save (or from a CSV written by the
command-line extractor). The explorer supplies `build_db(csv_path)` and `after_swap()`;
this module never touches the game (it only stats files and runs `pgrep`).
"""
import datetime
import json
import os
import subprocess
import threading
import time

from fm24.save import parse_save

SETTLE_SECONDS = 1.0       # a save is ready once size+mtime are unchanged this long (E6)
PGREP_CACHE_SECONDS = 5.0  # the banner polls every 5 s per open tab; one pgrep is enough


class _Cached:
    """A value refreshed at most every `seconds`."""

    def __init__(self, fn, seconds):
        self._fn, self._seconds = fn, seconds
        self._value, self._at = None, 0.0
        self._lock = threading.Lock()

    def get(self):
        with self._lock:
            if time.monotonic() - self._at >= self._seconds:
                self._value, self._at = self._fn(), time.monotonic()
            return self._value


def _pgrep_fm():
    """True while FM24 runs (process `fm`, E7). Only the exit status is used: the game's
    command line carries launcher credentials and must never be logged."""
    try:
        return subprocess.run(["pgrep", "-x", "fm"], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, timeout=5).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


fm_running = _Cached(_pgrep_fm, PGREP_CACHE_SECONDS).get


class SaveDataset:
    def __init__(self, out_dir=parse_save.OUT, saves_dir=parse_save.SAVES):
        self.out_dir = out_dir
        self.saves_dir = saves_dir
        self.csv_path, self.meta_path = parse_save.output_paths(out_dir)
        self._lock = threading.Lock()              # guards _job and _seen
        self._job = {"state": "idle", "error": None, "save": None}
        self._seen = {}                            # path -> (size, mtime, first seen at)

    # ------------------------------------------------------------------ provenance
    def loaded(self):
        """Metadata of the data currently served (written by parse_save)."""
        try:
            with open(self.meta_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return {}

    def _settled_newest(self):
        """The newest career save if it has stopped changing for SETTLE_SECONDS, else None."""
        saves = parse_save.career_saves(self.saves_dir)
        if not saves:
            return None
        path = max(saves, key=os.path.getmtime)
        st = os.stat(path)
        key, now = (st.st_size, st.st_mtime), time.monotonic()
        with self._lock:
            prev = self._seen.get(path)
            if not prev or prev[:2] != key:
                self._seen[path] = (*key, now)
                return None
        return path if now - prev[2] >= SETTLE_SECONDS else None

    def newer_save(self):
        """A settled career save that is not the one loaded (newer, or another file)."""
        loaded = self.loaded()
        path = self._settled_newest()
        if not path:
            return None
        saved_at = datetime.datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds")
        if os.path.basename(path) == loaded.get("save") and saved_at <= (loaded.get("saved_at") or ""):
            return None
        return {"path": path, "save": os.path.basename(path), "saved_at": saved_at}

    def db_stale(self, db_path):
        """True when the CSV is newer than the database (e.g. parse_save.py was run by hand)."""
        try:
            return os.path.getmtime(self.csv_path) > os.path.getmtime(db_path)
        except OSError:
            return False

    def status(self):
        loaded = self.loaded()
        newer = self.newer_save()
        with self._lock:
            job = dict(self._job)
        return {
            "save": {k: loaded.get(k) for k in ("save", "saved_at", "in_game_date", "manager_club")},
            "unverified": loaded.get("columns", {}).get("unverified", []),
            "fm_running": fm_running(),
            "newer_save": {k: newer[k] for k in ("save", "saved_at")} if newer else None,
            "reload": job,
        }

    # ------------------------------------------------------------------ background jobs
    def start_reload(self, build_db, after_swap):
        """Re-extract the newest settled save and rebuild the database (one job at a time).
        On failure the previous CSV, metadata and database stay in place."""
        newer = self.newer_save()
        if not newer:
            return self._current()
        return self._start(newer["save"], lambda: self._reload_from(newer["path"], build_db, after_swap))

    def start_rebuild(self, build_db, after_swap):
        """Rebuild the database from the CSV already on disk (it is newer than the DB)."""
        return self._start(self.loaded().get("save"), lambda: self._rebuild(build_db, after_swap))

    def _current(self):
        with self._lock:
            return dict(self._job)

    def _start(self, save_name, work):
        with self._lock:
            if self._job["state"] == "running":
                return dict(self._job)
            self._job = {"state": "running", "error": None, "save": save_name}
        threading.Thread(target=self._finish, args=(save_name, work), daemon=True).start()
        return self._current()

    def _finish(self, save_name, work):
        try:
            work()
            result = {"state": "idle", "error": None, "save": save_name}
        except Exception as e:                      # any failure is shown in the banner
            result = {"state": "error", "error": str(e) or e.__class__.__name__, "save": save_name}
        with self._lock:
            self._job = result

    def _reload_from(self, path, build_db, after_swap):
        rows, meta = parse_save.extract(path)
        staged = parse_save.stage(rows, meta, self.out_dir)
        try:
            build_db(staged[0])                     # swaps the database in atomically
        except Exception:
            parse_save.discard(staged)             # old CSV, metadata and DB stay
            raise
        parse_save.commit(staged)                  # immediately: keep CSV/meta in step with the DB
        self._refresh(after_swap)

    def _rebuild(self, build_db, after_swap):
        build_db(self.csv_path)
        self._refresh(after_swap)

    @staticmethod
    def _refresh(after_swap):
        try:
            after_swap()
        except Exception as e:
            raise RuntimeError(f"new data is loaded, but refreshing the explorer failed: {e}") from e
