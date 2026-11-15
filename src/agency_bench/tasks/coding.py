"""Coding-style task: fix one wrong value in a config file without touching
the rest.

Mirrors the paper's coding task class (SWE-bench-style local edit). The
wasteful strategy re-reads and rewrites the whole file; the frugal strategy
greps for the target line and writes a small patch. Success is identical;
cost is not.
"""

from __future__ import annotations

from .base import Task

CONFIG_NAME = "service.conf"
BUGGY_LINE = "timeout_seconds = 30"
FIXED_LINE = "timeout_seconds = 120"
FILLER_LINES = [
    "# service configuration",
    "log_level = info",
    "retries = 3",
    "cache_mb = 128",
    "flags = none",
    "metrics = off",
    "# end of configuration",
]


def build_workspace() -> dict:
    body = [
        FILLER_LINES[0],
        BUGGY_LINE,
        *FILLER_LINES[1:],
    ]
    return {CONFIG_NAME: "\n".join(body) + "\n"}


def check_fixed(ws: dict) -> bool:
    content = ws.get(CONFIG_NAME, "")
    lines = content.splitlines()
    return FIXED_LINE in lines and BUGGY_LINE not in lines and len(lines) == len(FILLER_LINES) + 1


class FixConfigTask(Task):
    def __init__(self) -> None:
        super().__init__(
            task_id="coding-fix-config",
            prompt=(
                f"In {CONFIG_NAME}, the timeout_seconds value is too low. Raise it "
                f"to 120. Do not change anything else in the file."
            ),
            build_fn=build_workspace,
            checker=check_fixed,
            metadata={f"{BUGGY_LINE.split(' = ')[0]}=": CONFIG_NAME},
        )
