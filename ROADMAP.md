# ROADMAP.md — ordered next steps

## 1. First real-model run (MONEY-GATED — owner approval required)

Replace the stub agent with a live `glm-5.3-flash` agent on the same two
tasks, through the Z.ai Coding Plan only:

```bash
export AGENCY_ZAI_KEY="<owner key>"        # https://api.z.ai/api/coding/paas/v4
export AGENCY_ZAI_MODEL="glm-5.3-flash"    # pinned; anything else is rejected
```

- [ ] **Get owner approval BEFORE any spend.** No approval → do not start.
- [ ] `src/agency_bench/live_agent.py`: a `StubAgent`-compatible agent that
      turns tool schemas + history into chat messages and executes returned
      tool calls. Reuse `Harness` accounting unchanged.
- [ ] Smoke test first: ONE task, ONE variant, one run. Verify billing error
      path stops cleanly (`BillingError` → report, never retry elsewhere).
- [ ] Then the full 2×5 matrix, N=3 repeats; record provider-reported usage
      alongside our estimate so `cost.estimate_tokens` gets a calibration
      factor.
- [ ] Compare real ratios against the offline stub ratios in
      `eval/results.md`; write findings into README "Findings".

STOP clause: if no key/endpoint is available, commit the tooling with
results marked "not yet run" and stop there. On ANY billing error: stop,
report to the owner, touch nothing else.

## 2. Estimate-vs-actual calibration

With item-1 data: fit `chars/4` per role (system / tool output / model
output), expose `PriceTable` overrides, re-baseline `eval/results.md`.

## 3. More tasks per class

- Retrieval: deeper trees, pointer chains of length 2–3, repeated listings
  (paper finding 4).
- Coding: multi-file fixes, decoy files (paper's SWE-bench-style class).
- New class: multi-subtask task to implement the paper's **subtask stack
  machine** (currently deferred — needs interleaved independent subtasks).

## 4. Variance & statistics

Per (task, variant): N≥5 runs with seeded stub-policy jitter; report mean,
min, and the analogue of the paper's per-task "cheaper/more expensive"
split (71–83% / 17–29%).

## 5. Real-harness adapter (stretch)

Bridge to the official Agency platform or a local harness to measure REAL
harness variance (the paper's 2.6× claim). Heavy: needs containers — keep
out of the zero-dep core, optional-dependency only.
