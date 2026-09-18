# Selective lexical Threshold Report

Evaluated: 427 (345 positive, 82 no-gold)
Skipped: `{}`

## Confidence Summary

- positive: count 345, median 21.9232, p10 14.8464, p90 66.6443
- no_gold: count 82, median 15.3505, p10 5.3631, p90 36.0348

## Operating Points

| point | threshold | selective acc | balanced acc | no-gold abstain | positive pass | success@20 | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| no_abstain | -inf | 0.808 | 0.500 | 0.000 | 1.000 | 0.461 | 1.000 |
| best_selective_accuracy | 9.50851 | 0.862 | 0.650 | 0.305 | 0.994 | 0.518 | 0.937 |
| best_balanced_accuracy | 16.6336 | 0.773 | 0.711 | 0.610 | 0.812 | 0.496 | 0.731 |
| best_selective_success@20 | 13.527 | 0.857 | 0.693 | 0.427 | 0.959 | 0.522 | 0.885 |
| target_no_gold_abstain_80 | 23.9909 | 0.482 | 0.605 | 0.805 | 0.406 | 0.356 | 0.365 |
| target_positive_pass_90 | 14.804 | 0.822 | 0.690 | 0.476 | 0.904 | 0.508 | 0.831 |

## Positive Retrieval Without Abstention

- Recall@5: 0.2292
- Recall@10: 0.3548
- Recall@20: 0.4940
- MRR: 0.1574
- gold_coverage@8k: 0.0720
- Precision@20: 0.0354
- context_efficiency@8k: 0.0269
