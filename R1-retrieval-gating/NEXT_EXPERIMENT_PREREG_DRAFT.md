# Next experiment pre-registration draft

**Draft for human review. Does not authorize execution. Not yet signable.**

Proposed identity: **Candidate B — frozen-controller, repository-disjoint
confirmation of selective retrieval.**

This is a **true transfer test**, not another nested-CV fit on new data.
Discovery (E006/E007 official natural 427) is closed. Confirmation labels
and scores must not be used to fit a scaler, classifier, threshold,
feature, or decision rule.

Locked methodological choices are below. **Not locked:** the exact
confirmation sample/repository manifest, and the minimum N / repository
count. Those wait on `CONFIRMATION_DATASET_INVENTORY.md` plus a power
analysis performed **before scoring**.

## Design (locked)

```text
DISCOVERY — already completed
ARB official v2_selective_retrieval_natural, n=427, 25 repos

Lexical: 12-feature C3 looked promising (exploratory)
Qwen:    official top-score C1 looked promising (exploratory)

             ↓

TRAIN / FREEZE USING DISCOVERY ONLY
(after confirmation manifest is hashed; before confirmation scores)

Lexical H1:
  one StandardScaler + LogisticRegression on all 427
  one decision threshold from E006 choose_threshold
  coefficients / scaler / threshold hashed

Qwen H2 (secondary):
  one numerical top-score threshold from official C1 rule
  on all 427 Qwen discovery confidences
  threshold hashed

             ↓

NEW REPOSITORIES
zero overlap with every E006/E007 repository

             ↓

NO RETRAINING
NO THRESHOLD CHANGE
NO FEATURE CHANGE
NO C1-vs-C2 selection

             ↓

Primary population: natural-like selective cases

             ↓

PASS / FAIL per hypothesis (separate)
```

## Research question

Do the **frozen** discovery-derived controllers improve Selective
Success@20 over always-retrieve on **natural-like** selective-retrieval
cases from repositories that were never in E006/E007?

## Hypotheses (separate; not a conjunction)

### H1 — primary confirmatory (lexical)

Frozen lexical C3, fit once on the 427 discovery cases, improves
Selective Success@20 over C0 always-retrieve on the primary confirmation
population.

H1 is primary because lexical C3 was the only mechanism that improved
natural-like cases in discovery (E006 natural-like 395: C0 =
0.49873417721518987, C3 = 0.5544303797468354). Qwen 12-feature C3 did
not.

If H1 passes, Candidate C may proceed using **lexical** even if H2 fails.

### H2 — pre-registered secondary confirmatory (Qwen C1)

Frozen Qwen **C1 top-score threshold** (not C2), derived once from the
427 discovery cases, improves Selective Success@20 over C0 on the same
primary confirmation population.

C1 is locked rather than C2 because it was simpler and slightly stronger
on E007 discovery (427: C1 = 0.65807962529274, C2 = 0.6557377049180327;
natural-like 395: C1 = 0.6379746835443038, C2 = 0.6354430379746835). Do
**not** run C1 and C2 on confirmation and pick whichever looks better.

H2 cannot rescue a failed H1. H2 cannot block Candidate C if H1 passed.

### Not hypotheses

- RepoMap C3: **dropped.** E007 was a clean null (C3 = C0 on 427 and on
  natural-like 395). Repeating it adds multiplicity without changing the
  decision this experiment is for.
- Nested-CV refit of C3 or C1 on confirmation repositories.
- New features, subset search, or Qwen 12-feature C3 as a confirmation
  arm.

## Pass / fail (locked)

Primary metric: Selective Success@20.

A no-gold abstention is correct. An accepted positive is correct only
when a gold file appears in the frozen top-20. ABSTAIN returns no files.
RETRIEVE uses the frozen ranked top-20 from that retriever.

For **each** hypothesis independently:

1. Point estimate Δ = Success@20(controller) − Success@20(C0) on the
   primary population **≥ +0.05**.
2. Repository-clustered paired bootstrap 95% CI lower bound **> 0**
   (10,000 replicates, seed 0).

Both clauses are required. A scientifically trivial lift that is
“significant” only because N is large is a fail. A +5pp lift whose
clustered CI includes 0 is a fail.

The +0.05 floor applies to H2 as well. A different Qwen floor would have
to be justified **before scoring**; none is justified now.

### Decision tree

```text
H1 lexical passes
    ↓
Candidate C justified (lexical controller)
    ↓
coding-model experiment (separate prereg)
    ↓
does less context preserve patch success
while reducing GPU / tokens / joules?

H1 fails
    ↓
do not rescue C3 with new features on confirmation or on the 427
    ↓
do not proceed to Candidate C
    ↓
H2 is recorded but cannot reopen lexical C3
    and cannot authorize Candidate C by itself

H1 and H2 both fail
    ↓
kill this selective-confidence branch
and reconsider Paper 1 mechanism

H2 unevaluable (cannot finish official Qwen on confirmation corpora)
    ↓
not a pass, not a fail of H2
    ↓
H1 may still pass and authorize Candidate C
    ↓
if H1 also failed, do not go to C;
do not declare the whole branch killed until H2 is evaluated
or explicitly abandoned before scoring
```

## Frozen lexical controller (H1)

Fit **once** on all 427 discovery cases. **No fitting on confirmation
labels or scores.**

Source rankings: frozen E005/E006 lexical natural details
(`results/raw/E005_natural_lexical_details.jsonl`), same 427 IDs as
official `v2_selective_retrieval_natural`.

Exact specification (must match `scripts/e006_score_shape_gate.py`):

- 12 features, this order:
  `top1`, `top2`, `margin_top1_top2`, `safe_ratio_top1_top2`,
  `mean_top5`, `std_top5`, `mean_top20`, `std_top20`, `range_top20`,
  `top1_z_top20`, `mass_top5_over_top20`, `norm_entropy_top20_nonneg`
- Feature function: `score_shape_features` (pad to 20 with 0.0; EPS =
  1e-12; population std `ddof=0`; non-negative mass/entropy)
- Label: `y = 1` if `label == "no_gold"` else `0`
- `StandardScaler()` fit on the 427 × 12 matrix (sklearn defaults:
  `with_mean=True`, `with_std=True`)
- `LogisticRegression(penalty="l2", C=1.0, solver="liblinear",
  max_iter=2000, random_state=0)`
- Class-1 probability = P(abstain)
- Decision: **ABSTAIN iff `p_abstain >= t`**
- `t` from E006 `choose_threshold` on the 427 in-sample `p_abstain`
  values: maximize Selective Success@20; ties: fewer false abstentions,
  then more retrieve decisions, then smaller threshold

Save and hash, before any confirmation retrieval score exists:

- scaler `mean_` and `scale_`
- classifier `coef_`, `intercept_`, `classes_`
- feature name order
- numerical `t`
- the exact freeze script bytes

Confirmation applies `scaler.transform` + `predict_proba` + the same `t`.
Do not refit. Do not re-run nested CV.

## Frozen Qwen controller (H2)

Not C2. Not a menu.

Discovery rankings: frozen E007 Qwen natural details
(`results/raw/E007_natural_qwen_details.jsonl`), n=427.

Confidence = top-1 file score (E007 `confidence` / `top_score`).

Derive **one** threshold with the official C1 rule already defined in
nested ARB `selective_cv.py`:

- `select_balanced_threshold(rows)` = `max(threshold_sweep(rows), key=
  (balanced_accuracy, selective_accuracy, selective_success@20))`
- `threshold_sweep`: unique confidences, midpoints between consecutive
  unique values, plus `-inf` and `max(confidence)+eps`
- Decision: **ABSTAIN iff `confidence < threshold`**
  (`_predict_abstain`)

Apply that rule **once to all 427 discovery rows** (the same mixed list
E007 C1 used). That yields one numerical threshold. Save and hash it,
plus the freeze script bytes.

On confirmation Qwen rankings, apply that number unchanged. Do not
recalibrate per repository, per fold, or on natural-like-only
confirmation rows.

Official encoding (when H2 is evaluated): `Qwen/Qwen3-Embedding-4B`,
`normalize=True`, empty prefixes, `all_files`, official
`query_text_for_eval`. Per-corpus official CLI shards if RAM requires
it. Do not substitute another embedder.

## Primary confirmation population

**Natural-like selective retrieval is primary.**

Include a row iff it is **not** a counterfactual-wrong-repo no-gold:

`not (label == "no_gold" and no_gold_reason == "counterfactual_wrong_repo")`

This is the E006/E007 `natural_like_395` / ARB
`_is_natural_selective_row` definition.

Counterfactual-wrong-repo rows, if present in the confirmation release,
are a **pre-specified secondary stress-test** and are **excluded from
the primary endpoint**. They must not determine confirmation. E007
showed that full-mixture C3−C0 can be carried almost entirely by those
32 artificial negatives.

Do not drop or add counterfactuals after seeing confirmation Δ.

## Dataset (not locked)

Intended class: labeled selective-retrieval samples (gold files or
labeled no-gold) whose `repo` keys have **zero overlap** with every
repository in E006/E007 `outer_repo_folds` (the 25 repos listed in
`CONFIRMATION_DATASET_INVENTORY.md`).

Current inventory: **no such labeled set exists** in the local ARB
v0.2.1 checkout or in the current public `arb releases` catalog. Same-
repo later commits are forbidden. See the inventory file.

Signing requires, committed and hashed **before** confirmation retrieval
scores are produced:

- exact sample IDs
- exact repository IDs
- primary vs secondary (counterfactual) partition
- SHA-256 of that manifest

Minimum sample count and minimum repository count are set by a power
analysis on that candidate list’s **labels and repo sizes only** (no
rankings, no controller outputs). Do not invent N after seeing what
scores exist.

## What makes the data independent

- No sample ID overlap with official `v2_selective_retrieval_natural`
  427.
- No repository overlap with the 25 E006/E007 fold-map repos.
- Controllers hashed before confirmation details exist.
- Analysts must not inspect confirmation per-sample outcomes before
  those hashes exist.
- Confirmation rankings are produced with the same official retrievers
  and `all_files` protocol as discovery; only the sample list is new.

## Inclusion / exclusion (locked rules; list itself not locked)

Include: official-style selective samples with gold files **or** labeled
no-gold, evaluable under `all_files`, using official
`query_text_for_eval`, subject to the same query-leakage skip official
ARB eval already uses.

Exclude:

- any repository in the E006/E007 25-repo fold map
- unlabeled rows official eval would skip
- any sample chosen after seeing confirmation residuals
- same-repository later commits of discovery repos

## Baselines

- C0 always-retrieve on the **same** frozen ranked lists (primary
  comparator).
- No confirmation-tuned threshold.
- BM25 is not a confirmatory arm.
- RepoMap is not a confirmatory arm.

## Secondary endpoints (cannot rescue H1/H2)

- Counterfactual-wrong-repo stress-test, if those rows exist.
- Sample-level paired bootstrap (10,000, seed 0), for comparability with
  E006/E007 only. **Not** confirmatory inference.
- False-abstention rate; no-gold abstention rate; retrieve rate.
- Positive-only Recall@20 among retrieved positives.

## Statistics (locked)

**Confirmatory inference:** repository-clustered paired bootstrap.

- Population: primary natural-like rows only.
- Pairing: each sample contributes `(success_controller, success_C0)`.
- Resample **repositories** with replacement (`n_repos` draws). Carry
  every primary sample of a drawn repository. If a repository is drawn
  `k` times, its samples appear `k` times.
- Repositories that have zero primary samples are not clusters.
- 10,000 replicates, `numpy.random.RandomState(0)` (same generator class
  as E006 `paired_bootstrap_delta`).
- Report point Δ, `ci95_low`, `ci95_high`. Pass clause 2 iff
  `ci95_low > 0`.

**Secondary, non-confirmatory:** the old sample-level paired bootstrap
(10,000, seed 0) on the same primary rows.

Do not treat samples in the same repository as independent for the
primary CI.

## Compute measurements

Wall time, CPU user/sys, peak RSS per official CLI process. GPU-seconds
and nvidia-smi energy/joules if exposed. Embedding encode vs cache-hit
counts.

These are evaluator cost. Do not report them as task compute saved.

## Leakage controls

- Frozen queries only (`query_text_for_eval`).
- No gold file names in queries (official leakage skip).
- Nested ARB source unmodified
  (`07014c986f3deadb1548c62b32c0ffbe6a81465d`).
- Confirmation manifest committed/hashed before details exist.
- Controller bytes hashed before details exist.
- No threshold, coefficient, scaler, or feature update after the first
  confirmation score.
- Do not inspect confirmation per-sample success while choosing the
  manifest.

## Stop conditions / unevaluable

- Sample or repository count below the pre-declared minimum from the
  power analysis: do not interpret; do not “see what we got.”
- Hardware cannot finish official Qwen on confirmation corpora even with
  per-corpus shards: H2 unevaluable; do not substitute another embedder.
- Any change to ranker, model, features, threshold rule, or primary
  population: abort and re-prereg.
- Finding that the “new” set overlaps a discovery repository after
  hashing: abort.

## Not in this experiment

- SWE-bench / coding models / tool scaffolds (Candidate C).
- gpt-oss, model escalation, web search.
- Feature ablation or new score-shape dimensions (Candidate A).
- Nested CV on the confirmation set.
- Claiming reduced inference compute on verified patches.
- RepoMap C3.

## Authorization sequence (none of this is authorized yet)

1. Methods in this draft — **locked for review, not signed.**
2. Identify a genuinely repo-disjoint labeled candidate set. Inventory
   so far: none in current ARB.
3. Power analysis on that set’s labels and repository sizes. Freeze
   minimum N and minimum n_repos.
4. Commit and hash the exact sample/repo manifest.
5. Fit and hash discovery-only lexical C3 and Qwen C1 artifacts.
6. Sign this prereg with those hashes filled in.
7. Only then produce confirmation retrieval scores and apply the frozen
   controllers.

**Do not start E008 / Candidate B scoring.**
