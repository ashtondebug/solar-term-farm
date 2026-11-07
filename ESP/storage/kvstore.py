"""Tiny JSON file store with an atomic replace.

The store is intentionally synchronous: files are small and writes happen at
most every few minutes.  Atomic replace is tmp-file + rename; if the target
exists and the port refuses to rename over it, the target is removed first.
"""

import json
import os


class KVStore:
    def __init__(self, root, logger=None):
        self.root = root.rstrip("/")
        self.logger = logger
        try:
            os.mkdir(self.root)
        except OSError:
            pass

    def path(self, name):
        return self.root + "/" + name

    def exists(self, name):
        try:
            os.stat(self.path(name))
            return True
        except OSError:
            return False

    def read_text(self, name, default=None):
        try:
            with open(self.path(name), "r") as handle:
                return handle.read()
        except Exception as exc:
            if self.logger:
                self.logger.warn("read %s failed: %s", name, exc)
            return default

    def write_text(self, name, text):
        target = self.path(name)
        temp = target + ".tmp"
        with open(temp, "w") as handle:
            handle.write(text)
            try:
                handle.flush()
            except Exception:
                pass
        try:
            os.rename(temp, target)
        except OSError:
            try:
                os.remove(target)
            except OSError:
                pass
            os.rename(temp, target)

    def read_json(self, name, default=None):
        text = self.read_text(name)
        if text is None:
            return default
        try:
            return json.loads(text)
        except Exception as exc:
            if self.logger:
                self.logger.error("corrupt json %s: %s", name, exc)
            return default

    def write_json(self, name, value):
        self.write_text(name, json.dumps(value))

    def backup(self, name):
        text = self.read_text(name)
        if text is None:
            return False
        self.write_text(name + ".bak", text)
        return True
