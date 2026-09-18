#!/usr/bin/env python3
"""Official repo-grouped selective CV for lexical and BM25 only. No threshold tuning for our method."""

from __future__ import annotations

import os
from pathlib import Path

from agent_retrieval_bench.selective_cv import report_selective_group_cv

ROOT = Path("/home/sauravsvt/Desktop/Research/R1")
ARB = ROOT / "agent-retrieval-bench"


def main() -> None:
    os.chdir(ARB)
    for name in ("natural", "balanced"):
        details = {
            "lexical": ROOT / "results/raw" / f"E005_{name}_lexical_details.jsonl",
            "BM25": ROOT / "results/raw" / f"E005_{name}_bm25_details.jsonl",
        }
        missing = [str(path) for path in details.values() if not path.exists()]
        if missing:
            raise SystemExit(f"missing details for {name}: {missing}")
        out_md = ROOT / "results/baselines" / f"E005_{name}_selective_cv.md"
        out_json = ROOT / "results/baselines" / f"E005_{name}_selective_cv.json"
        result = report_selective_group_cv(
            detail_paths=details,
            out_path=out_md,
            json_out_path=out_json,
            fold_count=5,
        )
        print(name, result)


if __name__ == "__main__":
    main()
