#!/usr/bin/env bash
set -euo pipefail
ROOT=/home/sauravsvt/Desktop/Research/R1
ARB="$ROOT/agent-retrieval-bench"
PY="$ARB/.venv/bin/python"
ARB_BIN="$ARB/.venv/bin/arb"
CACHE="$ROOT/results/embeddings/E007_qwen3_embedding_4b"
SHARED="$ROOT/results/embeddings/E007_qwen3_embedding_4b_texts.sqlite"
LOG="$ROOT/results/logs/E007_qwen_backend.txt"
MODEL=Qwen/Qwen3-Embedding-4B
mkdir -p "$CACHE" "$ROOT/results/raw" "$ROOT/results/baselines" "$ROOT/results/logs"
{
  echo "===== QWEN START $(date -Iseconds) ====="
  echo "HARDWARE DEVIATION: official Qwen job uses --batch-size 8; that OOMed on this 20GB/70W GPU on etcd chunks. Retrying batch-size 1 with PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True. Model/normalize/prefixes/device unchanged."
  nvidia-smi --query-gpu=name,memory.total,memory.free,power.limit --format=csv
  cd "$ARB"
  for subset in v2_code2test v2_comment2context v2_trace2code v2_edit2ripple; do
    echo "===== QWEN POSITIVE $subset $(date -Iseconds) ====="
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
    /usr/bin/time -v "$ARB_BIN" eval-embedding \
      --derived "data/benchmark/$subset" \
      --corpus "data/corpus/$subset" \
      --model "$MODEL" \
      --device cuda \
      --trust-remote-code \
      --batch-size 1 \
      --query-batch-size 1 \
      --candidate-filter all_files \
      --no-keep-list \
      --cache "$CACHE" \
      --shared-text-cache "$SHARED" \
      --resume-details \
      --out "$ROOT/results/baselines/E007_${subset}_qwen_summary.json" \
      --details "$ROOT/results/raw/E007_${subset}_qwen_details.jsonl"
  done
  echo "===== QWEN SELECTIVE 427 REFUSED $(date -Iseconds) ====="
  echo "Monolithic eval-selective-embedding is permanently abandoned (unbounded in-process corpus/vector caches; details not checkpointed). Use scripts/run_e007_qwen_shard_queue.sh"
  exit 2
  echo "===== QWEN BACKEND DONE $(date -Iseconds) ====="
  nvidia-smi --query-gpu=utilization.gpu,memory.used,power.draw --format=csv
} >> "$LOG" 2>&1
