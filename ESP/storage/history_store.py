"""Append-only environmental history with a bounded memory window.

Points are sampled every ``history_interval_s`` (default 5 min).  The file is
rotated by size; old points are pruned from memory by age.  This keeps flash
writes low and makes a corrupt tail harmless: a bad line is skipped on load.
"""

import json
import os

MAX_BYTES = 256 * 1024
MAX_POINTS = 256


class HistoryStore:
    def __init__(self, root, logger=None, retention_days=7, max_bytes=MAX_BYTES, max_points=MAX_POINTS):
        self.root = root.rstrip("/")
        self.logger = logger
        self.retention_s = int(retention_days) * 86400
        self.max_bytes = int(max_bytes)
        self.max_points = int(max_points)
        self.points = []
        self.path = self.root + "/history.jsonl"
        try:
            os.mkdir(self.root)
        except OSError:
            pass

    def _now(self):
        try:
            import time

            epoch_offset = 946684800 if time.gmtime(0)[0] == 2000 else 0
            return int(time.time()) + epoch_offset
        except Exception:
            return 0

    def load(self):
        self.points = []
        cutoff = self._now() - self.retention_s
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
                        if not isinstance(point, dict) or "ts" not in point:
                            continue
                        try:
                            if int(point.get("ts", 0)) < cutoff:
                                continue
                            if len(self.points) >= self.max_points:
                                del self.points[0]
                            self.points.append(point)
                        except MemoryError:
                            if self.logger:
                                self.logger.warn("history load memory limit; truncated")
                            break
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
            now = self._now()
        cutoff = int(now) - self.retention_s
        self.points = [p for p in self.points if int(p.get("ts", 0)) >= cutoff]
        if len(self.points) > self.max_points:
            self.points = self.points[-self.max_points :]

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
