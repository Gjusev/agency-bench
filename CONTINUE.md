# CONTINUE.md — read this first when an agent picks up this repo

## What this repo is

agency-bench is an offline harness-cost benchmark for LLM agent harnesses —
an independent, unofficial mechanism-level repro of arXiv:2611.12122
("System Optimizations for Cost-Efficient Agent Harnesses", UC Berkeley,
2026). Implemented: deterministic tasks + scripted stub agents + harness
variants (compaction, batching, metadata index, context GC) + full
token/call/$ accounting. Honest status: mechanism implemented and
offline-tested (61 tests green); the paper's benchmark numbers are NOT
reproduced — that needs real-model runs which are money-gated.

Read README.md, ROADMAP.md, NOTES.md and docs/planning/paper-summary.md fully.

## Working rules

- **Offline-first**: the test suite is zero-dependency and passes with
  `python3 -m unittest` from the repo root (author's canonical command —
  do not "re-derive" a different discovery invocation). Network imports
  stay lazy/stdlib; nothing may require `pip install`.
- **Honest claims**: never state benchmark numbers that haven't been run.
  Stub-run output is labeled HARNESS VALIDATION — never present it as a
  paper-numbers reproduction. Anything measured goes into eval/results.md
  with the exact command that produced it.
- Cite the paper first (arXiv:2611.12122); independent, unofficial
  implementation — never imply affiliation with the authors.
- Commits in English, conventional-commit style (feat:/fix:/docs:).
- Before pushing: run `python3 -m unittest` — it must be green.

## Models — Z.ai Coding Plan (MANDATORY, no other provider)

```bash
export AGENCY_ZAI_BASE_URL="https://api.z.ai/api/coding/paas/v4"
export AGENCY_ZAI_MODEL="glm-5.3-flash"     # pinned — NO alternatives
export AGENCY_ZAI_KEY="<Z.ai Coding Plan key>"
```

- Flat subscription. On ANY billing/endpoint error: **STOP and report to
  the owner** — do NOT switch to a pay-per-call provider to "get it
  working". This is enforced in code (`real_model.BillingError`) and must
  stay that way.
- Model is pinned to `glm-5.3-flash`; `resolve_config()` rejects any other
  model string. Never offer/document an alternative model.
- **Real-model runs are owner-approval-gated.** No spend without explicit
  owner OK (see ROADMAP item 1).

## Current task (do this now)

ROADMAP.md item 1 — first real-model run — **only if the owner has given
approval and AGENCY_ZAI_KEY is set in the environment**:

1. Write `src/agency_bench/live_agent.py`: a StubAgent-compatible agent
   that prompts `glm-5.3-flash` with the tool schemas + rendered history
   and executes returned tool calls. Acceptance: passes the existing
   offline tests via the mocked `real_model.chat` pattern
   (tests/test_real_model.py).
2. Smoke test: ONE task, ONE variant, one live run. Acceptance: success and
   provider usage recorded; any `BillingError` → STOP and report.
3. Full 2 tasks × 5 variants × 3 repeats. Acceptance: results in
   eval/results.md with provider-reported usage next to estimates.
4. Add the estimate-vs-actual calibration table (ROADMAP item 2 start).

**STOP point**: if no key/endpoint is available, or the owner has not
approved spend, commit whatever tooling is ready with results marked
"not yet run" and stop there. On any billing error, stop immediately.

## After that

Follow ROADMAP.md in order. One item per commit series.
