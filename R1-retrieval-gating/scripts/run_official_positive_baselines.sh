#!/usr/bin/env bash
# Official ARB lexical/BM25 reproduction. Does not implement our method.
set -euo pipefail

ROOT=/home/sauravsvt/Desktop/Research/R1
ARB="$ROOT/agent-retrieval-bench"
LOG="$ROOT/results/logs/E004_official_positive_baselines.txt"
cd "$ARB"
# shellcheck disable=SC1091
. .venv/bin/activate

run_positive() {
  local subset="$1"
  local ranker="$2"
  local out="$ROOT/results/baselines/E004_${subset}_${ranker}_summary.json"
  local details="$ROOT/results/raw/E004_${subset}_${ranker}_details.jsonl"
  if [[ -f "$details" && -f "$out" ]]; then
    echo "[skip] $subset $ranker already exists"
    return 0
  fi
  echo "==== $(date --iso-8601=seconds) eval-baseline $subset $ranker ===="
  /usr/bin/time -v arb eval-baseline \
    --derived "data/benchmark/${subset}" \
    --corpus "data/corpus/${subset}" \
    --ranker "$ranker" \
    --candidate-filter all_files \
    --no-keep-list \
    --out "$out" \
    --details "$details"
  echo "==== $(date --iso-8601=seconds) done $subset $ranker ===="
}

{
  echo "start $(date --iso-8601=seconds)"

  # Reuse frozen E002 BM25 for edit2ripple instead of overwriting that experiment.
  if [[ ! -f "$ROOT/results/raw/E004_v2_edit2ripple_bm25_details.jsonl" ]]; then
    cp -a "$ROOT/results/raw/E002_v2_edit2ripple_bm25_details.jsonl" \
      "$ROOT/results/raw/E004_v2_edit2ripple_bm25_details.jsonl"
    cp -a "$ROOT/results/baselines/E002_v2_edit2ripple_bm25_summary.json" \
      "$ROOT/results/baselines/E004_v2_edit2ripple_bm25_summary.json"
    echo "copied E002 BM25 artifacts to E004_v2_edit2ripple_bm25_*"
  fi

  run_positive v2_trace2code lexical
  run_positive v2_trace2code bm25
  run_positive v2_edit2ripple lexical
  run_positive v2_comment2context lexical
  run_positive v2_comment2context bm25
  run_positive v2_code2test lexical
  run_positive v2_code2test bm25

  echo "positive_done $(date --iso-8601=seconds)"
} 2>&1 | tee "$LOG"
