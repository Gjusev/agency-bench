"""Task base classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# A workspace is a plain {relpath: content} dict — hermetic and serializable.
Workspace = dict


@dataclass
class Task:
    task_id: str
    prompt: str
    build_fn: Callable[[], Workspace]
    checker: Callable[[Workspace], bool]
    # Optional precomputed metadata index (paper: "metadata-assisted search").
    # Populated only when the harness variant enables metadata_index.
    metadata: dict = field(default_factory=dict)

    def build(self) -> Workspace:
        """Fresh, deterministic workspace."""
        return dict(self.build_fn())

    def check(self, workspace: Workspace) -> bool:
        return bool(self.checker(workspace))
