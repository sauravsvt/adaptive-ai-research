# E001 pre-registration — frozen A4 vs A1 on fixed early trajectory prefixes

**Status: DRAFT for human review. Does not authorize execution.**
This document designs E001 only. Do not run initials, arms, or scoring
until a human freezes this file. It does not authorize retrieval,
analogy databases, extra models, A2, prompt edits, or Paper 2 writing.

Experiment ID: `E001`
Project: `/home/sauravsvt/Desktop/Research/R2`
Does not read or write `/home/sauravsvt/Desktop/Research/R1`.
Does not read E000 evaluation labels to choose tasks, prompts, or K.

## Why this experiment exists

E000 on HumanEval+ did not confirm saturation-triggered structural
escape. The A4−A1 difference was larger on LOW prefixes than on HIGH
prefixes. E001 is an independent test of a narrower claim:

The **exact frozen E000 A4 text**, applied to a **fixed early
trajectory prefix** (not the E000 saturation detector), improves
executable verified success over the **exact frozen E000 A1 text**.

This is not a claim about saturation, AGI, creativity, analogy
engines, or compute efficiency. Because A2 is not run, a positive
result cannot distinguish structural escape from generic
“do something different.”

## Hypothesis

On MBPP+ plus-tests, mean(A4 − A1) is a material improvement when both
arms continue from the same deterministic fixed-length prefix of one
initial trajectory.

## Model (frozen; identical to E000)

- Name: `gpt-oss:20b`
- Ollama list ID: `17052f91a42e`
- Blob: `sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb`
- Confirmed present at design time (2026-09-17) via `ollama show`
- `temperature = 0`
- `think = "medium"`
- `num_ctx = 8192`
- Initial generation `num_predict = 1536`
- Each intervention arm `num_predict = 1024` (identical remaining budget)
- Same system prompt as E000 (byte-identical)
- Local Ollama

Do not compare other models in E001. Do not switch models if Ollama
fails; record unevaluable.

## Benchmark choice and justification

**MBPP+ / EvalPlus MbppPlus.jsonl.gz v0.2.0.**

Loader: `evalplus.data.get_mbpp_plus` (evalplus 0.3.1 already in
`R2/.venv`).
Dataset hash: `get_mbpp_plus_hash()` = `ee43ecabebf20deef4bb776a405ac5b1`.
Verifier: `evalplus.evaluate.check_correctness(dataset="mbpp", ...)`
with official MBPP special oracles and
`get_groundtruth(..., MBPP_OUTPUT_NOT_NONE_TASKS)`.

Why MBPP+, not HumanEval+ or BigCodeBench:

- HumanEval+ was the E000 benchmark. Forbidden to reuse.
- EvalPlus already provides the same executable plus-test path used
  in E000 (`check_correctness`, plus suite, ground-truth cache).
  Design-time smoke: `Mbpp/2` canonical `prompt + canonical_solution`
  plus-tests **PASS**.
- BigCodeBench remains the E000 fallback: official tests depend on
  pandas/sklearn/matplotlib/seaborn and file/network mocks. Heavier,
  weaker verifier. Not needed because MBPP+ loaded cleanly.

Selected for **an unused benchmark with a clean reproducible
verifier**, not because it is easy for A4.

Primary success: **plus-tests PASS** (EvalPlus plus suite). Base-tests
are recorded but are not the confirmatory endpoint.

## Number of usable tasks

Catalog (design-time, before any E001 generation):

- MBPP+ v0.2.0: **378** tasks
- Drop `Mbpp/793` a priori: `plus_input` is empty, so plus-tests are
  not a defined confirmatory endpoint
- Plus-testable catalog: **377**

Analysis n is not 377 until after initials:

- A task is **usable** iff it is in the plus-testable catalog and its
  initial trajectory has at least `K = 160` word tokens under the
  prefix rule below
- Exact n is counted and frozen after initials, **before** any arm
  call, without using tests or pass/fail (Stage 2 freeze below)
- Expected n ≈ 347 if the E000 initial length distribution transfers
  (13/164 E000 initials had `< 160` words). This expectation is a
  runtime guess only; it is not a sample-size target to hunt

If usable n < 80 after initials: **UNEVALUABLE**. Do not add tasks,
change K, or switch benchmarks.

No calibration split. No HumanEval+ tasks. All usable tasks are
confirmatory.

Recorded order and arm-order digest (not a holdout):
`digest = sha256("R2-E001|" + task_id)`, sort by `(digest, task_id)`.
The same digest’s last bit sets A1-first vs A4-first (see
Intervention execution order).

## Deterministic prefix rule (frozen before evaluation)

Do **not** use or retune the E000 saturation detector. Do not compute
`dup_rate_8`, `novelty_100`, `has_solution`, `W_min`, `W_long`,
`T_dup`, `T_nov`, or `L*`. Do not use pass/fail, canonical solutions,
or tests to choose or adjust the cut.

One initial trajectory per plus-testable task, same settings as E000.
Save `thinking`, `response`, token/duration fields, and

```text
trajectory = thinking + "\n" + response
```

Tokenize with the E000 word counter only as a **length ruler**:
`[A-Za-z0-9_]+`, case-folded. Let `W` be that word sequence.

**FIXED-K prefix**

- `K = 160`
- If `len(W) < 160`: task is unusable (do not fall back to the full
  trajectory)
- Else: `prefix = align_prefix(trajectory, 160)` using the existing
  E000 helper (end at the 160th word; if a newline exists within 40
  characters after that end, include through the newline)

One prefix per usable task. No HIGH/LOW groups.

Non-decision diagnostic (not eligibility, not a stratum): after the
prefix bytes are frozen, record whether that prefix already contains
a fenced code block (markdown opening fence, with or without a
python language tag). Do not exclude, re-cut, stratify, weight, or
decide by this flag.

Why K = 160, and why this is not the E000 detector:

- 160 is the only early-cut length written in the E000 prereg
  **before calibration**, as the fallback `L*`. It is not the
  calibrated E000 LOW length (`L* = 319`) and not `W_min = 199`
- The cut does not depend on repetition, novelty, code-fence
  presence, or correctness
- Alignment reuses `align_prefix` so prefix bytes are mechanically
  defined, not hand-trimmed

Do not change K after seeing initials or scores.

## System prompt (frozen; identical to E000)

```text
You are a careful programmer. Solve the given Python function-completion problem. Reason step by step. Do not use tools, web search, or external files. End with one complete implementation in a single fenced python code block.
```

sha256: `988834b3804622cef83deaa27c18a55329eff3432579466c89a3a924c1236863`

## Task user prompt (frozen wrapper; official MBPP+ `prompt` field)

```text
Complete the following Python function. Return only the full function implementation in a ```python``` block after your reasoning.

{prompt}
```

where `{prompt}` is the official MBPP+ `prompt` field (docstring plus
one embedded assert; not a HumanEval-style `def` stub). The wrapper
bytes are the E000 `TASK_TEMPLATE`. Do not rewrite the wrapper for
MBPP style.

sha256 of template: `85b7b076af2dc9d3260a96350604bbe53b1c483c8a258720e749b583f43a25af`

## Intervention wrapper (frozen; identical to E000)

From the frozen prefix, one `/api/chat` call per arm.
`num_predict = 1024`, same model settings.

```text
{original_task_user_prompt}

--- FROZEN REASONING PREFIX (do not rewrite the prefix) ---
{prefix}
--- END PREFIX ---

{ARM_INSTRUCTION}

Continue from the prefix. Use only the remaining generation budget. End with one complete implementation in a single fenced python code block.
```

## Intervention execution order (execution only)

Deterministic counterbalance by the same task-ID digest used for log
order, independent of correctness and of the fence diagnostic:

`digest = sha256("R2-E001|" + task_id)`

- last bit of the digest is 0: run A1, then A4
- last bit of the digest is 1: run A4, then A1

This is approximately 50/50 A1-first vs A4-first. Do not retune the
split after seeing usable IDs or scores.

Arm order is an execution schedule only. It must not affect analysis:
both arms are scored, and Δ remains `mean(A4 − A1)` on paired tasks.
Do not drop, weight, or stratify by order.

## Exact frozen A1 / A4 texts (copied from E000 `r2_lib.ARM_INSTRUCTIONS`)

These strings must be used byte-for-byte. Do not retune after seeing
results.

### A1 — CONTINUE_LOCAL

```text
Continue solving from the current reasoning. Do not explicitly change strategy. Extend the same approach until you produce a final implementation.
```

- utf-8 bytes: 146
- sha256: `ea2c65a2b7be99cf3eb73923129563e2ec115d3ca558d6a260daf394b689ffcc`

### A4 — STRUCTURAL_ESCAPE

```text
Stop extending the current line of reasoning. Abstract the problem in terms of states, transitions, constraints, resources, invariants, feedback, failure modes, thresholds and objective. Identify a mechanism from a semantically distant domain that has the same underlying structure. Map that mechanism back to this problem, then continue solving from the new representation.
```

- utf-8 bytes: 374
- sha256: `2bb16c2f1b2e576bf8ec5af25f2c2e8ec30a46efb1755f78b6d64286bcea7286`

### A2 — not run

A2 is not required for the primary A4−A1 test. It is **not**
pre-registered as a secondary in E001. A later experiment may add A2
only if E001 first shows a material A4−A1 gain; that is a new
prereg, not a post-hoc arm.

### A3

Not used.

No external retrieval. No tool use. Extract code from the last fenced
python block; if none, score fail. Build the executable solution as in
E000: if the official `prompt` is not already inside the extract,
prepend `prompt`.

## Statistical plan

**Unit.** Usable task. One frozen prefix per task. Paired arms share
that prefix.

**Primary outcome.** `Y ∈ {0,1}` = EvalPlus plus-tests PASS.

**Primary contrast.**
`Δ = mean_i (Y_A4,i − Y_A1,i)` over usable tasks that have both arms
scored.

**Bootstrap.** 10,000 replicates, `numpy.random.RandomState(0)`,
resample tasks with replacement. Report the point estimate and 95%
percentile CI. Reuse `r2_lib.paired_bootstrap`.

**Pre-registered success (material improvement).**
`Δ ≥ +0.05` **and** paired 95% CI lower bound `> 0`.

This is the only confirmatory test. No HIGH/LOW interaction. No A4−A2.
No multiplicity correction.

**Decisions**

- `CONTINUE — FIXED-PREFIX A4 OVER A1` if the material rule holds
- `STOP — NO A4 OVER A1 SIGNAL` if Δ ≤ 0, or Δ > 0 but the material
  rule fails, and A1 is not ceiling-limited
- `UNEVALUABLE` if usable n < 80, Ollama cannot finish on this model,
  or the MBPP+ verifier cannot run
- `CEILING-LIMITED` if mean(A1) ≥ 0.95: still report Δ and CI; do not
  treat a failed material rule as a negative mechanism result; do not
  retune prompts or change K

Do not change A1/A4 text, K, the wrapper, or the success rule after
seeing results.

## Secondary (not confirmatory)

Record for every initial and arm call:

- Ollama `eval_count` (output tokens)
- `eval_duration` → GPU-seconds when `ollama ps` reports GPU
- wall time
- `done_reason`
- plus-test and base-test success

Energy: **unavailable** if NVML remains broken. **No efficiency
claim** in E001.

McNemar counts `(n_A4=1,A1=0)` and `(n_A4=0,A1=1)` may be reported
as descriptive only.

The per-prefix fenced-code-block flag is a non-decision diagnostic
only. Do not exclude or stratify by it.

## Two-stage artifact freezing

### Stage 1 — pre-initial freeze (before any E001 generation)

Write a manifest and freeze hashes of:

- this prereg (`PREREG_E001.md`)
- E001 config, if/when written (`configs/E001_*.json`)
- model identity: name `gpt-oss:20b`, ollama id `17052f91a42e`,
  blob `sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb`
- benchmark: MBPP+ v0.2.0, `get_mbpp_plus_hash()` =
  `ee43ecabebf20deef4bb776a405ac5b1`, plus-testable catalog
  (378 minus `Mbpp/793`)

No initials, arms, or scoring before this freeze is written.

### Stage 2 — post-initial / pre-arm freeze (after initials, before any arm)

After initials and the unchanged K=160 eligibility rule, freeze:

- exact usable task IDs
- usable n
- initial trajectory sha256 for every plus-testable initial
- frozen prefix bytes and sha256 for every usable task
- the fence-diagnostic flag for each frozen prefix (non-decision)

Do not start A1/A4 calls until this freeze is written. Do not change
K, prompts, or the usable set after this freeze.

## Leakage / hygiene

- Prefix rule never sees tests, canonical solutions, or pass/fail
- E000 saturation features and thresholds are not computed
- Nested R1 is not used
- temperature 0; no sampling hunt
- No prompt edits after any E001 score is visible
- Do not drop tasks post hoc except the a-priori `Mbpp/793` rule and
  the a-priori `len(W) < 160` rule
- The fence diagnostic does not exclude or stratify
- Arm execution order does not enter the confirmatory test

## Estimated runtime (not a compute claim)

From E000 realized means (164 initials at 11.8 s wall; 300 arms at
10.3 s wall):

- 377 initials ≈ 1.2 h
- 2 arms × ~347–377 prefixes ≈ 2.0–2.2 h
- Plus-test scoring: minutes (ground-truth cache already built at
  design-time smoke; ~100 plus inputs/task typical)
- CUDA-abort retries (seen in E000): add ~25–40%

**Planning envelope: about 4.5–7 hours wall; roughly 4–5 hours of
eval-duration GPU-seconds.** Same retry/health-ping as E000. Do not
switch models.

## Not in E001

Saturation detector, A2, HumanEval+, BigCodeBench, retrieval, analogy
databases, multi-agent, web search, failure memory, weight updates,
prompt tuning, Paper 2 prose, novelty claims, compute-saving claims.

## Design-time checks already done (not E001 execution)

- MBPP+ v0.2.0 loaded: n=378, hash `ee43ecabebf20deef4bb776a405ac5b1`
- `Mbpp/793` has 0 plus inputs → excluded from the usable catalog
- Canonical `Mbpp/2` plus-tests PASS via `check_correctness("mbpp")`
- Model blob matches E000
- A1/A4 sha256 values above match `scripts/r2_lib.py`

**Do not execute E001 until this draft is human-reviewed and frozen.**
