# Paper summary — arXiv:2611.12122

**"System Optimizations for Cost-Efficient Agent Harnesses"**
Jongseok Park, Jiaxiang Yu, Eric Zhou, Tony Hong, Sunga Kim, Yusuf Afifi, Ian Wong, Ion Stoica, Alvin Cheung (UC Berkeley; Northwestern; UIUC). Submitted 2026-11-09, arXiv:2611.12122v1 [cs.AI]. <https://arxiv.org/abs/2611.12122>

Everything below is taken from the arXiv abstract page and the arXiv HTML full text (v1). Items we could not verify from the paper text are marked **OPEN QUESTION** at the end.

## What the paper does

- **Problem**: an agent *harness* (system prompt, tools, agent loop, telemetry — e.g. Claude Code, OpenAI Codex) barely changes task *accuracy* — accuracy is dominated by the LLM — but harness-side variance changes *cost* by **up to 2.6×** on the same model and task.
- **"Agency"** (what is named in the paper) is not a metric — it is a **harness interposition platform** (inspired by Valgrind): a transparent layer between an unmodified off-the-shelf harness and its model/tool/environment. It captures every LLM call, child-process spawn and file access, translates them into a unified format, logs them to SQLite, and lets hooks modify context or tool calls. Neither the harness binary nor the LLM backend is modified.
- **Claim**: optimizations written once against Agency's abstraction are portable across harnesses and models.

## Harness cost dimensions measured

Cost = a function of **tokens read/written per LLM call** (including cache re-reads, billed at a discount but paid on the whole context every call) and the **number of LLM calls / agent turns** (tool calls cost money per call even at constant token count). Reported in US dollars from provider prices, plus accuracy. Wall time is not a primary metric in the paper.

## Cost-accumulation findings (trace analysis, Sec. 3)

Five patterns from public traces (TraceLab, FreeInference) + own runs:

1. **Cache re-reads dominate**: reading existing context is up to **73% of total cost** (share grows from 13%/30% to 53%/73% as context lengthens; cache reads cost 5–10% of new-input price per token but the whole context is re-billed every call).
2. **Tool calls cost per call, not per token**: at similar context sizes, runs with more calls cost **1.6×–26×** more; cost grows roughly quadratically with call count.
3. **Tool outputs are sparse**: only **27%** of output tokens are ever referenced again; **36%** of tool outputs are never used at all.
4. **Filesystem search eats turns**: up to **89%** of turns in retrieval-heavy tasks are searches; **42%** of directory listings repeat across sessions.
5. **Independent subtasks pollute each other**: long tasks interleave **2.7** independent threads on average; replaying with separated contexts saves **30%** of cost.

## The five proof-of-concept techniques (Sec. 4.2)

| Technique | Type | Reported effect |
|---|---|---|
| Tool output compaction | context compression | ~14% average token reduction, mechanical/near-lossless, zero compaction cost |
| Context garbage collection (GBDT predicts per-line reuse probability; fires only when predicted net savings are positive) | context compression | 47% reduction per compaction |
| Subtask stack machine (context as a stack; finished subtasks popped) | context compression | 91% per compaction, ~once per 20 turns |
| Metadata-assisted search (offline SQLite tables over the filesystem; one SQL query replaces chains of ls/grep) | turn reduction | up to 80% fewer search calls; −32% cost as standalone ablation |
| Tool call batching (user-prompt nudge to batch independent calls) | turn reduction | up to 30% fewer turns, 1.8 batched calls/turn avg; +2% cost as standalone ablation |

## Headline numbers (Secs. 4–5)

- **Transparency check**: Claude Code + Haiku 5.5 on 5 SWE-bench Verified tasks × 100 runs, with vs without Agency: mean $0.0746 vs $0.0766 per run → mean per-task cost change **−1.50%**, 95% CI [−4.69%, +2.04%].
- **End-to-end**: 200 tasks (100 coding, 100 retrieval) × 4 models × 3 harnesses. Averaged over all tasks: **cost ratio 0.77** of baseline (range 0.65–0.85 across model/harness combos), **accuracy ratio 0.97** — i.e. up to ~35% cheaper with marginal accuracy loss.
- Largest single-model saving: GPT-6-Luna, cost ratio **0.70**. OfficeQA with UUID names + tree: **0.51–0.66**. SWE-bench: **0.80–0.92**. Runs exceeding 1M tokens: **0.67**.
- Per task: **71–83%** of tasks get cheaper; 17–29% get more expensive (mostly short runs with nothing to compact).
- Coding task instances are SWE-bench-style (repos include ansible/ansible, flipt-io/flipt, future-architect/vuls, internetarchive/openlibrary, navidrome/navidrome, qutebrowser/qutebrowser — Python and Go).

## Official code

**Yes** — the authors open-sourced the platform: <https://github.com/agency-project/Agency> ("Open-source platform for debugging, profiling, and analyzing AI agent execution", UC Berkeley Sky Computing Lab; its README cites this exact paper as the citation). It is a full platform (Docker/Podman sandboxes, ptrace/cgroups engine, uv-managed Python 3.12, supports Claude Code / Codex / OpenCode / native harnesses), not a small benchmark harness.

## Open questions (not verifiable from the abstract/HTML text we fetched)

- Exact per-model price tables and cache-read discount rates used for the $ figures.
- Whether the 200-task retrieval half is publicly released as a task list (the coding half appears to be SWE-bench-Verified-derived instances).
- The exact prompts used for the tool-call-batching nudge.
- Whether the five techniques' code ships in the public repo today or only the platform (repo README markets debugging/profiling; technique modules not confirmed).

**Consequence for this repo**: because the paper's evaluation needs real commercial harnesses (Claude Code, Codex) and paid LLM calls, we cannot reproduce its numbers offline. What we *can* do offline, deterministically: implement the harness-cost **measurement mechanism** (token/call/$ accounting over identical tasks) and demonstrate the paper's *mechanism-level* findings — that harness-side configuration changes cost (sometimes orders of magnitude) while accuracy stays constant — using scripted stub agents. That is exactly what this repo does; see README "Honest status".
