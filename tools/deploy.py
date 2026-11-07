#!/usr/bin/env python3
"""Upload the firmware tree to a MicroPython board with mpremote.

This script is intentionally explicit about the remote layout: the contents of
``ESP/`` become the root of the board filesystem, and ``web/static`` is served
from ``/web/static``.  Requires ``mpremote`` (installed by install.bat).
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ESP = ROOT / "ESP"
STATIC = ESP / "web" / "static"


def collect_files():
    files = []
    for path in ESP.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        files.append((path, path.relative_to(ESP).as_posix()))
    for name in ("index.html", "app.js", "app.css"):
        path = STATIC / name
        if path.is_file():
            files.append((path, "web/static/%s" % name))
    return files


def remote_dirs(files):
    dirs = set()
    for _local, remote in files:
        parent = remote.rsplit("/", 1)[0] if "/" in remote else ""
        while parent:
            dirs.add(parent)
            parent = parent.rsplit("/", 1)[0] if "/" in parent else ""
    return sorted(dirs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="auto", help="mpremote connect target, e.g. COM6")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT / "tools"))
    import build_web

    if build_web.main() != 0:
        return 1

    files = collect_files()
    dirs = remote_dirs(files)
    print("files: %d, remote dirs: %s" % (len(files), ", ".join(dirs) or "(root)"))

    if args.dry_run:
        for local, remote in files:
            print("  %s -> :%s" % (local.relative_to(ROOT), remote))
        return 0

    if shutil.which("mpremote") is None:
        print("mpremote not found. Run install.bat, then retry.")
        return 2

    base = ["mpremote"]
    if args.port and args.port != "auto":
        base += ["connect", args.port]

    def run(command):
        print("+ %s" % " ".join(command))
        return subprocess.call(command)

    for directory in dirs:
        run(base + ["fs", "mkdir", ":%s" % directory])

    for local, remote in files:
        code = run(base + ["fs", "cp", str(local), ":%s" % remote])
        if code != 0:
            print("upload failed: %s" % remote)
            return code

    run(base + ["reset"])
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
