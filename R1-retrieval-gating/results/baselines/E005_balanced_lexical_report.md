# Selective lexical Threshold Report

Evaluated: 164 (82 positive, 82 no-gold)
Skipped: `{}`

## Confidence Summary

- positive: count 82, median 21.7301, p10 15.3219, p90 68.0321
- no_gold: count 82, median 15.3505, p10 5.3631, p90 36.0348

## Operating Points

| point | threshold | selective acc | balanced acc | no-gold abstain | positive pass | success@20 | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_abstain | -inf | 0.500 | 0.500 | 0.000 | 1.000 | 0.256 | 1.000 |
| best_selective_accuracy | 16.5388 | 0.713 | 0.713 | 0.598 | 0.829 | 0.506 | 0.616 |
| best_balanced_accuracy | 16.5388 | 0.713 | 0.713 | 0.598 | 0.829 | 0.506 | 0.616 |
| best_selective_success@20 | 45.8993 | 0.591 | 0.591 | 0.988 | 0.195 | 0.549 | 0.104 |
| target_no_gold_abstain_80 | 24.8984 | 0.622 | 0.622 | 0.817 | 0.427 | 0.524 | 0.305 |
| target_positive_pass_90 | 15.2504 | 0.701 | 0.701 | 0.500 | 0.902 | 0.482 | 0.701 |

## Positive Retrieval Without Abstention

- Recall@5: 0.2063
- Recall@10: 0.3404
- Recall@20: 0.4380
- MRR: 0.1466
- gold_coverage@8k: 0.0732
- Precision@20: 0.0341
- context_efficiency@8k: 0.0288
