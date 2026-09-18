# R3 Experimental Record

## Research Question

Can verification-gated adaptive inference preserve verified coding
success while materially reducing GPU compute compared with always
using the expensive inference path?

## Current Status

R3-E000 confirmatory analysis frozen.

**STOP — NO EXPENSIVE ADVANTAGE**

Do not start E001. Do not retune `think=low/high`, `num_predict`,
gate, margins, or prompts.

See `PREREG.md` and `configs/E000_verification_gated.json`.

## Software isolation

R3 does not import, copy, or depend on R1 or R2 experimental
artifacts. R2 is closed (**STOP — NO A4 OVER A1 SIGNAL**) and is
not an input to R3 scoring.

## E000

### Stage-0 freeze (before any HumanEval+ generation)

Prereg frozen exactly as reviewed:
`PREREG.md` sha256 `329b68dacb84dafaa6178f66a46deaa3d0a43e4021dd2e72144e56726a2f2f7f`

- Warm: non-benchmark prompt; `ollama ps` `100% GPU`
- Model load_duration 11.535 s (not in policy `G_decode`)
- HumanEval+ v0.1.10, n=164, dataset hash `fe585eb4df8c88d844eeb463ea4d0302`
- Order: cheap-first 84, expensive-first 80
- Frozen copies: `results/frozen/E000_stage0/`
  - `PREREG.md` sha256 `329b68dacb84dafaa6178f66a46deaa3d0a43e4021dd2e72144e56726a2f2f7f`
  - `E000_verification_gated.json` sha256 `afe6a0d044fa0865c5ea33492e2b61703f7ef78dc97e22fc3afddde6cbb40009`
  - `r3_lib.py` sha256 `21054a6a808bfd5dd834b3234aa2675dd6cd563db54e83350c99735c0f64be47`
  - `r3_e000.py` sha256 `1def8966efa7bd2e76d1e687b0a9923e97e62a69721f657e20268e6c41e1039c`
  - `E000_task_ids.json` sha256 `09d6743d7ed0e620848a1bc96b3b58c98d8d0465dc4529f8968c953f2a70ab77`
  - `E000_generation_order.json` sha256 `29f4a64d9a9c250ddd717dcc9f18b4b4e12d4585fd9a5542101d6062418a6448`
  - `E000_warm_residency.json` sha256 `3dbd878c192aec3fe6b8eac97e7bd1d8b21bb77edd6afdb83f430587e077271f`
  - `E000_stage0_manifest.json` sha256 `2c95bf41215481293cc25b612efeb49171e970870fac45edd955a91a4d457471`

Started `scripts/r3_e000.py --stage all`. Log: `results/logs/E000_run.txt`.

### Execution

164/164 tasks scored. Paired cheap (`think=low`, 512) and expensive
(`think=high`, 1536). No third sample. GPU residency remained
`100% GPU` on post-call checks.

- `HumanEval/115` HTTP 500 on pass 1 (both paths); succeeded on a
  later pass at the same frozen settings
- `HumanEval/99` expensive once returned no `eval_duration`; retried
  at the same frozen settings and then scored

Process wall of the main generation run: 5857 s (1.63 h).

### Confirmatory table (HumanEval+ plus-tests PASS)

                    n_pass/n     rate
CHEAP_ONLY          142/164      0.866
EXPENSIVE_ONLY       58/164      0.354
ADAPTIVE            142/164      0.866

Paired bootstrap, 10,000 replicates, seed 0, n=164:

- Δ_QE expensive−cheap: −0.512, 95% CI [−0.585, −0.439]
- Δ_PE adaptive−expensive: +0.512, 95% CI [+0.439, +0.585]
- Δ_G G_decode expensive−adaptive: +17.69 s, 95% CI [+15.89, +19.41]
- R_G = 0.653

Material quality gap required Δ_QE ≥ +0.05 and CI lower bound > 0.

### Frozen decision

Expensive-only is worse than cheap-only on plus-tests. The
pre-registered quality-gap test fails. Later branches (non-inferiority,
20% `G_decode` reduction) are not applied.

**STOP — NO EXPENSIVE ADVANTAGE**

Do not retune low/high, budgets, gate, margins, or prompts. Do not
start E001.

### Secondary (not confirmatory)

`G_decode` means (s/task): cheap 6.02, expensive 27.09, adaptive 9.40.

`G_service` means (s/task): expensive 27.29, adaptive 9.61. Not a
confirmatory criterion.

ADAPTIVE gate: escalate 18/164 (0.110). False accept (base-pass,
plus-fail) 4. Unnecessary escalate (base-fail, plus-pass) 0.
Gate verifier wall 7.76 s total (mean 0.047 s); CPU 2.90 s total.
Not included in `G_decode`.

Experimental sum `G_decode` (both paths, all tasks): 5431 s.
Generation wall sum: 5564 s.
Model load/warm: 11.535 s, not in policy compute.

Energy: unavailable (NVML not used / not claimed).

### Analysis freeze

- `results/raw/E000_analysis.json` and `results/frozen/E000_run/`
- analysis sha256 `ed3e991dca515e177f32812b50f7b04459c0a1db2d84f8bfe1b0df7a0f1a6f6f`
- `E000_generations.jsonl` sha256 `ce64bc2306179ddb3d52f1474bcd570be39acbbcacb92f5fef73b7a8c97c2046`
- `E000_verify.jsonl` sha256 `16d030888670610acae47105f9cfe7d5e0dffa13f120199f425c9292a3bb4e00`
- `E000_run.txt` sha256 `53ae19978619cd38febe167e717440746a6e8c86738f520d67832f7e72aee62b`
