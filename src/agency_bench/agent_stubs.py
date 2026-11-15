"""Scripted stub agents — deterministic, offline stand-ins for an LLM.

A stub agent's *policy* adapts to what the harness offers (metadata index,
batching) exactly the way a real model would exploit harness features, and
it reacts to truncated tool outputs the way a real model does (falling back
to a targeted grep). All decisions are pure functions of the accumulated
tool outputs, so runs are reproducible without any network. Success is
identical across harness variants; only cost moves — the mechanism the
bench measures.

Agents are history-scanning state machines: each `next_turn` inspects the
full transcript and emits the next batch of tool calls (independent calls
marked batchable), then declares itself done.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from .harness import ToolCall

if TYPE_CHECKING:  # pragma: no cover
    from .tasks.base import Task
    from .tools import ToolResult

_TOKEN_RE = re.compile(r"secret=([A-Za-z0-9\-]{6,})")
_WHERE_RE = re.compile(r"where=([\w./\-]+)")
_HIT_RE = re.compile(r"^([\w./\-]+):\d+:", re.MULTILINE)


class StubAgent:
    """Base class for deterministic scripted agents."""

    name = "stub"

    def __init__(self, thought_text: str = "thinking step by step") -> None:
        self.thought_text = thought_text
        self._task: "Task | None" = None
        self._metadata: dict = {}
        self._finished = False

    # lifecycle -------------------------------------------------
    def reset(self, task: "Task", metadata: dict) -> None:
        self._task = task
        self._metadata = metadata
        self._finished = False

    def done(self) -> bool:
        return self._finished

    def thought(self, calls: list[ToolCall]) -> str:
        return f"{self.thought_text} ({self.name}, {len(calls)} call(s))"

    # helpers ---------------------------------------------------
    @staticmethod
    def _joined(history: list["ToolResult"], *names: str) -> str:
        return "\n".join(r.output for r in history if not names or r.name in names)

    def _final(self, calls: list[ToolCall]) -> list[ToolCall]:
        self._finished = True
        return calls


class RetrievalStubAgent(StubAgent):
    """Follow the handoff note to the token.

    Strategy ladder, cheapest first:
    1. token already visible anywhere in the transcript -> answer;
    2. harness offers a metadata index -> read the target file directly
       (skips the handoff grep);
    3. otherwise grep for the handoff note (batched with a root listing),
       read the pointed-at file, answer;
    4. if a read came back truncated (compaction cut the token out), fall
       back to a targeted grep inside that file — one short call.
    """

    name = "retrieval-stub"

    def next_turn(self, history: list["ToolResult"]) -> list[ToolCall]:
        token = _TOKEN_RE.search(self._joined(history))
        if token is not None:
            return self._final(
                [ToolCall("write_file", {"path": "answer.txt", "content": token.group(1)})]
            )
        read_paths = [r.args["path"] for r in history if r.name == "read_file"]
        secret_greps = [r for r in history if r.name == "grep" and r.args.get("pattern") == "secret="]
        where_greps = [r for r in history if r.name == "grep" and r.args.get("pattern") == "where"]

        # 2. metadata index: straight to the target file
        if self._metadata and not read_paths:
            return [ToolCall("read_file", {"path": next(iter(self._metadata.values()))})]
        # 3. handoff grep done -> read the pointed-at file
        if where_greps:
            match = _WHERE_RE.search(where_greps[0].output)
            if match is not None and match.group(1) not in read_paths:
                return [ToolCall("read_file", {"path": match.group(1)})]
        # 4. a target file was read but the token did not surface (truncated
        #    by compaction) -> targeted grep inside it (short output)
        if read_paths and not secret_greps:
            return [ToolCall("grep", {"pattern": "secret=", "path": read_paths[-1]})]
        if secret_greps:  # gave it our best: deterministic give-up
            return self._final([])
        # first move: grep + root listing are independent — batchable.
        return [
            ToolCall("grep", {"pattern": "where"}, independent=True),
            ToolCall("list_dir", {"path": ""}, independent=True),
        ]


class CodingStubAgent(StubAgent):
    """Fix the config value. With a metadata index it reads the target file
    directly; otherwise it greps for the setting (batched with a root
    listing) before reading the file and writing the fix."""

    name = "coding-stub"

    def next_turn(self, history: list["ToolResult"]) -> list[ToolCall]:
        for r in history:
            if r.name == "read_file" and "timeout_seconds" in r.output:
                fixed = r.output.replace("timeout_seconds = 30", "timeout_seconds = 120")
                return self._final([ToolCall("write_file", {"path": r.args["path"], "content": fixed})])
        if self._metadata:
            return [ToolCall("read_file", {"path": next(iter(self._metadata.values()))})]
        if any(r.name == "grep" for r in history):
            hit = _HIT_RE.search(self._joined(history, "grep"))
            path = hit.group(1) if hit else "service.conf"
            return [ToolCall("read_file", {"path": path})]
        return [
            ToolCall("grep", {"pattern": "timeout_seconds"}, independent=True),
            ToolCall("list_dir", {"path": ""}, independent=True),
        ]


STUB_AGENTS = {
    "retrieval-hidden-token": RetrievalStubAgent,
    "coding-fix-config": CodingStubAgent,
}


def agent_for(task_id: str) -> StubAgent:
    return STUB_AGENTS[task_id]()
