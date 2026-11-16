# agency-bench

[![tests](https://github.com/Gjusev/agency-bench/actions/workflows/tests.yml/badge.svg)](https://github.com/Gjusev/agency-bench/actions/workflows/tests.yml)
[![dependencies](https://img.shields.io/badge/dependencies-0-success)]()
[![python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Offline harness-cost benchmark for LLM agent harnesses** — a mechanism-level, deterministic repro/test repo for [arXiv:2611.12122](https://arxiv.org/abs/2611.12122), *"System Optimizations for Cost-Efficient Agent Harnesses"* (Park et al., UC Berkeley, 2026). Independent and unofficial — not affiliated with the authors.

## What & why

The paper's core observation: an agent **harness** (system prompt, tools, loop, telemetry) barely moves task *accuracy* — that's the model's job — but harness-side variance moves *cost* by **up to 2.6×** on the same model and task. The paper then builds *Agency*, an interposition layer that cuts cost up to **35%** across real benchmarks at accuracy ratio **0.97**.

This repo reproduces the **measurement mechanism**, not the paper's numbers: run identical tasks under different harness configurations, account tokens / LLM calls / estimated $ / wall time per run, and show that harness knobs move cost while success stays constant — fully offline, with deterministic scripted stub agents standing in for a real LLM.

- Every token count is **estimated** (`ceil(chars/4)`) and deterministic — labeled as an estimate, never provider-reported usage.
- Dollar figures use an **illustrative price table** (`cost.PriceTable`), with cache re-reads billed at a 0.1× discount, mirroring the paper's cost model.
- No network, no API key, zero dependencies (stdlib only, PEP 668-safe).

## Quickstart

```bash
git clone https://github.com/Gjusev/agency-bench.git
cd agency-bench
python3 -m unittest            # 61 tests, offline, <1s
python3 eval/run_bench.py      # the offline comparison table
```

## Layout

```
src/agency_bench/
  harness.py      # HarnessConfig variants + accounting run loop
  cost.py         # token estimation, price table, CostMeter, RunResult
  tools.py        # deterministic offline tools + near-lossless compaction
  agent_stubs.py  # scripted stub agents (offline LLM stand-ins)
  real_model.py   # Z.ai Coding Plan client (OWNER-GATED, inert without key)
  tasks/          # deterministic tasks: retrieval-hidden-token, coding-fix-config
  eval_runner.py  # matrix runner shared by CLI and tests
eval/
  run_bench.py    # CLI: prints the comparison table, optional --json
  results.md      # committed output of the offline (stub) runs
tests/            # 61 offline unittest tests
docs/planning/    # paper-summary.md — what arXiv:2611.12122 actually does
NOTES.md          # existing-implementation check + from-scratch decision
ROADMAP.md        # next steps; item 1 = first real-model run (money-gated)
CONTINUE.md       # agent handoff: working rules + STOP points
```

## Harness variants (the paper's technique classes)

| variant | paper technique | knob |
|---|---|---|
| `baseline` | — | unmodified harness |
| `compact-output` | tool output compaction | near-lossless: collapse runs of structurally identical lines, keep signal lines verbatim |
| `batched` | tool call batching | independent calls share one LLM call/turn |
| `indexed` | metadata-assisted search | agent gets the precomputed location index |
| `agency-lite` | all of the above + context GC | past tool outputs compacted to markers |

## Findings so far (offline, harness validation)

From `python3 eval/run_bench.py` (see `eval/results.md` for the full table):

- **Success is invariant**: 100% on both tasks under every variant — reproducing the paper's claim that accuracy is a property of the (stubbed) agent/model, not the harness.
- **Cost moves a lot**: full stack (`agency-lite`) = **0.53× tokens / 0.49× est. $** vs baseline; metadata index alone 0.55×/0.63×; batching 0.92×/0.89×; compaction 0.90×/0.83×.
- **Short outputs have nothing to compact**: on `coding-fix-config`, compaction is a no-op (file has no repeated-line runs) — the offline analogue of the paper's finding that 17–29% of tasks don't get cheaper.
- Implementing the stub agents surfaced a real mechanism trap: naive character truncation cut the secret out of a tool output, forcing the agent into an extra recovery turn that made the "optimized" variant *more* expensive than baseline. Compaction that preserves signal lines fixes this — same lesson the paper's "near-lossless" phrasing implies.

## Honest status

| claim | status |
|---|---|
| Measurement mechanism (tokens/calls/$ per task, harness variants, comparison table) | ✅ implemented + offline-tested (61 tests green) |
| Offline bench table | ✅ real runs of stub agents (`eval/results.md`) — **harness validation only**, 0% claim about the paper's benchmarks |
| Paper's headline numbers (35% cost cut, 0.77 cost / 0.97 accuracy ratio) | ❌ NOT reproduced — needs real-model runs (owner-approval-gated, see ROADMAP item 1) |
| Agency interposition platform (ptrace/cgroups, real harnesses) | ❌ out of scope — use the official [agency-project/Agency](https://github.com/agency-project/Agency) |

## Owner rules (baked in, non-negotiable)

- Real LLM runs **only** via the owner's **Z.ai Coding Plan**: `https://api.z.ai/api/coding/paas/v4`, model **`glm-5.3-flash` ONLY** (env `AGENCY_ZAI_KEY`).
- Flat subscription: on any billing/endpoint error → **STOP and report**. There is no pay-per-call fallback, by design (`real_model.BillingError`).
- Real-model runs are **owner-approval-gated**; the client is inert without the key and every path that could spend money raises first.

## License

MIT — see [LICENSE](LICENSE).
