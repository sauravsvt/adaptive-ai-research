# R2 closed

**Status: CLOSED**

Project: `/home/sauravsvt/Desktop/Research/R2`

Closed decision (E001, confirmatory):

**STOP — NO A4 OVER A1 SIGNAL**

E000 remains frozen as **CONTINUE — MIXED SIGNAL**. That did not
authorize E002. E001 independently tested frozen A4 vs A1 on fixed
early trajectory prefixes (MBPP+, K=160) and did not show a material
A4−A1 gain.

## What this close does

- Freezes a hash-only checkpoint of existing artifacts
- Does not modify E000 or E001 preregs, configs, scripts, raw files,
  or `results/frozen/E000_*` / `E001_*` contents
- Does not start E002
- Does not retune A1/A4/K
- Does not authorize Paper 2 claims

## Integrity (2026-09-18)

All 31 files listed in the existing frozen `SHA256SUMS.json` files
were re-hashed and matched. See `results/frozen/R2_close/`.

## Not in the close

Retrieval, new models, prompt edits, E002, or any R3 execution.
R3 is a separate project and is not authorized by this file.
