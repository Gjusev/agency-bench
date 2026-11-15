#!/usr/bin/env python3
"""Run the offline harness-cost bench and print a comparison table.

Pure stdlib, offline, deterministic: stub agents only, no network. Output is
labeled HARNESS VALIDATION (mechanism-level), not a reproduction of the
paper's benchmark numbers.

Usage: python3 eval/run_bench.py [--json PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agency_bench.eval_runner import run_matrix  # noqa: E402
from agency_bench.harness import VARIANTS  # noqa: E402

COLUMNS = [
    "task",
    "variant",
    "success",
    "calls",
    "input_tok",
    "cached_tok",
    "output_tok",
    "total_tok",
    "est_$",
    "wall_s",
]

BANNER = """\
# Offline bench table — HARNESS VALIDATION ONLY

Runs below use deterministic scripted stub agents with estimated tokens
(ceil(chars/4)) and an illustrative price table. This validates the
measurement mechanism (harness-side cost variance at constant success), NOT
the paper's benchmark numbers — no real LLM was called.
"""


def fmt_table(rows: list[dict]) -> str:
    def fmt(row: dict) -> list[str]:
        return [
            row["task"],
            row["variant"],
            "yes" if row["success"] else "NO",
            str(row["calls"]),
            str(row["input_tokens"]),
            str(row["cached_tokens"]),
            str(row["output_tokens"]),
            str(row["total_tokens"]),
            f"{row['est_cost_usd']:.6f}",
            f"{row['wall_time_s']:.4f}",
        ]

    lines = ["| " + " | ".join(COLUMNS) + " |",
             "|" + "|".join("---" for _ in COLUMNS) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row)) + " |")
    return "\n".join(lines)


def fmt_summary(rows: list[dict]) -> str:
    base_tok = sum(r["total_tokens"] for r in rows if r["variant"] == "baseline") or 1
    base_cost = sum(r["est_cost_usd"] for r in rows if r["variant"] == "baseline") or 1
    lines = [
        "| variant | success | total tokens | tokens vs baseline | est. $ | est. $ vs baseline |",
        "|---|---|---|---|---|---|",
    ]
    for name in VARIANTS:
        vrows = [r for r in rows if r["variant"] == name]
        tok = sum(r["total_tokens"] for r in vrows)
        cost = sum(r["est_cost_usd"] for r in vrows)
        succ = sum(1 for r in vrows if r["success"])
        lines.append(
            f"| {name} | {succ}/{len(vrows)} | {tok} | {tok / base_tok:.2f}x "
            f"| {cost:.6f} | {cost / base_cost:.2f}x |"
        )
    return "\n".join(lines)


def render_report(rows: list[dict]) -> str:
    return (
        BANNER
        + "\n## Per-run results\n\n"
        + fmt_table(rows)
        + "\n\n## Summary per variant\n\n"
        + fmt_summary(rows)
        + "\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="also write rows as JSON to this path")
    args = ap.parse_args()
    rows = run_matrix()
    out = render_report(rows)
    print(out)
    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=2) + "\n")
    ok = all(r["success"] for r in rows)
    print(f"All runs successful: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
