# Offline bench table — HARNESS VALIDATION ONLY

Runs below use deterministic scripted stub agents with estimated tokens
(ceil(chars/4)) and an illustrative price table. This validates the
measurement mechanism (harness-side cost variance at constant success), NOT
the paper's benchmark numbers — no real LLM was called.

## Per-run results

| task | variant | success | calls | input_tok | cached_tok | output_tok | total_tok | est_$ | wall_s |
|---|---|---|---|---|---|---|---|---|---|
| retrieval-hidden-token | baseline | yes | 4 | 287 | 1577 | 52 | 1916 | 0.000381 | 0.0002 |
| retrieval-hidden-token | compact-output | yes | 4 | 120 | 1405 | 52 | 1577 | 0.000271 | 0.0004 |
| retrieval-hidden-token | batched | yes | 3 | 286 | 1434 | 39 | 1759 | 0.000343 | 0.0002 |
| retrieval-hidden-token | indexed | yes | 2 | 243 | 842 | 26 | 1111 | 0.000254 | 0.0000 |
| retrieval-hidden-token | agency-lite | yes | 2 | 80 | 806 | 26 | 912 | 0.000154 | 0.0001 |
| coding-fix-config | baseline | yes | 4 | 145 | 1235 | 48 | 1428 | 0.000267 | 0.0001 |
| coding-fix-config | compact-output | yes | 4 | 145 | 1235 | 48 | 1428 | 0.000267 | 0.0001 |
| coding-fix-config | batched | yes | 3 | 145 | 1128 | 36 | 1309 | 0.000234 | 0.0001 |
| coding-fix-config | indexed | yes | 2 | 110 | 596 | 24 | 730 | 0.000155 | 0.0001 |
| coding-fix-config | agency-lite | yes | 2 | 110 | 722 | 24 | 856 | 0.000162 | 0.0001 |

## Summary per variant

| variant | success | total tokens | tokens vs baseline | est. $ | est. $ vs baseline |
|---|---|---|---|---|---|
| baseline | 2/2 | 3344 | 1.00x | 0.000648 | 1.00x |
| compact-output | 2/2 | 3005 | 0.90x | 0.000538 | 0.83x |
| batched | 2/2 | 3068 | 0.92x | 0.000577 | 0.89x |
| indexed | 2/2 | 1841 | 0.55x | 0.000409 | 0.63x |
| agency-lite | 2/2 | 1768 | 0.53x | 0.000316 | 0.49x |

All runs successful: True
