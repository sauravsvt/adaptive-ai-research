# Confirmation dataset inventory

**Not an experiment. No retrieval, controller, or scoring run.**
**Does not lock N. Does not authorize Candidate B.**

Purpose: find whether any **labeled** selective-retrieval data exist whose
repositories are disjoint from every E006/E007 discovery repository, so
that a power analysis and an immutable manifest can be done **before**
confirmation scores exist.

Checked 2026-09-11 against:

- nested ARB commit `07014c986f3deadb1548c62b32c0ffbe6a81465d` (v0.2.1)
- local `data/benchmark/**/samples.jsonl` and `data/corpus/**/corpus_manifest.jsonl`
- live `arb releases` catalog (`eyuansu71/agent_retrieval_bench`)
- Hugging Face dataset card for that repo (read-only)

No confirmation rankings were produced. No ARB v1/v3 bundle was
downloaded. Nested ARB was not modified.

## Discovery repositories (must have zero overlap)

E006/E007 `outer_repo_folds` — all 25 sample-bearing repos in official
`v2_selective_retrieval_natural` (n=427):

```text
HypothesisWorks/hypothesis
astral-sh/ruff
caddyserver/caddy
clap-rs/clap
eslint/eslint
etcd-io/etcd
fastapi/fastapi
gin-gonic/gin
huggingface/diffusers
huggingface/transformers
ipython/ipython
microsoft/playwright
mockito/mockito
numpy/numpy
pallets/click
pydantic/pydantic
pypa/pip
pytest-dev/pytest
python/mypy
scrapy/scrapy
spring-projects/spring-boot
tokio-rs/tokio
tox-dev/tox
vitejs/vite
vuejs/core
```

Same-repository later commits of these 25 are **forbidden**. Independence
is at repository identity, not commit SHA.

## Local labeled samples: disjoint count = 0

| Sample list | n | repos | disjoint repos |
| --- | ---: | ---: | ---: |
| `v2_selective_retrieval_natural` | 427 | 25 | **0** |
| `v2_selective_retrieval_balanced` | 164 | 23 | **0** |
| `v2_code2test` | 106 | 12 | **0** |
| `v2_trace2code` | 101 | 7 | **0** |
| `v2_abstention` | 82 | 16 | **0** |
| `v2_comment2context` | 80 | 18 | **0** |
| `v2_edit2ripple` | 58 | 10 | **0** |
| `v0_1` | 35 | 12 | **0** |

Natural 427 composition (discovery, not confirmation): 345 positive + 50
natural no-gold + 32 `counterfactual_wrong_repo`. Primary confirmation
population would analogously exclude the counterfactual stratum.

Balanced 164 is a subset of the same 23 overlapping repos. It is not
independent.

## Local corpora: disjoint count = 0

All downloaded `corpus_manifest.jsonl` files use only the same 25 repos.
Unique `repo@base_commit` snapshots across local manifests: **271**, all
on those 25 repos (the snapshots referenced by the 427 samples).

The Hugging Face card mentions a larger combined inventory (~308
snapshots; 271 referenced by the released samples). Unused snapshots in
that inventory are still not a confirmation set: they have **no labeled
selective rows** in the current release, and any snapshot whose `repo`
is one of the 25 is ineligible even if the commit differs.

## Public ARB catalog: no later release

`arb releases` current benchmark tracks:

- `v2_code2test` (106)
- `v2_comment2context` (80)
- `v2_trace2code` (101)
- `v2_edit2ripple` (58)
- `v2_abstention` (82)

Auxiliary:

- `v2_selective_retrieval_balanced`
- `v2_selective_retrieval_natural`

No v3. No held-out repo split. The Hugging Face card describes the same
427 samples / 25 repositories.

Historical GitHub text for an older V1 (~225 samples) is **not** in the
current download catalog. It is almost certainly the same repository
family. It was **not downloaded** and is **not** treated as a confirmed
disjoint source.

## Candidate sources (none ready)

| Source | Status | Notes |
| --- | --- | --- |
| Current ARB v2 (local + public catalog) | **Not usable** | 0 repo-disjoint labeled samples |
| Same-repo later commits / unused 308-snapshot remainder | **Forbidden** | Repository overlap with discovery |
| Future ARB release with new repos | **Does not exist** | Intended class if authors add labeled rows on new repos |
| Author-held-out split | **Not public** | Would still need exact IDs, zero repo overlap, and a hash before scoring |
| Newly constructed selective set on disjoint repos (e.g. SWE-bench-derived) | **Not a dataset yet** | Would require gold / no-gold labels under an ARB-like protocol; leakage and construction bias are high; **not official ARB**; do not score while constructing |
| Other code-search benches (CodeSearchNet, CoSQA, …) | **Wrong task** | Not selective RETRIEVE vs ABSTAIN with workflow gold files |

## Power analysis: blocked

Minimum N and minimum n_repos must be declared from a power analysis
**before scoring**, using only the candidate set’s labels and repository
sizes (no rankings).

That analysis cannot be performed until a repo-disjoint **labeled**
manifest exists. Do not back-solve N from “whatever ARB currently
ships.”

When a candidate list exists, the analysis should target the confirmatory
rule in `NEXT_EXPERIMENT_PREREG_DRAFT.md`: Δ Selective Success@20 ≥
+0.05 **and** repository-clustered 95% CI lower bound > 0, 10,000
replicates, seed 0. Discovery clustering (25 repos, highly unbalanced;
Gin alone is 88/345 positives) is why sample-level bootstrap is no
longer confirmatory. A confirmation set with only a handful of
repositories would make the clustered CI degenerate; the power note must
say how many clusters are required, not only how many rows.

Exploratory discovery magnitudes (not confirmation, not a substitute for
power):

- Lexical C3 − C0 on natural-like 395: 0.5544303797468354 −
  0.49873417721518987 ≈ **+0.0557** (barely above the +0.05 floor, and
  this was nested-CV OOF, not the frozen full-427 fit).
- Qwen C1 − C0 on natural-like 395: 0.6379746835443038 −
  0.6126582278481013 ≈ **+0.0253** (below +0.05; E007 OOF C1, not the
  frozen single threshold).

Those numbers argue for taking the +0.05 floor seriously. They must not
be used to lower H2 after seeing confirmation data.

## What this implies for signing

The confirmatory **methods** can be reviewed now. The experiment
**cannot be signed** until:

1. a labeled, repo-disjoint candidate set is identified or constructed
   without scoring it;
2. power analysis freezes minimum N and minimum n_repos;
3. an immutable sample-ID + repo-ID manifest is committed and hashed;
4. discovery-only controller bytes are fit and hashed;
5. the prereg is signed with those hashes.

Until then: **no E008, no confirmation retrieval, no controller
evaluation on new rows.**
