#!/usr/bin/env python3
"""Preflight: verify the offline suite is runnable before any work.

Zero-dependency. Checks Python version, that the package imports without
installing, and runs the full test suite.

Usage: python3 scripts/preflight.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    ok = True
    if sys.version_info < (3, 10):
        print(f"FAIL: Python >= 3.10 required, got {sys.version}")
        ok = False
    else:
        print(f"ok: Python {sys.version.split()[0]}")

    sys.path.insert(0, str(REPO / "src"))
    try:
        import agency_bench  # noqa: F401
        from agency_bench import harness, cost, tools, agent_stubs, tasks  # noqa: F401

        print(f"ok: agency_bench {agency_bench.__version__} imports (no install needed)")
        print(f"ok: paper pinned to arXiv:{agency_bench.PAPER_ARXIV_ID}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: package import: {exc}")
        ok = False

    # real-model must be inert without a key
    from agency_bench.real_model import RealModelNotConfigured, chat
    try:
        chat([{"role": "user", "content": "hi"}])
        print("note: AGENCY_ZAI_KEY present — real-model calls AVAILABLE (owner-gated)")
    except RealModelNotConfigured:
        print("ok: real-model client inert without key (offline-safe)")

    proc = subprocess.run(
        [sys.executable, "-m", "unittest"], cwd=REPO, capture_output=True, text=True, timeout=120
    )
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1] if (proc.stdout + proc.stderr).strip() else ""
    if proc.returncode == 0:
        print(f"ok: offline test suite green ({tail})")
    else:
        print(f"FAIL: test suite: {tail}")
        ok = False

    print("PREFLIGHT PASS" if ok else "PREFLIGHT FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
