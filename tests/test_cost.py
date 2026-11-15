"""Tests for cost accounting (deterministic token estimates and prices)."""

import unittest

from agency_bench.cost import CallRecord, CostMeter, PriceTable, estimate_tokens


class TestTokenEstimate(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(estimate_tokens(""), 0)

    def test_exact_multiple(self):
        self.assertEqual(estimate_tokens("x" * 40), 10)

    def test_rounds_up(self):
        self.assertEqual(estimate_tokens("x" * 41), 11)

    def test_deterministic(self):
        self.assertEqual(estimate_tokens("a" * 100), estimate_tokens("a" * 100))


class TestPriceTable(unittest.TestCase):
    def test_cached_discount_applied(self):
        prices = PriceTable(input_per_mtok=1.0, cached_input_per_mtok=0.1, output_per_mtok=2.0)
        # 1000 new input + 0 cached + 0 output = 1000/1M * $1 = $0.001
        self.assertAlmostEqual(prices.call_cost(1000, 0, 0), 0.001)
        # same tokens but cached -> $0.0001 (0.1x)
        self.assertAlmostEqual(prices.call_cost(0, 1000, 0), 0.0001)
        # output at 2.0/Mtok
        self.assertAlmostEqual(prices.call_cost(0, 0, 500), 0.001)

    def test_per_call_fee(self):
        prices = PriceTable(per_call_usd=0.01)
        self.assertAlmostEqual(prices.call_cost(0, 0, 0), 0.01)


class TestCostMeter(unittest.TestCase):
    def test_totals(self):
        meter = CostMeter(prices=PriceTable())
        meter.record(100, 50, 10)
        meter.record(80, 60, 20)
        self.assertEqual(meter.total_calls, 2)
        self.assertEqual(meter.input_tokens, 180)
        self.assertEqual(meter.cached_tokens, 110)
        self.assertEqual(meter.output_tokens, 30)
        self.assertEqual(meter.total_tokens, 320)

    def test_cost_sums_call_costs(self):
        prices = PriceTable()
        meter = CostMeter(prices=prices)
        recs = [meter.record(1000, 0, 100), meter.record(0, 1000, 100)]
        expected = sum(r.cost(prices) for r in recs)
        self.assertAlmostEqual(meter.est_cost_usd, expected)

    def test_wall_time(self):
        meter = CostMeter()
        meter._CLOCK = staticmethod(lambda: 0.0)
        meter.start()
        meter.stop()
        # with a frozen clock, elapsed must be 0, not garbage
        self.assertEqual(meter.wall_time_s, 0.0)

    def test_call_record_total(self):
        rec = CallRecord(10, 20, 30)
        self.assertEqual(rec.total_tokens, 60)


if __name__ == "__main__":
    unittest.main()
