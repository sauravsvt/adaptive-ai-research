# Selective bm25 Threshold Report

Evaluated: 427 (345 positive, 82 no-gold)
Skipped: `{}`

## Confidence Summary

- positive: count 345, median 241.1661, p10 71.6715, p90 1825.7257
- no_gold: count 82, median 304.2749, p10 46.3613, p90 588.2806

## Operating Points

| point | threshold | selective acc | balanced acc | no-gold abstain | positive pass | success@20 | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_abstain | -inf | 0.808 | 0.500 | 0.000 | 1.000 | 0.429 | 1.000 |
| best_selective_accuracy | 52.4281 | 0.827 | 0.572 | 0.159 | 0.986 | 0.457 | 0.958 |
| best_balanced_accuracy | 752.74 | 0.356 | 0.597 | 0.988 | 0.206 | 0.288 | 0.169 |
| best_selective_success@20 | 61.5777 | 0.815 | 0.588 | 0.220 | 0.957 | 0.461 | 0.923 |
| target_no_gold_abstain_80 | 485.99 | 0.377 | 0.549 | 0.829 | 0.270 | 0.293 | 0.251 |
| target_positive_pass_90 | 64.6814 | 0.806 | 0.592 | 0.244 | 0.939 | 0.459 | 0.904 |

## Positive Retrieval Without Abstention

- Recall@5: 0.1899
- Recall@10: 0.3034
- Recall@20: 0.4452
- MRR: 0.1520
- gold_coverage@8k: 0.0928
- Precision@20: 0.0328
- context_efficiency@8k: 0.0431
