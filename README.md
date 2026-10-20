# Adaptive AI research

Independent research archive of three sequential local-inference projects (R1–R3). Frozen experimental files are copied as-is; they are not rewritten.

This is not a paper claim set. Each project records a confirmatory stop or a limited continue.

## Projects

### R1 — retrieval gating (`R1-retrieval-gating/`)

Selective retrieval gating. A broad universal mechanism was not confirmed. The recorded signal is lexical-specific.

Checkpoint: `r1-e007` (E007 complete; do not start E008 from this archive).

### R2 — structural escape (`R2-structural-escape/`)

Structural escape (A4 vs continue A1). Stopped after failed independent replication on fixed early-trajectory prefixes (MBPP+, K=160).

Checkpoint: `r2-e001` (R2 closed; do not start E002).

### R3 — verification gating (`R3-verification-gating/`)

Verification-gated low→high reasoning. Stopped because high reasoning was substantially worse than low on HumanEval+ plus-tests.

Checkpoint: `r3-e000` (do not start E001).

## Layout

```
adaptive-ai-research/
├── README.md
├── R1-retrieval-gating/
├── R2-structural-escape/
├── R3-verification-gating/
└── docs/
    └── RESEARCH_LOG.md
```

Each project keeps preregistrations, configs, scripts, compact frozen results, manifests, and hashes. Trajectory dumps (full generations, arm transcripts, prefixes) and benchmark/model caches are omitted; their hashes remain in the frozen `SHA256SUMS` files.

## Tags

| Tag | Meaning |
| --- | --- |
| `r1-e007` | R1 through frozen E007 |
| `r2-e001` | R2 through frozen E001 close |
| `r3-e000` | R3 through frozen E000 stop |

See `docs/RESEARCH_LOG.md` for the decision sequence.
