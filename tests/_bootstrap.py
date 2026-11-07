"""Make ESP modules importable when tests run from the repository root."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ESP = os.path.join(ROOT, "ESP")
TESTS = os.path.dirname(__file__)

for path in (ESP, TESTS):
    if path not in sys.path:
        sys.path.insert(0, path)
