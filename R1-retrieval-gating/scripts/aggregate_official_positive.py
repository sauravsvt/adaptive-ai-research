#!/usr/bin/env python3
"""Aggregate official subset evals with ARB's own summarizers and BCY packer."""

from __future__ import annotations

import json
from pathlib import Path

from agent_retrieval_bench.baseline import summarize_details
from agent_retrieval_bench.bcy_curve import (
    CorpusFileCache,
    DEFAULT_BUDGETS,
    DEFAULT_COVERAGE_THRESHOLDS,
    evaluate_run,
    load_corpus_manifest,
)
from agent_retrieval_bench.io import read_json, read_jsonl, write_json
from agent_retrieval_bench.v2_positive_report import RANK_METRICS, TASK_SAMPLES, TASKS

ROOT = Path("/home/sauravsvt/Desktop/Research/R1")
ARB = ROOT / "agent-retrieval-bench"
PUBLISHED = {"Recall@20": 0.4452, "MRR": 0.1520, "BCY@8k": 0.2051}


def positive_corpus_manifest() -> dict[tuple[str, str], Path]:
    combined: dict[tuple[str, str], Path] = {}
    for subset in ("v2_code2test", "v2_comment2context", "v2_trace2code", "v2_edit2ripple"):
        combined.update(load_corpus_manifest(ARB / "data/corpus" / subset / "corpus_manifest.jsonl"))
    return combined


def load_details(ranker: str) -> list[dict]:
    rows: list[dict] = []
    for subset in ("v2_code2test", "v2_comment2context", "v2_trace2code", "v2_edit2ripple"):
        path = ROOT / "results/raw" / f"E004_{subset}_{ranker}_details.jsonl"
        part = read_jsonl(path)
        if not part:
            raise SystemExit(f"missing or empty details: {path}")
        rows.extend(part)
    return rows


def main() -> None:
    import os

    os.chdir(ARB)
    out_dir = ROOT / "results/baselines"
    cache = CorpusFileCache(positive_corpus_manifest())

    comparison = {"published_bm25_positive_only": PUBLISHED, "methods": {}}
    for ranker, bcy_label in (("lexical", "Lexical"), ("bm25", "BM25")):
        details = load_details(ranker)
        summary = summarize_details(details)
        details_path = ROOT / "results/raw" / f"E004_positive345_{ranker}_details.jsonl"
        with details_path.open("w", encoding="utf-8") as handle:
            for row in details:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        bcy = evaluate_run(
            bcy_label,
            "lexical",
            details_path,
            details,
            cache,
            DEFAULT_BUDGETS,
            DEFAULT_COVERAGE_THRESHOLDS,
        )
        overall = summary["overall"]
        bcy8k = float(bcy["overall"]["BCY@8000"])
        row = {
            "evaluated": overall["samples"],
            "Recall@20": overall["Recall@20"],
            "MRR": overall["MRR"],
            "Recall@5": overall["Recall@5"],
            "Recall@10": overall["Recall@10"],
            "BCY@8k": bcy8k,
            "by_task": {
                task: {
                    "samples": summary[task]["samples"],
                    **{metric: summary[task][metric] for metric in RANK_METRICS},
                    "BCY@8k": float(bcy["by_task"][task]["BCY@8000"]),
                }
                for task in TASKS
            },
        }
        if overall["samples"] != 345:
            raise SystemExit(f"{ranker} details have {overall['samples']} rows; expected 345")
        for task, expected in TASK_SAMPLES.items():
            if row["by_task"][task]["samples"] != expected:
                raise SystemExit(f"{ranker} {task} n={row['by_task'][task]['samples']} expected {expected}")
        write_json(out_dir / f"E004_positive345_{ranker}_summary.json", {"ranker": ranker, **row, "bcy_run": bcy})
        write_json(out_dir / f"E004_positive345_{ranker}_bcy.json", bcy)
        comparison["methods"][ranker] = row
        if ranker == "bm25":
            comparison["bm25_vs_published"] = {
                metric: {
                    "reproduced": row[metric],
                    "published": PUBLISHED[metric],
                    "abs_diff": abs(row[metric] - PUBLISHED[metric]),
                }
                for metric in PUBLISHED
            }

    write_json(out_dir / "E004_positive345_comparison.json", comparison)
    print(json.dumps(comparison, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
