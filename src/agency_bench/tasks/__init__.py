"""Tasks: deterministic, offline-runnable task definitions.

Each task builds a fixed workspace and provides a checker over the final
workspace. Building and checking are pure functions of the task definition,
so a task run twice gives byte-identical workspaces.
"""

from .base import Task, Workspace
from .coding import FixConfigTask
from .retrieval import HiddenTokenTask

ALL_TASKS = [HiddenTokenTask(), FixConfigTask()]
TASKS_BY_ID = {t.task_id: t for t in ALL_TASKS}

__all__ = ["Task", "Workspace", "HiddenTokenTask", "FixConfigTask", "ALL_TASKS", "TASKS_BY_ID"]
