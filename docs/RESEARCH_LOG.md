# Research log

Chronology of confirmatory decisions. Numbers below are copied from frozen analyses; this file does not replace the per-project records.

## R1 — selective retrieval gating

Status at packaging: **CONTINUE — LEXICAL-SPECIFIC SIGNAL**.

- E000–E005: frozen official lexical/BM25 setup.
- E006: exploratory score-shape gate; promising on lexical, BM25 did not replicate.
- E007: frozen 12-feature family did not show a reliable C3−C0 gain on official RepoMap or official Qwen embedding under the pre-registered reliability rule.
- Do not start E008 from this archive.
- Nested Agent Retrieval Bench checkout, corpora, and embedding matrices are not in this repository.

Checkpoint: `r1-e007`.

## R2 — structural escape

Status at packaging: **CLOSED**.

- E000 (HumanEval+): **CONTINUE — MIXED SIGNAL**. A4 helped more on LOW than HIGH saturation prefixes; not an authorization to retune.
- E001 (MBPP+, K=160, no saturation detector): usable n=341. A1 252/341 (0.739), A4 253/341 (0.742). Δ = +0.003, 95% CI [−0.023, +0.029].
- Decision: **STOP — NO A4 OVER A1 SIGNAL**. Independent replication failed. Do not start E002. Do not retune A1/A4 or K.

Checkpoint: `r2-e001`.

## R3 — verification-gated low→high reasoning

Status at packaging: **STOPPED**.

- Isolation: R3 does not import R1 or R2 experimental artifacts.
- E000 (HumanEval+ plus-tests, n=164): cheap (`think=low`, 512) 142/164 (0.866); expensive (`think=high`, 1536) 58/164 (0.354); adaptive 142/164 (0.866).
- Δ_QE (expensive−cheap) = −0.512, 95% CI [−0.585, −0.439].
- Decision: **STOP — NO EXPENSIVE ADVANTAGE**. High reasoning was substantially worse than low. Do not start E001. Do not retune `think`, `num_predict`, gate, margins, or prompts.

Checkpoint: `r3-e000`.

## Packaging note (2026-09-18)

Sources copied without rewriting frozen bytes. Omitted from Git: model weights, Agent Retrieval Bench corpora, embedding caches, huge trajectory jsonl (`*_arms.jsonl`, `*_initial.jsonl`, `*_prefixes.jsonl`, `*_generations.jsonl`), run logs, `.venv`, and secrets. SHA256 manifests still list omitted blobs.
