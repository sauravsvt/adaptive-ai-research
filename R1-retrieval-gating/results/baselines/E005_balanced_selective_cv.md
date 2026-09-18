# Selective Retrieval: Repo-Grouped 5-Fold Cross-Validation

- Samples: 164 (82 positive, 82 no-gold)
- No-gold reasons: counterfactual_wrong_repo=32, external_service=7, upstream_dependency=41, user_error=2
- Repository groups: 23
- Folds: 5
- Calibration: maximize balanced accuracy on four folds; evaluate once on held-out repositories.
- Aggregate metrics use one out-of-fold decision per sample.

## Mixed Out-of-Fold Results

| Ranker | Pos. pass | No-gold abstain | Balanced acc. | Selective acc. | Success@20 | Coverage | No-abstain Success@20 |
|---|---:|---:|---:|---:|---:|---:|---:|
| lexical | 0.8293 | 0.5000 | 0.6646 | 0.6646 | 0.4573 | 0.6646 | 0.2561 |
| BM25 | 0.2439 | 0.9634 | 0.6037 | 0.6037 | 0.5488 | 0.1402 | 0.2439 |

## Natural Evidence-Only Out-of-Fold Results

This view contains 82 positives and 50 natural no-gold samples. Thresholds are recalibrated within the natural-only repo-grouped folds; counterfactual wrong-repository negatives are excluded from both calibration and evaluation.

| Ranker | Pos. pass | No-gold abstain | Balanced acc. | Selective acc. | Success@20 | Coverage | No-abstain Success@20 |
|---|---:|---:|---:|---:|---:|---:|---:|
| lexical | 0.4878 | 0.5800 | 0.5339 | 0.5227 | 0.3864 | 0.4621 | 0.3182 |
| BM25 | 0.2073 | 0.9400 | 0.5737 | 0.4848 | 0.4242 | 0.1515 | 0.3030 |

## Fold Composition

| Fold | Samples | Positive | No-gold | Repositories |
|---:|---:|---:|---:|---|
| 0 | 37 | 23 | 14 | gin-gonic/gin, microsoft/playwright, numpy/numpy, pydantic/pydantic, scrapy/scrapy |
| 1 | 33 | 14 | 19 | huggingface/transformers, pytest-dev/pytest, spring-projects/spring-boot, vuejs/core |
| 2 | 31 | 14 | 17 | clap-rs/clap, fastapi/fastapi, pallets/click, vitejs/vite |
| 3 | 32 | 16 | 16 | HypothesisWorks/hypothesis, astral-sh/ruff, huggingface/diffusers, tokio-rs/tokio, tox-dev/tox |
| 4 | 31 | 15 | 16 | caddyserver/caddy, eslint/eslint, etcd-io/etcd, ipython/ipython, pypa/pip |

## lexical Fold Results

| Fold | Threshold | Test n | Pos. pass | No-gold abstain | Balanced acc. | Success@20 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 16.4348 | 37 | 0.6957 | 0.4286 | 0.5621 | 0.4865 |
| 1 | 14.1258 | 33 | 1.0000 | 0.3684 | 0.6842 | 0.4242 |
| 2 | 15.2504 | 31 | 0.8571 | 0.2353 | 0.5462 | 0.2581 |
| 3 | 14.3561 | 32 | 0.9375 | 0.7500 | 0.8438 | 0.5312 |
| 4 | 16.5981 | 31 | 0.7333 | 0.7500 | 0.7417 | 0.5806 |

## BM25 Fold Results

| Fold | Threshold | Test n | Pos. pass | No-gold abstain | Balanced acc. | Success@20 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 699.926 | 37 | 0.3043 | 0.9286 | 0.6165 | 0.4865 |
| 1 | 673.711 | 33 | 0.2143 | 0.8947 | 0.5545 | 0.5152 |
| 2 | 878.253 | 31 | 0.1429 | 1.0000 | 0.5714 | 0.5484 |
| 3 | 699.926 | 32 | 0.2500 | 1.0000 | 0.6250 | 0.5938 |
| 4 | 699.926 | 31 | 0.2667 | 1.0000 | 0.6333 | 0.6129 |
