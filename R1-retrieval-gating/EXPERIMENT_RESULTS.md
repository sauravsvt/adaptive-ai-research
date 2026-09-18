# Paper 1 Experimental Record

## Research Question

Can a local software-engineering AI system improve verified task success per
unit of real compute by dynamically deciding whether to STOP/abstain, reason,
retrieve repository context, search external documentation, use a small local
model, escalate to a stronger local model, verify, or retry — instead of using
the same expensive strategy for every task?

First-experiment narrowing: can the system determine WHEN repository retrieval
is useful, WHEN retrieval should be skipped, and eventually WHEN additional
model compute should be spent?

## Hypothesis

An evidence-gated controller can decide RETRIEVE vs ABSTAIN (and later
SMALL vs LARGE model) using pre-outcome signals, improving useful context per
compute relative to always-retrieve / never-retrieve / simple score-threshold
policies, without leaking ground-truth files.

Not yet tested as a paper claim. E000–E002 remain the frozen setup plus
one-subset BM25 reproduction. E003–E005 lock the official lexical/BM25 suite.
E006 is the first authorized exploratory test of retrieval score-shape evidence
for RETRIEVE vs ABSTAIN (promising on lexical; BM25 did not replicate). E007
tests whether that frozen feature family generalizes to RepoMap and official
Qwen embedding retrieval. Do not claim a paper result from E006/E007 alone.

## Current Status

EXPLORATORY

E000–E006 remain frozen. E007 is complete: CONTINUE — LEXICAL-SPECIFIC
SIGNAL. The frozen 12-feature family did not show a reliable C3−C0 gain on
official RepoMap or official Qwen embedding under the pre-registered
reliability rule. Not a paper claim. Do not start E008.

## Hardware

Recorded 2026-09-09 from live machine queries (not trusted from protocol text).

- CPU: Intel(R) Core(TM) i7-14700
- Topology: 20 cores / 28 threads (lscpu: 1 socket, 20 cores/socket, 2 threads/core, 28 CPUs)
- RAM: 31 GiB total (`free -h`); ~10 GiB available at first recording; 8.0 GiB swap
- GPU: NVIDIA RTX 4000 SFF Ada Generation
- VRAM: 20475 MiB
- GPU power limit: 70.00 W
- NVIDIA driver: 580.173.02
- CUDA Version (nvidia-smi): 13.0
- GPU state at first recording: ~721 MiB used (desktop/display processes), 37 C, P8, 14 W
- OS: Ubuntu 24.04.4 LTS (Noble Numbat)
- Kernel: Linux 7.0.0-31-generic (`SauravPC`)
- Disk (project filesystem `/dev/nvme0n1p2`): 915G total, 335G used, 535G available (39%) at first recording

Protocol-stated historical Ollama `gpt-oss:20b` benchmark numbers were NOT
re-verified in this first task. GPU was not used for E001/E002 (CPU-only
lexical/BM25 evaluator).

## Software Environment

Recorded 2026-09-09.

System:

- System Python: 3.12.3 (`/usr/bin/python3`)
- System pip (before venv): 24.0
- Ollama: 0.33.3
- zstd: 1.5.5 (`/usr/bin/zstd`)
- tar: `/usr/bin/tar`
- `hf` CLI: not installed system-wide; installed in the project venv

Isolated venv: `agent-retrieval-bench/.venv`

- venv Python: 3.12.3 (`agent-retrieval-bench/.venv/bin/python`)
- venv pip: 26.2.1 (upgraded from the venv bootstrap 24.0; see Deviations)
- `agent-retrieval-bench`: 0.2.1 (editable install of cloned repo)
- pytest: 9.1.1
- huggingface_hub: 1.30.0 (`hf` CLI 1.30.0)
- Full freeze: `results/logs/E002_pip_freeze.txt`

Official `pyproject.toml` runtime dependencies are empty. pytest and
huggingface_hub were added only to run the official test command and the
official download CLI. Embedding extras were not installed.

E006 additionally installed `scikit-learn==1.9.0` (pulling numpy 2.5.3,
scipy 1.18.1, joblib, threadpoolctl, narwhals, cloudpickle) in the same
isolated venv solely to fit the frozen logistic gate. No embedding extras.
GPU unused.

## Repository / Commit Information

Project root: `/home/sauravsvt/Desktop/Research/R1`

Initialized as a Git repository after E002 (pre-method freeze). Nested
`agent-retrieval-bench` Git repository was not altered.

- R1 pre-method commit: `d384c94c0048734b10295f768466ab4c8ff19e01`
  - Subject: Record pre-method experimental state after E002 BM25 reproduction.
  - Author env-only (no `git config` write): Saurav Shriwastav `<sauravsvt@localhost>`
  - Branch: `master`
- Git HEAD recorded immediately before E007 protocol/commit work:
  `d384c94c0048734b10295f768466ab4c8ff19e01` (E003–E006 artifacts were
  present on disk but not yet committed at that moment).
- `.gitignore` excludes the nested ARB checkout (corpora, venv, caches) and
  tracks protocol/config/scripts/`EXPERIMENT_RESULTS.md`/frozen results.

Initial tracked contents at that commit included `CHAT.md`, `Prompt1.md`,
`Step1.md`, E000–E002 artifacts, and configs.

No git reset or history rewrite was performed.

Canonical benchmark clone:

- URL: https://github.com/eyuansu62/agent-retrieval-bench
- Local path: `/home/sauravsvt/Desktop/Research/R1/agent-retrieval-bench`
- Branch: `main`
- Commit: `07014c986f3deadb1548c62b32c0ffbe6a81465d`
- Author date: 2026-08-04 12:00:58 +0800
- Subject: Make the published paper discoverable from the benchmark
- Package version: 0.2.1
- Tags present: `v0.2.0`, `v0.2.1`

## Dataset

Source: Hugging Face dataset `eyuansu71/agent_retrieval_bench` via official
`arb download-benchmark`.

Release used in E002:

- Release ID: `v2_edit2ripple`
- Schema: `arb_subset_release_v2`
- Task: `edit2ripple` only
- Samples: 58
- Split: none (full released subset; no train/dev/test split in this bundle)
- Repositories: 10 (`caddyserver/caddy` 6, `clap-rs/clap` 5, `etcd-io/etcd` 6,
  `gin-gonic/gin` 17, `huggingface/diffusers` 1, `huggingface/transformers` 8,
  `pytest-dev/pytest` 1, `spring-projects/spring-boot` 3, `tokio-rs/tokio` 6,
  `vitejs/vite` 5)
- Corpus snapshots: 44
- Corpus files: 68647
- Corpus chunks: 1186092
- Manifest created_at: 2026-06-26T13:51:43.419866+00:00
- `all_gold_in_corpus`: true
- `all_samples_have_corpus`: true
- `arb validate`: 58 total, 0 invalid
- `samples.jsonl` identical to `edit2ripple.jsonl`

Hashes:

- Archive `agent_retrieval_bench_v2_edit2ripple.tar.zst`
  SHA-256: `a174196d69b531d176a65c76fea928b3f1c893710baa4efccc48e901ff404b2c`
  (matches Hugging Face LFS oid and the release `.sha256` file)
- `samples.jsonl` SHA-256:
  `31d97ffe815dda8730149880c0159239a986eceb306e5a5df816dfc420717cef`

Full v2 releases used from E003 onward (all validated, 0 invalid samples):

| Release | Samples | samples.jsonl SHA-256 | archive SHA-256 |
| --- | ---: | --- | --- |
| `v2_code2test` | 106 | `712b2699d3f963c2f940688ae5248304263c4ecda1b3831b2801c95712a50b85` | `387cdfb25835b176ba27707d43dc31cae6b31514231923af237ad04deef19c0b` |
| `v2_comment2context` | 80 | `543267024f7f06127c50664a3a1b8825d3c213e4b12dbbfabf9a3346902ad796` | `be68161844d63c64e687e0c6da1d52434160fafcaf8932a5767fbe64b643b3f5` |
| `v2_trace2code` | 101 | `9d0ff50155fa4f65c1bbb632abc4f1f11393c50fa7b0a9249e06128b368b6266` | `19b252e8cfff42107fedc74005dbb6972f2970af33651ce0c1571546819e41c4` |
| `v2_edit2ripple` | 58 | `31d97ffe815dda8730149880c0159239a986eceb306e5a5df816dfc420717cef` | `a174196d69b531d176a65c76fea928b3f1c893710baa4efccc48e901ff404b2c` |
| `v2_abstention` | 82 | `f469624153339e0847fe882e937e60f42fc386cc0285b6be56a960893b31e6f6` | `bb358d6b65b7ef6aa36b417240cab4f2d51a8d69e699e573cf324ab339a5c1d8` |
| `v2_selective_retrieval_balanced` | 164 | `86d8ccdb3ecaeea2973fe78c62b25968fd80f645de2fd4da1e1654a39a95dba0` | `470876de20453e22fa905e132dfdd1d99799bb4bda0e1acd3ea32f17267956c9` |
| `v2_selective_retrieval_natural` | 427 | `6c7b02b0f8684fd7613bf7c7e7523dc41b1058c4a886f47b33b8b5546656a3d7` | `1be829d7fc03631765bff389970afabd4f74be54d9c0d7eaab00bb9c467fc0cc` |

Positive total: 106+80+101+58 = 345. No-gold: 82 (50 natural-like + 32
`counterfactual_wrong_repo`). Natural mixed list: 345+82 = 427.
`arb merge-corpus-manifests`: 271 unique snapshots (365 input rows, 94
duplicates), matching the official README.

No train/dev/test split was invented. Split: none (official full releases).

## Frozen Configurations

- `configs/E002_official_bm25_v2_edit2ripple.json`
- Bundled official eval:
  `results/frozen/E002_official_bundled_v2_edit2ripple_bm25/`
- Local reproduction:
  `results/frozen/E002_reproduced_v2_edit2ripple_bm25/`
- R1 git pre-method commit: `d384c94c0048734b10295f768466ab4c8ff19e01`
- `configs/E004_official_positive345.json`
- `configs/E005_official_selective.json`
- Release checksums: `results/frozen/E003_release_checksums/`
- 345-sample aggregate: `results/frozen/E004_positive345/`
- Selective composition + summaries: `results/frozen/E005_selective/`

Experiment 1B primary metric (frozen before any of our method code):

- Primary: Selective Success@20
- Secondary: Recall@20, MRR, canonical BCY@8k, retrieval latency, CPU time
  (GPU unused for these lexical/BM25 runs)

## Baselines

### B0 — official BM25 on `v2_edit2ripple`

Command:

```bash
arb eval-baseline \
  --derived data/benchmark/v2_edit2ripple \
  --corpus data/corpus/v2_edit2ripple \
  --ranker bm25 \
  --candidate-filter all_files \
  --no-keep-list \
  --out /home/sauravsvt/Desktop/Research/R1/results/baselines/E002_v2_edit2ripple_bm25_summary.json \
  --details /home/sauravsvt/Desktop/Research/R1/results/raw/E002_v2_edit2ripple_bm25_details.jsonl
```

Working directory: `agent-retrieval-bench` with `.venv` activated.

Configuration:

- Ranker: BM25 (`k1=1.5`, `b=0.75`, official implementation in
  `src/agent_retrieval_bench/baseline.py`)
- Candidate filter: `all_files`
- Keep-list: none (`--no-keep-list`)
- Samples: 58
- Corpora: 44 commit snapshots
- Seed: n/a (deterministic ranker; no RNG)

Metrics (local rerun; identical to bundled official summary except runtime):

| Metric | Value |
| --- | ---: |
| evaluated | 58 |
| skipped | {} |
| Recall@5 | 0.20689655172413793 |
| Recall@10 | 0.2873563218390805 |
| Recall@20 | 0.49856321839080464 |
| MRR | 0.15362462887170653 |
| Precision@5 | 0.06896551724137931 |
| Precision@10 | 0.05 |
| Precision@20 | 0.039655172413793106 |
| F0.5@5 | 0.07800077234110217 |
| F0.5@10 | 0.0592193093219948 |
| F0.5@20 | 0.04832910479677531 |
| gold_coverage@8k | 0.0603448275862069 |
| context_efficiency@8k | 0.034408658162168024 |
| coverage_auc@20 | 0.3043103448275862 |
| redundancy@8k | 0.17567505790894097 |

Official README states that JSON fields named `gold_coverage@8k` and
`context_efficiency@8k` are legacy character-counted packing, not canonical
BCY. This run did not compute canonical BCY separately.

Runtime:

- Local wall_time_seconds (evaluator): 91.69567346000076
- `/usr/bin/time` elapsed: 1:31.93
- User CPU: 89.82 s
- Max RSS: 1214928 KiB (~1.16 GiB)
- Bundled official artifact runtime: 180.37311317026615 s (`progress: false`)
- GPU: not used

Raw result path:

- Summary: `results/baselines/E002_v2_edit2ripple_bm25_summary.json`
- Details: `results/raw/E002_v2_edit2ripple_bm25_details.jsonl`
- Log: `results/logs/E002_eval_bm25.txt`
- Frozen copy: `results/frozen/E002_reproduced_v2_edit2ripple_bm25/`

SHA-256:

- Reproduced summary:
  `6fc081a66625608a22d32253830a27609f269599aab2f6e6f2092c348e0a16c2`
- Reproduced details:
  `c377b1af5a9798d118fe937be0c84fc4abff9b211b24bdcb1e5fa5c2c6a44568`
- Bundled official details:
  `c377b1af5a9798d118fe937be0c84fc4abff9b211b24bdcb1e5fa5c2c6a44568`
- Bundled official summary:
  `1268180ed2d254cf34d7f6b07d1281bd93a68d5a98012865853098cb0d8aff0c`

Details JSONL of the local rerun is byte-identical to the bundled official
details. Summaries differ only in the `runtime` object (`progress` flag and
wall time).

This is **not** a reproduction of the paper's 345-sample overall BM25 row
(Recall@20 0.4452 / MRR 0.1520 / BCY@8k 0.2051). It is a reproduction of the
official README BM25 command on the official example subset.

### B0-full — official lexical on 345 positive samples (E004)

Command: `scripts/run_official_positive_baselines.sh` then
`scripts/aggregate_official_positive.py` (official `summarize_details` +
`bcy_curve.evaluate_run`).

Configuration: `--ranker lexical --candidate-filter all_files --no-keep-list`
on each of `v2_code2test`, `v2_comment2context`, `v2_trace2code`,
`v2_edit2ripple`.

Metrics (345-sample mean):

| Metric | Reproduced | Published (README, 4 d.p.) | abs diff |
| --- | ---: | ---: | ---: |
| Recall@20 | 0.4939613526570048 | 0.4940 | 3.86e-5 |
| MRR | 0.15741480361234275 | 0.1574 | 1.48e-5 |
| BCY@8k | 0.264975845410628 | 0.2650 | 2.42e-5 |

Runtime: subset walls 12.72 s + 163.53 s + 86.89 s + 167.51 s (lexical);
aggregate BCY 20.88 s. GPU unused.

Raw: `results/raw/E004_*_lexical_details.jsonl`,
`results/raw/E004_positive345_lexical_details.jsonl`,
`results/baselines/E004_positive345_lexical_summary.json`.

### B1 — official BM25 on 345 positive samples (E004)

Same official evaluator as E002, now over all four positive releases.
`v2_edit2ripple` BM25 reused frozen E002 details (byte-identical to bundled
official details).

Metrics (345-sample mean):

| Metric | Reproduced | Published check | abs diff |
| --- | ---: | ---: | ---: |
| Recall@20 | 0.4451690821256039 | 0.4452 | 3.09e-5 |
| MRR | 0.1520385836822835 | 0.1520 | 3.86e-5 |
| BCY@8k | 0.20507246376811594 | 0.2051 | 2.75e-5 |

Discrepancy: none beyond 4-decimal rounding of the published table.
Published values were not hard-coded into evaluation logic.

Runtime: subset walls 13.27 s + 169.07 s + 91.70 s (E002) + 175.80 s;
aggregate BCY included in the 20.88 s pass above. Max RSS during BCY ~1.61 GiB.
GPU unused.

Raw: `results/raw/E004_positive345_bm25_details.jsonl`,
`results/baselines/E004_positive345_bm25_summary.json`,
`results/baselines/E004_positive345_comparison.json`.

### B2 — official selective lexical/BM25 (E005)

Command: `scripts/run_official_selective_baselines.sh` with
`--candidate-filter all_files --no-keep-list` and corpus
`data/corpus/v2_selective_mixed`.

Selective Success@20, always-retrieve (`no_abstain`):

| Manifest | n | Lexical | BM25 |
| --- | ---: | ---: | ---: |
| natural | 427 | 0.4613583138173302 | 0.42857142857142855 |
| balanced | 164 | 0.25609756097560976 | 0.24390243902439024 |

Official repo-grouped 5-fold OOF (natural-only 395: 345 positive + 50
natural no-gold): lexical 0.2937 vs always-retrieve 0.4987; BM25 0.2203 vs
always-retrieve 0.4633.

No thresholds were tuned for our method.

Raw: `results/raw/E005_*_details.jsonl`,
`results/baselines/E005_*_summary.json`.

## Proposed Method

E006 SCORE-SHAPE EVIDENCE GATE (exploratory; contract frozen before fitting).

Primary dataset: official `v2_selective_retrieval_natural`, n=427. Primary
metric: Selective Success@20. Primary retrieval backend: LEXICAL (stronger
frozen always-retrieve / positive-only baseline). Secondary replication: BM25.
Gates operate on one ranker only. RETRIEVE uses that ranker's frozen top-20
unchanged; ABSTAIN returns no files. Ranking is not changed.

Train labels (allowed folds only): RETRIEVE = gold repository context;
ABSTAIN = official no-gold. Outer-test inference receives no ground-truth
label or gold-file information.

Frozen 12 pre-outcome score-shape features only: top1, top2, top1−top2
margin, safe top1/top2 ratio, mean/std top5, mean/std top20, max−min top20,
top1 z-score vs top20, top5/top20 mass, normalized entropy of non-negative
top20 scores. No query/repo/task/filename/embedding/LLM/dependency/gold-file
/no-gold-reason/counterfactual-marker features.

Comparators: C0 ALWAYS_RETRIEVE; C1 official top-score repo-grouped OOF
threshold (procedure unchanged); C2 TOP1_LOGISTIC (feature 1 only);
C3 SCORE_SHAPE_LOGISTIC (all 12). Classifier: sklearn LogisticRegression,
L2, C=1.0, solver=liblinear, max_iter=2000, random_state=0. Standardize with
training-fold statistics only. No hyperparameter tuning.

CV: official repository-grouped outer 5-fold from E005 natural 427
`repo_folds`. Nested inner repo-grouped 5-fold on each outer-training set
via the official `assign_repo_folds` function. Inner threshold maximizes
Selective Success@20 on inner validation predictions only. If nested CV is
invalid, STOP; do not in-sample-tune.

Ablation (frozen): C3_NO_CONCENTRATION drops entropy, top5/top20 mass, and
top1 z-score.

Config: `configs/E006_score_shape_gate.json`.

E007 (exploratory; contract frozen before backend/gate code): test whether
the SAME frozen 12-feature family generalizes to official RepoMap and official
Qwen/Qwen3-Embedding-4B. Fit per-backend nested CV weights; do not transfer
lexical coefficients as the primary test. Do not add features.

## Experiment Log

### Experiment E000

Date/time: 2026-09-09T16:04+02:00
Purpose: Inspect project root, record environment, create result directories
  and this handover file.
Hypothesis tested: none (setup)
Configuration: n/a
Command/script: environment inspection (`python3 --version`, `nvidia-smi`,
  `lscpu`, `free -h`, `df -h`, `ollama --version`, `git status`)
Seed: n/a
Input split: n/a
Output file: `EXPERIMENT_RESULTS.md`
Metrics: n/a
Interpretation: Project root is `R1`, not `~/research/paper1-evidence-gated`.
  Work proceeded from the current repository root.
Decision:
- CONTINUE

### Experiment E001

Date/time: 2026-09-09T16:05+02:00
Purpose: Clone Agent Retrieval Bench, install in an isolated venv, run the
  official test suite.
Hypothesis tested: none (tooling validity)
Configuration:

- clone `https://github.com/eyuansu62/agent-retrieval-bench.git`
- `python3 -m venv .venv`
- `pip install -e .`
- extra: `pip install pytest` (required to execute the documented
  `pytest -q` command; not listed in `pyproject.toml`)

Command/script:

```bash
PYTHONPATH=src pytest -q
```

Seed: n/a
Input split: n/a
Output file: `results/logs/E001_pytest.txt`
Metrics:

- 325 passed
- 6 skipped
- 0 failed
- wall ~5.58 s (`/usr/bin/time`); pytest reported 5.21 s

Skipped tests:

- 5× `tests/test_embedding_eval.py`: numpy is optional
- 1× `tests/test_v1_1.py`: frozen V1 fixture is not available

Interpretation: Official unit/integration suite is green on this machine.
  Skips are optional embedding/numpy and a missing frozen V1 fixture, not
  BM25 evaluator failures.
Decision:
- CONTINUE

### Experiment E002

Date/time: 2026-09-09T16:07+02:00 through 2026-09-09T16:09:08+02:00
Purpose: Download one official release and reproduce the official BM25
  baseline unchanged.
Hypothesis tested: none (baseline reproduction)
Configuration: see `configs/E002_official_bm25_v2_edit2ripple.json`
Command/script:

```bash
arb download-benchmark --version v2_edit2ripple --local-dir data --force
arb validate data/benchmark/v2_edit2ripple/samples.jsonl
arb eval-baseline \
  --derived data/benchmark/v2_edit2ripple \
  --corpus data/corpus/v2_edit2ripple \
  --ranker bm25 \
  --candidate-filter all_files \
  --no-keep-list \
  --out results/baselines/E002_v2_edit2ripple_bm25_summary.json \
  --details results/raw/E002_v2_edit2ripple_bm25_details.jsonl
```

Seed: n/a
Input split: full `v2_edit2ripple` release (58/58)
Output file:

- `results/baselines/E002_v2_edit2ripple_bm25_summary.json`
- `results/raw/E002_v2_edit2ripple_bm25_details.jsonl`
- `results/logs/E002_download_v2_edit2ripple.txt`
- `results/logs/E002_eval_bm25.txt`

Metrics: Recall@20 = 0.49856321839080464; MRR = 0.15362462887170653;
  evaluated = 58; skipped = {}.
Interpretation: Local BM25 details match the official bundled
  `data/eval/v2_edit2ripple/bm25_details.jsonl` exactly. Baseline reproduction
  is valid for this subset/command.
Decision:
- CONTINUE

### Experiment E003

Date/time: 2026-09-09T16:18 through 2026-09-09T16:22:40+02:00
Purpose: Initialize R1 git (pre-method freeze), download remaining official
  v2 releases, validate, hash, merge selective corpus, document selective
  composition without inventing a split.
Hypothesis tested: none (baseline lock / data integrity)
Configuration: see `configs/E005_official_selective.json` composition dump
Command/script:

```bash
git init  # R1 only; nested ARB git untouched
arb download-benchmark --version <release> --local-dir data
  # remaining: v2_code2test, v2_comment2context, v2_trace2code,
  # v2_abstention, v2_selective_retrieval_balanced,
  # v2_selective_retrieval_natural
arb validate data/benchmark/<release>/samples.jsonl
arb merge-corpus-manifests --local-dir data
python scripts/inspect_selective_composition.py
```

Seed: n/a
Input split: official full releases; no invented split
Output file:

- `results/logs/E003_download_remaining_releases.txt`
- `results/logs/E003_validate_and_hash.txt`
- `results/frozen/E003_release_checksums/`
- `results/baselines/E003_selective_composition.json`

Metrics: all listed sample files 0 invalid; 271 unique mixed snapshots.
Interpretation: Selective natural = 427 (345 positive + 82 no-gold).
  Selective balanced = 164 (82 positive + 82 no-gold), a subset of natural
  IDs. No-gold strata: 50 natural-like (organic=true; reasons
  upstream_dependency 41, external_service 7, user_error 2) and 32
  counterfactual_wrong_repo. Official abstention calibration is repo-grouped
  5-fold CV on top-score thresholds (`arb report-selective-cv`), not an
  in-sample sweep chosen by us.
Decision:
- CONTINUE

### Experiment E004

Date/time: 2026-09-09T16:23:59 through 2026-09-09T16:37:30+02:00
Purpose: Reproduce official lexical and BM25 on all 345 positive samples;
  compute canonical BCY@8k with the official packer.
Hypothesis tested: none (baseline reproduction)
Configuration: `configs/E004_official_positive345.json`
Command/script: `scripts/run_official_positive_baselines.sh` then
  `scripts/aggregate_official_positive.py`
Seed: n/a
Input split: full official positive releases (345/345)
Output file:

- `results/raw/E004_v2_*_{lexical,bm25}_details.jsonl`
- `results/raw/E004_positive345_{lexical,bm25}_details.jsonl`
- `results/baselines/E004_positive345_comparison.json`
- `results/logs/E004_official_positive_baselines.txt`
- `results/logs/E004_aggregate_positive345.txt`

Metrics: BM25 Recall@20=0.4451690821256039 MRR=0.1520385836822835
  BCY@8k=0.20507246376811594 (n=345, skipped={}). Lexical
  Recall@20=0.4939613526570048 MRR=0.15741480361234275
  BCY@8k=0.264975845410628.
Interpretation: BM25 matches the published 4-decimal table
  (0.4452 / 0.1520 / 0.2051) within rounding. Lexical matches published
  0.4940 / 0.1574 / 0.2650 within rounding. edit2ripple lexical metrics
  match the bundled official summary; details differ only by a later
  `ranker` field.
Decision:
- CONTINUE

### Experiment E005

Date/time: 2026-09-09T16:37:59 through 2026-09-09T17:00:17+02:00
Purpose: Reproduce official selective lexical/BM25 on released balanced and
  natural manifests; record official OOF CV without tuning our method.
Hypothesis tested: none (baseline reproduction)
Configuration: `configs/E005_official_selective.json`
Command/script: `scripts/run_official_selective_baselines.sh` then
  `scripts/report_official_selective_cv.py`
Seed: n/a (rankers deterministic; CV fold assignment is official repo-grouped
  heuristic, not a random seed we set)
Input split: official `v2_selective_retrieval_balanced` (164) and
  `v2_selective_retrieval_natural` (427)
Output file:

- `results/raw/E005_{balanced,natural}_{lexical,bm25}_details.jsonl`
- `results/baselines/E005_*_summary.json`
- `results/baselines/E005_{balanced,natural}_selective_cv.json`
- `results/logs/E005_official_selective_baselines.txt`

Metrics (primary = Selective Success@20):

Natural mixed 427, always-retrieve (`no_abstain`):
lexical 0.4613583138173302; BM25 0.42857142857142855.

Natural-only 395 (345 positive + 50 natural no-gold), official 5-fold
repo-grouped OOF vs always-retrieve:
lexical no_abstain 0.49873417721518987 vs OOF 0.2936708860759494;
BM25 no_abstain 0.46329113924050636 vs OOF 0.22025316455696203.

Interpretation: On the paper's natural no-gold setting, official top-score
  thresholding did not improve Selective Success@20 over always retrieving.
  In-sample sweep maxima exist in the official evaluator output and were not
  used to design a split or our method.
Decision:
- CONTINUE

### Experiment E006

Date/time: 2026-09-09T19:46+02:00 (contract freeze); execution wall 1048.13 s
  the same evening (score recovery + nested CV).
Purpose: First exploratory test of whether retrieval score geometry can
  distinguish RETRIEVE vs ABSTAIN better than always-retrieve and the
  official top-score threshold, without embeddings, LLMs, RepoMap, gold
  files, or repository-answer leakage.
Hypothesis tested: score-shape evidence for RETRIEVE vs ABSTAIN (exploratory;
  not a paper claim from E006 alone).
Configuration: `configs/E006_score_shape_gate.json`

Contract frozen before classifier implementation:

- PRIMARY dataset: official `v2_selective_retrieval_natural`, n=427
  (345 positive + 82 no-gold). Do not replace after seeing results.
- Primary metric: Selective Success@20.
- Diagnostic strata only: natural-like 395; counterfactual 32; official
  balanced 164; positive 345; no-gold 82.
- Primary backend: LEXICAL. Secondary: BM25. No ranker fusion.
- If gate says RETRIEVE: frozen top-20 unchanged. If ABSTAIN: no files.
- Features: the 12 frozen score-shape features listed in Proposed Method.
- C0 ALWAYS_RETRIEVE; C1 official OOF top-score threshold; C2 top1 logistic;
  C3 score-shape logistic; ablation C3_NO_CONCENTRATION.
- Outer folds: official E005 `repo_folds` on the 427 manifest (all samples of
  one repository stay in the same fold). Inner: official `assign_repo_folds(5)`
  on each outer-training set. Nested CV preflight: VALID (each inner fold has
  both classes).
- Thresholds for C2/C3 chosen on inner validation Selective Success@20 only.
- Paired bootstrap 95% CI for C3−C0, C3−C1, C3−C2.

Missing/zero/negative score handling (frozen):

- Pad fewer than 20 file scores with 0.0.
- Missing top2: 0.0.
- Safe ratio: top1 / max(top2, 1e-12); if both |top1| and |top2| < 1e-12,
  ratio = 1.0.
- std uses population std (ddof=0). If n<2, std=0.0.
- top1 z-score: (top1 − mean_top20) / std_top20; if std_top20 < 1e-12, z=0.0.
- Mass: sum(max(s,0) for top5) / sum(max(s,0) for top20); if denominator
  < 1e-12, mass=0.0.
- Normalized entropy: clip top20 to ≥0; if mass sum < 1e-12, entropy=0.0;
  else p_i = s_i / sum, H = −∑ p_i ln p_i (0 ln 0 := 0), divide by ln(20).

Command/script: `scripts/e006_score_shape_gate.py` (implemented after this
contract block).
Seed: LogisticRegression random_state=0; paired bootstrap random_state=0;
  n_resamples=10000. Fold assignment is the official deterministic
  repo-grouped heuristic, not a sample-level random split.
Input split: official 427-sample natural manifest; outer folds from frozen
  E005 `results/baselines/E005_natural_selective_cv.json` `repo_folds`.
Output file:

- `results/raw/E006_fold_assignments.json`
- `results/raw/E006_lexical_oof.jsonl`
- `results/raw/E006_bm25_oof.jsonl`
- `results/raw/E006_fold_thresholds.json`
- `results/baselines/E006_comparison.json`
- `results/logs/E006_run.txt`
- `results/frozen/E006_score_shape_gate/`

SHA-256 (`results/frozen/E006_score_shape_gate/SHA256.json`):

- `E006_lexical_oof.jsonl`: `9ff40cf352856117dfa19268c7a006925d12f264226b04de20bad4d04c0e8b1b`
- `E006_bm25_oof.jsonl`: `8a799e2762432ab280691e7b80ca1e4dead1b6961e4a156f7effca67c3938a6a`
- `E006_comparison.json`: `2c80d91df1c6f5a2a5e5d99108b43f21a83c9c0389f1f4c610ba4af809d1c63a`
- `E006_fold_assignments.json`: `90b43566ab68cbba932c98c5ddcade7fd480a6df30771c5fcf7700aa8361118f`
- `E006_fold_thresholds.json`: `48501161d6dc7ae80ba73968fa058290b085bf509cbbee0b3e68d8f756d796b0`
- `E006_run.txt`: `e55c5bfbfae6ce97bd33c66ebdc64edfccf0cfbdc8665dfeaa9a9be8154a2173`
- `E006_score_shape_gate.json`: `da2b4f762c54ed460b2c6ee542ff25165d559672ed8a18294e8ceed3929ccc4e`
- `e006_score_shape_gate.py`: `5ce95aed7c8902e1d05a54300aa18ebe847183e8f1c39005b79b2831cd5445bd`

C1 lexical OOF Selective Success@20 matches frozen E005
`methods.lexical.out_of_fold` exactly (0.4964871194379391).

Metrics (PRIMARY = lexical OOF Selective Success@20 on official 427):

| Comparator | Selective Success@20 | retrieve rate | false abstention | no-gold abstention |
| --- | ---: | ---: | ---: | ---: |
| C0 ALWAYS_RETRIEVE | 0.4613583138173302 | 1.000 | 0.000 | 0.000 |
| C1 official top-score OOF | 0.4964871194379391 | 0.735 | 0.186 | 0.598 |
| C2 TOP1_LOGISTIC | 0.4777517564402810 | 0.979 | 0.003 | 0.098 |
| C3 SCORE_SHAPE_LOGISTIC | 0.5737704918032787 | 0.841 | 0.035 | 0.683 |

C3 successes: 245/427 (189 successful positive retrievals + 56 correctly
abstained no-gold). C0: 197/427 (197 hits + 0 abstentions).

Paired bootstrap 10000, seed 0, 95% CI:

- C3−C0: +0.112412 [0.077283, 0.147541], excludes 0
- C3−C1: +0.077283 [0.044496, 0.110070], excludes 0
- C3−C2: +0.096019 [0.065574, 0.128806], excludes 0

Diagnostic strata (same OOF decisions, no retuning):

- natural-like 395: C0 0.498734, C3 0.554430
- counterfactual 32: C0 0.000000, C3 0.812500
- official balanced 164: C0 0.256098, C3 0.579268
- positive 345: C0 0.571014, C3 0.547826
- no-gold 82: C0 0.000000, C3 0.682927

C3 vs C0 on all five outer folds (lexical): 0.721>0.667, 0.550>0.363,
0.443>0.316, 0.538>0.462, 0.557>0.418.

Secondary BM25 replication, same protocol: C0 0.428571, C1 0.377049,
C2 0.428571, C3 0.454333. C3−C0 +0.025761, CI [−0.014052, 0.065574]
includes 0. Natural-like 395 BM25: C0 0.463291 vs C3 0.450633 (no
improvement).

Ablation C3_NO_CONCENTRATION (lexical): 0.585480 vs C3_FULL 0.573770.

Interpretation: On the pre-registered primary (lexical, n=427), richer
score geometry is a PROMISING EXPLORATORY SIGNAL: C3 beats C0 and C1 with
paired CIs excluding zero; C2 is not equivalent to C3; false abstention is
3.5% (12/345), not pathological; the natural-like 395 slice also improves,
so the gain is not solely the 32 counterfactual cases. BM25 does not
replicate a reliable gain, so this is ranker-sensitive and not a paper
result. The frozen ablation without concentration features was slightly
higher than the 12-feature C3; that is diagnostic only and does not
redefine C3.
Decision:
- CONTINUE — PROMISING SCORE-SHAPE SIGNAL

### Experiment E007

Date/time: 2026-09-09T20:18+02:00 (protocol freeze before gate/backend code);
  execution 2026-09-09 through 2026-09-11 (RepoMap, Qwen positive, per-corpus
  selective shards, merge, gate).
Purpose: Test whether the frozen E006 score-shape hypothesis generalizes
  beyond lexical retrieval to official RepoMap and official Qwen embedding.
Hypothesis tested: same 12-feature score geometry is useful for RETRIEVE vs
  ABSTAIN on substantially different retrieval mechanisms (exploratory; not
  a paper claim).
Configuration: `configs/E007_cross_retriever_generalization.json`

Git recorded before E007 protocol commit:
`d384c94c0048734b10295f768466ab4c8ff19e01`.

Contract frozen before implementation:

- PRIMARY: official `v2_selective_retrieval_natural`, n=427.
- Primary metric: Selective Success@20 (unchanged).
- Outer folds: reuse E006 `outer_repo_folds` exactly.
- Features: exactly the E006 12-feature family and transforms.
- C0 ALWAYS_RETRIEVE; C1 official repo-grouped top-score OOF if applicable,
  else `E007_EQUIVALENT_TOP_SCORE_THRESHOLD`; C2 TOP1_LOGISTIC; C3
  SCORE_SHAPE_LOGISTIC. Fit per backend; do not reuse lexical weights as
  primary.
- Optional secondary: C3_NO_CONCENTRATION exactly once; do not redefine C3.
- RepoMap: official `aider-style-repomap` (`eval-repomap`, weights
  0.65/0.25/0.10). If legitimate numeric file scores exist, apply the gate;
  if not, record NOT APPLICABLE FOR SCORE-SHAPE GATING and still reproduce
  the retrieval baseline. Do not fabricate rank-position scores.
- Qwen: official `Qwen/Qwen3-Embedding-4B` via `eval-embedding` /
  `eval-selective-embedding`, `--device cuda --trust-remote-code`,
  normalize=True, batch 8, empty prefixes, `all_files`.
- Reproduce official 345-sample published rows before gating.
- Do not rerun lexical/BM25 to improve them.

Command/script:

- `scripts/e007_cross_retriever.py`
- `scripts/run_e007_qwen.sh` (positive 345 only; monolithic selective refused)
- `scripts/e007_qwen_shards.py` / `scripts/run_e007_qwen_shard_queue.sh`
- `scripts/run_e007_qwen_gate.sh`

Seed: LogisticRegression random_state=0; paired bootstrap 10000 seed 0.
Input split: official 427 natural; E006 outer folds reused exactly.
Output file:

- `results/raw/E007_fold_assignments.json`
- `results/raw/E007_qwen_embedding_oof.jsonl`
- `results/raw/E007_repomap_oof.jsonl`
- `results/raw/E007_thresholds.json`
- `results/raw/E007_qwen_shard_validation.json`
- `results/raw/E007_qwen_equivalence_smoke.json`
- `results/raw/E007_natural_qwen_details.jsonl`
- `results/raw/E007_natural_qwen_merge_report.json`
- `results/raw/E007_qwen_shards/manifest.json`
- `results/baselines/E007_official_backend_reproduction.json`
- `results/baselines/E007_cross_retriever_comparison.json`
- `results/logs/E007_run.txt`
- `results/frozen/E007_cross_retriever_generalization/`

SHA-256 (`results/frozen/E007_cross_retriever_generalization/SHA256.json`):

- `E007_cross_retriever_comparison.json`: `c3f9354b2865a31dacd9313ef15f30de728af2003e3a86b31566d1181237551d`
- `E007_qwen_gate.json`: `1a7a8c9da378da89d80b8fde44314ac14e07aa55f2d500ee1ab604e3ee8ca715`
- `E007_repomap_gate.json`: `9220179d7744600ea1f2c2b76ee832bfb57d895a09c8807e0f21d4362c4c421c`
- `E007_natural_qwen_details.jsonl`: `9aa8b6856b959eebc8879df892f849381495ac4fe16badba44cc4952c0dff5b3`
- `E007_run.txt`: `4f9e8982cdaea92f493813209729c3df6ede6faea8be01f1fff8915cbacd43be`

Official 345 reproduction vs published:

- RepoMap: R@20 0.6414975845410628 (pub 0.6333), MRR 0.21115439508581774
  (pub 0.2158), BCY@8k 0.37739130434782603 (pub 0.3788).
- Qwen: R@20 0.6281642512077295 (pub 0.6306), MRR 0.23916247263115145
  (pub 0.2379), BCY@8k 0.34429951690821253 (pub 0.3409).

RepoMap score-shape is applicable (`final_score` = 0.65 query + 0.25
pagerank + 0.10 affinity). Official `eval-repomap` skips no-gold; selective
427 used official `rank_files_for_sample` including no-gold.

Qwen selective 427 was official `eval-selective-embedding` per unique
`(repo, base_commit)` corpus (`--sample-id-file`), then lossless merge.
Not a single monolithic official invocation. Nested ARB was not modified.
Smoke: gin-gonic/gin@0cbb30aa…, 2/2 overlapping samples, top-20 files
matched completed official positive `eval-embedding` details. Positive
details do not store numeric scores; numeric equality was not forced.

Metrics (PRIMARY = Selective Success@20 on official natural 427):

Frozen lexical reference: C0 0.4613583138173302, C3 0.5737704918032787.
Frozen BM25 reference: C0 0.42857142857142855, C3 0.45433255269320844.

RepoMap:

| Comparator | Selective Success@20 | retrieve rate | false abstention | no-gold abstention |
| --- | ---: | ---: | ---: | ---: |
| C0 ALWAYS_RETRIEVE | 0.5925058548009368 | 1.000 | 0.000 | 0.000 |
| C1 official top-score OOF | 0.5035128805620609 | 0.557 | 0.409 | 0.585 |
| C2 TOP1_LOGISTIC | 0.5925058548009368 | 1.000 | 0.000 | 0.000 |
| C3 SCORE_SHAPE_LOGISTIC | 0.5925058548009368 | 0.998 | 0.003 | 0.000 |

Paired bootstrap 10000, seed 0:

- C3−C0: 0.0 [0.0, 0.0], includes 0
- C3−C1: +0.088993 [0.037471, 0.142857], excludes 0
- C3−C2: 0.0 [0.0, 0.0], includes 0
- natural-like 395: C0 = C3 = 0.640506329113924
- reliable_positive_C3_minus_C0: false

Qwen embedding:

| Comparator | Selective Success@20 | retrieve rate | false abstention | no-gold abstention |
| --- | ---: | ---: | ---: | ---: |
| C0 ALWAYS_RETRIEVE | 0.5667447306791569 | 1.000 | 0.000 | 0.000 |
| C1 official top-score OOF | 0.65807962529274 | 0.756 | 0.128 | 0.732 |
| C2 TOP1_LOGISTIC | 0.6557377049180327 | 0.766 | 0.122 | 0.707 |
| C3 SCORE_SHAPE_LOGISTIC | 0.6323185011709602 | 0.761 | 0.139 | 0.659 |

Paired bootstrap 10000, seed 0:

- C3−C0: +0.065574 [0.025761, 0.105386], excludes 0
- C3−C1: −0.025761 [−0.044496, −0.007026], excludes 0
- C3−C2: −0.023419 [−0.042155, −0.004684], excludes 0

Qwen diagnostic strata (same OOF decisions, no retuning):

- natural-like 395: C0 0.612658 = C3 0.612658
- counterfactual 32: C0 0.000000, C3 0.875000
- official balanced 164: C0 0.353659, C3 0.658537
- positive 345: C0 0.701449, C3 0.626087
- no-gold 82: C0 0.000000, C3 0.658537

C3_NO_CONCENTRATION (secondary, once): RepoMap 0.592506; Qwen 0.644028.
Does not redefine C3.

Interpretation: Zero non-lexical retrievers met the frozen reliable
C3>C0 rule (C3−C0 > 0, CI excludes 0, C3−C2 ≥ 0.005 with CI excluding 0,
and the gain not only from the 32 counterfactuals). RepoMap C3 = C0.
Qwen C3 beats always-retrieve on the 427 mix, but loses to official
top-score and to top1 logistic, and natural-like 395 is flat (C3 = C0);
the 427 C3−C0 lift is the 32 counterfactuals. The lexical E006 gain
therefore did not transfer as a score-shape controller to these two
official backends.
Decision:
- CONTINUE — LEXICAL-SPECIFIC SIGNAL

## Compute Accounting

E001 (pytest):

- wall ~5.58 s
- CPU user 3.06 s / sys 1.54 s
- max RSS ~70 MiB
- GPU: unused

E002 download:

- wall ~17.02 s
- CPU user 3.31 s / sys 2.68 s
- max RSS ~190 MiB
- network download of 128720663-byte archive

E002 BM25 eval:

- evaluator wall 91.70 s
- `/usr/bin/time` wall 1:31.93
- CPU user 89.82 s / sys 2.08 s
- max RSS ~1.16 GiB
- GPU: unused
- model tokens: n/a
- retrieval calls: 58 samples over 44 corpora
- verification: `arb validate` 58/0 invalid; byte compare of details JSONL

No GPU-seconds or joules for this baseline (CPU-only).

E003 download remaining releases:

- wall ~110 s for six archives (~935 MB compressed; extracted corpora ~7.9 GB)
- GPU: unused

E004 positive lexical/BM25:

- trace2code lexical 12.85 s / bm25 13.37 s
- edit2ripple lexical 87.13 s (bm25 reused E002 91.70 s)
- comment2context lexical 163.90 s / bm25 169.21 s
- code2test lexical 167.85 s / bm25 176.13 s
- BCY aggregate wall 20.88 s, max RSS ~1.61 GiB
- GPU: unused

E005 selective:

- balanced lexical 157.03 s / bm25 167.14 s (n=164)
- natural lexical 471.46 s / bm25 503.08 s (n=427)
- GPU: unused

E006 score-shape gate:

- wall 1048.13 s (`/usr/bin/time` 17:29.14)
- CPU user 1042.26 s / sys 12.04 s
- peak RSS 1691992 KiB (~1.61 GiB)
- lexical score-vector recovery 510.72 s; BM25 recovery 534.52 s
  (reconstruction of missing E005 top-20 scores; ranking matched frozen
  `top_files`)
- classifier train (lexical C3, nested CV + outer fits) 0.0427 s
- C3 outer-test inference 0.00103 s
- feature extraction from scores 0.00937 s
- gate overhead per sample (features + C3 infer, scores already available):
  2.43e-5 s
- GPU: unused for E006 (nvidia-smi showed desktop/display load only; no LLM)

E007 RepoMap selective 427:

- wall 308.28 s
- peak RSS 9153269760 bytes (~8.52 GiB)
- GPU: unused

E007 Qwen positive 345: official eval-embedding, batch size 1, CUDA, 70 W
  cap; encodings cached under `results/embeddings/E007_qwen3_embedding_4b/`.

E007 Qwen selective shards (271 official CLI processes):

- wall 07:42:13–08:29:18 CEST 2026-09-11 (~47 min)
- CPU time 1h 25min 26s (`e007-qwen-shards.service`)
- peak RSS per shard ~5866308 kB (~5.59 GiB); VRAM typically ~0.3–8 GiB
  depending on corpus
- GPU: Qwen3-Embedding-4B, power limit 70 W

E007 Qwen score recovery + gate:

- score recovery 206.81 s (official vectors, ranking matched `top_files`)
- C3 train 0.0347 s; C3 infer 0.00078 s
- gate overhead per sample ~1.83e-6 s
- systemd wall 08:54:57–08:58:46; CPU 23min 53.959s; memory peak 4.2G

## Ablations

E006 frozen ablation only (no extra search):

Lexical OOF Selective Success@20:

- C3_FULL (12 features): 0.5737704918032787
- C3_NO_CONCENTRATION (drop entropy, top5/top20 mass, top1 z-score):
  0.5854800936768150

The ablation is exploratory. C3 remains the 12-feature method. Concentration
features were not required for the lexical gain.

## Failures / Bugs

None that blocked E000–E005 baseline reproduction or the E006 OOF write.

Pytest skips are recorded in E001; they did not affect BM25.

E006 process exited 120 after successful artifact write because the log Tee
flushed a closed file handle during interpreter shutdown. Metrics files were
already complete. sklearn 1.9.0 emitted `penalty` FutureWarnings; L2 / C=1.0
/ liblinear were used as contracted.

E007 Qwen:

- Official documented `--batch-size 8` CUDA-OOMed on large etcd/transformers
  corpora. Hardware-only retry: batch size 1.
- Monolithic `eval-selective-embedding` on 427 was kernel OOM-killed at
  ~29 GB RSS (unbounded in-process chunk/vector caches; details not
  checkpointed). Permanently abandoned. Positive 345 encodings were kept.
- Cursor/user-cgroup kills also interrupted earlier long runs; the shard
  queue used `systemd-run --user` with `OOMScoreAdjust=0` and linger.
- These did not change the ranker, model, or scoring.

## Deviations From Protocol

1. Protocol mentioned an intended path `~/research/paper1-evidence-gated`.
   Actual workspace is `/home/sauravsvt/Desktop/Research/R1`. Work was done
   here because Prompt1 says not to assume paths if the repository structure
   shows otherwise.
2. At E000/E002 time the project root was not yet a Git repository; it was
   initialized after E002 and frozen at commit
   `d384c94c0048734b10295f768466ab4c8ff19e01`.
3. venv pip was upgraded 24.0 → 26.2.1 during venv bootstrap. Not required by
   the benchmark; recorded here. Benchmark package itself was not upgraded.
4. `pytest` is not an official `pyproject.toml` dependency. It was installed
   in the venv solely to run the documented `PYTHONPATH=src pytest -q`.
5. `huggingface_hub` (providing `hf`) is not an official Python dependency
   list entry, but the official download path shells out to `hf download`.
   Installed in the venv to run `arb download-benchmark`.
6. Official README writes BM25 outputs into
   `data/eval/v2_edit2ripple/bm25_{summary,details}.*`. Those files already
   exist inside the release bundle. Outputs were redirected to `results/` so
   bundled official artifacts were not overwritten. Ranker/data/flags were
   unchanged.
7. Only `v2_edit2ripple` (58 samples) was downloaded, not `--all` five
   subsets / 427 samples. This follows the README's single-subset example and
   avoids a larger download in the first run.
8. `--force` was used on download as in the README example. It did not delete
   unrelated existing `data/` trees (`v0_1`, reports, etc.).
9. Git author/committer identity was unset on this machine. The pre-method
   commit used one-shot `GIT_AUTHOR_*` / `GIT_COMMITTER_*` environment
   variables. `git config` was not written.
10. Remaining downloads omitted `--all --force` so E002's `v2_edit2ripple`
    extraction was not overwritten.
11. E004 reused E002 BM25 details for `v2_edit2ripple` instead of rerunning.
12. Canonical BCY was computed via the official `bcy_curve.evaluate_run`
    Python API because `arb report-bcy-curve` hard-codes v1.3/v1.4 default
    detail paths. Ranked lists came from unchanged `eval-baseline` details.
13. `report-selective-cv` was invoked for lexical and BM25 only (no Jina
    embedding run this phase).
14. Eval outputs were written under `results/` rather than overwriting
    bundled `data/eval/` artifacts.
15. `scikit-learn` is not an official ARB dependency. It was installed in the
    isolated venv for E006 logistic gates only.
16. Frozen E005 details store `top_score`/`second_score` (chunk-level) and
    `top_files`, not the top-20 file-score vector. E006 recovered file-level
    scores by re-running the official ranker. Recovered unique-file ranking
    matched frozen `top_files` for all 427 samples × both rankers. Evaluation
    still used the frozen top-20 files unchanged.
17. sklearn 1.9.0 deprecates passing `penalty='l2'` explicitly. The contract
    required L2; the explicit argument was kept.
18. E007 official Qwen batch size 8 OOMed on this 20 GB / 70 W GPU. The
    rerun used `--batch-size 1` and `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.
    Model, normalize=True, empty prefixes, cuda, trust_remote_code, and
    `all_files` were unchanged.
19. E007 Qwen selective 427 used official per-corpus `--sample-id-file`
    shards plus lossless aggregation because the official single-process
    evaluator's unbounded caches exceeded 32 GB RAM. Rankings and numeric
    scores are official ARB output. Nested ARB source was not patched.
20. `loginctl enable-linger` was turned on so the user systemd instance
    survived leaving the graphical session. Not a ranker change.

## Current Best Result

Official BM25 on 345 positive samples: Recall@20 = 0.4451690821256039,
MRR = 0.1520385836822835, BCY@8k = 0.20507246376811594. Matches published
0.4452 / 0.1520 / 0.2051 at 4 decimal places.

Official lexical on 345: Recall@20 = 0.4939613526570048,
MRR = 0.15741480361234275, BCY@8k = 0.264975845410628.

These are reproduced baselines, not results for our method.

E002 subset BM25 on `v2_edit2ripple` remains frozen as previously recorded.

E006 exploratory (not a paper result): lexical SCORE_SHAPE_LOGISTIC OOF
Selective Success@20 = 0.5737704918032787 on official natural 427.

E007 exploratory (not a paper result): the same 12 features are
lexical-specific under the frozen reliability rule. RepoMap C3 = C0 =
0.5925058548009368. Qwen C3 = 0.6323185011709602 vs C0 = 0.5667447306791569,
but C3 loses to C1 and C2 and is flat on natural-like 395.

## Evidence AGAINST Our Hypothesis

BM25 score-shape did not reliably beat always-retrieve (C3−C0 CI includes
zero). On natural-like 395, BM25 C3 (0.450633) is below BM25 C0 (0.463291).
Lexical C3 also loses some positive hits versus always-retrieve (189 vs 197
successful positive retrievals; false-abstention 12/345). Official top-score
thresholding still fails on the natural-like 395 slice. Score-shape evidence
is therefore ranker-sensitive and not shown to be a general controller.

E007: RepoMap score-shape never abstains usefully (C3 = C0). Qwen C3 beats
always-retrieve only by abstaining counterfactuals; on natural-like 395,
C3 = C0, and C3 is worse than official top-score and top1 logistic. The
frozen 12-feature family is not a cross-retriever controller on these
official backends.

## Evidence FOR Our Hypothesis

Exploratory only. On the frozen primary lexical 427-sample test, 12
score-shape features distinguished RETRIEVE vs ABSTAIN better than
always-retrieve, official top-score OOF thresholding, and top1-only logistic,
without gold files, embeddings, or LLMs. Natural-like 395 also improved
(0.498734 → 0.554430). Paired C3−C2 excludes zero, so the lexical gain is
not merely “fitting a classifier on top1.”

E007 does not add a second retriever family with a reliable C3−C0
score-shape gain. Official Qwen top-score thresholding (C1) is the stronger
Qwen abstain rule on this split; that is a different hypothesis than the
frozen 12-feature C3.

## Open Questions

- Does the lexical score-shape gain survive a pre-registered confirmation
  that cannot retune after seeing E006?
- Why BM25 fails while lexical succeeds: score geometry, calibration, or
  threshold fragility?
- The frozen ablation without concentration features was slightly stronger
  than 12-feature C3. That must not become post-hoc feature search.
- RepoMap / embedding official rows remain unreproduced (not required for
  E006). E007 reproduced both; score-shape did not generalize as C3.
- Why Qwen C1/C2 beat C3: calibration of cosine top1 vs the 12-feature
  logistic, or threshold fragility on embedding scores.
- SWE-bench end-to-end remains out of scope until 1A/1B/1C have confirmed
  evidence.

## Next Legal Experiment

E007 is finished. Do **not** begin E008 in this run.

Do **not** add gpt-oss routing, model escalation, web search, dependency
features, query-text classification, SWE-bench, failure memory, or Paper 1
prose. Do not change the E006 12-feature family.

## Paper Claim Status

NO CLAIM YET

E006 is exploratory (PROMISING on lexical; not replicated on BM25). E007
is exploratory (LEXICAL-SPECIFIC SIGNAL). Do not claim a paper result from
E006/E007.
