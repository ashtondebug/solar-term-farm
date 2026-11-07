#!/usr/bin/env python3
"""Build the device web bundle from the canonical UI source.

The root ``agriverse_admin_dashboard.html`` stays the single authored copy of
the visual design.  This script copies it plus the app assets into
``ESP/web/static`` so the firmware serves exactly what was reviewed.
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "ESP" / "web" / "static"
FILES = ("agriverse_admin_dashboard.html", "app.js", "app.css")


def main():
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        print("missing UI source: %s" % ", ".join(missing))
        return 1
    STATIC.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / FILES[0], STATIC / "index.html")
    shutil.copyfile(ROOT / "app.js", STATIC / "app.js")
    shutil.copyfile(ROOT / "app.css", STATIC / "app.css")
    print("built %s" % STATIC)
    for name in ("index.html", "app.js", "app.css"):
        print("  %-12s %6d bytes" % (name, (STATIC / name).stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
