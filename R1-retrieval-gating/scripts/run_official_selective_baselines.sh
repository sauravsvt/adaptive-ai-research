#!/usr/bin/env bash
# Official selective lexical/BM25 on released mixed manifests.
set -euo pipefail

ROOT=/home/sauravsvt/Desktop/Research/R1
ARB="$ROOT/agent-retrieval-bench"
LOG="$ROOT/results/logs/E005_official_selective_baselines.txt"
cd "$ARB"
# shellcheck disable=SC1091
. .venv/bin/activate

run_sel() {
  local derived="$1"
  local name="$2"
  local ranker="$3"
  local stem="E005_${name}_${ranker}"
  local out="$ROOT/results/baselines/${stem}_summary.json"
  local details="$ROOT/results/raw/${stem}_details.jsonl"
  local sweep="$ROOT/results/raw/${stem}_threshold_sweep.jsonl"
  local report="$ROOT/results/baselines/${stem}_report.md"
  if [[ -f "$details" && -f "$out" ]]; then
    echo "[skip] $name $ranker already exists"
    return 0
  fi
  echo "==== $(date --iso-8601=seconds) eval-selective-baseline $name $ranker ===="
  /usr/bin/time -v arb eval-selective-baseline \
    --derived "$derived" \
    --corpus data/corpus/v2_selective_mixed \
    --ranker "$ranker" \
    --candidate-filter all_files \
    --no-keep-list \
    --out "$out" \
    --details "$details" \
    --sweep "$sweep" \
    --report "$report"
  echo "==== $(date --iso-8601=seconds) done $name $ranker ===="
}

{
  echo "start $(date --iso-8601=seconds)"
  run_sel data/benchmark/v2_selective_retrieval_balanced balanced lexical
  run_sel data/benchmark/v2_selective_retrieval_balanced balanced bm25
  run_sel data/benchmark/v2_selective_retrieval_natural natural lexical
  run_sel data/benchmark/v2_selective_retrieval_natural natural bm25
  echo "selective_done $(date --iso-8601=seconds)"
} 2>&1 | tee "$LOG"
