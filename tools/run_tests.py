#!/usr/bin/env python3
"""Run the host-side unit tests with the standard library."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    print("+ %s" % " ".join(command))
    return subprocess.call(command, cwd=str(ROOT))


if __name__ == "__main__":
    sys.exit(main())
