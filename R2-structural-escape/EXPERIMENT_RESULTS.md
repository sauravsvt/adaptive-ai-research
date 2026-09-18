# Paper 2 Experimental Record

## Research Question

When a language model's reasoning has become measurably saturated, does
forcing a structural escape produce better verified solutions than
continuing the same reasoning or merely trying another ordinary
in-domain approach?

## Hypothesis

On HumanEval+ plus-tests, A4 (structural escape) beats A1 (continue)
more on high-saturation prefixes than on low-saturation prefixes, and
also beats A2 (ordinary branch) on high-saturation prefixes.

Not a paper claim until E000 is frozen and interpreted.

## Current Status

R2 CLOSED.

E000 confirmatory analysis frozen: **CONTINUE — MIXED SIGNAL**.

E001 confirmatory analysis frozen: **STOP — NO A4 OVER A1 SIGNAL**.

Do not start E002. Do not retune A1/A4 or K. Do not modify E000/E001
artifacts. See `CLOSE.md`.

## Hardware / software (live, 2026-09-17)

- Ollama: 0.33.3
- Model: `gpt-oss:20b` id `17052f91a42e`
  blob `sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb`
- Probe: `100% GPU`, temperature 0, think medium
- NVML: unavailable (`Driver/library version mismatch`, library 580.178)
- Python: 3.12.3, project venv `R2/.venv`
- evalplus: 0.3.1
- HumanEval+: v0.1.10, 164 tasks
- MBPP+: v0.2.0, 378 tasks (377 plus-testable)

## Software isolation

R2 does not import, copy, or depend on R1 experimental artifacts.

## E000

See `PREREG.md` and `configs/E000_structural_escape.json`.

### Freeze (2026-09-17, before evaluation interventions)

- Benchmark: HumanEval+ v0.1.10, n=164
- Split: 40 calibration / 124 evaluation (`sha256("R2-E000|"+task_id)`)
- Frozen copies: `results/frozen/E000_prereg/`
  - `PREREG.md` sha256 `9bf07f9437f04bf7c0666a136ac29deae3d7f76d6c2159f03e96d24cb70096c4`
  - `E000_structural_escape.json` sha256 `002983b0bd858de6fa5c1af692ab5734feca4c6a946e72b2ad8c894feda07b28`
  - `E000_split.json` sha256 `59375a3e0db4bf6079aec639953cc0647aceb5c566a05ad22e716c0c796cc768`
- Verifier smoke: HumanEval/1 canonical plus-tests PASS

Detector numeric thresholds frozen from 40 calibration initials
(verifier unused) before evaluation interventions:

- `W_min=199`, `W_long=307`, `T_dup=0.12`, `T_nov=0.465`, `L*=319`
- calibration HIGH prefixes for `L*`: 9
- `results/frozen/E000_prereg/E000_detector_thresholds.json`

### Execution

Started `scripts/r2_e000.py --stage all`. Log: `results/logs/E000_run.txt`.

Calibration initials paused at 31/40 (`HumanEval/115`) after Ollama
CUDA abort (`ggml_cuda_error` / illegal memory access). Driver/library
mismatch remains. Runner now waits for a one-token health ping after
HTTP 500 and retries the same frozen generation settings. No prompt or
threshold change. `HumanEval/115` succeeded when deferred after other
calibration tasks.

Evaluation initials: 124/124. Frozen prefixes before arm scoring:
HIGH 41, LOW 59, 100 prefixes on 82 evaluation tasks, 300 arm calls
all completed. Plus-tests: 300/300. Log: `results/logs/E000_run.txt`.
Frozen run artifacts: `results/frozen/E000_run/`.

### Confirmatory table (HumanEval+ plus-tests PASS)

Success rates (n successes / n prefixes):

                    A1 Continue   A2 Branch   A4 Structural
High saturation     26/41 0.634   27/41 0.659  27/41 0.659
Low saturation      51/59 0.864   47/59 0.797  55/59 0.932

Paired bootstrap, 10,000 replicates, seed 0:

- A4−A1 high: +0.024, 95% CI [−0.049, +0.122], n=41
- A4−A1 low:  +0.068, 95% CI [+0.017, +0.136], n=59
- interaction EscapeAdvantage = (A4−A1 high) − (A4−A1 low):
  −0.043, 95% CI [−0.150, +0.064]
- A4−A2 high: +0.000, 95% CI [−0.098, +0.098], n=41
- A2−A1 high: +0.024, 95% CI [−0.073, +0.122], n=41

Material improvement was pre-defined as Δ ≥ +0.05 and 95% CI lower
bound > 0.

### Frozen decision

A4 does not materially beat A1 on high-saturation prefixes. A4 and A2
are identical on high-saturation prefixes. The A4−A1 difference is
larger on low-saturation prefixes, so the saturation interaction is
negative and the CI includes 0. The high-saturation A4−A1 point
estimate is slightly positive but unstable.

**CONTINUE — MIXED SIGNAL**

This is not a structural-escape confirmation. It is also not a clean
generic-branching confirmation (A2 does not materially beat A1 on
high-saturation prefixes). Do not change the A4 prompt after seeing
these evaluation scores. Do not start the next experiment.

### Secondary (no compute-efficiency claim)

Intervention-arm means:

                    eval tokens   wall s   eval GPU-s
High A1             709.5         13.13    12.79
High A2             732.2         13.31    13.15
High A4             680.2         12.39    12.21
Low A1              422.9          7.88     7.60
Low A2              535.3          9.74     9.58
Low A4              423.9          7.75     7.58

- All 300 intervention calls: wall 3089 s, eval-duration 3026 s
- 164 initial trajectories: wall 1935 s, eval-duration 1892 s
- Energy: unavailable (NVML driver/library mismatch)
- 56 / 300 intervention outputs had no extractable solution (scored fail)
- `done_reason`: 241 stop, 59 length

### Analysis freeze

- `results/raw/E000_analysis.json` and `results/frozen/E000_run/E000_analysis.json`
- analysis sha256 `1ffd0c7ae4b95397f75ca452da8877aed659c129324ce9ff72173c6968850727`

## E001

See `PREREG_E001.md` and `configs/E001_fixed_prefix.json`.

### Stage-1 freeze (2026-09-17, before any E001 generation)

Prereg frozen exactly as reviewed:
`PREREG_E001.md` sha256 `cca6fb2e20793ee7c8143e5a4c16219716f38a61fd373863bb9e44f8e4c067ad`

- Benchmark: MBPP+ v0.2.0, plus-testable n=377 (`Mbpp/793` excluded a priori)
- Dataset hash `ee43ecabebf20deef4bb776a405ac5b1`
- Model blob `sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb`
- Frozen copies: `results/frozen/E001_stage1/`
  - `PREREG_E001.md` sha256 `cca6fb2e20793ee7c8143e5a4c16219716f38a61fd373863bb9e44f8e4c067ad`
  - `E001_fixed_prefix.json` sha256 `243e52c9fc9a1f67a6486b2f288b926ca417e15c6b90a9e30496dcef253ae3fd`
  - `E001_plus_testable.json` sha256 `2c2fdabe17f720140ed6151aafe4e226603b0b8eda23a1737d44adc20e33d423`
  - `E001_stage1_manifest.json` sha256 `f6ab4cf3ee794ed98120b27c5ee6fe996e2fd6a1dae671b6353b641e72e989bc`
- No git repo; checkpoint is the Stage-1 freeze directory and SHA256SUMS.

Started `scripts/r2_e001.py --stage all`. Log: `results/logs/E001_run.txt`.

### Stage-2 freeze (after 377 initials, before any arm)

K=160 eligibility only. No plus-test labels inspected before this freeze.

- Plus-testable initials: 377/377
- Usable n: **341** (≥ 80)
- Unusable short trajectories: 36
- Execution order: A1-first 166, A4-first 175
- Fence-open diagnostic (non-decision, not a stratum): 93 / 341
- Frozen copies: `results/frozen/E001_stage2/`
  - `E001_usable.json` sha256 `4436dd26ab98d56805b8b264cca605abdc58c9ac525bdd9d6bac6a82f0868873`
  - `E001_prefixes.jsonl` sha256 `1b544cd3451895fbd498334b08d8b593c11e104d25793a8d39d32d43e611f757`
  - `E001_initial_hashes.json` sha256 `c868a30d507a836a9884e8aee198815ad05ca380c381db7bdfa588ac9bf6e606`
  - `E001_initial.jsonl` sha256 `c4fc2955ab303047ddff47106ad2951d232992f222fc92304a73bf2d8a7a559f`
  - `E001_stage2_manifest.json` sha256 `55ef7aee71755a63bf402be31d2b907011d199748611c45998accd19b1df48d7`

### Execution

Initials 377/377 and arms 682/682 completed with no FAILED retries
and no CUDA abort in `results/logs/E001_run.txt`. Plus-tests: 682/682.
A2 was not run. Frozen run artifacts: `results/frozen/E001_run/`.
Process wall: 9408 s (2.61 h).

### Confirmatory table (MBPP+ plus-tests PASS)

Success rates (n successes / n usable prefixes):

                    A1 Continue           A4 Structural
Fixed K=160         252/341 0.739         253/341 0.742

Paired bootstrap, 10,000 replicates, seed 0, n=341:

- A4−A1: +0.003, 95% CI [−0.023, +0.029]

Material improvement was pre-defined as Δ ≥ +0.05 and 95% CI lower
bound > 0.

McNemar (descriptive only): A4-pass/A1-fail 10, A4-fail/A1-pass 9,
both pass 243, both fail 79.

### Frozen decision

A4 does not materially beat A1. The point estimate is near zero, the
CI includes 0, and A1 success is 0.739 (< 0.95), so this is not
ceiling-limited.

**STOP — NO A4 OVER A1 SIGNAL**

Do not change A1/A4 text or K after seeing these scores. Do not add
A2. Do not stratify by the fence diagnostic. Do not start E002.

### Secondary (no compute-efficiency claim)

Intervention-arm means:

                    eval tokens   wall s   eval GPU-s
A1                  409.2          7.52      7.35
A4                  418.1          7.73      7.52

- 377 initial trajectories: wall 4167 s, eval-duration 4110 s,
  output tokens 226672
- 682 intervention calls: wall 5199 s, eval-duration 5070 s,
  output tokens 282099
- Energy: unavailable (NVML driver/library mismatch)
- 74 / 682 intervention outputs had no extractable solution (scored fail)
- Arm `done_reason`: 608 stop, 74 length
- Initial `done_reason`: 345 stop, 32 length
- Execution failures/retries: none

### Analysis freeze

- `results/raw/E001_analysis.json` and `results/frozen/E001_run/E001_analysis.json`
- analysis sha256 `ac3e99d2537e862df165b76dee913960098dfb68b2f46809ff5a0c5a83158705`
- `E001_arms.jsonl` sha256 `1ee97330d4f92a1736d75624ab36a98f8396fef0240a43c7c7cd85f93230d502`
- `E001_verify.jsonl` sha256 `8fafbf99522e3c489451919c5257eda1ec1a1be2a40cf397c80000770f457c60`

## R2 close

Closed 2026-09-18. Confirmatory project decision is E001's
**STOP — NO A4 OVER A1 SIGNAL**. E000/E001 artifacts were not modified.
Hash checkpoint: `results/frozen/R2_close/`. E002 not started.
