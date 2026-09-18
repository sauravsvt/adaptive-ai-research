# Confirmation dataset construction plan

**Not an experiment. No retrieval, controller, or scoring run.**
**Does not create the final confirmation set. Does not authorize E008.**

Companion to `CONFIRMATION_DATASET_METHOD.md` (ARB reconstruction) and
`CONFIRMATION_DATASET_INVENTORY.md` (no disjoint labeled ARB set exists).

Candidate B methods remain provisionally locked in
`NEXT_EXPERIMENT_PREREG_DRAFT.md`. This document only asks whether a
scientifically defensible **repository-disjoint** selective-retrieval
confirmation set can be constructed, and how.

## Why natural no-gold is load-bearing

On a **positive-only** set, Selective Success@20(controller) cannot beat
always-retrieve (C0):

- Retrieve + hit: both succeed.
- Retrieve + miss: both fail.
- Abstain on a positive: controller fails, C0 may succeed or fail; the
  controller never gains.

True negatives (natural no-gold) are the only primary-population cases
where abstention can improve the metric. Counterfactual-wrong-repo cases
can also improve it, which is exactly why E007’s 427 mix was misleading
and why they are locked **out** of the primary endpoint.

**If a defensible natural no-gold set cannot be labeled, H1 as specified
cannot be confirmed.** Do not weaken no-gold to “wrong repo” or “random
issue” to obtain N.

## Design principles (frozen before any construction)

1. **Repository-first.** Choose repositories by eligibility rules.
   Hash the repo list. Only then mine issues/PRs. Never add a repo
   because lexical or Qwen would have succeeded or failed on it.
2. **No retriever in the loop.** Construction, audit, and keep/drop use
   GitHub/git evidence only. No ranking, no score-shape, no C3/C1.
3. **ARB-like semantics, not SWE-bench patch success.** File-level gold
   must be “files to read next” under a declared task contract, derived
   independently of our controllers.
4. **Natural no-gold requires positive evidence of abstention**, not
   absence of a gold label.
5. **Do not execute construction until this procedure is reviewed.**

---

## 1. Proposed construction protocol (not executed)

### 1.1 Source classes considered

| Class | Can support ARB-like positives? | Can support natural no-gold? |
| --- | --- | --- |
| SWE-bench / Verified issue→patch | Only under a **different** gold contract (files in `patch` / FAIL_TO_PASS tests), not ARB’s four workflow tasks | **No.** Every instance is a local fix. |
| SWE-Gym / SWE-smith / SWE-bench-extra | Same: localization/repair instances with a patch | **No.** |
| Public GitHub issue→merged-PR workflows on new repos | **Yes**, if we re-run ARB miners (`code2test`, `comment2context`, `trace2code`, optionally `edit2ripple`) | **Only** via a separate organic abstention audit, not from the PR itself |
| Closed issues with maintainer “not our repo” evidence | Not positives | **Yes, in principle**, following ARB organic rules |
| Counterfactual wrong-repo pairing | N/A | Secondary only; **forbidden as primary** |

SWE-bench-family datasets are useful as a **repository catalog** and as
an optional **secondary localization-style positive arm**. They are not,
by themselves, a selective RETRIEVE-vs-ABSTAIN confirmation set.

### 1.2 Repository eligibility (apply first; hash the list)

A repository is eligible iff **all** of the following hold. These rules
use GitHub/git metadata only.

1. **Identity:** `owner/name` is not in the 25 E006/E007 discovery
   repos (see inventory). Same-repo forks and renames that resolve to
   those 25 are excluded.
2. **Public clone** with a recorded default branch and a license that
   allows research snapshots (prefer OSI licenses already common in
   ARB: MIT, Apache-2.0, BSD, MPL). Exclude repos with no license or
   with non-redistributable corpus terms.
3. **Language:** primary language in `{Python, Go, Rust, TypeScript,
   Java, JavaScript}` — the ARB V2 language set — so confirmation is
   not a silent language shift. Record language; do not drop after
   seeing task yield.
4. **Size:** GitHub `size` ≥ 5,000 KB **or** ≥ 200 tracked source files
   at default HEAD (whichever is used must be declared before cloning
   corpora). Exclude tiny tutorial repos.
5. **Activity:** ≥ 200 merged PRs and ≥ 50 closed issues (thresholds
   chosen to make organic no-gold mining possible, not to match
   retrieval difficulty). Created or first commit **before** a frozen
   date `T0` (propose `T0 = 2024-01-01`) so we are not scraping only
   post-E006 GitHub fashion.
6. **Not archived**, `has_issues = true`.
7. **Not a discovery near-duplicate:** exclude `pallets/flask` if we
   already have `pallets/click` **only if** a pre-specified
   org-duplicate rule says so. Default: **org overlap is allowed;
   repository identity is the unit.** Flask is allowed; pytest is not.
8. **Deterministic order:** sort eligible repos by
   `(stargazers_count desc, full_name asc)` from a frozen GitHub
   snapshot date, then take the first `R` repos that pass. Do not
   reshuffle after looking at issues.

**Propose R for planning only, not a signed N:** start the eligibility
pass at **R = 30** repositories so that after no-gold attrition we can
still hope for ≥ 15 repos with at least one natural no-gold (ARB organic
no-gold used 10 of 25 repos). Do not reduce R because a repo looks
hard for lexical retrieval.

Hash: `repos.json` with `full_name`, `html_url`, `license`, `language`,
`stars`, `size_kb`, `created_at`, `eligibility_snapshot_date`.

### 1.3 Task date window

After the repo list is hashed:

- Mine merged PRs with `merged_at ∈ [T1, T2]`.
- Mine closed issues with `closed_at ∈ [T1, T2]`.

Propose `T1 = 2022-01-01`, `T2 = 2025-12-31` (inclusive), frozen before
mining. Do not extend T2 after seeing yield.

Base commit for positives: PR `baseRefOid` before merge, as in ARB
`derive._sample`. Corpus is that snapshot, not HEAD.

### 1.4 Positive inclusion (ARB miners, not SWE-bench patches)

For each eligible repo, run the **official ARB miner gates** documented
in `CONFIRMATION_DATASET_METHOD.md`:

- `code2test`: same-PR implementation + tests; query does not contain
  exact test paths or the fix hash; gold = related tests that exist at
  base.
- `comment2context`: review comment + given file; gold = additional
  files changed in the response commit with required relation evidence;
  given file not gold.
- `trace2code`: failure excerpt; gold = root-cause sources, not
  automatic stack-frame files.
- `edit2ripple` optional: 2–8 files, anchor vs ripple, `valid` audit.

**Duplicate handling.** At most one retained positive per
`(repo, merge_commit)` cluster (ARB `code2test_pr` cluster rule). At
most 1–2 `edit2ripple` anchors per PR. Cap **per repository** at
`min(20, 15% of eventual primary N)` **after** the set exists, using a
pre-declared cap formula so one django-like repo cannot dominate. Until
N is known, cap **8 positives per repo per task** during mining
(ARB-scale; gin’s 88/345 in discovery is a warning).

**Ambiguous-gold handling.** If two plausible gold sets exist, or the
only candidates fail relation-evidence checks, **drop** (do not union,
do not guess). Require gold files present in the base corpus.
`confidence=weak` automatic candidates **do not enter** confirmation
until a dual audit says `valid`. This is **stricter** than ARB’s
inherited 287, which released `confidence=weak` rows after a Codex
span pass. Confirmation should not be weaker than discovery’s
abstention bar.

**SWE-bench Verified as optional extra positive contract (not primary).**
If used at all, declare a **separate** secondary table: gold = paths in
the gold `patch` excluding tests, or FAIL_TO_PASS test files, frozen
before scoring. Do **not** mix that gold definition into H1’s primary
population. Primary H1 positives should be ARB-task miners so the
controller is tested on the same decision type.

### 1.5 Natural no-gold inclusion

Follow ARB organic rules with **stricter** agreement:

Minimum evidence for `valid_no_gold` (all required):

1. Query is a real coding-workflow signal (issue title/body or CI
   failure excerpt), length ≥ 80, no resolution answer in the query.
2. Base SHA is a recorded commit at or immediately before the event,
   regenerable from git.
3. A maintainer (`OWNER`/`MEMBER`/`COLLABORATOR`) comment, or same-SHA
   CI rerun-pass with no new commit, that supports one declared reason:
   `upstream_dependency` | `external_service` | `user_error` |
   `flaky_ci`.
4. Issue/PR closed **without** a repository-local fix: no closing
   commit event, no linked fixing PR that changes source/tests/config/
   lockfiles/CI, no pin/workaround.
5. Two independent annotators, working from an evidence packet **that
   does not include retrieval scores**, both mark `valid_no_gold`.
   Discordant or `ambiguous` → **exclude**.
6. Annotators must answer ARB’s audit questions (is any local file
   necessary? would top-k from this repo help or waste context?). If
   either annotator lists a local gold file, the row is `has_local_gold`
   and is **not** no-gold (it may become a positive only if it also
   passes a positive-task gold contract; default: drop).

Keyword search is recall only. Labels such as `invalid` are not
sufficient (`user_error` in ARB).

**Do not fabricate no-gold by assigning the wrong repository.** That is
counterfactual, secondary only, and excluded from H1.

### 1.6 Counterfactuals

If created: ARB `mine_abstention_counterfactuals` pairing among
**confirmation** repos only (not pairing confirmation queries onto
discovery corpora). Secondary stress-test. Cap so they cannot exceed
organic no-gold count (ARB plan: ≤ half of clean no-gold; we already
exclude them from primary).

### 1.7 Leakage and eval contract

Reuse official:

- `query_text_for_eval` = `json.dumps(query, sort_keys=True)`
- fatal leakage skip: exact gold path, raw patch, fix hash, generated
  review
- `all_files` at base commit
- no gold path / fix hash in queries

### 1.8 What this protocol is not

- Not official ARB V3.
- Not an excuse to fit C3 on new labels.
- Not a license to look at E006/E007 residuals when picking repos.

---

## 2. Dataset-construction bias controls

| Risk | Control |
| --- | --- |
| Picking repos where lexical C3 “should work” | Repo list hashed before any ranking or even issue reading beyond eligibility metadata |
| Keeping no-gold cases that look low-confidence | Annotators forbidden from running retrievers; evidence packets have no scores |
| Dropping hard positives so C0 is weak | Per-repo caps and pre-declared task mix; no drop after seeing C0 |
| Using SWE-bench because patches are easy gold | SWE-bench gold is a different task; not H1 primary |
| Inflating N with counterfactuals | Primary = natural-like only |
| One-repo dominance (django 46% of Verified) | Per-repo cap; clustered inference |
| Same lab labels the stratum that can make H1 pass | Dual annotation + public evidence URLs; still a residual conflict — reason for WAIT |

Exclusion rules (in addition to eligibility):

- Discovery 25 repos and their later commits
- Rows with fatal leakage
- Ambiguous gold or single-annotator no-gold
- Queries that contain the maintainer resolution
- Samples whose only “no-gold” evidence is “we did not find gold”

---

## 3. Natural no-gold feasibility (hardest part)

### 3.1 Can it be labeled without retrieval?

**Yes in protocol, weakly in practice.** ARB did it: 50 organic issues,
all `valid_no_gold`, from 10 of 25 discovery repos, using maintainer
comments + no local-fix signals. The miner is in `abstention.py`. The
released set did **not** include the plan’s best source (`flaky_ci`).
Yield was ~2 organic no-gold per discovery repo overall, and 0 on many
repos.

Observable evidence that **no repository file was required**:

| Proposed source | Observable evidence | Two annotators could agree? | Must exclude | False no-gold risk |
| --- | --- | --- | --- | --- |
| Maintainer “fixed upstream” / “not our bug”, issue closed, no local PR | Comment + closing events + empty linked-fix set | **Yes**, if both see the same packet and a checklist | Any linked pin/lockfile/compat PR; query that already says “upstream” | **High** if “upstream” still needed a local adapter file |
| External outage / credentials / cannot reproduce | Maintainer or CI metadata; no config change | **Moderate.** “cannot reproduce” is often incomplete | Need-more-info closures; local `.env`/config gold | **High** |
| User error / works as intended | Maintainer explanation that no code change is needed | **Low–moderate.** Easy to miss a docs/file the user should have read | Label-only closes; docs-only fixes (those **are** local gold) | **Very high** (ARB kept 2) |
| Flaky CI, same SHA later green | Check-run timestamps + identical SHA | **Yes** when SHA identity is clear | Reruns after a push; infra YAML workarounds | **Moderate** (ARB released 0) |
| SWE-bench instance with empty patch | Does not occur in Verified | N/A | — | Do not invent |
| Wrong-repository pairing | Construction artifact | Agree it is wrong-repo, not that local files were unnecessary in nature | Must stay secondary | **Not natural** |

### 3.2 Explicit finding

A **defensible** natural no-gold set can be constructed only if we
accept:

- GitHub-scale crawling on hashed new repos,
- dual annotation,
- aggressive exclusion,
- likely **tens, not hundreds**, of organic no-gold rows (ARB: 50 from
  25 already-instrumented repos, 2 reasons dominating).

It **cannot** be constructed from SWE-bench/SWE-Gym patches. It
**should not** be constructed by lowering the bar to “no linked PR.”

If dual annotation is refused, **say no-gold is not constructible** and
do not run H1.

Residual scientific problem even with dual annotation: the same
research group that discovered lexical C3 would be creating the only
stratum on which C3 can beat C0. Repository-first rules do not remove
that conflict.

---

## 4. Power-analysis design (no final N)

Do **not** publish a minimum N until a candidate repo list and
label-only counts exist. Labels and repo sizes do not determine the
variance of paired controller-vs-C0 effects, so the procedure is a
**simulation-based sensitivity analysis**.

### 4.1 Confirmatory target (locked)

H1 pass: Δ Selective Success@20 ≥ +0.05 **and** repository-clustered
paired bootstrap 95% CI lower bound > 0 (10,000, seed 0).

### 4.2 Inputs allowed

- Frozen Δ\* = 0.05
- Candidate `n_repos`, samples per repo, positive vs natural-no-gold
  counts (from labels only)
- Conservative ranges of within-repo correlation / repo-level
  heterogeneity of the **paired difference** D_i = 1{success_C3} −
  1{success_C0}
- Optionally, discovery-derived Var(D) and ICC from E006 lexical
  natural-like **OOF** paired indicators, **explicitly labeled
  planning-only, not confirmation**

Forbidden: any confirmation ranking or controller output.

### 4.3 Simulation

For each scenario in a grid:

1. Assume a true mean D̄ = 0.05 (boundary) and also 0.08 / 0.03 as
   sensitivity (0.03 should usually fail the magnitude gate).
2. Draw repo-level effects `b_r ~ N(0, τ²)` and within-repo Bernoulli
   or bounded noise with ICC ρ ∈ {0.02, 0.05, 0.10, 0.20}.
3. Respect the empirical repo-size schedule (including caps).
4. Replay the **exact** clustered bootstrap that the prereg will use.
5. Empirical power = fraction of replicates with
   `mean(D) ≥ 0.05` and `ci95_low > 0`.

Target power: 80% at Δ\* = 0.05 under the **most conservative** grid
cell we are willing to sign (propose ρ = 0.10 and τ large enough that
two repos can cancel the effect). If 80% is unreachable without
weakening Δ\*, **do not weaken Δ\***; wait for more repos or do not
sign.

### 4.4 Minimum repositories (planning floor, not yet signed)

Clustered inference with 2–5 repos is degenerate. Discovery used 25
clusters and was already unbalanced.

- **Hard planning floor:** ≥ **15** independent repositories in the
  **primary** natural-like set, each with ≥ 1 primary sample.
- **Preferred:** ≥ 20.
- **Sensitivity:** report whether 12 SWE-bench-Verified-disjoint repos
  could ever suffice under the grid; if only at ρ ≈ 0 and balanced n,
  treat 12 as **insufficient** for signing.
- **Samples:** no invented number. After a hashed candidate list,
  choose the smallest N that hits 80% in the conservative cell, subject
  to per-repo caps. Expect that **organic no-gold count**, not
  positives, will bind: if natural no-gold < ~30–50 across ≥ 15 repos,
  H1 has little room to gain +5pp (ARB organic 50/395 ≈ 12.7% of
  natural-like discovery).

Planning-only discovery note (not a power result): lexical natural-like
C3−C0 was ≈ +0.0557 under nested-CV OOF, barely above +0.05. Frozen
full-427 C3 may differ. Power at the boundary is inherently fragile.

---

## 5. Strategy comparison

Counts are **public catalog / paper figures**, not a mined eligibility
pass. Overlap with the ARB 25 is only partially enumerated (Verified:
`pytest-dev/pytest` is in both). Exact eligible-repo counts require the
hashed eligibility script; it has **not** been run (running it would
start construction).

| Source | Potentially eligible new repos (approx.) | Positive-label quality | Natural-no-gold feasibility | Independence from ARB 25 | Construction-bias risk | Annotation burden | Licensing / reproducibility | Expected sample count | Suitability for H1 confirmation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current ARB V2 | **0** | Official ARB gold | Already used (discovery) | None | N/A | None | MIT metadata; upstream corpora | 427, all overlapping | **Unsuitable** |
| Future official ARB release with new repos | Unknown (does not exist) | Highest (same protocol, external authors) | Only if they include audited organic no-gold | High if repos disjoint | Low for us | None for us | Same as ARB | Unknown | **Best if it appears** |
| SWE-bench Verified | 11 after dropping pytest (12 total; django-heavy) | Patch/test gold; **not** ARB task gold | **None** | High except pytest | Medium if we stretch gold | Low (existing labels) | Per-repo OSS + dataset license | 481 if pytest dropped | **Unsuitable for H1 primary** (no natural no-gold; different gold) |
| SWE-bench full / Lite | Same 12-repo family | Same | **None** | Same | Medium | Low | Same | Larger n, still 12 clusters | **Unsuitable for H1 primary** |
| SWE-Gym (executable) | ~11 Python repos (paper); overlap with ARB not fully checked | Patch instances | **None** | Partial | Medium | Low–medium | OSS + large Docker images | 2,438 | **Unsuitable for H1 primary** |
| SWE-Gym Raw / SWE-bench-extra | Hundreds–~2k Python repos; several ARB 25 appear in published freq tables (mypy, numpy, pip, pydantic, hypothesis, …) | Patch instances, weaker validation | **None** in the dataset | High after exclusions | High if we cherry-pick | Medium | Mixed; reproduction heavy | Large positives possible | Positives only; **cannot confirm H1 alone** |
| SWE-smith | ~128 repos | Mixed real/synthetic | **None** | Likely high after exclusions | High (synthetic tasks) | Medium | OSS + envs | ~50k tasks, wrong semantics | **Unsuitable** |
| GitHub crawl + ARB miners on hashed new repos | User-chosen R (plan: 30) after eligibility | Can match ARB if dual-audited | **Possible**, low yield, high labor | High by construction | **High** for no-gold (same lab) | **High** (dual audit of gold and no-gold) | Must snapshot licenses like ARB | Uncertain; ARB-scale organic no-gold was 50/25 repos | **Only defensible self-build path**, and still not independent |
| ARB `crawl_targets` reserve not in 25 (`sqlalchemy`, `axios`, `react-router`, `junit5`, `hyper`, `ripgrep`, …) | Handful | Would still need full mining+audit | Same no-gold problem | High | Medium (list was ARB’s, not ours) | High | Same as ARB | Too few clusters | **Insufficient n_repos** |
| Code-search benches (CodeSearchNet, CoSQA) | Many | NL↔code, not workflow gold | No | High | N/A | Low | Dataset licenses | Large | **Wrong task** |

---

## 6. Recommendation

**WAIT — PUBLIC INDEPENDENT SET PREFERRED**

Reason: H1 is a selective-abstention claim. It is untestable without
defensible **natural** no-gold labels, and those labels cannot be mined
from SWE-bench-family patch datasets. They can be constructed by
replaying ARB’s organic protocol on hashed new repositories, but that
set would be **labeled by the same lab that discovered lexical C3**, on
the only stratum where C3 can beat always-retrieve. That is not the
independent confirmation Candidate B is for. The scientifically cleaner
object is a **public, repository-disjoint selective release** (ARB or
equivalent) with audited organic no-gold. Until that exists, do not
sign B, do not weaken no-gold, and do not execute the self-build
protocol above — it is specified for review, not for construction.

Not **BUILD** now: the procedure has not been reviewed, yield is
unknown, and executing it would create the confirmation set before
that review. Not **STOP**: construction is possible in principle; the
blocker is independence and no-gold validity, not a proof that no set
can ever exist.

If a public disjoint set does not appear, a later reviewed decision may
revisit BUILD under the protocol in this file. That is not authorized
here.

NO RETRIEVAL SCORES PRODUCED. NO E008 STARTED.
