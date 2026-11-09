#!/usr/bin/env python3
"""Build the device web bundle from the canonical UI source.

The root ``agriverse_admin_dashboard.html`` stays the single authored copy of
the visual design.  This script copies it plus the app assets into
``ESP/web/static`` so the firmware serves exactly what was reviewed.
"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "ESP" / "web" / "static"
FILES = ("agriverse_admin_dashboard.html", "app.js", "app.css")
sys.path.insert(0, str(ROOT / "ESP"))


def build_solar_terms():
    from solar_terms.data import TERMS
    from solar_terms.culture import CULTURE

    terms = []
    for index, term in enumerate(TERMS):
        item = dict(term)
        item.update(CULTURE.get(term["name"], {}))
        item["index"] = index
        terms.append(item)
    payload = {
        "ok": True,
        "data": {"current": None, "time_synced": True, "terms": terms},
    }
    target = STATIC / "solar-terms.json"
    target.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return target


def main():
    missing = [name for name in FILES if not (ROOT / name).is_file()]
    if missing:
        print("missing UI source: %s" % ", ".join(missing))
        return 1
    STATIC.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / FILES[0], STATIC / "index.html")
    shutil.copyfile(ROOT / "app.js", STATIC / "app.js")
    shutil.copyfile(ROOT / "app.css", STATIC / "app.css")
    solar = build_solar_terms()
    terms = json.loads(solar.read_text(encoding="utf-8"))["data"]["terms"]
    embedded = "<script>window.__AGRI_TERMS__=%s;</script>" % json.dumps(
        terms, ensure_ascii=False, separators=(",", ":")
    )
    index_path = STATIC / "index.html"
    html = index_path.read_text(encoding="utf-8")
    html = html.replace(
        '<script src="app.js"></script>',
        embedded + '\n<script src="app.js"></script>',
    )
    index_path.write_text(html, encoding="utf-8")
    print("built %s" % STATIC)
    for name in ("index.html", "app.js", "app.css", solar.name):
        print("  %-18s %6d bytes" % (name, (STATIC / name).stat().st_size))
    return 0


if __name__ == "__main__":
    sys.exit(main())
