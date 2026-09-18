# Confirmation dataset methodology reconstruction

**Not an experiment. No retrieval, controller, or scoring run.**
**Does not construct a confirmation set. Does not authorize E008.**

This document reconstructs how the released Agent Retrieval Bench (ARB) V2
selective-retrieval benchmark was obtained, from the nested checkout at
`07014c986f3deadb1548c62b32c0ffbe6a81465d` (v0.2.1): `paper/main.tex`,
`docs/`, and `src/agent_retrieval_bench/`.

Every claim is tagged:

- **Official:** stated in the paper, README/dataset card, released sample
  schema, or executable construction/eval code.
- **Inferred:** implied by code paths, metadata, or internal docs, but not
  a paper-facing rule.
- **Unavailable / not reproducible here:** human/Codex audit content we do
  not have as a complete, independent protocol; raw crawls not in this
  checkout; decisions not recorded as deterministic code.

Sources (nested ARB, unmodified):

- `paper/main.tex` §§ Benchmark Tasks, Dataset Construction, Quality and
  Leakage Controls, Limitations
- `docs/paper_dataset.md`, `docs/v2_abstention_crawling_plan.md`,
  `docs/edit2ripple_data_construction.md`
- `src/agent_retrieval_bench/{derive.py,code2test_pr.py,edit2ripple.py,abstention.py,filters.py,baseline.py,dataset_validity.py,quality.py,corpus.py,crawler.py}`
- released `data/benchmark/v2_*/samples.jsonl`

## 1. What ARB is trying to label

**Official.** A sample is `(repo, base_commit, query, gold files or
no-gold)`. The candidate universe is **all files** at that frozen base
commit. Relevance is **agentic**: files an agent needs to read *next*,
not query–file semantic similarity. Positive samples use the repository
state **before** the resolving change. No-gold samples have an empty gold
set and an audited reason that local retrieval should abstain.

This is **not** SWE-bench patch success, not span-level localization, and
not “any file mentioned in a stack trace.”

## 2. Repository snapshots

**Official.**

- V2: 427 samples, 25 sample-bearing repositories, 271 distinct
  `repo@base_commit` pairs used by those samples.
- Combined corpus manifest: 308 snapshots across **29** repositories,
  ~392K files, ~7.9M chunks. 37 snapshots are unused by the 427 rows.
- Corpus type: `repo_at_base_commit`. Chunks are built from the checkout
  at `base_commit` (`corpus.py`), skipping binaries and selected generated
  artifacts.
- Positive `base_commit` is the PR base (`baseRefOid` in `derive.py`
  `_sample`). The resolving change is `gold.fix_commit` (merge commit
  oid) and must not appear in the query.

**Inferred.** Repositories were pre-chosen, not sampled from a frozen
public catalog at construction time. `configs/crawl_targets.json` lists
12 “primary” repos plus 8 “reserve” names (`sqlalchemy/sqlalchemy`,
`axios/axios`, `remix-run/react-router`, `junit-team/junit5`,
`hyperium/hyper`, `BurntSushi/ripgrep`, plus `pydantic/pydantic` and
`caddyserver/caddy` which later appear in the 25). How the remaining
discovery repos (numpy, pip, mypy, playwright, eslint, hypothesis, ruff,
click, scrapy, tox, ipython, spring-boot already in primary, …) were
added is not a single documented lottery.

**Unavailable.** The four extra corpus-only repositories in the 29-repo
manifest are not labeled in the 427. Raw GitHub crawl dumps for all 25
are not required to be present for evaluation; this checkout has
benchmark JSONL + prebuilt corpora, not a complete raw-issue archive for
reproduction from GitHub.

## 3. Positive queries and gold files

Four positive tasks. Official evaluation gold is
`baseline.target_gold_files`:

| Task | Query (official fields) | Gold used at eval |
| --- | --- | --- |
| `code2test` | `changed_file`, `pr_title`, `pr_body` | `gold.related_tests` |
| `comment2context` | `review_comment`, `given_file`/`path`, `line`, `diff_hunk_context`, `pr_title` | `must_context_files` (reviewed file is given, not gold) |
| `trace2code` | released rows use `command`, `failure_excerpt`, `run_strategy`, `source_type` | `root_cause_files` (tests/frames are not main gold unless they are the audited root cause) |
| `edit2ripple` | `intent`, `anchor_file`, `anchor_diff` | `gold.files` (anchor is given, not gold) |

If `gold.files` is explicitly set, that list wins for all tasks.

### 3.1 `code2test`

**Official (paper).** Query is a PR / implementation-change signal.
Construction excludes exact test paths and final-patch evidence. Gold is
“review-confirmed related tests.”

**Official (code).** Two miners exist:

1. `derive._code2test`: merged PRs with both implementation and test
   changes (`max_changed_files=20` via `should_skip_pr` / `_usable_pr`).
   Query includes the implementation `changed_file` plus truncated PR
   title/body. Gold tests = other test files changed in the **same PR**
   (up to 10 in derive; `code2test_pr.mine_code2test_prs` caps tests).
2. `code2test_pr.py`: tighter PR miner (behavior/test-request markers,
   template/CodeRabbit filters, duplicate cluster drop, optional
   gold-in-corpus).

Released 106 rows: `metadata.confidence = "weak"` on all 106; **no**
`audit.verdict` field. They do have `gold_spans` / `gold_blocks` with
reasons such as `"manual round3: smallest readable symbol/window tied to
query evidence"`. Default validity code looks for Codex-reviewed
annotation files:

`data/reports/v1_3/manual_annotations_{task}_codex_reviewed.jsonl`

**Inferred.** “Review-confirmed” for the inherited 287 means a later
span/block annotation pass (named Codex-reviewed in paths), not
independent dual human annotation, and not a recorded `valid` audit
verdict on the JSONL the way `edit2ripple` and abstention have.

**Unavailable.** The exact keep/drop list from that Codex/manual round,
inter-annotator agreement, and whether annotators saw retriever outputs.
`docs/paper_dataset.md` explicitly warns: do not call these independent
human annotations unless an independent human review pass is added.

### 3.2 `comment2context`

**Official (paper).** Review comment + reviewed file; gold is additional
context files. The reviewed file is given context, not gold.

**Official (code, `derive._comment2context`).** Keep a review comment on
a **changed, already-existing** file if:

- body survives `sanitize_review_body` and is not
  `contains_review_leakage` / low-value;
- a post-comment response commit exists in a time window;
- that commit changes other files that already existed at base;
- those candidates have required relation evidence
  (`_has_required_context_evidence`: same module, path-token overlap,
  implementation/test pairing, etc.);
- the comment text does not already name the context files
  (`_query_mentions_any_context`);
- gold paths are redacted from the query (`_redact_paths_from_query`).

Released 80 rows: spans/blocks present; `confidence=weak`; no
`audit.verdict`.

### 3.3 `trace2code`

**Official (paper).** Query is reproduced failure command + excerpt.
Gold is root-cause **source** files. Visible tests and stack frames are
evidence, not automatic gold.

**Official (code).** Multiple miners:

- review comments containing traces (`_review_trace2code`);
- failing check runs (`_failure_samples`);
- job logs (`_log_samples`).

Matching maps trace paths onto changed implementation files
(`_matching_trace_files`). If no trace match, derive may emit
`testlog2code` instead; that task type is **not** in the V2 public
positive four.

Released 101 rows use a cleaned query schema (`command`,
`failure_excerpt`, …), not the raw miner `raw_signal` field. 100/101
have `confidence=weak`.

**Unavailable.** The mapping from miner output → released query schema
and the root-cause audit that demotes visible frames/tests are not a
single pure function in the evaluated JSONL. Stack-path mentions in the
query are **non-fatal** leakage (`direct_stack_hint` in
`dataset_validity.detect_query_leakage`).

### 3.4 `edit2ripple`

**Official.** Miner (`edit2ripple.py`, `docs/edit2ripple_data_construction.md`):

- PRs with 2–8 changed files;
- one non-test source **anchor**;
- gold = other co-changed files with at least one ripple signal (same
  component, path-token overlap, symbol/config/schema, optional test
  ripple);
- query = truncated intent + anchor path + sanitized **anchor-only**
  diff (added/removed lines stripped from hunk context);
- fatal leakage: gold paths, full multi-file patch, fix hash;
- gold stems in natural language are non-fatal;
- at most 1–2 anchors per PR;
- generated/vendor/lock/changelog-style files excluded.

Released 58 rows: every row has `audit.verdict = "valid"`. This is the
only positive task with a uniform `valid` audit field on the public
JSONL.

## 4. Natural no-gold cases

**Official (paper).** Evidence-backed issues where repository-local
retrieval should not return a file (upstream, external platform, etc.).
Empty gold set. Audited no-gold reason. Evaluated only in selective
retrieval. All 82 no-gold rows carry `audit.verdict = valid_no_gold`.

**Official (construction plan + `abstention.py`).** Organic sources
planned:

1. Flaky / infra CI: same `head_sha` later passes with no new commit;
   maintainer/labels support flaky/infra; no local fix.
2. Upstream dependency: maintainer attributes to upstream; issue closes
   without local fix; no pin/lockfile/compat patch.
3. External service / environment: maintainer or CI metadata; no local
   config change required.
4. User error / invalid: maintainer explanation; still a plausible
   coding-agent query; no local file should be read. Labels alone are
   not enough.

Automatic prefilter drops (`organic_prefilter_drop_reason`): missing
base SHA, missing resolution evidence, local-fix signals (closing
commits, linked PRs, or local-fix path tokens in text), query containing
the resolution answer, query shorter than 80 characters.

Query construction **must not** include the resolution comment. Evidence
lives in metadata/audit packets only.

`issue_query_text` = `"Issue title: …\nIssue body excerpt: …"` (body
truncated). CI queries use failed command + excerpt + optional PR title.

Maintainer comments: `author_association ∈ {OWNER, MEMBER, COLLABORATOR}`.

Reason classification is **keyword matching on the maintainer comment**,
not on the query (`classify_issue_reason` / `ISSUE_REASON_KEYWORDS`).

**Official (released 50 organic rows).**

| reason | n |
| --- | ---: |
| `upstream_dependency` | 41 |
| `external_service` | 7 |
| `user_error` | 2 |
| `flaky_ci` | **0** |

All 50 organic queries have `query.source = "issue"`. None are CI/flaky
despite the plan ranking flaky CI as highest-priority. Concentration:
`pytest-dev/pytest` 14, `vitejs/vite` 14; 10 repos total for organic
no-gold.

**Inferred.** The flaky-CI miner exists, but the released clean set did
not retain any `flaky_ci` row. Precision-first audit likely discarded
them, or the CI crawl was not completed for release. Keywords are recall
aids, not labels; the plan requires a human/auditor `valid_no_gold`
verdict.

**Unavailable.**

- Inter-annotator agreement for `valid_no_gold` vs `has_local_gold` vs
  `ambiguous`.
- Whether auditors could see repository files or retriever rankings.
- Complete rejected-candidate archive (the plan’s
  `has_local_gold` / `ambiguous` packets).
- Deterministic base-commit rule: code can backfill “commit before issue
  creation,” but the plan says skip if unreliable. Released SHAs are not
  regenerable from the JSONL alone without GitHub + git history.

The guiding official sentence (plan): a sample is not no-gold because
nobody labeled gold; it is no-gold because there is **evidence an agent
should abstain**.

## 5. Counterfactual no-gold cases

**Official.** Reuse a real positive ARB query on a **plausible wrong
repository** of similar language/domain (`REPO_PROFILES` /
`choose_wrong_pairs`). `gold.files = []`,
`reason = counterfactual_wrong_repo`, `metadata.organic = false`. Drop if
the query contains source-repo identity tokens. Cap per source repo and
per wrong repo.

Released: 32 counterfactual rows, all `valid_no_gold`. Example metadata
records source sample id, source repo, pairing profile (e.g.
`python:ml`), and the wrong-repo corpus SHA.

**Official for Candidate B (already locked).** These are **secondary
stress-tests only**. They must not determine confirmation. They are
**not** a substitute for natural no-gold.

## 6. Query text used at evaluation

**Official.** `query_text_for_eval(sample)` is:

```python
json.dumps(sample.get("query") or {}, ensure_ascii=False, sort_keys=True)
```

It is the JSON of the query object, not a separately curated natural-
language string. Controllers and retrievers in E000–E007 used this
function.

## 7. Query leakage filtering

**Official (paper validity table).** Fatal categories, all zero on V2:
exact gold-path leakage, raw patch/diff markers, fix-commit hash,
generated-review leakage.

**Official (eval skip, `query_has_leakage`).** Skip a sample if:

- `contains_raw_patch_marker(query)`, or
- `gold.fix_commit` is non-empty and appears in the query string, or
- `edit2ripple` fatal leakage helper fires.

**Official (diagnostics, `detect_query_leakage`).** Additional
**non-fatal** flags: gold basename, gold stem, gold/test symbols, test
names, and for `trace2code` stack-path hits (`direct_stack_hint`).
Realistic workflow evidence is allowed; exact answer strings are not.

**Official (construction sanitizers).** Strip review suggestion fences
and CodeRabbit markers (`contains_review_leakage`); strip `+/-` lines
from review diff hunks (`sanitize_diff_hunk`); redact fix hashes
(`_redact_query`); redact gold paths from comment2context queries.

**Inferred.** Eval-time `query_has_leakage` is stricter than “basename
appears in the issue.” A query may still mention symbols or basenames
and be scored.

## 8. Inclusion / exclusion (released V2)

**Official / executable.**

Include:

- Rows with gold files **or** `gold.no_gold is True`.
- `candidate_corpus.type == repo_at_base_commit`.
- Gold files present in the base-commit corpus (validity: 345/345
  positive golds corpus-backed).
- Official `all_files` candidate filter for leaderboard / selective
  eval.

Exclude / drop during mining (task-specific):

- PRs with no usable base/merge SHA, too many changed files, or only
  generated/lock files.
- Review comments that are replies, leaked, low-value, on added-only
  files, or that name their own gold paths.
- Abstention candidates with local-fix signals, missing SHA, missing
  evidence, resolution leakage in the query, or non-coding-like text.
- After audit: anything not `valid` / `valid_no_gold`.

**Inferred.** Inherited positive rows with `confidence=weak` were still
released if they passed schema/corpus/leakage gates and the Codex/manual
span pass. That is weaker than the abstention `valid_no_gold` bar.

## 9. Selective mixed lists

**Official.**

- Natural: all 345 positives + 82 no-gold = 427
  (`v2_selective_retrieval_natural`).
- Balanced: 82 positives paired with the same 82 no-gold = 164.

No-gold reasons on the 82: 50 organic + 32 counterfactual, as above.

## 10. What cannot be reproduced from this checkout alone

1. Independent human dual annotation of gold or no-gold.
2. The Codex “manual round3” keep/drop decisions as a script.
3. Inter-annotator agreement.
4. Full raw GitHub issue/PR/CI crawls for all 25 repos.
5. Why `flaky_ci` is in the miner but 0 in the release.
6. How the 25 repos were chosen beyond `crawl_targets.json` (which does
   not list all 25, and whose reserve list was only partly used).
7. Exact unused 4 corpus-only repos in the 29-repo combined manifest
   (not needed for 427 eval; unused snapshots are still those families
   plus extras without labels).

## 11. Implications for a new confirmation set

ARB’s selective task is **not** “issue text → files changed in the
fixing PR.” Gold is task-specific (tests vs extra review context vs
root-cause sources vs ripple files) plus a **separately audited**
natural-abstention class.

Any confirmation set that only copies SWE-bench `patch` paths would
change the gold definition. Any confirmation set without natural no-gold
cannot test RETRIEVE vs ABSTAIN improvement over always-retrieve (see
the construction plan).

Do not generate retrieval scores while designing that set.
