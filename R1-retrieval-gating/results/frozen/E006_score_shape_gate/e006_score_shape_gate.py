#!/usr/bin/env python3
"""E006 score-shape evidence gate.

Contract: configs/E006_score_shape_gate.json
Frozen before this classifier was implemented: EXPERIMENT_RESULTS.md E006 block.

Does not change ranking. RETRIEVE uses frozen E005 top-20 files. ABSTAIN returns
no files. Features are pre-outcome file-level score-shape only.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import shutil
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path("/home/sauravsvt/Desktop/Research/R1")
ARB = ROOT / "agent-retrieval-bench"
SRC = ARB / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_retrieval_bench.baseline import (  # noqa: E402
    filter_candidate_chunks,
    load_corpus_manifest,
    query_text_for_eval,
)
from agent_retrieval_bench.io import read_jsonl  # noqa: E402
from agent_retrieval_bench.selective_cv import assign_repo_folds  # noqa: E402
from agent_retrieval_bench.selective_eval import rank_chunks_with_scores_for_ranker  # noqa: E402

EPS = 1e-12
N_FEATURES = 12
FEATURE_NAMES = [
    "top1",
    "top2",
    "margin_top1_top2",
    "safe_ratio_top1_top2",
    "mean_top5",
    "std_top5",
    "mean_top20",
    "std_top20",
    "range_top20",
    "top1_z_top20",
    "mass_top5_over_top20",
    "norm_entropy_top20_nonneg",
]
CONCENTRATION_IDX = (9, 10, 11)  # z-score, mass, entropy
NO_CONCENTRATION_IDX = tuple(i for i in range(N_FEATURES) if i not in CONCENTRATION_IDX)
BOOTSTRAP_N = 10000
BOOTSTRAP_SEED = 0
CLF_RANDOM_STATE = 0
CLF_MAX_ITER = 2000
LOGREG_C = 1.0


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def cpu_times() -> dict[str, float]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {"user_s": float(usage.ru_utime), "sys_s": float(usage.ru_stime)}


def gpu_snapshot() -> dict[str, Any]:
    import subprocess

    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=utilization.gpu,memory.used,power.draw",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        ).strip()
        util, mem, power = [part.strip() for part in out.split(",")]
        return {
            "utilization_pct": float(util),
            "memory_used_mib": float(mem),
            "power_w": float(power),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def read_jsonl_path(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hit_at_20(row: dict[str, Any]) -> bool:
    if row.get("label") != "positive":
        return False
    metrics = row.get("metrics") or {}
    if "Recall@20" in metrics:
        return float(metrics["Recall@20"]) > 0.0
    gold = set(row.get("gold_files") or [])
    return any(path in gold for path in (row.get("top_files") or [])[:20])


def success_flag(is_no_gold: bool, abstain: bool, hit: bool) -> bool:
    if is_no_gold:
        return bool(abstain)
    return (not abstain) and bool(hit)


def pad20(scores: list[float]) -> np.ndarray:
    values = [float(x) for x in scores[:20]]
    if len(values) < 20:
        values.extend([0.0] * (20 - len(values)))
    return np.asarray(values, dtype=np.float64)


def pop_std(values: np.ndarray) -> float:
    if values.size < 2:
        return 0.0
    return float(np.std(values, ddof=0))


def score_shape_features(file_scores: list[float]) -> list[float]:
    top20 = pad20(file_scores)
    top5 = top20[:5]
    top1 = float(top20[0])
    top2 = float(top20[1])
    margin = top1 - top2
    if abs(top1) < EPS and abs(top2) < EPS:
        ratio = 1.0
    else:
        ratio = top1 / max(abs(top2), EPS)
    mean5 = float(np.mean(top5))
    std5 = pop_std(top5)
    mean20 = float(np.mean(top20))
    std20 = pop_std(top20)
    range20 = float(np.max(top20) - np.min(top20))
    zscore = 0.0 if std20 < EPS else (top1 - mean20) / std20
    pos5 = np.maximum(top5, 0.0)
    pos20 = np.maximum(top20, 0.0)
    mass20 = float(np.sum(pos20))
    mass = 0.0 if mass20 < EPS else float(np.sum(pos5) / mass20)
    if mass20 < EPS:
        entropy = 0.0
    else:
        probs = pos20 / mass20
        entropy_raw = 0.0
        for prob in probs:
            p = float(prob)
            if p > 0.0:
                entropy_raw -= p * math.log(p)
        entropy = entropy_raw / math.log(20.0)
    return [
        top1,
        top2,
        margin,
        ratio,
        mean5,
        std5,
        mean20,
        std20,
        range20,
        zscore,
        mass,
        entropy,
    ]


def unique_file_scores(scored: list[tuple[float, dict[str, Any]]]) -> tuple[list[str], list[float]]:
    paths: list[str] = []
    scores: list[float] = []
    seen: set[str] = set()
    for score, chunk in scored:
        path = str(chunk.get("path", ""))
        if path and path not in seen:
            paths.append(path)
            scores.append(float(score))
            seen.add(path)
            if len(paths) >= 20:
                break
    return paths, scores


def recover_top20_scores(ranker: str, details: list[dict[str, Any]]) -> tuple[dict[str, list[float]], float]:
    started = time.perf_counter()
    cwd = os.getcwd()
    os.chdir(ARB)
    try:
        samples_path = ARB / "data/benchmark/v2_selective_retrieval_natural/samples.jsonl"
        samples = {str(row["id"]): row for row in read_jsonl(samples_path)}
        manifest = load_corpus_manifest(ARB / "data/corpus/v2_selective_mixed")
        pending: dict[Path, list[dict[str, Any]]] = defaultdict(list)
        for detail in details:
            sample_id = str(detail["sample_id"])
            sample = samples[sample_id]
            chunks_path = manifest.get((sample.get("repo"), sample.get("base_commit")))
            if chunks_path is None:
                raise SystemExit(f"STOP E006: missing corpus for {sample_id}")
            pending[chunks_path].append(detail)
        recovered: dict[str, list[float]] = {}
        mismatches = []
        for corpus_index, (chunks_path, group) in enumerate(pending.items(), start=1):
            print(
                f"[{ranker}] corpus {corpus_index}/{len(pending)} n={len(group)} {chunks_path}",
                flush=True,
            )
            chunks = filter_candidate_chunks(read_jsonl(chunks_path), "all_files")
            for detail in group:
                sample = samples[str(detail["sample_id"])]
                query_text = query_text_for_eval(sample)
                scored = rank_chunks_with_scores_for_ranker(query_text, chunks, ranker)
                paths, scores = unique_file_scores(scored)
                frozen_top = list(detail.get("top_files") or [])
                if paths != frozen_top:
                    mismatches.append(
                        {
                            "sample_id": detail["sample_id"],
                            "frozen": frozen_top,
                            "recovered": paths,
                        }
                    )
                recovered[str(detail["sample_id"])] = scores
        if mismatches:
            preview = mismatches[:3]
            raise SystemExit(
                f"STOP E006: recovered ranking != frozen top_files "
                f"({len(mismatches)} mismatches). preview={preview}"
            )
        return recovered, time.perf_counter() - started
    finally:
        os.chdir(cwd)


def make_classifier() -> LogisticRegression:
    return LogisticRegression(
        penalty="l2",
        C=LOGREG_C,
        solver="liblinear",
        max_iter=CLF_MAX_ITER,
        random_state=CLF_RANDOM_STATE,
    )


def fit_predict_proba(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_eval: np.ndarray,
) -> tuple[np.ndarray, StandardScaler, LogisticRegression]:
    scaler = StandardScaler()
    x_train_s = scaler.fit_transform(x_train)
    x_eval_s = scaler.transform(x_eval)
    clf = make_classifier()
    clf.fit(x_train_s, y_train)
    proba = clf.predict_proba(x_eval_s)
    classes = list(clf.classes_)
    abstain_index = classes.index(1)
    return proba[:, abstain_index], scaler, clf


def selective_success_from_decisions(
    rows: list[dict[str, Any]],
    abstain: dict[str, bool],
) -> float:
    hits = 0
    for row in rows:
        sample_id = str(row["sample_id"])
        is_no_gold = row["label"] == "no_gold"
        if success_flag(is_no_gold, abstain[sample_id], row["_hit20"]):
            hits += 1
    return hits / len(rows) if rows else 0.0


def choose_threshold(rows: list[dict[str, Any]], probs: dict[str, float]) -> dict[str, Any]:
    values = sorted({float(probs[str(row["sample_id"])]) for row in rows})
    candidates = [2.0]
    if values:
        candidates.append(values[0] - max(EPS, abs(values[0]) * 1e-9))
        candidates.extend((left + right) / 2.0 for left, right in zip(values, values[1:]))
        candidates.append(values[-1] + max(EPS, abs(values[-1]) * 1e-9))
        candidates.extend(values)
        candidates.append(0.0)
    unique = sorted(set(float(x) for x in candidates))
    best: dict[str, Any] | None = None
    for threshold in unique:
        decisions = {str(row["sample_id"]): float(probs[str(row["sample_id"])]) >= threshold for row in rows}
        ss = selective_success_from_decisions(rows, decisions)
        false_abs = sum(
            1 for row in rows if row["label"] == "positive" and decisions[str(row["sample_id"])]
        )
        n_retrieve = sum(1 for row in rows if not decisions[str(row["sample_id"])])
        key = (ss, -false_abs, n_retrieve, -threshold)
        record = {
            "threshold": threshold,
            "selective_success@20": ss,
            "false_abstentions": false_abs,
            "n_retrieve": n_retrieve,
        }
        if best is None or key > best["_key"]:
            record["_key"] = key
            best = record
    assert best is not None
    best.pop("_key")
    return best


def nested_oof(
    rows: list[dict[str, Any]],
    x_all: np.ndarray,
    y_all: np.ndarray,
    feature_idx: tuple[int, ...],
    outer_folds: dict[str, int],
    inner_folds_by_outer: dict[int, dict[str, int]],
    model_name: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float], dict[str, float]]:
    index_by_id = {str(row["sample_id"]): i for i, row in enumerate(rows)}
    oof_rows: list[dict[str, Any]] = []
    threshold_records: list[dict[str, Any]] = []
    train_wall = 0.0
    infer_wall = 0.0
    for outer_fold in range(5):
        train_idx = [i for i, row in enumerate(rows) if outer_folds[str(row["repo"])] != outer_fold]
        test_idx = [i for i, row in enumerate(rows) if outer_folds[str(row["repo"])] == outer_fold]
        train_rows = [rows[i] for i in train_idx]
        test_rows = [rows[i] for i in test_idx]
        inner_map = inner_folds_by_outer[outer_fold]
        inner_probs: dict[str, float] = {}
        t_train = 0.0
        t_infer = 0.0
        t0 = time.perf_counter()
        for inner_fold in range(5):
            inner_train_pos = [
                i for i in train_idx if inner_map[str(rows[i]["repo"])] != inner_fold
            ]
            inner_val_pos = [
                i for i in train_idx if inner_map[str(rows[i]["repo"])] == inner_fold
            ]
            if not inner_train_pos or not inner_val_pos:
                raise SystemExit(
                    f"STOP E006: empty inner split outer={outer_fold} inner={inner_fold}"
                )
            x_tr = x_all[np.array(inner_train_pos)][:, feature_idx]
            y_tr = y_all[np.array(inner_train_pos)]
            x_va = x_all[np.array(inner_val_pos)][:, feature_idx]
            if len(set(y_tr.tolist())) < 2:
                raise SystemExit(
                    f"STOP E006: inner train lacks a class outer={outer_fold} inner={inner_fold}"
                )
            proba, _, _ = fit_predict_proba(x_tr, y_tr, x_va)
            for local, sample_index in enumerate(inner_val_pos):
                inner_probs[str(rows[sample_index]["sample_id"])] = float(proba[local])
        t_train += time.perf_counter() - t0
        chosen = choose_threshold(train_rows, inner_probs)
        x_tr = x_all[np.array(train_idx)][:, feature_idx]
        y_tr = y_all[np.array(train_idx)]
        x_te = x_all[np.array(test_idx)][:, feature_idx]
        t_fit = time.perf_counter()
        scaler = StandardScaler()
        x_tr_s = scaler.fit_transform(x_tr)
        clf = make_classifier()
        clf.fit(x_tr_s, y_tr)
        t_mid = time.perf_counter()
        x_te_s = scaler.transform(x_te)
        proba_all = clf.predict_proba(x_te_s)
        abstain_index = list(clf.classes_).index(1)
        proba_test = proba_all[:, abstain_index]
        t_done = time.perf_counter()
        t_train += t_mid - t_fit
        t_infer += t_done - t_mid
        train_wall += t_train
        infer_wall += t_infer
        threshold = float(chosen["threshold"])
        threshold_records.append(
            {
                "model": model_name,
                "outer_fold": outer_fold,
                "threshold": threshold,
                "inner_selective_success@20": chosen["selective_success@20"],
                "inner_false_abstentions": chosen["false_abstentions"],
                "n_train": len(train_rows),
                "n_test": len(test_rows),
            }
        )
        for local, sample_index in enumerate(test_idx):
            row = rows[sample_index]
            sample_id = str(row["sample_id"])
            p_abstain = float(proba_test[local])
            abstain = p_abstain >= threshold
            oof_rows.append(
                {
                    "sample_id": sample_id,
                    "repo": row["repo"],
                    "label": row["label"],
                    "no_gold_reason": row.get("no_gold_reason"),
                    "outer_fold": outer_fold,
                    "model": model_name,
                    "p_abstain": p_abstain,
                    "threshold": threshold,
                    "abstain": abstain,
                    "hit20": bool(row["_hit20"]),
                    "success": success_flag(row["label"] == "no_gold", abstain, row["_hit20"]),
                }
            )
    times = {"train_s": train_wall, "infer_s": infer_wall}
    oof_map = {row["sample_id"]: row for row in oof_rows}
    return oof_rows, threshold_records, times, oof_map


def confusion_and_rates(rows: list[dict[str, Any]], abstain: dict[str, bool]) -> dict[str, Any]:
    cm = Counter(
        {
            "positive_returned": 0,
            "positive_abstained": 0,
            "no_gold_returned": 0,
            "no_gold_abstained": 0,
            "successful_positive_retrievals": 0,
            "correct_no_gold_abstentions": 0,
        }
    )
    successes = 0
    for row in rows:
        sample_id = str(row["sample_id"])
        is_no_gold = row["label"] == "no_gold"
        predict_abstain = bool(abstain[sample_id])
        hit = bool(row["_hit20"])
        if is_no_gold and predict_abstain:
            cm["no_gold_abstained"] += 1
            cm["correct_no_gold_abstentions"] += 1
        elif is_no_gold:
            cm["no_gold_returned"] += 1
        elif predict_abstain:
            cm["positive_abstained"] += 1
        else:
            cm["positive_returned"] += 1
            if hit:
                cm["successful_positive_retrievals"] += 1
        if success_flag(is_no_gold, predict_abstain, hit):
            successes += 1
    n = len(rows)
    n_pos = cm["positive_returned"] + cm["positive_abstained"]
    n_neg = cm["no_gold_returned"] + cm["no_gold_abstained"]
    n_retrieve = cm["positive_returned"] + cm["no_gold_returned"]
    n_abstain = cm["positive_abstained"] + cm["no_gold_abstained"]
    return {
        "n": n,
        "selective_success@20": successes / n if n else 0.0,
        "n_success": successes,
        "retrieve_rate": n_retrieve / n if n else 0.0,
        "abstention_rate": n_abstain / n if n else 0.0,
        "positive_retrieve_rate": cm["positive_returned"] / n_pos if n_pos else 0.0,
        "no_gold_abstention_rate": cm["no_gold_abstained"] / n_neg if n_neg else 0.0,
        "false_abstention_rate": cm["positive_abstained"] / n_pos if n_pos else 0.0,
        "false_retrieval_rate": cm["no_gold_returned"] / n_neg if n_neg else 0.0,
        "successful_positive_retrievals": cm["successful_positive_retrievals"],
        "correctly_abstained_no_gold": cm["correct_no_gold_abstentions"],
        "confusion": dict(cm),
        "n_positive": n_pos,
        "n_no_gold": n_neg,
    }


def paired_bootstrap_delta(
    success_a: np.ndarray,
    success_b: np.ndarray,
    n_resamples: int = BOOTSTRAP_N,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, float]:
    rng = np.random.RandomState(seed)
    n = success_a.size
    point = float(success_a.mean() - success_b.mean())
    deltas = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        idx = rng.randint(0, n, n)
        deltas[i] = float(success_a[idx].mean() - success_b[idx].mean())
    lo, hi = np.percentile(deltas, [2.5, 97.5])
    return {
        "point": point,
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "ci_includes_zero": bool(lo <= 0.0 <= hi),
        "n_resamples": n_resamples,
        "random_state": seed,
    }


def decisions_from_oof(oof_rows: list[dict[str, Any]]) -> dict[str, bool]:
    return {row["sample_id"]: bool(row["abstain"]) for row in oof_rows}


def stratum_mask(rows: list[dict[str, Any]], name: str, balanced_ids: set[str]) -> list[dict[str, Any]]:
    if name == "full_427":
        return list(rows)
    if name == "natural_like_395":
        return [row for row in rows if row.get("no_gold_reason") != "counterfactual_wrong_repo"]
    if name == "counterfactual_32":
        return [row for row in rows if row.get("no_gold_reason") == "counterfactual_wrong_repo"]
    if name == "balanced_164":
        return [row for row in rows if str(row["sample_id"]) in balanced_ids]
    if name == "positive_345":
        return [row for row in rows if row["label"] == "positive"]
    if name == "no_gold_82":
        return [row for row in rows if row["label"] == "no_gold"]
    raise KeyError(name)


def always_retrieve_decisions(rows: list[dict[str, Any]]) -> dict[str, bool]:
    return {str(row["sample_id"]): False for row in rows}


def build_fold_assignments(rows: list[dict[str, Any]], repo_folds: dict[str, int]) -> dict[str, Any]:
    inner_folds_by_outer: dict[int, dict[str, int]] = {}
    inner_summaries = []
    for outer_fold in range(5):
        train = [row for row in rows if repo_folds[str(row["repo"])] != outer_fold]
        inner = assign_repo_folds(train, 5)
        inner_folds_by_outer[outer_fold] = inner
        by_inner: dict[int, Counter[str]] = defaultdict(Counter)
        repos: dict[int, set[str]] = defaultdict(set)
        for row in train:
            inner_id = inner[str(row["repo"])]
            by_inner[inner_id][str(row["label"])] += 1
            repos[inner_id].add(str(row["repo"]))
        for inner_id in range(5):
            if not by_inner[inner_id]["positive"] or not by_inner[inner_id]["no_gold"]:
                raise SystemExit(
                    f"STOP E006: nested repo-grouped CV invalid: outer={outer_fold} "
                    f"inner={inner_id} composition={dict(by_inner[inner_id])}"
                )
        inner_summaries.append(
            {
                "outer_fold": outer_fold,
                "n_train": len(train),
                "inner_folds": {
                    str(i): {
                        "positive": by_inner[i]["positive"],
                        "no_gold": by_inner[i]["no_gold"],
                        "repos": sorted(repos[i]),
                    }
                    for i in range(5)
                },
            }
        )
    outer_composition = []
    for fold in range(5):
        subset = [row for row in rows if repo_folds[str(row["repo"])] == fold]
        outer_composition.append(
            {
                "outer_fold": fold,
                "n": len(subset),
                "positive": sum(1 for row in subset if row["label"] == "positive"),
                "no_gold": sum(1 for row in subset if row["label"] == "no_gold"),
                "repos": sorted({str(row["repo"]) for row in subset}),
            }
        )
    return {
        "protocol": "Official E005 natural-427 repo_folds for outer 5-fold; official assign_repo_folds(5) on each outer-training set for inner CV.",
        "source_outer_folds": "results/baselines/E005_natural_selective_cv.json:repo_folds",
        "nested_cv_valid": True,
        "n_samples": len(rows),
        "n_repos": len(repo_folds),
        "outer_repo_folds": repo_folds,
        "outer_composition": outer_composition,
        "inner_repo_folds_by_outer": {
            str(outer): mapping for outer, mapping in inner_folds_by_outer.items()
        },
        "inner_composition": inner_summaries,
        "written_before_model_fitting": True,
    }, inner_folds_by_outer


def run_backend(
    ranker: str,
    details: list[dict[str, Any]],
    c1_predictions: dict[str, bool],
    outer_folds: dict[str, int],
    inner_folds_by_outer: dict[int, dict[str, int]],
    balanced_ids: set[str],
) -> dict[str, Any]:
    print(f"=== recovering top-20 file scores for {ranker} ===", flush=True)
    recovered, recover_s = recover_top20_scores(ranker, details)
    feat_t0 = time.perf_counter()
    x = np.zeros((len(details), N_FEATURES), dtype=np.float64)
    y = np.zeros(len(details), dtype=np.int32)
    for i, row in enumerate(details):
        sample_id = str(row["sample_id"])
        feats = score_shape_features(recovered[sample_id])
        x[i] = np.asarray(feats, dtype=np.float64)
        y[i] = 1 if row["label"] == "no_gold" else 0
        row["_hit20"] = hit_at_20(row)
        row["_features"] = feats
    feat_s = time.perf_counter() - feat_t0

    models = {
        "C2_TOP1_LOGISTIC": (0,),
        "C3_SCORE_SHAPE_LOGISTIC": tuple(range(N_FEATURES)),
        "C3_NO_CONCENTRATION": NO_CONCENTRATION_IDX,
    }
    oof_by_model: dict[str, list[dict[str, Any]]] = {}
    threshold_records: list[dict[str, Any]] = []
    model_times: dict[str, dict[str, float]] = {}
    for model_name, idx in models.items():
        print(f"=== fitting {ranker} {model_name} ===", flush=True)
        oof_rows, thresh, times, _ = nested_oof(
            details, x, y, idx, outer_folds, inner_folds_by_outer, model_name
        )
        oof_by_model[model_name] = oof_rows
        threshold_records.extend(thresh)
        model_times[model_name] = times

    c0 = always_retrieve_decisions(details)
    c1 = {str(row["sample_id"]): bool(c1_predictions[str(row["sample_id"])]) for row in details}
    c2 = decisions_from_oof(oof_by_model["C2_TOP1_LOGISTIC"])
    c3 = decisions_from_oof(oof_by_model["C3_SCORE_SHAPE_LOGISTIC"])
    c3_nc = decisions_from_oof(oof_by_model["C3_NO_CONCENTRATION"])
    comparators = {
        "C0_ALWAYS_RETRIEVE": c0,
        "C1_OFFICIAL_TOP_SCORE_THRESHOLD": c1,
        "C2_TOP1_LOGISTIC": c2,
        "C3_SCORE_SHAPE_LOGISTIC": c3,
        "C3_NO_CONCENTRATION": c3_nc,
    }

    primary_rows = details
    primary_metrics = {
        name: confusion_and_rates(primary_rows, decisions) for name, decisions in comparators.items()
    }

    success_vectors = {}
    for name, decisions in comparators.items():
        vec = np.array(
            [
                1.0
                if success_flag(row["label"] == "no_gold", decisions[str(row["sample_id"])], row["_hit20"])
                else 0.0
                for row in primary_rows
            ],
            dtype=np.float64,
        )
        success_vectors[name] = vec

    deltas = {
        "C3-C0": paired_bootstrap_delta(
            success_vectors["C3_SCORE_SHAPE_LOGISTIC"], success_vectors["C0_ALWAYS_RETRIEVE"]
        ),
        "C3-C1": paired_bootstrap_delta(
            success_vectors["C3_SCORE_SHAPE_LOGISTIC"],
            success_vectors["C1_OFFICIAL_TOP_SCORE_THRESHOLD"],
        ),
        "C3-C2": paired_bootstrap_delta(
            success_vectors["C3_SCORE_SHAPE_LOGISTIC"], success_vectors["C2_TOP1_LOGISTIC"]
        ),
    }

    strata_names = [
        "full_427",
        "natural_like_395",
        "counterfactual_32",
        "balanced_164",
        "positive_345",
        "no_gold_82",
    ]
    strata = {}
    for stratum in strata_names:
        subset = stratum_mask(details, stratum, balanced_ids)
        strata[stratum] = {
            "n": len(subset),
            "metrics": {
                name: confusion_and_rates(subset, decisions) for name, decisions in comparators.items()
            },
        }

    fold_ss = []
    for fold in range(5):
        subset = [row for row in details if outer_folds[str(row["repo"])] == fold]
        fold_ss.append(
            {
                "outer_fold": fold,
                "n": len(subset),
                "metrics": {
                    name: confusion_and_rates(subset, decisions)["selective_success@20"]
                    for name, decisions in comparators.items()
                },
            }
        )

    oof_export = []
    c2_map = {row["sample_id"]: row for row in oof_by_model["C2_TOP1_LOGISTIC"]}
    c3_map = {row["sample_id"]: row for row in oof_by_model["C3_SCORE_SHAPE_LOGISTIC"]}
    c3nc_map = {row["sample_id"]: row for row in oof_by_model["C3_NO_CONCENTRATION"]}
    for i, row in enumerate(details):
        sample_id = str(row["sample_id"])
        oof_export.append(
            {
                "sample_id": sample_id,
                "repo": row["repo"],
                "label": row["label"],
                "no_gold_reason": row.get("no_gold_reason"),
                "outer_fold": outer_folds[str(row["repo"])],
                "ranker": ranker,
                "hit20": bool(row["_hit20"]),
                "features": row["_features"],
                "feature_names": FEATURE_NAMES,
                "C0_abstain": False,
                "C1_abstain": bool(c1[sample_id]),
                "C2_abstain": bool(c2[sample_id]),
                "C2_p_abstain": c2_map[sample_id]["p_abstain"],
                "C2_threshold": c2_map[sample_id]["threshold"],
                "C3_abstain": bool(c3[sample_id]),
                "C3_p_abstain": c3_map[sample_id]["p_abstain"],
                "C3_threshold": c3_map[sample_id]["threshold"],
                "C3_NO_CONCENTRATION_abstain": bool(c3_nc[sample_id]),
                "C3_NO_CONCENTRATION_p_abstain": c3nc_map[sample_id]["p_abstain"],
                "C3_NO_CONCENTRATION_threshold": c3nc_map[sample_id]["threshold"],
                "C0_success": bool(success_vectors["C0_ALWAYS_RETRIEVE"][i]),
                "C1_success": bool(success_vectors["C1_OFFICIAL_TOP_SCORE_THRESHOLD"][i]),
                "C2_success": bool(success_vectors["C2_TOP1_LOGISTIC"][i]),
                "C3_success": bool(success_vectors["C3_SCORE_SHAPE_LOGISTIC"][i]),
                "C3_NO_CONCENTRATION_success": bool(success_vectors["C3_NO_CONCENTRATION"][i]),
            }
        )

    n = len(details)
    gate_overhead = {
        "feature_from_scores_s": feat_s,
        "feature_from_scores_per_sample_s": feat_s / n,
        "C3_train_s": model_times["C3_SCORE_SHAPE_LOGISTIC"]["train_s"],
        "C3_infer_s": model_times["C3_SCORE_SHAPE_LOGISTIC"]["infer_s"],
        "C3_infer_per_sample_s": model_times["C3_SCORE_SHAPE_LOGISTIC"]["infer_s"] / n,
        "gate_overhead_per_sample_s": (feat_s + model_times["C3_SCORE_SHAPE_LOGISTIC"]["infer_s"]) / n,
        "score_recovery_s": recover_s,
        "note": "Score recovery reconstructs missing E005 top-20 score vectors by re-running the official ranker. Live gate overhead assumes those scores already exist from retrieval. Evaluation still uses frozen top-20 files.",
    }
    return {
        "ranker": ranker,
        "primary_metrics": primary_metrics,
        "paired_deltas": deltas,
        "strata": strata,
        "fold_selective_success@20": fold_ss,
        "thresholds": threshold_records,
        "oof": oof_export,
        "timing": gate_overhead,
        "model_times": model_times,
        "n_recovered_score_vectors": len(recovered),
    }


def interpret_lexical(result: dict[str, Any]) -> dict[str, Any]:
    primary = result["primary_metrics"]
    c0 = primary["C0_ALWAYS_RETRIEVE"]["selective_success@20"]
    c1 = primary["C1_OFFICIAL_TOP_SCORE_THRESHOLD"]["selective_success@20"]
    c2 = primary["C2_TOP1_LOGISTIC"]["selective_success@20"]
    c3 = primary["C3_SCORE_SHAPE_LOGISTIC"]["selective_success@20"]
    d30 = result["paired_deltas"]["C3-C0"]
    d31 = result["paired_deltas"]["C3-C1"]
    d32 = result["paired_deltas"]["C3-C2"]
    nat = result["strata"]["natural_like_395"]["metrics"]
    nat_c0 = nat["C0_ALWAYS_RETRIEVE"]["selective_success@20"]
    nat_c3 = nat["C3_SCORE_SHAPE_LOGISTIC"]["selective_success@20"]
    cf = result["strata"]["counterfactual_32"]["metrics"]
    cf_c0 = cf["C0_ALWAYS_RETRIEVE"]["selective_success@20"]
    cf_c3 = cf["C3_SCORE_SHAPE_LOGISTIC"]["selective_success@20"]
    false_abs = primary["C3_SCORE_SHAPE_LOGISTIC"]["false_abstention_rate"]
    false_abs_c0 = primary["C0_ALWAYS_RETRIEVE"]["false_abstention_rate"]
    geometry_supported = not d32["ci_includes_zero"] and abs(d32["point"]) >= 0.005
    natural_improves = nat_c3 > nat_c0
    cf_only = (c3 > c0) and (not natural_improves) and (cf_c3 > cf_c0)
    pathological_false_abs = false_abs > false_abs_c0 + 0.15
    meaningful = (not d30["ci_includes_zero"]) and d30["point"] > 0.01
    beats_c1 = (not d31["ci_includes_zero"]) and d31["point"] > 0.0
    label = "NO SIGNAL"
    reason = []
    if d30["point"] <= 0:
        label = "NO SIGNAL"
        reason.append("C3 does not reliably improve over always-retrieve.")
    elif (not meaningful) or d30["ci_includes_zero"]:
        label = "WEAK SIGNAL"
        reason.append("C3 improves numerically but paired uncertainty includes zero or the effect is tiny.")
    elif pathological_false_abs:
        label = "WEAK SIGNAL"
        reason.append("C3 Selective Success@20 rose with a large false-abstention increase.")
    elif cf_only:
        label = "NO SIGNAL"
        reason.append("Improvement exists only on counterfactual_wrong_repo; evidence against generality.")
    elif not natural_improves:
        label = "WEAK SIGNAL"
        reason.append("Natural-like 395 shows no improvement over always-retrieve.")
    elif meaningful and beats_c1 and (not cf_only) and (not pathological_false_abs):
        label = "PROMISING EXPLORATORY SIGNAL"
        reason.append("C3 improves over C0 and C1 with a paired difference excluding zero; not solely the 32 counterfactuals.")
    else:
        label = "WEAK SIGNAL"
        reason.append("C3 does not jointly satisfy the promising-signal criteria.")
    if abs(c3 - c2) < 0.005 or (d32["ci_includes_zero"] and abs(d32["point"]) < 0.02):
        reason.append("C2 TOP1_LOGISTIC is approximately the same as C3; richer score geometry is not supported.")
        if label == "PROMISING EXPLORATORY SIGNAL":
            label = "WEAK SIGNAL"
    if not geometry_supported and label == "PROMISING EXPLORATORY SIGNAL":
        label = "WEAK SIGNAL"
        reason.append("C3 vs C2 does not support richer geometry.")
    decision_map = {
        "NO SIGNAL": "STOP — NO SCORE-SHAPE SIGNAL",
        "WEAK SIGNAL": "CONTINUE — WEAK SCORE-SHAPE SIGNAL",
        "PROMISING EXPLORATORY SIGNAL": "CONTINUE — PROMISING SCORE-SHAPE SIGNAL",
    }
    return {
        "signal_label": label,
        "decision": decision_map[label],
        "reasons": reason,
        "c2_approx_c3": abs(c3 - c2) < 0.005 or d32["ci_includes_zero"],
        "natural_like_395_improves": natural_improves,
        "counterfactual_only": cf_only,
        "primary": {"C0": c0, "C1": c1, "C2": c2, "C3": c3},
        "natural_like_395": {"C0": nat_c0, "C3": nat_c3},
        "counterfactual_32": {"C0": cf_c0, "C3": cf_c3},
        "false_abstention_C3": false_abs,
    }


def main() -> None:
    log_path = ROOT / "results/logs/E006_run.txt"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")

    class Tee:
        def write(self, data: str) -> int:
            sys.__stdout__.write(data)
            log_handle.write(data)
            log_handle.flush()
            return len(data)

        def flush(self) -> None:
            sys.__stdout__.flush()
            log_handle.flush()

    sys.stdout = Tee()  # type: ignore[assignment]
    wall0 = time.perf_counter()
    print("E006 SCORE-SHAPE EVIDENCE GATE")
    print("contract:", ROOT / "configs/E006_score_shape_gate.json")
    print("sklearn", __import__("sklearn").__version__)
    print("numpy", np.__version__)
    print("gpu_start", gpu_snapshot())
    print("rss_start_bytes", peak_rss_bytes())

    lexical_details = read_jsonl_path(ROOT / "results/raw/E005_natural_lexical_details.jsonl")
    bm25_details = read_jsonl_path(ROOT / "results/raw/E005_natural_bm25_details.jsonl")
    if len(lexical_details) != 427 or len(bm25_details) != 427:
        raise SystemExit("STOP E006: frozen natural details are not n=427")
    cv = json.loads((ROOT / "results/baselines/E005_natural_selective_cv.json").read_text(encoding="utf-8"))
    repo_folds = {str(k): int(v) for k, v in cv["repo_folds"].items()}
    fold_doc, inner_folds_by_outer = build_fold_assignments(lexical_details, repo_folds)
    write_json(ROOT / "results/raw/E006_fold_assignments.json", fold_doc)
    print("wrote fold assignments BEFORE fitting")
    print("nested_cv_valid", fold_doc["nested_cv_valid"])

    balanced_details = read_jsonl_path(ROOT / "results/raw/E005_balanced_lexical_details.jsonl")
    balanced_ids = {str(row["sample_id"]) for row in balanced_details}
    print("balanced_ids", len(balanced_ids), "overlap", sum(1 for row in lexical_details if str(row["sample_id"]) in balanced_ids))

    c1_lex = {str(row["sample_id"]): bool(row["abstained"]) for row in cv["methods"]["lexical"]["predictions"]}
    c1_bm25 = {str(row["sample_id"]): bool(row["abstained"]) for row in cv["methods"]["BM25"]["predictions"]}
    if len(c1_lex) != 427 or len(c1_bm25) != 427:
        raise SystemExit("STOP E006: official C1 predictions do not cover 427 samples")

    lex = run_backend(
        "lexical",
        lexical_details,
        c1_lex,
        repo_folds,
        inner_folds_by_outer,
        balanced_ids,
    )
    bm25 = run_backend(
        "bm25",
        bm25_details,
        c1_bm25,
        repo_folds,
        inner_folds_by_outer,
        balanced_ids,
    )

    write_jsonl(ROOT / "results/raw/E006_lexical_oof.jsonl", lex["oof"])
    write_jsonl(ROOT / "results/raw/E006_bm25_oof.jsonl", bm25["oof"])
    write_json(
        ROOT / "results/raw/E006_fold_thresholds.json",
        {
            "lexical": lex["thresholds"],
            "bm25": bm25["thresholds"],
            "selection_rule": "Maximize inner-validation Selective Success@20; ties: fewer false abstentions, then more retrieve decisions, then smaller threshold.",
        },
    )

    interpretation = interpret_lexical(lex)
    comparison = {
        "experiment_id": "E006",
        "status": "EXPLORATORY",
        "primary_dataset": "official v2_selective_retrieval_natural",
        "n": 427,
        "primary_metric": "selective_success@20",
        "primary_backend": "lexical",
        "secondary_backend": "bm25",
        "lexical": {
            "primary_metrics": lex["primary_metrics"],
            "paired_deltas": lex["paired_deltas"],
            "strata": lex["strata"],
            "fold_selective_success@20": lex["fold_selective_success@20"],
            "timing": lex["timing"],
        },
        "bm25": {
            "primary_metrics": bm25["primary_metrics"],
            "paired_deltas": bm25["paired_deltas"],
            "strata": bm25["strata"],
            "fold_selective_success@20": bm25["fold_selective_success@20"],
            "timing": bm25["timing"],
        },
        "interpretation_primary_lexical": interpretation,
        "compute": {
            "wall_s": time.perf_counter() - wall0,
            "cpu": cpu_times(),
            "peak_rss_bytes": peak_rss_bytes(),
            "gpu_end": gpu_snapshot(),
            "gpu_expected": "zero dedicated E006 usage; no LLM",
            "e005_retrieval_reference": {
                "natural_lexical_s": 471.46,
                "natural_bm25_s": 503.08,
            },
        },
        "sklearn_version": __import__("sklearn").__version__,
        "numpy_version": np.__version__,
    }
    write_json(ROOT / "results/baselines/E006_comparison.json", comparison)

    print("=== PRIMARY lexical Selective Success@20 ===")
    for key in (
        "C0_ALWAYS_RETRIEVE",
        "C1_OFFICIAL_TOP_SCORE_THRESHOLD",
        "C2_TOP1_LOGISTIC",
        "C3_SCORE_SHAPE_LOGISTIC",
    ):
        print(key, lex["primary_metrics"][key]["selective_success@20"])
    print("paired", json.dumps(lex["paired_deltas"], sort_keys=True))
    print("interpretation", json.dumps(interpretation, sort_keys=True))
    print("peak_rss_bytes", peak_rss_bytes())
    print("wall_s", time.perf_counter() - wall0)
    sys.stdout.flush()
    log_handle.flush()

    frozen_dir = ROOT / "results/frozen/E006_score_shape_gate"
    if frozen_dir.exists():
        shutil.rmtree(frozen_dir)
    frozen_dir.mkdir(parents=True)
    artifacts = [
        ROOT / "configs/E006_score_shape_gate.json",
        ROOT / "results/raw/E006_fold_assignments.json",
        ROOT / "results/raw/E006_lexical_oof.jsonl",
        ROOT / "results/raw/E006_bm25_oof.jsonl",
        ROOT / "results/raw/E006_fold_thresholds.json",
        ROOT / "results/baselines/E006_comparison.json",
        ROOT / "results/logs/E006_run.txt",
        ROOT / "scripts/e006_score_shape_gate.py",
    ]
    hashes = {}
    for path in artifacts:
        dest = frozen_dir / path.name
        shutil.copy2(path, dest)
        hashes[path.name] = sha256_file(dest)
    write_json(frozen_dir / "SHA256.json", hashes)
    print("froze", frozen_dir)
    print("sha256", json.dumps(hashes, indent=2, sort_keys=True))
    log_handle.close()


if __name__ == "__main__":
    main()
