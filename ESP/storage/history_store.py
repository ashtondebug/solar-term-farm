"""Append-only environmental history with a bounded memory window.

Points are sampled every ``history_interval_s`` (default 5 min).  The file is
rotated by size; old points are pruned from memory by age.  This keeps flash
writes low and makes a corrupt tail harmless: a bad line is skipped on load.
"""

import json
import os

MAX_BYTES = 256 * 1024


class HistoryStore:
    def __init__(self, root, logger=None, retention_days=7, max_bytes=MAX_BYTES):
        self.root = root.rstrip("/")
        self.logger = logger
        self.retention_s = int(retention_days) * 86400
        self.max_bytes = int(max_bytes)
        self.points = []
        self.path = self.root + "/history.jsonl"
        try:
            os.mkdir(self.root)
        except OSError:
            pass

    def load(self):
        self.points = []
        for name in ("history.jsonl.1", "history.jsonl"):
            path = self.root + "/" + name
            try:
                with open(path, "r") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            point = json.loads(line)
                        except Exception:
                            continue
                        if isinstance(point, dict) and "ts" in point:
                            self.points.append(point)
            except OSError:
                continue
        self._prune()
        return self.points

    def seed(self, points):
        self.points = list(points)
        self._prune()

    def append(self, point, now):
        self.points.append(point)
        self._prune(now)
        try:
            with open(self.path, "a") as handle:
                handle.write(json.dumps(point) + "\n")
        except Exception as exc:
            if self.logger:
                self.logger.warn("history append failed: %s", exc)
        self._rotate()

    def _prune(self, now=None):
        if now is None:
            try:
                import time

                epoch_offset = 946684800 if time.gmtime(0)[0] == 2000 else 0
                now = int(time.time()) + epoch_offset
            except Exception:
                now = 0
        cutoff = int(now) - self.retention_s
        self.points = [p for p in self.points if int(p.get("ts", 0)) >= cutoff]

    def _rotate(self):
        try:
            if os.stat(self.path)[6] <= self.max_bytes:
                return
        except OSError:
            return
        try:
            os.rename(self.path, self.path + ".1")
        except OSError:
            pass

    def range(self, seconds, now):
        cutoff = int(now) - int(seconds)
        return [p for p in self.points if int(p.get("ts", 0)) >= cutoff]

    def latest(self):
        return self.points[-1] if self.points else None
