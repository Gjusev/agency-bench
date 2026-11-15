"""Test package: make the zero-install src/ layout importable for
`python3 -m unittest` run from the repo root (no PYTHONPATH needed)."""

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
