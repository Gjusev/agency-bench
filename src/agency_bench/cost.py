"""Cost accounting: deterministic token estimation and price table.

Mirrors the paper's (arXiv:2611.12122) cost dimensions: every LLM call pays
for (a) new input tokens at the input rate, (b) re-read context ("cache
reads") at a discounted rate, and (c) output tokens — plus a per-call cost
component. Tokens are ESTIMATED with a fixed chars/4 heuristic so results
are fully deterministic and offline; this is labeled as an estimate, never
as provider-reported usage.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """Deterministic token estimate: ceil(chars / 4). Labeled an estimate."""
    if not text:
        return 0
    return math.ceil(len(text) / 4)


@dataclass(frozen=True)
class PriceTable:
    """USD prices per million tokens, plus a per-call fee.

    Default values are an illustrative placeholder (labeled as such); pass a
    real provider table before quoting dollar figures as anything but
    relative comparisons.
    """

    input_per_mtok: float = 0.60
    cached_input_per_mtok: float = 0.06  # 0.1x input, mirroring cache-read pricing
    output_per_mtok: float = 2.20
    per_call_usd: float = 0.0

    def call_cost(self, new_input_tokens: int, cached_tokens: int, output_tokens: int) -> float:
        return (
            new_input_tokens * self.input_per_mtok / 1_000_000
            + cached_tokens * self.cached_input_per_mtok / 1_000_000
            + output_tokens * self.output_per_mtok / 1_000_000
            + self.per_call_usd
        )


@dataclass
class CallRecord:
    """One LLM call: new input, re-read (cached) context, output."""

    new_input_tokens: int
    cached_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.new_input_tokens + self.cached_tokens + self.output_tokens

    def cost(self, prices: PriceTable) -> float:
        return prices.call_cost(self.new_input_tokens, self.cached_tokens, self.output_tokens)


@dataclass
class CostMeter:
    """Accumulates CallRecords and wall time for one task run."""

    prices: PriceTable = field(default_factory=PriceTable)
    calls: list[CallRecord] = field(default_factory=list)
    wall_time_s: float = 0.0
    _t0: float | None = field(default=None, repr=False)

    _CLOCK = staticmethod(time.perf_counter)

    def start(self) -> None:
        self._t0 = self._CLOCK()

    def stop(self) -> None:
        if self._t0 is not None:
            self.wall_time_s += self._CLOCK() - self._t0
            self._t0 = None

    def record(self, new_input_tokens: int, cached_tokens: int, output_tokens: int) -> CallRecord:
        rec = CallRecord(new_input_tokens, cached_tokens, output_tokens)
        self.calls.append(rec)
        return rec

    @property
    def total_calls(self) -> int:
        return len(self.calls)

    @property
    def total_tokens(self) -> int:
        return sum(c.total_tokens for c in self.calls)

    @property
    def input_tokens(self) -> int:
        return sum(c.new_input_tokens for c in self.calls)

    @property
    def cached_tokens(self) -> int:
        return sum(c.cached_tokens for c in self.calls)

    @property
    def output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.calls)

    @property
    def est_cost_usd(self) -> float:
        return sum(c.cost(self.prices) for c in self.calls)


@dataclass
class RunResult:
    """Outcome of one (task, harness variant) run."""

    task_id: str
    variant: str
    success: bool
    meter: CostMeter

    @property
    def total_tokens(self) -> int:
        return self.meter.total_tokens

    @property
    def est_cost_usd(self) -> float:
        return self.meter.est_cost_usd

    @property
    def wall_time_s(self) -> float:
        return self.meter.wall_time_s

    def as_row(self) -> dict:
        return {
            "task": self.task_id,
            "variant": self.variant,
            "success": self.success,
            "calls": self.meter.total_calls,
            "input_tokens": self.meter.input_tokens,
            "cached_tokens": self.meter.cached_tokens,
            "output_tokens": self.meter.output_tokens,
            "total_tokens": self.total_tokens,
            "est_cost_usd": round(self.est_cost_usd, 6),
            "wall_time_s": round(self.wall_time_s, 4),
        }
