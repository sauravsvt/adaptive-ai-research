# Selective bm25 Threshold Report

Evaluated: 164 (82 positive, 82 no-gold)
Skipped: `{}`

## Confidence Summary

- positive: count 82, median 275.1405, p10 75.9265, p90 1848.0134
- no_gold: count 82, median 304.2749, p10 46.3613, p90 588.2806

## Operating Points

| point | threshold | selective acc | balanced acc | no-gold abstain | positive pass | success@20 | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_abstain | -inf | 0.500 | 0.500 | 0.000 | 1.000 | 0.244 | 1.000 |
| best_selective_accuracy | 699.926 | 0.622 | 0.622 | 0.976 | 0.268 | 0.561 | 0.146 |
| best_balanced_accuracy | 699.926 | 0.622 | 0.622 | 0.976 | 0.268 | 0.561 | 0.146 |
| best_selective_success@20 | 699.926 | 0.622 | 0.622 | 0.976 | 0.268 | 0.561 | 0.146 |
| target_no_gold_abstain_80 | 486.403 | 0.573 | 0.573 | 0.829 | 0.317 | 0.506 | 0.244 |
| target_positive_pass_90 | 74.4476 | 0.585 | 0.585 | 0.256 | 0.915 | 0.354 | 0.829 |

## Positive Retrieval Without Abstention

- Recall@5: 0.1728
- Recall@10: 0.2683
- Recall@20: 0.4075
- MRR: 0.1396
- gold_coverage@8k: 0.0894
- Precision@20: 0.0323
- context_efficiency@8k: 0.0448
