#!/usr/bin/env bash
# Sequential official per-corpus Qwen selective shards. One process at a time.
# Does not restart the abandoned monolithic eval-selective-embedding command.
set -euo pipefail
ROOT=/home/sauravsvt/Desktop/Research/R1
PY="$ROOT/agent-retrieval-bench/.venv/bin/python"
LOG="$ROOT/results/logs/E007_qwen_shards.txt"
LOCK="$ROOT/results/raw/E007_qwen_shards/queue.lock"
mkdir -p "$ROOT/results/raw/E007_qwen_shards" "$ROOT/results/logs"

if pgrep -f 'arb eval-selective-embedding' >/dev/null 2>&1; then
  echo "ABORT: an official eval-selective-embedding process is already running" | tee -a "$LOG"
  exit 1
fi
if pgrep -f 'arb eval-embedding' >/dev/null 2>&1; then
  echo "ABORT: an official eval-embedding process is already running" | tee -a "$LOG"
  exit 1
fi

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "ABORT: shard queue lock is held; refusing a second copy" | tee -a "$LOG"
  exit 1
fi

{
  echo "===== QWEN SHARD QUEUE START $(date -Iseconds) ====="
  echo "monolithic eval-selective-embedding is permanently abandoned"
  nvidia-smi --query-gpu=name,memory.total,memory.free,power.limit --format=csv || true
  "$PY" "$ROOT/scripts/e007_qwen_shards.py" build
  if [[ ! -f "$ROOT/results/raw/E007_qwen_equivalence_smoke.json" ]]; then
    echo "===== QWEN SHARD SMOKE $(date -Iseconds) ====="
    "$PY" "$ROOT/scripts/e007_qwen_shards.py" smoke
  else
    echo "smoke report already present; not rerunning unless missing"
  fi
  echo "===== QWEN SHARD QUEUE $(date -Iseconds) ====="
  "$PY" "$ROOT/scripts/e007_qwen_shards.py" queue
  echo "===== QWEN SHARD QUEUE DONE $(date -Iseconds) ====="
} >> "$LOG" 2>&1
