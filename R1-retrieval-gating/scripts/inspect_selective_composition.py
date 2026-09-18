#!/usr/bin/env python3
"""Document official selective-retrieval mixed lists. Does not invent a split."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ARB = Path("/home/sauravsvt/Desktop/Research/R1/agent-retrieval-bench")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sample_id(row: dict) -> str:
    return str(row.get("id") or "")


def summarize(name: str, rows: list[dict]) -> dict:
    ids = [sample_id(row) for row in rows]
    repos = Counter(str(row.get("repo") or "") for row in rows)
    tasks = Counter(str(row.get("task_type") or "") for row in rows)
    no_gold = [row for row in rows if (row.get("gold") or {}).get("no_gold") is True]
    positive = [row for row in rows if (row.get("gold") or {}).get("no_gold") is not True]
    reasons = Counter(str((row.get("gold") or {}).get("reason") or "") for row in no_gold)
    organic = Counter(bool((row.get("metadata") or {}).get("organic")) for row in no_gold)
    return {
        "name": name,
        "n": len(rows),
        "unique_ids": len(set(ids)),
        "duplicate_ids": len(ids) - len(set(ids)),
        "positive": len(positive),
        "no_gold": len(no_gold),
        "no_gold_share": (len(no_gold) / len(rows)) if rows else 0.0,
        "task_counts": dict(sorted(tasks.items())),
        "repo_counts": dict(sorted(repos.items())),
        "repo_n": len(repos),
        "no_gold_reasons": dict(sorted(reasons.items())),
        "no_gold_organic_true_false": {"true": organic.get(True, 0), "false": organic.get(False, 0)},
        "ids": sorted(set(ids)),
        "repos": sorted(repos),
    }


def overlap(a: dict, b: dict) -> dict:
    ids_a, ids_b = set(a["ids"]), set(b["ids"])
    repos_a, repos_b = set(a["repos"]), set(b["repos"])
    return {
        "id_intersection": len(ids_a & ids_b),
        "id_only_a": len(ids_a - ids_b),
        "id_only_b": len(ids_b - ids_a),
        "repo_intersection": sorted(repos_a & repos_b),
        "repo_only_a": sorted(repos_a - repos_b),
        "repo_only_b": sorted(repos_b - repos_a),
    }


def main() -> None:
    balanced = load_jsonl(ARB / "data/benchmark/v2_selective_retrieval_balanced/samples.jsonl")
    natural = load_jsonl(ARB / "data/benchmark/v2_selective_retrieval_natural/samples.jsonl")
    abstention = load_jsonl(ARB / "data/benchmark/v2_abstention/samples.jsonl")
    positives = {}
    for task, rel in (
        ("code2test", "data/benchmark/v2_code2test/samples.jsonl"),
        ("comment2context", "data/benchmark/v2_comment2context/samples.jsonl"),
        ("trace2code", "data/benchmark/v2_trace2code/samples.jsonl"),
        ("edit2ripple", "data/benchmark/v2_edit2ripple/samples.jsonl"),
    ):
        positives[task] = load_jsonl(ARB / rel)

    all_positive_ids = set()
    for rows in positives.values():
        all_positive_ids.update(sample_id(row) for row in rows)
    abstention_ids = {sample_id(row) for row in abstention}

    bal_s = summarize("v2_selective_retrieval_balanced", balanced)
    nat_s = summarize("v2_selective_retrieval_natural", natural)
    abs_s = summarize("v2_abstention", abstention)

    natural_no_gold = [
        row
        for row in abstention
        if str((row.get("gold") or {}).get("reason") or "") != "counterfactual_wrong_repo"
    ]
    counterfactual = [
        row
        for row in abstention
        if str((row.get("gold") or {}).get("reason") or "") == "counterfactual_wrong_repo"
    ]

    report = {
        "note": "Composition only. No train/dev/test split was invented.",
        "official_calibration": {
            "eval_command": "arb eval-selective-baseline --ranker {lexical|bm25} --candidate-filter all_files --no-keep-list",
            "confidence": "top retrieval score",
            "sweep": "eval-selective-baseline writes a threshold sweep over observed top scores; operating points include no_abstain and best_* but those in-sample maxima are not used as our method.",
            "paper_protocol": "arb report-selective-cv: repo-grouped 5-fold CV; threshold maximizing balanced accuracy on training repos is applied once to held-out repos.",
            "primary_metric_frozen": "selective_success@20",
            "selective_success@20_definition": "no-gold abstention is correct; an accepted positive is correct only when a gold file appears in the top 20.",
        },
        "balanced": {k: v for k, v in bal_s.items() if k not in {"ids", "repos"}},
        "natural": {k: v for k, v in nat_s.items() if k not in {"ids", "repos"}},
        "abstention_release": {k: v for k, v in abs_s.items() if k not in {"ids", "repos"}},
        "no_gold_strata": {
            "natural_like": {
                "n": len(natural_no_gold),
                "reasons": dict(Counter(str((row.get("gold") or {}).get("reason") or "") for row in natural_no_gold)),
            },
            "counterfactual_wrong_repo": {"n": len(counterfactual)},
        },
        "overlap": {
            "balanced_vs_natural": overlap(bal_s, nat_s),
            "natural_positive_ids_subset_of_v2_positive": sorted(set(nat_s["ids"]) & all_positive_ids).__len__()
            == 345
            and len(set(nat_s["ids"]) & all_positive_ids) == 345,
            "natural_ids_vs_all_positive": {
                "intersection_with_345_positive": len(set(nat_s["ids"]) & all_positive_ids),
                "natural_ids_not_in_345_positive": len(set(nat_s["ids"]) - all_positive_ids),
            },
            "natural_ids_vs_abstention82": {
                "intersection": len(set(nat_s["ids"]) & abstention_ids),
            },
            "balanced_ids_vs_345_positive": {
                "intersection": len(set(bal_s["ids"]) & all_positive_ids),
            },
            "balanced_ids_vs_abstention82": {
                "intersection": len(set(bal_s["ids"]) & abstention_ids),
            },
        },
        "positive_release_counts": {task: len(rows) for task, rows in positives.items()},
    }
    # Fix the awkward boolean field with explicit counts.
    report["overlap"]["natural_positive_coverage"] = {
        "expected_positive": 345,
        "natural_ids_in_345_positive": len(set(nat_s["ids"]) & all_positive_ids),
        "natural_no_gold_ids": len(set(nat_s["ids"]) - all_positive_ids),
        "missing_positive_ids_from_natural": len(all_positive_ids - set(nat_s["ids"])),
    }
    del report["overlap"]["natural_positive_ids_subset_of_v2_positive"]

    out = Path("/home/sauravsvt/Desktop/Research/R1/results/baselines/E003_selective_composition.json")
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("balanced", "natural", "no_gold_strata", "overlap")}, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
