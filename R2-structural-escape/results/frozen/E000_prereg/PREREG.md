# E000 pre-registration — saturation-triggered structural escape

**Status: FROZEN before evaluation-task intervention scoring.**
This document authorizes E000 only. It does not authorize retrieval,
analogy databases, extra models, or Paper 2 writing.

Experiment ID: `E000`
Project: `/home/sauravsvt/Desktop/Research/R2`
Does not read or write `/home/sauravsvt/Desktop/Research/R1`.

## Hypothesis

When a language model's reasoning has become **measurably saturated**
(mechanical trajectory signals only), forcing a **structural escape**
produces higher verified task success than (A1) continuing the same
reasoning or (A2) merely trying another ordinary in-domain approach.

This is not a claim about AGI, creativity, analogy engines, or compute
efficiency.

## Model (frozen)

- Name: `gpt-oss:20b`
- Ollama list ID: `17052f91a42e`
- Blob: `sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb`
- Ollama version at probe: `0.33.3`
- `temperature = 0`
- `think = "medium"`
- `num_ctx = 8192`
- Initial generation `num_predict = 1536`
- Each intervention arm `num_predict = 1024` (identical remaining budget)
- Same system prompt for all generations
- Local Ollama; probe showed `100% GPU`

Do not compare other models in E000.

## Benchmark (frozen)

**HumanEval+ / EvalPlus HumanEvalPlus.jsonl.gz v0.1.10, n=164.**

Why this, not LiveCodeBench or BigCodeBench:

- LiveCodeBench lite currently fails to load: Hugging Face dataset
  scripts are unsupported by the installed `datasets` library. Not
  reproducible here without an unofficial loader rewrite.
- BigCodeBench v0.1.2 loads (1140 tasks) but official tests depend on
  pandas/sklearn/matplotlib/seaborn and file/network mocks. That is a
  weaker, heavier verifier for a first kill test.
- HumanEval+ downloads in seconds, has an automatic executable
  verifier (`evalplus.evaluate.check_correctness`), and extra tests
  beyond HumanEval.

Selected for **reproducibility and verifier quality**, not because it
is easy for structural escape.

Primary success: **plus-tests PASS** (EvalPlus plus suite). Base-tests
are recorded but not the confirmatory endpoint.

## Split (frozen, before evaluation inspection)

`digest = sha256("R2-E000|" + task_id)`
Sort by `(digest, task_id)`.

- Calibration: first 40
- Evaluation: remaining 124

Calibration may be used only to set **mechanical** detector
thresholds. Evaluation tasks must not be used to tune prompts,
thresholds, or arms. Verifier labels are **not** inputs to the
detector or to threshold choice.

## System prompt (frozen)

```text
You are a careful programmer. Solve the given Python function-completion problem. Reason step by step. Do not use tools, web search, or external files. End with one complete implementation in a single fenced python code block.
```

## Task user prompt (frozen)

```text
Complete the following Python function. Return only the full function implementation in a ```python``` block after your reasoning.

{humaneval_prompt}
```

where `{humaneval_prompt}` is the official HumanEval+ `prompt` field.

## Initial trajectory

One generation per task with the frozen model settings. Save:

- `thinking` (Ollama reasoning trace)
- `response`
- token and duration fields from Ollama
- concatenated trajectory `thinking + "\n" + response`

Saturation uses only this trajectory text (and word counts derived
from it). It must not use the canonical solution, unit tests, or
pass/fail.

## Saturation detector (formula frozen; numeric thresholds from calibration mechanics)

Tokenize with `[A-Za-z0-9_]+`, case-folded. Let `W` be the word
sequence of a prefix of the trajectory.

If `len(W) < 80`, the prefix is **not** high-saturation.

Features:

1. `dup_rate_8` = `1 - unique(8-grams) / n_8grams` over `W`
   (0 if fewer than 8 words).
2. `novelty_100` = unique words in the last `min(100, len(W))` words
   divided by that window length.
3. `has_solution` = the prefix contains a ```python``` (or ```) block
   that includes `def {entry_point}`.
4. `n_words` = `len(W)`.

**HIGH-SATURATION** prefix = the shortest prefix, aligned to a
newline if possible otherwise to a word boundary, such that:

- `n_words >= W_min`, and
- at least two of:
  - `dup_rate_8 >= T_dup`
  - `novelty_100 <= T_nov`
  - (`has_solution` is false and `n_words >= W_long`)

**LOW-SATURATION** prefix = a prefix with `n_words` in
`[0.8 L*, 1.2 L*]` that does **not** meet the HIGH rule, where `L*`
is the median `n_words` of HIGH prefixes on **calibration** (if no
calibration HIGH prefix exists, `L* = 160`).

If a task has both an early LOW prefix at `L*` and a later HIGH
prefix, it may appear in both groups with those two frozen prefixes.

Threshold rule (verifier unused):

After calibration initial trajectories only:

- `W_min = max(80, floor(P25(n_words of cal trajectories)))`
- `W_long = max(W_min + 40, floor(P50(n_words of cal trajectories)))`
- `T_dup = max(0.12, P75(dup_rate_8 of cal full trajectories))`
- `T_nov = min(0.55, P25(novelty_100 of cal full trajectories))`

Write the four numbers to
`results/raw/E000_detector_thresholds.json` and freeze them **before**
any evaluation intervention. Do not change them after seeing
evaluation success.

## Intervention arms (identical remaining budget)

From the frozen prefix, one `/api/chat` call per arm.
`num_predict = 1024`, same model settings.

The user message is:

```text
{original_task_user_prompt}

--- FROZEN REASONING PREFIX (do not rewrite the prefix) ---
{prefix}
--- END PREFIX ---

{ARM_INSTRUCTION}

Continue from the prefix. Use only the remaining generation budget. End with one complete implementation in a single fenced python code block.
```

### A1 — CONTINUE_LOCAL

```text
Continue solving from the current reasoning. Do not explicitly change strategy. Extend the same approach until you produce a final implementation.
```

### A2 — BRANCH_LOCAL

```text
Abandon the current approach. Try a substantially different approach that stays inside the same problem domain (same programming task, ordinary alternative algorithm or implementation). Do not invoke analogies from other fields. Then produce a final implementation.
```

### A3

Not used.

### A4 — STRUCTURAL_ESCAPE

```text
Stop extending the current line of reasoning. Abstract the problem in terms of states, transitions, constraints, resources, invariants, feedback, failure modes, thresholds and objective. Identify a mechanism from a semantically distant domain that has the same underlying structure. Map that mechanism back to this problem, then continue solving from the new representation.
```

No external retrieval. No tool use.

## Groups

Apply A1/A2/A4 to HIGH prefixes and to LOW prefixes on evaluation
tasks. Calibration tasks are not used for confirmatory arm
comparisons.

If `n_high < 15` or `n_low < 15` on evaluation, the saturation
interaction is **unevaluable**. Then:

- if A4 does not beat A1 on the available high (or all-eval) set:
  `STOP — NO STRUCTURAL ESCAPE SIGNAL`
- else: `CONTINUE — MIXED SIGNAL`

## Primary analysis

Outcome: plus-test success (0/1) per task-prefix-arm.

- `Δ_high = mean(A4 − A1)` on evaluation HIGH prefixes
- `Δ_low = mean(A4 − A1)` on evaluation LOW prefixes
- `EscapeAdvantage = Δ_high − Δ_low`
- Also `Δ_high_A4A2 = mean(A4 − A2)` on evaluation HIGH prefixes

Paired task-level differences within a group (same task, same
prefix, different arm).

Bootstrap: 10,000 replicates, `numpy.random.RandomState(0)`, resample
tasks with replacement within each group. For EscapeAdvantage,
resample HIGH and LOW independently and subtract.

Report point estimates and 95% percentile CIs.

**Material** improvement: point Δ ≥ +0.05 **and** 95% CI lower bound
> 0.

## Interpretation (frozen)

**CONTINUE — STRUCTURAL ESCAPE SIGNAL** only if all hold on evaluation:

1. A4 materially beats A1 on HIGH
2. EscapeAdvantage > 0 and its 95% CI excludes 0
3. Δ_high > Δ_low (already implied by 2 if CI is on the interaction)
4. A4 materially beats A2 on HIGH **or** A4−A2 HIGH point ≥ +0.05 with
   CI excluding 0

**CONTINUE — GENERIC BRANCHING SIGNAL** if A2 and A4 both materially
beat A1 on HIGH and A4 does not materially beat A2 on HIGH.

**CONTINUE — MIXED SIGNAL** if the A4 direction is positive on HIGH
but statistics are weak, n_high/n_low insufficient, or there is no
convincing saturation interaction.

**STOP — NO STRUCTURAL ESCAPE SIGNAL** if A4 does not improve HIGH
verified success, LOW looks similar without a positive interaction,
or ordinary branching explains the gain.

Do not change A4 text after seeing evaluation results.

## Secondary (not confirmatory)

Ollama `eval_count`, `eval_duration`, wall time, plus-test success.
GPU-seconds ≈ `eval_duration` when `ollama ps` reports GPU.
Energy: **unavailable** if NVML remains broken (`Driver/library
version mismatch`). No compute-efficiency claim.

## Leakage / hygiene

- Detector never sees tests or canonical solutions
- Evaluation interventions start only after detector thresholds are
  frozen
- Nested R1 is not used
- temperature 0; no sampling hunt
- Extract code from the last fenced python block; if none, fail the
  verifier

## Stop / unevaluable

- Ollama cannot finish evaluation on GPU: record unevaluable; do not
  switch models
- HumanEval+ verifier cannot run: STOP and report
- Fewer than 15 HIGH or 15 LOW eval prefixes: interaction unevaluable
  (rule above)

## Not in E000

Structural retrieval, analogy databases, multi-agent, web search,
failure memory, weight updates, prompt tuning on evaluation,
Paper 2 prose, novelty or compute-saving claims.
