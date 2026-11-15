"""Tests for harness variants: cost moves, success must not."""

import unittest

from agency_bench.agent_stubs import agent_for
from agency_bench.harness import Harness, ToolCall, VARIANTS, pack_turns, render_history
from agency_bench.tools import ToolResult
from agency_bench.tasks import ALL_TASKS, TASKS_BY_ID


def run(task_id: str, variant: str):
    harness = Harness(VARIANTS[variant])
    return harness.run(TASKS_BY_ID[task_id], agent_for(task_id))


class TestPacking(unittest.TestCase):
    def test_no_batching_one_call_per_turn(self):
        calls = [ToolCall("grep", {}, independent=True), ToolCall("read_file", {})]
        turns = pack_turns(calls, batch_enabled=False)
        self.assertEqual(turns, [[calls[0]], [calls[1]]])

    def test_batching_merges_independent_calls(self):
        calls = [ToolCall("grep", {}, independent=True), ToolCall("list_dir", {}, independent=True),
                 ToolCall("read_file", {"path": "x"})]
        turns = pack_turns(calls, batch_enabled=True)
        self.assertEqual([len(t) for t in turns], [2, 1])

    def test_batching_never_merges_dependent_calls(self):
        calls = [ToolCall("grep", {}, independent=True), ToolCall("read_file", {})]
        turns = pack_turns(calls, batch_enabled=True)
        self.assertEqual([len(t) for t in turns], [1, 1])


class TestHistoryRendering(unittest.TestCase):
    def _results(self, n=3):
        return [ToolResult("grep", {}, "output %d %s" % (i, "y" * 50)) for i in range(n)]

    def test_no_gc_verbatim(self):
        text = render_history(self._results(), gc_enabled=False)
        self.assertEqual(text.count("output"), 3)

    def test_gc_compacts_older_turns(self):
        text = render_history(self._results(), gc_enabled=True)
        self.assertEqual(text.count("[compacted by harness]"), 2)
        self.assertEqual(text.count("output"), 1)

    def test_gc_with_single_result_verbatim(self):
        text = render_history(self._results(1), gc_enabled=True)
        self.assertEqual(text.count("output"), 1)


class TestSuccessInvariance(unittest.TestCase):
    """The paper's core claim at mechanism level: harness knobs change cost,
    never success."""

    def test_all_variants_succeed_on_all_tasks(self):
        for task in ALL_TASKS:
            for name in VARIANTS:
                with self.subTest(task=task.task_id, variant=name):
                    result = run(task.task_id, name)
                    self.assertTrue(result.success)

    def test_runs_are_deterministic(self):
        for task in ALL_TASKS:
            for name in ("baseline", "agency-lite"):
                a = run(task.task_id, name)
                b = run(task.task_id, name)
                self.assertEqual(a.total_tokens, b.total_tokens)
                self.assertEqual(a.meter.total_calls, b.meter.total_calls)
                self.assertEqual(a.est_cost_usd, b.est_cost_usd)


class TestCostMovement(unittest.TestCase):
    BASELINE_TOK = sum(run(t.task_id, "baseline").total_tokens for t in ALL_TASKS)

    def test_compact_output_reduces_tokens(self):
        tok = sum(run(t.task_id, "compact-output").total_tokens for t in ALL_TASKS)
        self.assertLess(tok, self.BASELINE_TOK)

    def test_context_gc_reduces_tokens(self):
        tok = sum(run(t.task_id, "agency-lite").total_tokens for t in ALL_TASKS)
        self.assertLess(tok, self.BASELINE_TOK)

    def test_batching_reduces_call_count(self):
        calls_base = sum(run(t.task_id, "baseline").meter.total_calls for t in ALL_TASKS)
        calls_batched = sum(run(t.task_id, "batched").meter.total_calls for t in ALL_TASKS)
        self.assertLess(calls_batched, calls_base)

    def test_metadata_index_reduces_calls(self):
        calls_base = sum(run(t.task_id, "baseline").meter.total_calls for t in ALL_TASKS)
        calls_indexed = sum(run(t.task_id, "indexed").meter.total_calls for t in ALL_TASKS)
        self.assertLess(calls_indexed, calls_base)

    def test_full_stack_biggest_saving(self):
        lite = sum(run(t.task_id, "agency-lite").total_tokens for t in ALL_TASKS)
        others = [
            sum(run(t.task_id, v).total_tokens for t in ALL_TASKS)
            for v in ("baseline", "compact-output", "batched")
        ]
        for other in others:
            self.assertLess(lite, other)

    def test_cached_tokens_rebill_static_prefix_every_call(self):
        """Every call pays the static prefix as a (discounted) cache re-read —
        the paper's dominant cost pattern."""
        result = run("retrieval-hidden-token", "baseline")
        static = VARIANTS["baseline"].static_prefix_tokens(
            TASKS_BY_ID["retrieval-hidden-token"].prompt
        )
        self.assertGreaterEqual(result.meter.cached_tokens, static * result.meter.total_calls)


if __name__ == "__main__":
    unittest.main()
