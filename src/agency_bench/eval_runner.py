"""Shared matrix runner used by tests and the CLI."""

from __future__ import annotations

from .agent_stubs import agent_for
from .harness import VARIANTS, Harness
from .tasks import TASKS_BY_ID


def run_one(task_id: str, variant: str) -> dict:
    harness = Harness(VARIANTS[variant])
    return harness.run(TASKS_BY_ID[task_id], agent_for(task_id)).as_row()


def run_matrix() -> list[dict]:
    rows = []
    for task_id in TASKS_BY_ID:
        for name in VARIANTS:
            rows.append(run_one(task_id, name))
    return rows
