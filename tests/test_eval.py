"""End-to-end run of the eval runner (offline) + RunResult accounting."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from agency_bench.cost import PriceTable, RunResult  # noqa: E402
from agency_bench.eval_runner import run_matrix, run_one  # noqa: E402


class TestRunResultRow(unittest.TestCase):
    def test_row_schema(self):
        from agency_bench.cost import CostMeter

        meter = CostMeter(prices=PriceTable())
        meter.record(10, 20, 30)
        result = RunResult(task_id="t", variant="v", success=True, meter=meter)
        row = result.as_row()
        for key in (
            "task", "variant", "success", "calls", "input_tokens",
            "cached_tokens", "output_tokens", "total_tokens",
            "est_cost_usd", "wall_time_s",
        ):
            self.assertIn(key, row)
        self.assertEqual(row["total_tokens"], 60)
        self.assertEqual(row["calls"], 1)


class TestMatrixRunner(unittest.TestCase):
    def test_run_matrix_shape(self):
        rows = run_matrix()
        self.assertEqual(len(rows), 10)  # 2 tasks x 5 variants
        self.assertTrue(all(r["success"] for r in rows))

    def test_run_one(self):
        row = run_one("retrieval-hidden-token", "agency-lite")
        self.assertEqual(row["variant"], "agency-lite")
        self.assertTrue(row["success"])

    def test_cli_writes_json_and_exits_zero(self):
        out_path = REPO / ".scratch" / "bench_out.json"
        proc = subprocess.run(
            [sys.executable, str(REPO / "eval" / "run_bench.py"), "--json", str(out_path)],
            capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = json.loads(out_path.read_text())
        self.assertEqual(len(rows), 10)
        self.assertIn("HARNESS VALIDATION", proc.stdout)


if __name__ == "__main__":
    unittest.main()
