# R3-E000 pre-registration — verification-gated adaptive inference

**Status: DRAFT for human review. Does not authorize execution.**
This document designs R3-E000 only. Do not generate, escalate, or
score until a human freezes this file.

Experiment ID: `E000`
Project: `/home/sauravsvt/Desktop/Research/R3`
Does not read or write `/home/sauravsvt/Desktop/Research/R1` or
`/home/sauravsvt/Desktop/Research/R2` experimental artifacts.
R2 hardware timings may be cited only as a planning envelope.

## Research question

Can verification-gated adaptive inference preserve verified coding
success while materially reducing GPU compute compared with always
using the expensive inference path?

This is not a claim about structural escape, analogies, AGI, or
energy.

## Why this is the smallest falsification-first test

Three policies, one paired generation design:

1. **CHEAP_ONLY** — always the cheap path
2. **EXPENSIVE_ONLY** — always the expensive path
3. **ADAPTIVE** — cheap first; escalate to expensive only if cheap
   fails an executable gate

Generate cheap and expensive independently on every task (needed for
both always-on baselines). Apply ADAPTIVE as a deterministic policy
over those frozen outputs. Do not generate a third sample.

If the expensive path has no quality advantage, adaptive inference
is unnecessary. If the cheap gate is leaky, adaptive can lose
plus-test success. If cheap fails often, adaptive `G_decode`
collapses toward cheap+expensive and cannot beat always-expensive.

## Hypothesis

ADAPTIVE plus-test success is non-inferior to EXPENSIVE_ONLY, and
ADAPTIVE policy `G_decode`/task is materially lower than
EXPENSIVE_ONLY, in a setting where EXPENSIVE_ONLY materially beats
CHEAP_ONLY on plus-tests.

## Benchmark

**HumanEval+ / EvalPlus HumanEvalPlus.jsonl.gz v0.1.10, n=164.**

Why this, not MBPP+ or BigCodeBench:

- EvalPlus `check_correctness` is a clean, already-available
  executable verifier with official base and plus suites
- n=164 is the smallest confirmatory coding set here that still
  supports paired bootstrap; 2 generations/task = 328 calls
- MBPP+ (377 plus-testable) would double+ the first kill test
- BigCodeBench still depends on pandas/sklearn/matplotlib/seaborn
  and file/network mocks
- HumanEval+ was used in R2-E000 for a different question. R3 does
  not reuse R2 trajectories, prefixes, prompts-as-arms, or labels

Primary verified success: **plus-tests PASS**.
Executable gate (escalation only): **base-tests PASS**.

Gate ≠ outcome on purpose. If the gate were plus-tests, adaptive
plus-success would be ≥ expensive plus-success by construction, and
“preserve success” would not be falsifiable. Base-as-gate can
false-accept a cheap solution that later fails plus-tests.

## Cheap / expensive definitions (frozen)

Same model, same prompt, same temperature. The only intended cost
axis is thinking level plus output budget.

**CHEAP**

- `think = "low"`
- `num_predict = 512`

**EXPENSIVE**

- `think = "high"`
- `num_predict = 1536`

Do not change these after seeing scores. Do not add a second model.
If `think=high` or `think=low` is unavailable on this blob, the
experiment is **UNEVALUABLE**; do not silently substitute medium.

## Model configuration (frozen)

- Name: `gpt-oss:20b`
- Ollama list ID: `17052f91a42e`
- Blob: `sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb`
- `temperature = 0`
- `num_ctx = 8192`
- Local Ollama
- Same system prompt and task wrapper for both paths

### System prompt

```text
You are a careful programmer. Solve the given Python function-completion problem. Reason step by step. Do not use tools, web search, or external files. End with one complete implementation in a single fenced python code block.
```

### Task user prompt

```text
Complete the following Python function. Return only the full function implementation in a ```python``` block after your reasoning.

{humaneval_prompt}
```

Extract code from the last fenced python block; if none, the path
fails the gate and the plus-outcome.

## Warm / model-residency freeze (before any HumanEval+ generation)

Load and warm the frozen model **without using a benchmark task**.
Verify with `ollama ps` that the model is fully GPU-resident.
Record that residency state.

Model loading time is **not** part of policy `G_decode`. Report it
separately.

If GPU residency changes materially during the run (model no longer
fully GPU-resident), record the change and **stop**. Do not silently
mix CPU/GPU execution.

## Compute definitions

Primary compute variable:

`G_decode` = Ollama `eval_duration`

This is a **decode-time GPU-compute proxy**, measured while
`ollama ps` confirms the model is fully GPU-resident.

It is **not** total GPU energy and **not** total inference compute.

Policy attribution (unchanged):

- cheap accepted: `G_adaptive = G_decode_cheap`
- cheap rejected: `G_adaptive = G_decode_cheap + G_decode_expensive`
- expensive-only: `G_expensive = G_decode_expensive`

CHEAP_ONLY uses `G_decode_cheap` only.

The experiment always spends cheap+expensive decode time on every
task so that baselines exist. The **primary compute outcome is the
policy attribution**, not the experimental sum. Report experimental
wall separately. No energy claim if NVML remains broken.

## Escalation policy (frozen)

For each task, after both path outputs exist:

1. Score CHEAP on **base-tests** (and treat no extractable code as
   gate failure). Record base-test verifier wall time and CPU time
   for this ADAPTIVE gate separately. Do not hide verification
   overhead and do not add it to `G_decode`.
2. If CHEAP base-passes: ADAPTIVE uses the cheap solution;
   `G_adaptive = G_decode_cheap`
3. If CHEAP base-fails: ADAPTIVE uses the expensive solution;
   `G_adaptive = G_decode_cheap + G_decode_expensive`
4. ADAPTIVE verified success = plus-tests PASS of the selected
   solution

CHEAP_ONLY success = cheap plus-pass; `G = G_decode_cheap`.
EXPENSIVE_ONLY success = expensive plus-pass; `G = G_decode_expensive`.

## Generation order

`digest = sha256("R3-E000|" + task_id)`. Sort by `(digest, task_id)`.
Last bit 0: cheap then expensive. Last bit 1: expensive then cheap.
Order is execution only; it must not enter the confirmatory tests.

All 164 tasks are confirmatory. No calibration split. No prompt
tuning after any score is visible.

## Baselines and arms

- CHEAP_ONLY
- EXPENSIVE_ONLY
- ADAPTIVE (policy over the same two generations)

No A4/A2 structural-escape arms. No retrieval.

## Primary outcomes

1. **Verified success** Y ∈ {0,1} = plus-tests PASS
2. **Decode-time GPU-compute proxy** `G_decode` = Ollama
   `eval_duration`, policy-attributed for ADAPTIVE as above,
   measured only while the model is fully GPU-resident

## Statistical design

Unit: task. All contrasts are paired.

Bootstrap: 10,000 replicates, `numpy.random.RandomState(0)`,
resample tasks with replacement. Report point estimates and 95%
percentile CIs.

Contrasts:

- `Δ_QE = mean(Y_expensive − Y_cheap)` — quality gap
- `Δ_PE = mean(Y_adaptive − Y_expensive)` — preserve / non-inferiority
- `Δ_G = mean(G_expensive − G_adaptive)` — `G_decode` saved vs expensive
- `R_G = Δ_G / mean(G_expensive)` — relative `G_decode` reduction

**Material quality gap:** `Δ_QE ≥ +0.05` and 95% CI lower bound > 0.

**Non-inferiority (preserve):** 95% CI lower bound of `Δ_PE` > −0.05.

**Material decode-compute reduction:** `R_G ≥ 0.20` and 95% CI lower
bound of `Δ_G` > 0. This 20% rule applies to `G_decode` only.

If n < 80 completed paired tasks: **UNEVALUABLE**.

## Success / kill (apply in this order; do not reinterpret)

1. **UNEVALUABLE** if Ollama cannot finish on this model, HumanEval+
   cannot verify, think levels are unavailable, GPU residency is
   not fully GPU at warm-up or changes materially during the run,
   or n < 80
2. **STOP — NO EXPENSIVE ADVANTAGE** if the material quality gap
   fails. Cheap-only is then the relevant policy; adaptive is not
   answering this research question
3. **STOP — ADAPTIVE LOSES SUCCESS** if non-inferiority fails
   (`Δ_PE` CI lower bound ≤ −0.05)
4. **STOP — NO COMPUTE SAVE** if the material `G_decode` reduction
   fails
5. **CONTINUE — VERIFICATION-GATED ADAPTIVE SIGNAL** only if 2–4
   all pass

Do not declare success from `G_decode` savings alone. Do not declare
success from a quality gap alone. Do not stratify post hoc. Do not
tune think levels, `num_predict`, prompts, or the gate after scores
exist.

## Secondary (not confirmatory)

For every generation, record all of:

- `prompt_eval_duration`
- `prompt_eval_count`
- `prompt_eval_cached_count` if exposed
- `eval_count`
- `eval_duration`
- `total_duration`
- `load_duration`
- process wall time

Report a secondary model-service duration

`G_service = prompt_eval_duration + eval_duration`

using the same policy attribution as `G_decode`. Do **not** make
`G_service` a confirmatory criterion in E000 because prompt
caching/order can affect prefill timing.

Also record:

- ADAPTIVE-gate base-test verifier wall time and CPU time
  (separate from `G_decode`; do not hide this overhead)
- Escalate rate (cheap base-fail)
- Gate errors: cheap base-pass / plus-fail (false accept);
  cheap base-fail / plus-pass (unnecessary escalate)
- `done_reason`
- CHEAP_ONLY vs ADAPTIVE `G_decode` (descriptive)
- Model load / warm time (not in policy compute)
- Residency snapshots from `ollama ps`
- Energy: unavailable if NVML remains broken

## Pre-execution artifact freeze

Before any HumanEval+ generation, write and hash a Stage-0
manifest. Freeze:

- this final preregistration (`PREREG.md`)
- executable config (`configs/E000_verification_gated.json`)
- execution/analysis scripts (as written at freeze time)
- exact 164 task IDs, ordered by `(digest, task_id)`
- HumanEval+ dataset hash and version (`v0.1.10`)
- model ID / blob
- system-prompt hash and task-prompt-template hash
- cheap settings (`think=low`, `num_predict=512`) and expensive
  settings (`think=high`, `num_predict=1536`)
- generation-order map (digest, last bit, cheap-first vs
  expensive-first)
- warm-up residency record (or a slot that must be filled before
  generation starts)

No methodology may change after this freeze. No initials, arms, or
scoring before it is written.

## Estimated runtime (planning only)

From R2 `gpt-oss:20b` medium/`num_predict=1536` HumanEval+ initials
(~11.8 s wall/task):

- Cheap low/512: planning 4–8 s/task → 164 × ~6 s ≈ 0.3 h
- Expensive high/1536: planning 12–20 s/task → 164 × ~16 s ≈ 0.7 h
- Plus/base scoring: minutes
- CUDA-abort retries (seen on this machine): +25–40%

**Planning envelope: about 1.5–3 hours wall; roughly 1.2–2.5 hours
of `G_decode` (`eval_duration`).** Experimental spend is both paths
on all 164 tasks even though ADAPTIVE would skip some expensive
calls in production.

## Leakage / hygiene

- R3 does not import R1 or R2 run artifacts
- temperature 0; no sampling hunt
- No prompt edits after scores
- Policy `G_decode` must not be replaced by experimental-sum
  decode time, by `G_service`, or by verifier time in the
  confirmatory compute test
- Do not call `G_decode` total GPU energy or total inference compute

## Not in R3-E000

Second models, A2/A4, saturation detectors, MBPP+, BigCodeBench,
retrieval, multi-agent, weight updates, Paper 3 prose, energy
claims, confirmatory use of `G_service`.

**Do not execute R3-E000 until this draft is human-reviewed and frozen.**
