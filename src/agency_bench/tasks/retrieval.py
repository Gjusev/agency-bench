"""Retrieval task: follow a handoff note to a hidden token in a file tree.

Mirrors the paper's retrieval-heavy task class (paper finding 4: filesystem
search eats turns; technique: metadata-assisted search). The tree is built
deterministically — no randomness — so every run is identical.

The token is NOT greppable directly: a root-level handoff note points at the
file that holds it, so every strategy must read a large file at least once.
This is what makes harness-side knobs (compaction, GC, metadata index)
matter for cost.
"""

from __future__ import annotations

from .base import Task

N_DIRS = 6
N_FILES_PER_DIR = 5
LINES_PER_FILE = 20

SECRET_TOKEN = "AGENCY-BENCH-7f3a91"
SECRET_DIR = "dir_3"
SECRET_FILE = "file_04"
SECRET_LINE = 13
TARGET_FILE = f"{SECRET_DIR}/{SECRET_FILE}.txt"


def _filler(dir_i: int, file_j: int, line_k: int) -> str:
    """Pure function -> deterministic file content."""
    return f"dir{dir_i} file{file_j} line{line_k}: status=ok payload={dir_i * 100 + file_j * 10 + line_k}"


def build_workspace() -> dict:
    ws = {}
    for d in range(N_DIRS):
        for f in range(1, N_FILES_PER_DIR + 1):
            lines = [_filler(d, f, k) for k in range(1, LINES_PER_FILE + 1)]
            if d == 3 and f == 4:
                lines[SECRET_LINE - 1] = f"secret={SECRET_TOKEN}"
            ws[f"dir_{d}/file_{f:02d}.txt"] = "\n".join(lines) + "\n"
    # Handoff note: grep-able, points at the file that holds the token.
    ws["HANDOFF.txt"] = (
        "# runbook handoff notes\n"
        "owner=platform-team\n"
        "where=dir_3/file_04.txt\n"
        "expires=never\n"
    )
    return ws


def check_answer(ws: dict) -> bool:
    answer = ws.get("answer.txt", "")
    return SECRET_TOKEN in answer


class HiddenTokenTask(Task):
    def __init__(self) -> None:
        super().__init__(
            task_id="retrieval-hidden-token",
            prompt=(
                "A handoff note somewhere in this tree says where a token is "
                "stored ('where=<path>'). Read that file, find the line "
                "'secret=<TOKEN>', and write the token (the part after "
                "'secret=') to answer.txt."
            ),
            build_fn=build_workspace,
            checker=check_answer,
            # Metadata index: precomputed map from content pattern -> location,
            # like the paper's offline SQLite tables over the filesystem.
            metadata={"secret=<TOKEN>": TARGET_FILE},
        )
