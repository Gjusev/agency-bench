"""Configurable harness variants and the run loop.

The harness wraps a stub agent's scripted turns with real accounting:
every LLM call pays for the static prefix (system prompt + tool schemas +
task prompt), a re-read of the accumulated context ("cache reads", billed
at a discount — the paper's dominant cost), the new tool outputs, and the
call's output text. Harness-side knobs change the cost; the agent's success
rate does not — the paper's core claim (arXiv:2611.12122), reproduced at
mechanism level.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .cost import CostMeter, RunResult, estimate_tokens
from .tools import TOOL_SPECS, ToolBox

if TYPE_CHECKING:  # pragma: no cover
    from .agent_stubs import StubAgent
    from .tasks.base import Task


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict
    independent: bool = False  # safe to batch with other independent calls in one turn


DEFAULT_SYSTEM_PROMPT = (
    "You are a careful file agent. Use the provided tools to complete the "
    "task. Verify your result before finishing."
)
DEFAULT_BATCHING_PROMPT = (
    " When several tool calls are independent of each other, issue them "
    "together in the same turn instead of one at a time."
)


@dataclass
class HarnessConfig:
    """One harness variant. The knobs mirror the paper's technique classes."""

    name: str
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    tools: tuple = ("list_dir", "read_file", "grep", "write_file")
    compact_tool_outputs: bool = False       # paper: tool output compaction (near-lossless)
    max_tool_output: int | None = None      # hard cap on top of compaction
    batch_tool_calls: bool = False          # paper: tool call batching
    metadata_index: bool = False            # paper: metadata-assisted search
    context_gc: bool = False                # paper: context garbage collection
    batching_prompt: str = DEFAULT_BATCHING_PROMPT

    @property
    def schema_text(self) -> str:
        return "\n".join(f"- {name}: {TOOL_SPECS[name][0]}" for name in self.tools)

    def static_prefix(self, task_prompt: str) -> str:
        parts = [self.system_prompt, "## Tools", self.schema_text, "## Task", task_prompt]
        if self.batch_tool_calls:
            parts.append("## Note" + self.batching_prompt)
        return "\n\n".join(parts)

    def static_prefix_tokens(self, task_prompt: str) -> int:
        return estimate_tokens(self.static_prefix(task_prompt))


COMPACTED_MARKER = "[compacted by harness]"


def render_history(results, gc_enabled: bool) -> str:
    """Render prior turns' tool outputs; with context_gc only the most recent
    turn's outputs survive verbatim, older ones become a marker."""
    if not results:
        return ""
    if not gc_enabled or len(results) <= 1:
        return "\n".join(r.render() for r in results)
    head = "\n".join(COMPACTED_MARKER for _ in results[:-1])
    return head + "\n" + results[-1].render()


def pack_turns(calls: list[ToolCall], batch_enabled: bool) -> list[list[ToolCall]]:
    """Group calls into turns. Without batching a harness issues one call per
    turn; independent calls may share a turn when batching is enabled."""
    if batch_enabled:
        turns: list[list[ToolCall]] = []
        for call in calls:
            if call.independent and turns and all(c.independent for c in turns[-1]):
                turns[-1].append(call)
            else:
                turns.append([call])
        return turns
    return [[c] for c in calls]


@dataclass
class Harness:
    config: HarnessConfig
    prices: "PriceTable | None" = None
    clock: "callable" = field(default=time.perf_counter, repr=False)

    def run(self, task: "Task", agent: "StubAgent") -> RunResult:
        from .cost import PriceTable

        prices = self.prices or PriceTable()
        ws = task.build()
        toolbox = ToolBox(
            ws,
            max_output_chars=self.config.max_tool_output,
            compact=self.config.compact_tool_outputs,
        )
        metadata = dict(task.metadata) if self.config.metadata_index else {}
        agent.reset(task, metadata)

        static_tokens = self.config.static_prefix_tokens(task.prompt)
        meter = CostMeter(prices=prices)
        history: list = []
        turns_used = 0
        meter._t0 = self.clock()

        while not agent.done():
            calls = agent.next_turn(history)
            if not calls:
                break
            for turn_calls in pack_turns(calls, self.config.batch_tool_calls):
                results = [toolbox.execute(c) for c in turn_calls]
                new_text = "\n".join(r.render() for r in results)
                cached_text = self.config.static_prefix(task.prompt) + "\n" + render_history(history, self.config.context_gc)
                output_text = agent.thought(turn_calls)
                meter.record(
                    new_input_tokens=estimate_tokens(new_text),
                    cached_tokens=static_tokens + estimate_tokens(cached_text),
                    output_tokens=estimate_tokens(output_text),
                )
                history.extend(results)
                turns_used += 1

        meter.wall_time_s = self.clock() - meter._t0
        meter._t0 = None
        return RunResult(
            task_id=task.task_id,
            variant=self.config.name,
            success=task.check(ws),
            meter=meter,
        )


def baseline() -> HarnessConfig:
    return HarnessConfig(name="baseline")


def compact_output() -> HarnessConfig:
    return HarnessConfig(name="compact-output", compact_tool_outputs=True)


def batched() -> HarnessConfig:
    return HarnessConfig(name="batched", batch_tool_calls=True)


def indexed() -> HarnessConfig:
    return HarnessConfig(name="indexed", metadata_index=True)


def agency_lite() -> HarnessConfig:
    """All four harness-side knobs on — the paper's full-optimization arm."""
    return HarnessConfig(
        name="agency-lite",
        compact_tool_outputs=True,
        batch_tool_calls=True,
        metadata_index=True,
        context_gc=True,
    )


VARIANTS: dict[str, HarnessConfig] = {
    c.name: c
    for c in (baseline(), compact_output(), batched(), indexed(), agency_lite())
}
