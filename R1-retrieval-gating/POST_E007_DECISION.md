# Post-E007 research decision

Status of last completed experiment: **CONTINUE — LEXICAL-SPECIFIC SIGNAL**

This is a falsification-first decision memo. It is not a paper draft. It does
not authorize E008 or any new model, retriever, classifier, feature ablation,
threshold search, or benchmark run.

Integrity audit (2026-09-11, no recomputation): E007 frozen SHA-256 records
match all 21 hashed files; live counterparts match frozen copies; merged Qwen
details are 427 unique IDs in official selective-natural order (345 positive +
82 no-gold, 0 duplicate / missing / extra); all 427 rows have 20 `top_files`
and 20 recovered `file_scores`; score-recovery was specified to abort on
`top_files` mismatch and did not abort; smoke test 2/2 file-order match vs
official positive Qwen; E006 frozen hashes still match live E006 artifacts;
nested ARB at `07014c986f3deadb1548c62b32c0ffbe6a81465d` with a clean tree.

## What E007 falsified

The frozen hypothesis that the **same 12-dimensional score-shape evidence
gate** would provide **reliable** selective-retrieval gains across
substantially different retrievers **was not supported**.

Record (official `v2_selective_retrieval_natural`, n=427, Selective
Success@20, paired bootstrap 10000 seed 0; lexical/BM25 from frozen E006):

| Retriever | C0 | C3 | C3−C0 | Reliable C3>C0 under E007 rule? |
| --- | ---: | ---: | --- | --- |
| Lexical (E006, frozen) | 0.4613583138173302 | 0.5737704918032787 | +0.112412, CI excludes 0 | yes (exploratory; discovery set) |
| BM25 (E006, frozen) | 0.42857142857142855 | 0.45433255269320844 | +0.025761, CI includes 0 | no |
| RepoMap (E007) | 0.5925058548009368 | 0.5925058548009368 | 0.0 [0.0, 0.0] | no |
| Qwen embedding (E007) | 0.5667447306791569 | 0.6323185011709602 | +0.065574, CI excludes 0 | no |

RepoMap: C3 = C0 = C2 = 0.5925058548009368. Official top-score C1
(0.5035128805620609) was worse than always-retrieve. Natural-like 395:
C0 = C3 = 0.640506329113924.

Qwen: C3 0.6323185011709602 vs C0 0.5667447306791569 looks like a gain on
the 427 mix. It is **not** acceptable as cross-retriever evidence for the
frozen 12-feature controller because:

- natural-like 395: C3 = C0 = 0.6126582278481013
- C3 loses to C1 official top-score (0.65807962529274); C3−C1 CI excludes 0
- C3 loses to C2 top1 logistic (0.6557377049180327); C3−C2 CI excludes 0
- the 427 C3−C0 lift is the 32 counterfactual-wrong-repo cases (C0 0.0,
  C3 0.875)

**We do not have evidence for a universal score-shape controller.**

The E007 reliability rule required C3−C0 > 0 with CI excluding 0, C3−C2 ≥
0.005 with CI excluding 0, and a gain not carried only by the 32
counterfactuals. RepoMap failed the first clause. Qwen failed C3 vs C1/C2
and the natural-like / counterfactual clause. Count of non-lexical
retrievers with a reliable positive C3−C0: **0**.

## What remains alive

The failed mechanism is: one frozen 12-feature logistic, fit per retriever
but with the same feature family, as a general RETRIEVE vs ABSTAIN rule.

That is not the larger research question. The following has **not** been
falsified:

**Can adaptive evidence-gated context/model allocation preserve or improve
verified software-engineering performance while reducing real inference
compute?**

We have not run a downstream coding-agent experiment with a frozen
controller, fixed model/scaffold/tools/sampling, and measured verified
patch success against tokens, GPU-seconds, joules, and latency. E006/E007
are retrieval-gate studies on ARB selective files. They do not show that
compute was reduced on real tasks.

## New observations worth investigating — NOT CLAIMS

Post-hoc interpretation; requires a newly frozen hypothesis and independent
evidence.

1. Lexical retrieval **appeared** to benefit from richer score geometry on
   the inspected 427 (C3 beat C0, C1, and C2; natural-like 395 also moved
   in the same direction). This is exploratory discovery, not confirmation.
2. Qwen embedding retrieval **appeared** better served by simple top-score
   / top1 confidence on this dataset (C1 and C2 beat the 12-feature C3).
3. RepoMap’s composite `final_score` geometry did not provide useful
   abstention (C3 = C0; C2 = C0).
4. Therefore confidence information **may** be retriever-dependent rather
   than universally represented by the same feature family.

Do not treat (1)–(4) as results to report. They are hypotheses generated
after seeing E006/E007.

## Candidate next directions (not executed)

### Candidate A — Retriever-specific confidence calibration

**Hypothesis.** Each retrieval family has a minimal confidence
representation appropriate to its score semantics (for example: lexical
12-feature score-shape; Qwen top1 / margin; RepoMap none / always
retrieve). Using that family-specific rule improves Selective Success@20
over always-retrieve and over forcing the E006 12-feature family on every
retriever.

**Why E006/E007 motivate it.** Universal 12-feature C3 failed E007. The
post-hoc pattern is: lexical C3 helped; Qwen C1/C2 helped; RepoMap nothing
helped.

**What would falsify it.** On **new** data, the pre-specified per-retriever
minimal rule does not beat always-retrieve, or a single simple rule (e.g.
top1 for all) matches the “family-specific” rules within the pre-registered
tolerance.

**Minimum new data.** A selective-retrieval set whose repositories/tasks
were not used to inspect E006/E007. Do **not** feature-hunt on the existing
427 as evidence for this hypothesis.

**Leakage / post-hoc risks.** High if the “minimal representation” is
chosen by searching features on the 427. The 427 already determined which
family “won.” Any A-test on the 427 is circular.

**Compute cost.** Low–moderate if restricted to already-cached retrievers
on a new sample list; high if new embedding corpora must be encoded.

**Value if positive.** Supports retriever-dependent confidence, not a
universal geometry.

**Value if negative.** The post-hoc E007 pattern was dataset-specific.

**Advances compute-efficiency claim?** Only indirectly (a better gate is
not yet a measured token/GPU/joule saving on verified patches).

### Candidate B — Frozen transfer confirmation (not nested-CV on new data)

**Hypothesis (separate, not a conjunction).**

- **H1 primary.** One lexical C3 model, scaler + `LogisticRegression(L2,
  C=1, liblinear, random_state=0)` fit **once on all 427 discovery
  cases** with the frozen E006 12 features and `choose_threshold`
  decision rule, applied unchanged, improves natural-like Selective
  Success@20 over C0 by **≥ +0.05** with repository-clustered 95% CI
  lower bound **> 0**.
- **H2 secondary.** One Qwen **C1** top-score threshold, derived once
  from the 427 discovery cases with the official
  `select_balanced_threshold` rule, applied unchanged, meets the same
  Δ ≥ +0.05 and clustered-CI rule. Not C2. Do not pick C1 vs C2 after
  seeing confirmation.

RepoMap C3 is **not** a B arm. E007 already gave a clean null.

**Why E006/E007 motivate it.** The lexical natural-like signal and the
Qwen C1 observation were measured on inspected discovery data. Nested-CV
on a new set would only show that the *learning procedure* can be
retrained on new repositories. Transfer requires frozen discovery
coefficients / one frozen threshold and **zero confirmation fitting**.

**What would falsify it.** H1 fails the +0.05-and-clustered-CI rule on
the pre-declared natural-like confirmation population. H2 is independent:
its failure does not reopen lexical C3; its success cannot authorize C
if H1 failed. If both fail, kill this selective-confidence branch. If
H1 fails and H2 is unevaluable, do not go to C and do not declare the
whole branch killed until H2 is evaluated or abandoned before scoring.

**Primary population.** Natural-like selective cases only
(`no_gold_reason != counterfactual_wrong_repo`). Counterfactuals, if
present, are a pre-specified secondary stress-test and must not
determine confirmation.

**Minimum new data.** Not locked. Current inventory
(`CONFIRMATION_DATASET_INVENTORY.md`): **no labeled ARB samples whose
repositories are disjoint from the 25 E006/E007 repos.** Same-repo later
commits are forbidden. Power analysis and an immutable sample/repo
manifest must precede scoring. Do not invent N after seeing availability.

**Leakage / post-hoc risks.** Choosing the confirmation list after seeing
which discovery repos “worked”; quietly using counterfactuals as primary;
refitting scaler/threshold on confirmation; running C1 and C2 and
keeping the winner. Mitigate by hashing the manifest and controller
bytes before any confirmation score exists.

**Compute cost.** Moderate once a disjoint set exists: lexical cheap;
Qwen needs per-corpus official shards on this workstation. Not started.

**Value if positive.** A pre-registered, repository-disjoint,
frozen-controller confirmation. Still not a compute-efficiency claim.

**Value if negative.** Stop this branch before SWE-bench budget.

**Advances compute-efficiency claim?** Necessary precursor only.

### Candidate C — Downstream context-value / compute experiment

**Hypothesis.** Holding coding model, scaffold, tools, sampling, and task
fixed, a frozen selective-context policy reduces input tokens and
GPU-seconds/joules versus always-retrieve **without reducing verified
patch success** relative to always-retrieve (and remains above no-seed-
context).

**Why E006/E007 motivate it.** The live research question is compute
allocation, not ARB Selective Success@20. E006/E007 never measured that.

**What would falsify it.** Verified success drops vs always-retrieve by
more than the pre-registered margin, or compute does not fall, or
selective ≈ always-retrieve on both success and compute (no decision
value).

**Minimum new data.** A frozen task suite with verified patches (design
only: e.g. a small SWE-bench slice). Arms: no seed context; always-
retrieve; selective retrieval (H1 lexical controller frozen in B);
oracle-gold context where available. Primary: verified task success. Secondary:
input/output tokens, GPU-seconds, energy/joules, latency,
retrieval/search overhead.

**Leakage / post-hoc risks.** High if the controller is chosen after
seeing which tasks fail; if gold files leak into queries; if the model
is changed mid-run.

**Compute cost.** High (coding-model decode dominates). Must not be spent
on an unconfirmed gate.

**Value if positive.** Directly addresses the compute-efficiency claim.

**Value if negative.** Selective retrieval can win ARB file metrics and
still fail as an agent policy.

**Advances compute-efficiency claim?** Yes, **if and only if** the
controller is frozen from independent confirmation. Running C now would
confound discovery-set overfit with downstream effects.

## Recommendation

**Next experiment, when signable: Candidate B as a frozen transfer
test.** Sequence remains **B then C**. C is unauthorized until H1
passes. H2 is secondary: useful if it also passes; not required for C;
not a license to salvage a failed H1.

B is **not signable yet**. Methods are locked in
`NEXT_EXPERIMENT_PREREG_DRAFT.md`. The confirmation dataset and minimum N
are not. Inventory: no currently available labeled set is repository-
disjoint from the E006/E007 25 repos.

Reasons (defensibility, not excitement):

1. Treat ARB 427 as discovery. Fit lexical C3 and Qwen C1 once on those
   427 rows; never on confirmation.
2. Primary endpoint is natural-like Selective Success@20. Do not let
   counterfactual-wrong-repo cases decide confirmation again.
3. Confirmatory inference is repository-clustered paired bootstrap, not
   sample-level iid.
4. Require Δ ≥ +0.05 **and** clustered CI lower bound > 0. p < .05
   alone is not enough.
5. Hypotheses are separate. Lexical H1 authorizes C. Qwen H2 does not
   have veto or rescue power over H1.
6. Drop RepoMap from B. Do not add Candidate A feature search on the
   427.
7. Real compute accounting belongs in C, after H1. Do not claim compute
   has already been reduced.

```text
H1 lexical passes → Candidate C justified → coding-model experiment
H1 fails → do not rescue C3 with new features
H1 and H2 both fail → kill this selective-confidence branch
```

Candidate A is **not** the next experiment if it means fitting new
features on the 427. Candidate C is **not** the next experiment until
H1 survives B. Dataset shopping, power analysis after seeing scores, and
E008 execution are all unauthorized.

This document does not authorize execution of B or C.
