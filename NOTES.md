# NOTES.md — decisions log

## STEP 1 — existing-implementation check (done 2026-11-15, online)

Searched for official code and third-party repros/implementations of arXiv:2611.12122 ("System Optimizations for Cost-Efficient Agent Harnesses", aka the Agency paper).

**Found — official (authors' own code):**
- `agency-project/Agency` — <https://github.com/agency-project/Agency>. UC Berkeley Sky Computing Lab. README cites exactly arXiv 2611.12122. Full interposition platform: Docker/Podman sandboxes, ptrace/cgroups capture engine, SQLite action log, supports Claude Code / Codex / OpenCode / native harnesses, uv + Python 3.12, model backends OpenAI/Anthropic/Bedrock/vLLM.

**Found — third-party repros of THIS paper's benchmark:** none. Search surfaced only adjacent same-domain work that is *not* a repro of 2611.12122:
- `Qihoo360/harness-bench` (arXiv:2605.27922) — different paper, compares native harnesses on work tasks.
- HarnessFlow (arXiv:2611.06254), HarnessDev (arXiv:2609.01437), SoL-Pi (arXiv:2609.20519, NVlabs) — related harness-optimization papers with their own repos; no overlap with this paper's mechanism.

## Decision: fork-and-fill vs from-scratch

**From-scratch.** Reasons:
1. The official repo is a *platform* (sandbox engine, ptrace, containers), not a runnable cost benchmark. Filling a "roadmap gap" inside it would mean contributing systems code we cannot test without Docker + paid harness runs — not a repro of the paper's *evaluation*.
2. No third-party repo reproduces the paper's cost-measurement evaluation, so the niche is open: a small, deterministic, offline-runnable bench that measures harness cost dimensions (tokens / LLM calls / est. $ / wall time) for identical tasks under different harness configurations.
3. The official Agency repo stays the reference for future *real-harness* work (ROADMAP item beyond the first real-model run).

This repo therefore positions itself as: **first open, offline, from-scratch harness-cost benchmark** modeled on the paper's cost-accounting methodology, not an implementation of the Agency interposition engine itself.

## Design notes

- Tokenizer: deterministic `ceil(chars/4)` heuristic (paper uses provider-reported tokens; we label ours as an estimate).
- Cost model: price table with input / cached-input (0.1× input) / output rates, mirroring the paper's cache re-read accounting (cache reads billed at a discount on every call).
- Harness variants map 1:1 to the paper's five technique *classes*: tool-output truncation (compaction), context GC, metadata-assisted search, tool-call batching, plus the unmodified baseline. The subtask stack machine is deferred (needs multi-subtask tasks).
- Stub agents are scripted policies that behave identically in accuracy across variants — mirroring the paper's core observation (accuracy ≈ f(model), cost ≈ f(harness)).
- Zero-dependency core: stdlib only, so the offline suite runs under PEP 668 system Python. The real-model client uses `urllib.request` (stdlib) — no httpx/openai dependency needed.
- Tests run with `python3 -m unittest` from the repo root (author's canonical command — do not "re-derive" a different discovery invocation).
