#!/usr/bin/env bash
# Recover official Qwen top-20 file scores (one corpus at a time) and run the frozen E007 gate.
set -euo pipefail
ROOT=/home/sauravsvt/Desktop/Research/R1
PY="$ROOT/agent-retrieval-bench/.venv/bin/python"
LOG="$ROOT/results/logs/E007_qwen_gate.txt"
mkdir -p "$ROOT/results/logs"
{
  echo "===== QWEN POSITIVE 345 $(date -Iseconds) ====="
  "$PY" "$ROOT/scripts/e007_cross_retriever.py" qwen-positive
  echo "===== QWEN SCORE RECOVERY + GATE $(date -Iseconds) ====="
  PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True \
  "$PY" "$ROOT/scripts/e007_cross_retriever.py" qwen-gate
  echo "===== QWEN GATE DONE $(date -Iseconds) ====="
} >> "$LOG" 2>&1
