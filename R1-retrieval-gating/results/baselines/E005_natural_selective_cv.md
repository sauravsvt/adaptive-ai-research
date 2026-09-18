# Selective Retrieval: Repo-Grouped 5-Fold Cross-Validation

- Samples: 427 (345 positive, 82 no-gold)
- No-gold reasons: counterfactual_wrong_repo=32, external_service=7, upstream_dependency=41, user_error=2
- Repository groups: 25
- Folds: 5
- Calibration: maximize balanced accuracy on four folds; evaluate once on held-out repositories.
- Aggregate metrics use one out-of-fold decision per sample.

## Mixed Out-of-Fold Results

| Ranker | Pos. pass | No-gold abstain | Balanced acc. | Selective acc. | Success@20 | Coverage | No-abstain Success@20 |
|---|---:|---:|---:|---:|---:|---:|---:|
| lexical | 0.8145 | 0.5976 | 0.7060 | 0.7728 | 0.4965 | 0.7354 | 0.4614 |
| BM25 | 0.6725 | 0.4512 | 0.5618 | 0.6300 | 0.3770 | 0.6487 | 0.4286 |

## Natural Evidence-Only Out-of-Fold Results

This view contains 345 positives and 50 natural no-gold samples. Thresholds are recalibrated within the natural-only repo-grouped folds; counterfactual wrong-repository negatives are excluded from both calibration and evaluation.

| Ranker | Pos. pass | No-gold abstain | Balanced acc. | Selective acc. | Success@20 | Coverage | No-abstain Success@20 |
|---|---:|---:|---:|---:|---:|---:|---:|
| lexical | 0.4232 | 0.5800 | 0.5016 | 0.4430 | 0.2937 | 0.4228 | 0.4987 |
| BM25 | 0.1884 | 0.9800 | 0.5842 | 0.2886 | 0.2203 | 0.1671 | 0.4633 |

## Fold Composition

| Fold | Samples | Positive | No-gold | Repositories |
|---:|---:|---:|---:|---|
| 0 | 111 | 97 | 14 | gin-gonic/gin, microsoft/playwright, numpy/numpy, pydantic/pydantic, scrapy/scrapy |
| 1 | 80 | 60 | 20 | clap-rs/clap, huggingface/transformers, mockito/mockito, pytest-dev/pytest, vuejs/core |
| 2 | 79 | 63 | 16 | fastapi/fastapi, pallets/click, python/mypy, spring-projects/spring-boot, vitejs/vite |
| 3 | 78 | 62 | 16 | caddyserver/caddy, eslint/eslint, etcd-io/etcd, ipython/ipython, pypa/pip |
| 4 | 79 | 63 | 16 | HypothesisWorks/hypothesis, astral-sh/ruff, huggingface/diffusers, tokio-rs/tokio, tox-dev/tox |

## lexical Fold Results

| Fold | Threshold | Test n | Pos. pass | No-gold abstain | Balanced acc. | Success@20 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 16.6336 | 111 | 0.6598 | 0.5000 | 0.5799 | 0.5315 |
| 1 | 16.6336 | 80 | 0.9333 | 0.6000 | 0.7667 | 0.5000 |
| 2 | 16.6599 | 79 | 0.8730 | 0.3750 | 0.6240 | 0.3671 |
| 3 | 16.53 | 78 | 0.7419 | 0.6875 | 0.7147 | 0.5128 |
| 4 | 16.6336 | 79 | 0.9524 | 0.8125 | 0.8824 | 0.5570 |

## BM25 Fold Results

| Fold | Threshold | Test n | Pos. pass | No-gold abstain | Balanced acc. | Success@20 |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 57.5687 | 111 | 0.9897 | 0.0000 | 0.4948 | 0.5315 |
| 1 | 64.6814 | 80 | 0.8667 | 0.2000 | 0.5333 | 0.3750 |
| 2 | 61.5777 | 79 | 0.9365 | 0.0625 | 0.4995 | 0.3165 |
| 3 | 752.74 | 78 | 0.2097 | 1.0000 | 0.6048 | 0.3205 |
| 4 | 752.74 | 79 | 0.1905 | 1.0000 | 0.5952 | 0.2785 |
