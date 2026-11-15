"""Tests for tasks (deterministic, offline) and tools."""

import unittest

from agency_bench.tasks import ALL_TASKS, TASKS_BY_ID
from agency_bench.harness import ToolCall
from agency_bench.tools import (
    TOOL_SPECS,
    ToolBox,
    ToolError,
    ToolResult,
    compact_lines,
    tool_grep,
    tool_list_dir,
    tool_read_file,
    tool_write_file,
)


class TestTasks(unittest.TestCase):
    def test_registry_complete(self):
        self.assertEqual(len(ALL_TASKS), 2)
        for t in ALL_TASKS:
            self.assertIn(t.task_id, TASKS_BY_ID)

    def test_build_is_deterministic(self):
        for t in ALL_TASKS:
            a, b = t.build(), t.build()
            self.assertEqual(sorted(a), sorted(b))
            for key in a:
                self.assertEqual(a[key], b[key])

    def test_fresh_build_unmodified(self):
        for t in ALL_TASKS:
            ws = t.build()
            self.assertFalse(t.check(ws), "task must not be pre-solved by its own build")

    def test_retrieval_checker_detects_answer(self):
        task = TASKS_BY_ID["retrieval-hidden-token"]
        ws = task.build()
        ws["answer.txt"] = "AGENCY-BENCH-7f3a91"
        self.assertTrue(task.check(ws))
        ws["answer.txt"] = "wrong-token"
        self.assertFalse(task.check(ws))

    def test_coding_checker_detects_fix(self):
        task = TASKS_BY_ID["coding-fix-config"]
        ws = task.build()
        ws["service.conf"] = ws["service.conf"].replace(
            "timeout_seconds = 30", "timeout_seconds = 120"
        )
        self.assertTrue(task.check(ws))
        ws["service.conf"] = ws["service.conf"].replace(
            "timeout_seconds = 120", "timeout_seconds = 999"
        )
        self.assertFalse(task.check(ws))


class TestTools(unittest.TestCase):
    WS = {
        "a.txt": "alpha\nbeta\n",
        "dir/b.txt": "beta in b\n",
    }

    def test_list_dir_root(self):
        out = tool_list_dir(self.WS, "")
        self.assertEqual(out, "a.txt\ndir/")

    def test_list_dir_subdir(self):
        out = tool_list_dir(self.WS, "dir")
        self.assertEqual(out, "b.txt")

    def test_read_file(self):
        self.assertEqual(tool_read_file(self.WS, "a.txt"), "alpha\nbeta\n")

    def test_read_missing_raises(self):
        with self.assertRaises(ToolError):
            tool_read_file(self.WS, "nope.txt")

    def test_grep_all(self):
        out = tool_grep(self.WS, "beta")
        self.assertIn("a.txt:2", out)
        self.assertIn("dir/b.txt:1", out)

    def test_grep_no_match(self):
        self.assertEqual(tool_grep(self.WS, "zzz"), "(no matches)")

    def test_write_file(self):
        ws = dict(self.WS)
        msg = tool_write_file(ws, "new.txt", "hello")
        self.assertIn("ok", msg)
        self.assertEqual(ws["new.txt"], "hello")


class TestCompaction(unittest.TestCase):
    def test_collapses_similar_runs_keeps_signal_lines(self):
        text = "\n".join(f"dir1 file2 line{k}: status=ok payload=1" for k in range(1, 20))
        text += "\nsecret=AGENCY-BENCH-7f3a91"
        out = compact_lines(text)
        self.assertIn("[19 similar lines:", out)
        self.assertIn("secret=AGENCY-BENCH-7f3a91", out)
        self.assertLess(len(out), len(text) // 2)

    def test_short_runs_kept_verbatim(self):
        text = "a = 1\nb = 2\n"
        self.assertEqual(compact_lines(text), text)

    def test_deterministic(self):
        text = "\n".join(f"row {k} col {k}" for k in range(10))
        self.assertEqual(compact_lines(text), compact_lines(text))


class TestToolBox(unittest.TestCase):
    def test_truncation(self):
        ws = {"big.txt": "x" * 1000}
        box = ToolBox(ws, max_output_chars=100)
        result = box.execute(ToolCall("read_file", {"path": "big.txt"}))
        self.assertLessEqual(len(result.output), 130)
        self.assertIn("truncated", result.output)

    def test_no_truncation_by_default(self):
        ws = {"big.txt": "x" * 1000}
        box = ToolBox(ws)
        result = box.execute(ToolCall("read_file", {"path": "big.txt"}))
        self.assertEqual(len(result.output), 1000)

    def test_compact_box_shrinks_output(self):
        ws = {"big.txt": "\n".join(f"row {k} col {k}" for k in range(50))}
        box = ToolBox(ws, compact=True)
        result = box.execute(ToolCall("read_file", {"path": "big.txt"}))
        self.assertIn("similar lines", result.output)
        self.assertLess(len(result.output), 200)

    def test_unknown_tool_raises(self):
        box = ToolBox({})
        with self.assertRaises(ToolError):
            box.execute(ToolCall("rm_rf", {}))

    def test_render_is_stable(self):
        r = ToolResult("grep", {"pattern": "x"}, "a.txt:1: x")
        self.assertEqual(r.render(), r.render())
        self.assertIn("[tool:grep(pattern=x)]", r.render())

    def test_every_spec_has_callable_and_description(self):
        for name, (desc, fn) in TOOL_SPECS.items():
            self.assertTrue(desc)
            self.assertTrue(callable(fn))


if __name__ == "__main__":
    unittest.main()
