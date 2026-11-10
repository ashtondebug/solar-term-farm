import os
import tempfile
import unittest

import _bootstrap  # noqa: F401
from storage.history_store import HistoryStore


class HistoryStoreTests(unittest.TestCase):
    def test_append_and_range(self):
        root = tempfile.mkdtemp(prefix="agri-history-")
        store = HistoryStore(root)
        store.append({"ts": 1000, "temp": 20.0}, now=1000)
        store.append({"ts": 2000, "temp": 21.0}, now=2000)
        self.assertEqual(len(store.range(1500, now=2000)), 2)
        self.assertEqual(store.range(500, now=2000)[0]["ts"], 2000)

    def test_load_skips_bad_tail(self):
        root = tempfile.mkdtemp(prefix="agri-history-")
        path = os.path.join(root, "history.jsonl")
        now = int(__import__("time").time())
        with open(path, "w", encoding="utf-8") as handle:
            handle.write('{"ts": %d, "temp": 20}\n' % (now - 100))
            handle.write("{bad json}\n")
            handle.write('{"ts": %d, "temp": 21}\n' % (now - 50))
        store = HistoryStore(root)
        store.load()
        self.assertEqual(len(store.points), 2)

    def test_load_caps_memory_points(self):
        root = tempfile.mkdtemp(prefix="agri-history-")
        path = os.path.join(root, "history.jsonl")
        now = int(__import__("time").time())
        with open(path, "w", encoding="utf-8") as handle:
            for offset in range(400):
                handle.write('{"ts": %d, "temp": 20}\n' % (now - offset))
        store = HistoryStore(root, max_points=64)
        store.load()
        self.assertEqual(len(store.points), 64)
        self.assertEqual(store.points[-1]["ts"], now - 399)


if __name__ == "__main__":
    unittest.main()
