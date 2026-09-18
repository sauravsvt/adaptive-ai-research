#!/usr/bin/env python3
"""E007 cross-retriever generalization.

Contract: configs/E007_cross_retriever_generalization.json
Protocol commit preceded this implementation.

Reuses E006 outer folds and the frozen 12-feature family. Does not modify
E000-E006 artifacts. Does not change official retrieval backends.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import resource
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path("/home/sauravsvt/Desktop/Research/R1")
ARB = ROOT / "agent-retrieval-bench"
SRC = ARB / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_retrieval_bench.baseline import (  # noqa: E402
    filter_candidate_chunks,
    gold_file_ranks,
    hard_negative_files,
    load_corpus_manifest,
    query_has_leakage,
    query_text_for_eval,
    sample_metrics,
    summarize_details,
    target_gold_files,
)
from agent_retrieval_bench.bcy_curve import (  # noqa: E402
    DEFAULT_BUDGETS,
    DEFAULT_COVERAGE_THRESHOLDS,
    CorpusFileCache,
    evaluate_run,
    load_corpus_manifest as load_bcy_manifest,
)
from agent_retrieval_bench.io import read_jsonl  # noqa: E402
from agent_retrieval_bench.repomap_eval import (  # noqa: E402
    build_repomap_index,
    candidate_paths_for_filter,
    format_file_score,
    rank_files_for_sample,
    ranked_file_chunks,
)
from agent_retrieval_bench.selective_cv import evaluate_group_cv  # noqa: E402
from agent_retrieval_bench.selective_embedding_eval import rank_chunks_by_vector_scores  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "e006_score_shape_gate",
    ROOT / "scripts/e006_score_shape_gate.py",
)
assert spec and spec.loader
e006 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(e006)

SUBSETS = ("v2_code2test", "v2_comment2context", "v2_trace2code", "v2_edit2ripple")
PUBLISHED_REPOMAP = {"Recall@20": 0.6333, "MRR": 0.2158, "BCY@8k": 0.3788}
PUBLISHED_QWEN = {"Recall@20": 0.6306, "MRR": 0.2379, "BCY@8k": 0.3409}
FROZEN_LEXICAL = {"C0": 0.4613583138173302, "C3": 0.5737704918032787}
FROZEN_BM25 = {"C0": 0.42857142857142855, "C3": 0.45433255269320844}
QUERY_W, PR_W, AFF_W = 0.65, 0.25, 0.10
QWEN_MODEL = "Qwen/Qwen3-Embedding-4B"


def cpu_times() -> dict[str, float]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {"user_s": float(usage.ru_utime), "sys_s": float(usage.ru_stime)}


def write_fold_assignments() -> dict[str, Any]:
    src = json.loads((ROOT / "results/raw/E006_fold_assignments.json").read_text(encoding="utf-8"))
    doc = dict(src)
    doc["e007_note"] = (
        "E007 reuses the E006 outer repository-grouped 5-fold assignment unchanged. "
        "Inner maps are the same official assign_repo_folds(5) maps frozen in E006."
    )
    doc["source"] = "results/raw/E006_fold_assignments.json"
    doc["written_before_e007_model_fitting"] = True
    e006.write_json(ROOT / "results/raw/E007_fold_assignments.json", doc)
    return doc


def load_folds(doc: dict[str, Any]) -> tuple[dict[str, int], dict[int, dict[str, int]]]:
    outer = {str(k): int(v) for k, v in doc["outer_repo_folds"].items()}
    inner = {
        int(outer_k): {str(repo): int(fold) for repo, fold in mapping.items()}
        for outer_k, mapping in doc["inner_repo_folds_by_outer"].items()
    }
    return outer, inner


def aggregate_positive(ranker_tag: str, published: dict[str, float]) -> dict[str, Any]:
    os.chdir(ARB)
    rows: list[dict[str, Any]] = []
    subset_metrics = {}
    for subset in SUBSETS:
        path = ROOT / "results/raw" / f"E007_{subset}_{ranker_tag}_details.jsonl"
        part = list(read_jsonl(path))
        if not part:
            raise SystemExit(f"STOP E007: missing positive details {path}")
        rows.extend(part)
        subset_metrics[subset] = {
            "n": len(part),
            "Recall@20": summarize_details(part)["overall"]["Recall@20"],
            "MRR": summarize_details(part)["overall"]["MRR"],
        }
    if len(rows) != 345:
        raise SystemExit(f"STOP E007: expected 345 positive rows, got {len(rows)} for {ranker_tag}")
    combined_path = ROOT / "results/raw" / f"E007_positive345_{ranker_tag}_details.jsonl"
    e006.write_jsonl(combined_path, rows)
    summary = summarize_details(rows)
    cache = CorpusFileCache(
        {k: v for subset in SUBSETS for k, v in load_bcy_manifest(ARB / "data/corpus" / subset / "corpus_manifest.jsonl").items()}
    )
    bcy = evaluate_run(
        ranker_tag,
        "lexical",
        combined_path,
        rows,
        cache,
        DEFAULT_BUDGETS,
        DEFAULT_COVERAGE_THRESHOLDS,
    )
    reproduced = {
        "Recall@20": float(summary["overall"]["Recall@20"]),
        "MRR": float(summary["overall"]["MRR"]),
        "BCY@8k": float(bcy["overall"]["BCY@8000"]),
        "n": int(summary["overall"]["samples"]),
    }
    return {
        "ranker": ranker_tag,
        "published": published,
        "reproduced": reproduced,
        "abs_diff": {k: abs(reproduced[k] - published[k]) for k in published},
        "subset_metrics": subset_metrics,
    }


def evaluate_selective_repomap() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    cwd = os.getcwd()
    os.chdir(ARB)
    try:
        samples = list(read_jsonl(ARB / "data/benchmark/v2_selective_retrieval_natural/samples.jsonl"))
        manifest = load_corpus_manifest(ARB / "data/corpus/v2_selective_mixed")
        pending: dict[Path, list[tuple[int, dict[str, Any], list[str], str, bool]]] = defaultdict(list)
        skipped = {"no_gold_unlabeled": 0, "query_leakage": 0, "missing_corpus": 0, "empty_corpus": 0}
        for sample_index, sample in enumerate(samples):
            gold_files = target_gold_files(sample)
            is_no_gold = bool((sample.get("gold") or {}).get("no_gold") is True)
            if not gold_files and not is_no_gold:
                skipped["no_gold_unlabeled"] += 1
                continue
            query_text = query_text_for_eval(sample)
            if query_has_leakage(sample, query_text):
                skipped["query_leakage"] += 1
                continue
            chunks_path = manifest.get((sample.get("repo"), sample.get("base_commit")))
            if not chunks_path:
                skipped["missing_corpus"] += 1
                continue
            pending[chunks_path].append((sample_index, sample, gold_files, query_text, is_no_gold))
        details: list[dict[str, Any]] = []
        index_cache: dict[Path, Any] = {}
        for corpus_index, (chunks_path, group) in enumerate(pending.items(), start=1):
            print(f"[repomap-selective] corpus {corpus_index}/{len(pending)} n={len(group)} {chunks_path}", flush=True)
            index = index_cache.get(chunks_path)
            if index is None:
                chunks = list(read_jsonl(chunks_path))
                if not chunks:
                    skipped["empty_corpus"] += len(group)
                    continue
                index = build_repomap_index(chunks, max_symbol_refs_per_file=80)
                index_cache[chunks_path] = index
            candidate_paths = candidate_paths_for_filter(index.nodes, "all_files")
            if not candidate_paths:
                skipped["empty_corpus"] += len(group)
                continue
            for sample_index, sample, gold_files, query_text, is_no_gold in group:
                ranked = rank_files_for_sample(
                    sample=sample,
                    query_text=query_text,
                    index=index,
                    candidate_paths=candidate_paths,
                    query_weight=QUERY_W,
                    pagerank_weight=PR_W,
                    affinity_weight=AFF_W,
                )
                if not ranked:
                    skipped["empty_corpus"] += 1
                    continue
                ranked_chunks = ranked_file_chunks(ranked, index.nodes)
                top20 = ranked[:20]
                file_scores = [float(item[1]) for item in top20]
                top_score = float(top20[0][1])
                second_score = float(top20[1][1]) if len(top20) > 1 else 0.0
                detail: dict[str, Any] = {
                    "sample_id": sample.get("id"),
                    "task_type": sample.get("task_type"),
                    "repo": sample.get("repo"),
                    "base_commit": sample.get("base_commit"),
                    "candidate_filter": "all_files",
                    "ranker": "aider-style-repomap",
                    "label": "no_gold" if is_no_gold else "positive",
                    "no_gold_reason": (sample.get("gold") or {}).get("reason") if is_no_gold else None,
                    "gold_files": gold_files,
                    "confidence": top_score,
                    "top_score": top_score,
                    "second_score": second_score,
                    "score_margin": top_score - second_score,
                    "top_files": [item[0] for item in top20],
                    "top_file_scores": [format_file_score(item) for item in top20],
                    "file_scores": file_scores,
                    "score_semantics": "official RepoMap final_score = 0.65*query + 0.25*pagerank + 0.10*affinity (per-sample min-max components)",
                }
                if gold_files:
                    hard_negatives = hard_negative_files(sample)
                    metrics = sample_metrics(gold_files, ranked_chunks, hard_negative_files=hard_negatives)
                    detail.update(
                        {
                            "metrics": metrics,
                            "gold_ranks": gold_file_ranks(gold_files, ranked_chunks),
                            "hard_negative_files": hard_negatives,
                        }
                    )
                details.append(detail)
        details.sort(key=lambda row: str(row["sample_id"]))
        if len(details) != 427:
            raise SystemExit(f"STOP E007: selective RepoMap evaluated {len(details)} != 427 skipped={skipped}")
        runtime = {
            "wall_s": time.perf_counter() - started,
            "cpu": cpu_times(),
            "peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024,
            "skipped": skipped,
            "gpu": "unused",
        }
        return details, runtime
    finally:
        os.chdir(cwd)


def score_vector_audit(details: list[dict[str, Any]]) -> dict[str, Any]:
    scores = [float(s) for row in details for s in (row.get("file_scores") or [])]
    unique = sorted(set(round(s, 12) for s in scores))
    # rank-position fake scores would be 20,19,...,1 or 1/rank
    looks_like_ranks = unique == list(range(1, 21)) or unique == [round(1.0 / k, 12) for k in range(1, 21)]
    return {
        "n_score_values": len(scores),
        "n_unique_rounded": len(unique),
        "min": min(scores) if scores else None,
        "max": max(scores) if scores else None,
        "mean": float(np.mean(scores)) if scores else None,
        "std": float(np.std(scores)) if scores else None,
        "looks_like_rank_position_scores": looks_like_ranks,
        "legitimate_numeric_geometry": bool(scores) and len(unique) > 25 and not looks_like_ranks,
    }


def gate_from_file_scores(
    ranker: str,
    details: list[dict[str, Any]],
    outer_folds: dict[str, int],
    inner_folds_by_outer: dict[int, dict[str, int]],
    balanced_ids: set[str],
    c1_label: str,
) -> dict[str, Any]:
    missing = [row["sample_id"] for row in details if row["repo"] not in outer_folds]
    if missing:
        raise SystemExit(f"STOP E007: sample repos missing from E006 folds: {missing[:5]}")
    for row in details:
        row["_hit20"] = e006.hit_at_20(row)
        row["_features"] = e006.score_shape_features(list(row["file_scores"]))
    x = np.asarray([row["_features"] for row in details], dtype=np.float64)
    y = np.asarray([1 if row["label"] == "no_gold" else 0 for row in details], dtype=np.int32)
    # C1 official balanced-accuracy OOF on frozen E006 folds
    c1_cv = evaluate_group_cv(details, outer_folds, 5)
    c1 = {str(row["sample_id"]): bool(row["abstained"]) for row in c1_cv["predictions"]}
    models = {
        "C2_TOP1_LOGISTIC": (0,),
        "C3_SCORE_SHAPE_LOGISTIC": tuple(range(e006.N_FEATURES)),
        "C3_NO_CONCENTRATION": e006.NO_CONCENTRATION_IDX,
    }
    oof_by_model: dict[str, list[dict[str, Any]]] = {}
    threshold_records: list[dict[str, Any]] = []
    model_times: dict[str, dict[str, float]] = {}
    feat_t0 = time.perf_counter()
    # features already computed above; time only the sklearn nested CV
    feat_s = time.perf_counter() - feat_t0
    for model_name, idx in models.items():
        print(f"=== fitting {ranker} {model_name} ===", flush=True)
        oof_rows, thresh, times, _ = e006.nested_oof(
            details, x, y, idx, outer_folds, inner_folds_by_outer, model_name
        )
        oof_by_model[model_name] = oof_rows
        threshold_records.extend(thresh)
        model_times[model_name] = times
    c0 = e006.always_retrieve_decisions(details)
    c2 = e006.decisions_from_oof(oof_by_model["C2_TOP1_LOGISTIC"])
    c3 = e006.decisions_from_oof(oof_by_model["C3_SCORE_SHAPE_LOGISTIC"])
    c3_nc = e006.decisions_from_oof(oof_by_model["C3_NO_CONCENTRATION"])
    comparators = {
        "C0_ALWAYS_RETRIEVE": c0,
        c1_label: c1,
        "C2_TOP1_LOGISTIC": c2,
        "C3_SCORE_SHAPE_LOGISTIC": c3,
        "C3_NO_CONCENTRATION": c3_nc,
    }
    primary_metrics = {name: e006.confusion_and_rates(details, dec) for name, dec in comparators.items()}
    success_vectors = {}
    for name, decisions in comparators.items():
        success_vectors[name] = np.array(
            [
                1.0
                if e006.success_flag(row["label"] == "no_gold", decisions[str(row["sample_id"])], row["_hit20"])
                else 0.0
                for row in details
            ],
            dtype=np.float64,
        )
    deltas = {
        "C3-C0": e006.paired_bootstrap_delta(
            success_vectors["C3_SCORE_SHAPE_LOGISTIC"], success_vectors["C0_ALWAYS_RETRIEVE"]
        ),
        "C3-C1": e006.paired_bootstrap_delta(success_vectors["C3_SCORE_SHAPE_LOGISTIC"], success_vectors[c1_label]),
        "C3-C2": e006.paired_bootstrap_delta(
            success_vectors["C3_SCORE_SHAPE_LOGISTIC"], success_vectors["C2_TOP1_LOGISTIC"]
        ),
    }
    strata = {}
    for stratum in (
        "full_427",
        "natural_like_395",
        "counterfactual_32",
        "balanced_164",
        "positive_345",
        "no_gold_82",
    ):
        subset = e006.stratum_mask(details, stratum, balanced_ids)
        strata[stratum] = {
            "n": len(subset),
            "metrics": {name: e006.confusion_and_rates(subset, dec) for name, dec in comparators.items()},
        }
    n = len(details)
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
                "feature_names": e006.FEATURE_NAMES,
                "file_scores": row["file_scores"],
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
                "C1_success": bool(success_vectors[c1_label][i]),
                "C2_success": bool(success_vectors["C2_TOP1_LOGISTIC"][i]),
                "C3_success": bool(success_vectors["C3_SCORE_SHAPE_LOGISTIC"][i]),
                "C3_NO_CONCENTRATION_success": bool(success_vectors["C3_NO_CONCENTRATION"][i]),
            }
        )
    return {
        "ranker": ranker,
        "c1_label": c1_label,
        "c1_official_cv": {
            "out_of_fold": c1_cv["out_of_fold"],
            "no_abstain": c1_cv["no_abstain"],
            "threshold_summary": c1_cv["threshold_summary"],
        },
        "primary_metrics": primary_metrics,
        "paired_deltas": deltas,
        "strata": strata,
        "thresholds": threshold_records,
        "oof": oof_export,
        "timing": {
            "feature_from_scores_s": feat_s,
            "C3_train_s": model_times["C3_SCORE_SHAPE_LOGISTIC"]["train_s"],
            "C3_infer_s": model_times["C3_SCORE_SHAPE_LOGISTIC"]["infer_s"],
            "gate_overhead_per_sample_s": (feat_s + model_times["C3_SCORE_SHAPE_LOGISTIC"]["infer_s"]) / n,
        },
        "score_audit": score_vector_audit(details),
    }


def backend_verdict(result: dict[str, Any]) -> dict[str, Any]:
    pm = result["primary_metrics"]
    c0 = pm["C0_ALWAYS_RETRIEVE"]["selective_success@20"]
    c1_key = result["c1_label"]
    c1 = pm[c1_key]["selective_success@20"]
    c2 = pm["C2_TOP1_LOGISTIC"]["selective_success@20"]
    c3 = pm["C3_SCORE_SHAPE_LOGISTIC"]["selective_success@20"]
    d30 = result["paired_deltas"]["C3-C0"]
    d32 = result["paired_deltas"]["C3-C2"]
    nat = result["strata"]["natural_like_395"]["metrics"]
    nat_c0 = nat["C0_ALWAYS_RETRIEVE"]["selective_success@20"]
    nat_c3 = nat["C3_SCORE_SHAPE_LOGISTIC"]["selective_success@20"]
    cf = result["strata"]["counterfactual_32"]["metrics"]
    reliable = (
        d30["point"] > 0
        and not d30["ci_includes_zero"]
        and (c3 - c2) >= 0.005
        and not d32["ci_includes_zero"]
        and nat_c3 >= nat_c0
        and not ((c3 > c0) and (nat_c3 <= nat_c0) and (cf["C3_SCORE_SHAPE_LOGISTIC"]["selective_success@20"] > cf["C0_ALWAYS_RETRIEVE"]["selective_success@20"]))
    )
    return {
        "C0": c0,
        "C1": c1,
        "C2": c2,
        "C3": c3,
        "C3-C0": d30,
        "C3-C1": result["paired_deltas"]["C3-C1"],
        "C3-C2": d32,
        "natural_like_delta": nat_c3 - nat_c0,
        "natural_like_C0": nat_c0,
        "natural_like_C3": nat_c3,
        "counterfactual_C0": cf["C0_ALWAYS_RETRIEVE"]["selective_success@20"],
        "counterfactual_C3": cf["C3_SCORE_SHAPE_LOGISTIC"]["selective_success@20"],
        "false_abstention_C3": pm["C3_SCORE_SHAPE_LOGISTIC"]["false_abstention_rate"],
        "reliable_positive_C3_minus_C0": reliable,
    }


def recover_embedding_file_scores(details: list[dict[str, Any]], cache_dir: Path, shared_text_cache: Path) -> tuple[list[dict[str, Any]], float]:
    from agent_retrieval_bench.embedding_eval import (
        SentenceTransformerEmbedder,
        TextEmbeddingCache,
        embedding_cache_metadata,
        encode_query_texts_resilient,
        load_or_encode_chunk_vectors,
    )

    started = time.perf_counter()
    cwd = os.getcwd()
    os.chdir(ARB)
    try:
        samples = {str(row["id"]): row for row in read_jsonl(ARB / "data/benchmark/v2_selective_retrieval_natural/samples.jsonl")}
        manifest = load_corpus_manifest(ARB / "data/corpus/v2_selective_mixed")
        embedder = SentenceTransformerEmbedder(
            QWEN_MODEL,
            device="cuda",
            normalize_embeddings=True,
            trust_remote_code=True,
        )
        passage_opts = embedding_cache_metadata(embedder, input_type=None)
        shared = TextEmbeddingCache(
            shared_text_cache,
            {
                "model": QWEN_MODEL,
                "normalize_embeddings": True,
                "passage_prefix": "",
                "embedding_options": passage_opts,
            },
        )
        pending: dict[Path, list[dict[str, Any]]] = defaultdict(list)
        for detail in details:
            sample = samples[str(detail["sample_id"])]
            chunks_path = manifest.get((sample.get("repo"), sample.get("base_commit")))
            if chunks_path is None:
                raise SystemExit(f"STOP E007: missing corpus for {detail['sample_id']}")
            pending[chunks_path].append(detail)
        mismatches = []
        try:
            import gc

            for corpus_index, (chunks_path, group) in enumerate(pending.items(), start=1):
                print(f"[qwen-scores] corpus {corpus_index}/{len(pending)} n={len(group)}", flush=True)
                chunks = filter_candidate_chunks(read_jsonl(chunks_path), "all_files")
                vectors = load_or_encode_chunk_vectors(
                    chunks=chunks,
                    chunks_path=chunks_path,
                    embedder=embedder,
                    model_name=QWEN_MODEL,
                    cache_dir=cache_dir,
                    shared_text_cache=shared,
                    batch_size=1,
                    passage_prefix="",
                    input_type=None,
                    normalize_embeddings=True,
                    embedding_options=passage_opts,
                    candidate_filter="all_files",
                )
                queries = [query_text_for_eval(samples[str(d["sample_id"])]) for d in group]
                qvecs = encode_query_texts_resilient(embedder, queries, batch_size=1, show_progress_bar=False, input_type=None)
                for detail, qvec in zip(group, qvecs):
                    scored = rank_chunks_by_vector_scores(qvec, vectors, chunks)
                    paths, scores = e006.unique_file_scores(scored)
                    frozen_top = list(detail.get("top_files") or [])
                    if paths != frozen_top:
                        mismatches.append({"sample_id": detail["sample_id"], "frozen": frozen_top[:3], "recovered": paths[:3]})
                    detail["file_scores"] = scores
                    detail["score_semantics"] = "dot product of L2-normalized Qwen3-Embedding-4B vectors (cosine)"
                del chunks, vectors, queries, qvecs
                gc.collect()
        finally:
            shared.close()
        if mismatches:
            raise SystemExit(f"STOP E007: Qwen recovered ranking != official top_files n={len(mismatches)} preview={mismatches[:3]}")
        return details, time.perf_counter() - started
    finally:
        os.chdir(cwd)


def interpret(repomap: dict[str, Any] | None, qwen: dict[str, Any] | None) -> dict[str, Any]:
    n_new_reliable = 0
    reasons = []
    if repomap is None:
        reasons.append("RepoMap score-shape gating not applicable or not evaluated.")
    elif repomap["reliable_positive_C3_minus_C0"]:
        n_new_reliable += 1
        reasons.append("RepoMap shows a reliable C3>C0 paired gain not only from counterfactuals.")
    else:
        reasons.append("RepoMap does not show a reliable C3-C0 gain under the frozen protocol.")
    if qwen is None:
        reasons.append("Qwen embedding was not successfully evaluated.")
    elif qwen["reliable_positive_C3_minus_C0"]:
        n_new_reliable += 1
        reasons.append("Qwen embedding shows a reliable C3>C0 paired gain not only from counterfactuals.")
    else:
        reasons.append("Qwen embedding does not show a reliable C3-C0 gain under the frozen protocol.")
    if n_new_reliable >= 1 and (repomap is None or qwen is None or (repomap["reliable_positive_C3_minus_C0"] and qwen["reliable_positive_C3_minus_C0"])):
        # stronger if at least one new family works; mixed if the two new backends disagree
        if repomap is not None and qwen is not None and (repomap["reliable_positive_C3_minus_C0"] != qwen["reliable_positive_C3_minus_C0"]):
            label = "CONTINUE — MIXED RANKER-SENSITIVE SIGNAL"
        elif n_new_reliable >= 1:
            label = "CONTINUE — STRONGER CROSS-RETRIEVER SIGNAL"
        else:
            label = "CONTINUE — LEXICAL-SPECIFIC SIGNAL"
    elif n_new_reliable == 1:
        label = "CONTINUE — MIXED RANKER-SENSITIVE SIGNAL"
    elif n_new_reliable == 0:
        label = "CONTINUE — LEXICAL-SPECIFIC SIGNAL"
    else:
        label = "STOP — NO GENERALIZATION SIGNAL"
    if n_new_reliable >= 2:
        label = "CONTINUE — STRONGER CROSS-RETRIEVER SIGNAL"
    return {"decision": label, "n_non_lexical_reliable": n_new_reliable, "reasons": reasons}


def compact_verdict(ranker: str, result: dict[str, Any] | None, status: str) -> dict[str, Any]:
    if result is None:
        return {"ranker": ranker, "status": status}
    v = result["verdict"]
    pm = result["primary_metrics"]
    return {
        "ranker": ranker,
        "status": status,
        "C0": v["C0"],
        "C1": v["C1"],
        "C2": v["C2"],
        "C3": v["C3"],
        "C3-C0": v["C3-C0"],
        "C3-C1": v["C3-C1"],
        "C3-C2": v["C3-C2"],
        "natural_like_delta": v["natural_like_delta"],
        "natural_like_C0": v["natural_like_C0"],
        "natural_like_C3": v["natural_like_C3"],
        "counterfactual_C0": v["counterfactual_C0"],
        "counterfactual_C3": v["counterfactual_C3"],
        "false_abstention_C3": v["false_abstention_C3"],
        "reliable_positive_C3_minus_C0": v["reliable_positive_C3_minus_C0"],
        "c1_label": result["c1_label"],
        "score_audit": result.get("score_audit"),
        "timing": result.get("timing"),
        "C3_NO_CONCENTRATION": pm["C3_NO_CONCENTRATION"]["selective_success@20"],
    }


def write_thresholds(repomap: dict[str, Any] | None, qwen: dict[str, Any] | None) -> None:
    doc = {
        "source_folds": "results/raw/E007_fold_assignments.json (copy of E006 outer_repo_folds)",
        "repomap": None if repomap is None else repomap.get("thresholds"),
        "qwen_embedding": None if qwen is None else qwen.get("thresholds"),
        "c1_repomap": None if repomap is None else repomap.get("c1_official_cv", {}).get("threshold_summary"),
        "c1_qwen_embedding": None if qwen is None else qwen.get("c1_official_cv", {}).get("threshold_summary"),
    }
    e006.write_json(ROOT / "results/raw/E007_thresholds.json", doc)


def freeze_e007() -> dict[str, str]:
    frozen_dir = ROOT / "results/frozen/E007_cross_retriever_generalization"
    if frozen_dir.exists():
        shutil.rmtree(frozen_dir)
    frozen_dir.mkdir(parents=True)
    artifacts = [
        ROOT / "configs/E007_cross_retriever_generalization.json",
        ROOT / "scripts/e007_cross_retriever.py",
        ROOT / "scripts/run_e007_qwen.sh",
        ROOT / "scripts/e007_qwen_shards.py",
        ROOT / "scripts/run_e007_qwen_shard_queue.sh",
        ROOT / "results/raw/E007_fold_assignments.json",
        ROOT / "results/raw/E007_thresholds.json",
        ROOT / "results/raw/E007_qwen_shard_validation.json",
        ROOT / "results/raw/E007_qwen_equivalence_smoke.json",
        ROOT / "results/raw/E007_natural_qwen_merge_report.json",
        ROOT / "results/raw/E007_natural_qwen_details.jsonl",
        ROOT / "results/raw/E007_qwen_shards/manifest.json",
        ROOT / "results/baselines/E007_official_backend_reproduction.json",
        ROOT / "results/baselines/E007_cross_retriever_comparison.json",
        ROOT / "results/logs/E007_run.txt",
        ROOT / "results/baselines/E007_repomap_positive345.json",
        ROOT / "results/baselines/E007_repomap_gate.json",
        ROOT / "results/raw/E007_repomap_oof.jsonl",
    ]
    optional = [
        ROOT / "results/baselines/E007_qwen_positive345.json",
        ROOT / "results/baselines/E007_qwen_gate.json",
        ROOT / "results/raw/E007_qwen_embedding_oof.jsonl",
    ]
    hashes: dict[str, str] = {}
    for path in artifacts + optional:
        if not path.exists():
            if path in optional:
                continue
            raise SystemExit(f"STOP E007 freeze: missing {path}")
        dest = frozen_dir / path.name
        shutil.copy2(path, dest)
        hashes[path.name] = sha256_file(dest)
    e006.write_json(frozen_dir / "SHA256.json", hashes)
    return hashes


def summarize_e007() -> dict[str, Any]:
    repomap_pos_path = ROOT / "results/baselines/E007_repomap_positive345.json"
    qwen_pos_path = ROOT / "results/baselines/E007_qwen_positive345.json"
    repomap_gate_path = ROOT / "results/baselines/E007_repomap_gate.json"
    qwen_gate_path = ROOT / "results/baselines/E007_qwen_gate.json"
    if not repomap_pos_path.exists() or not repomap_gate_path.exists():
        raise SystemExit("STOP E007 summarize: RepoMap positive/gate artifacts missing")
    repomap_pos = json.loads(repomap_pos_path.read_text(encoding="utf-8"))
    repomap_gate = json.loads(repomap_gate_path.read_text(encoding="utf-8"))
    qwen_pos = json.loads(qwen_pos_path.read_text(encoding="utf-8")) if qwen_pos_path.exists() else None
    qwen_gate = json.loads(qwen_gate_path.read_text(encoding="utf-8")) if qwen_gate_path.exists() else None
    qwen_status = "evaluated" if qwen_gate is not None else "not_evaluated"
    if qwen_status == "not_evaluated":
        qwen_note = (
            "Official Qwen/Qwen3-Embedding-4B was not completed at summarize time. "
            "Do not substitute an unofficial embedder."
        )
    else:
        qwen_note = "Official Qwen/Qwen3-Embedding-4B evaluated with frozen score-shape family."
    write_thresholds(repomap_gate, qwen_gate)
    reproduction = {
        "repomap": {
            "score_shape_applicable": True,
            "score_semantics": "official final_score = 0.65*query + 0.25*pagerank + 0.10*affinity",
            "positive_345": repomap_pos,
            "discrepancy_note": (
                "Bundled data/eval/v2_edit2ripple/repomap_* does not match this machine's official "
                "CLI on the frozen ARB commit. E007 used unmodified official rank_files_for_sample."
            ),
        },
        "qwen_embedding": {
            "model": QWEN_MODEL,
            "status": qwen_status,
            "note": qwen_note,
            "positive_345": qwen_pos,
            "hardware_deviation": (
                "Official documented job uses --batch-size 8. That OOMed on this 20GB/70W GPU. "
                "Retry used --batch-size 1 and PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True. "
                "Model, normalize=True, empty prefixes, device=cuda, trust_remote_code, and all_files were unchanged."
            ),
        },
    }
    e006.write_json(ROOT / "results/baselines/E007_official_backend_reproduction.json", reproduction)
    repomap_v = backend_verdict(repomap_gate) if "verdict" not in repomap_gate else repomap_gate["verdict"]
    # backend_verdict expects full gate dict with primary_metrics; stored file already has verdict
    qwen_v = None if qwen_gate is None else qwen_gate.get("verdict")
    interpretation = interpret(repomap_v, qwen_v)
    comparison = {
        "experiment_id": "E007",
        "primary_dataset": "official v2_selective_retrieval_natural n=427",
        "primary_metric": "Selective Success@20",
        "frozen_feature_family": "E006 12 score-shape features; per-backend nested CV; lexical coefficients not reused",
        "lexical_frozen_reference": FROZEN_LEXICAL,
        "bm25_frozen_reference": FROZEN_BM25,
        "repomap": compact_verdict("repomap", repomap_gate, "score_shape_applicable"),
        "qwen_embedding": compact_verdict("qwen_embedding", qwen_gate, qwen_status),
        "interpretation": interpretation,
        "sklearn_version": __import__("sklearn").__version__,
        "numpy_version": np.__version__,
    }
    e006.write_json(ROOT / "results/baselines/E007_cross_retriever_comparison.json", comparison)
    return comparison


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    fold_doc = write_fold_assignments()
    print("wrote E007_fold_assignments.json from frozen E006 folds", flush=True)
    outer, inner = load_folds(fold_doc)
    balanced_ids = {
        str(row["sample_id"])
        for row in e006.read_jsonl_path(ROOT / "results/raw/E005_balanced_lexical_details.jsonl")
    }

    if stage in ("all", "repomap-selective", "repomap-gate", "summarize"):
        sel_path = ROOT / "results/raw/E007_natural_repomap_details.jsonl"
        if not sel_path.exists() or stage in ("all", "repomap-selective"):
            print("=== selective RepoMap on official 427 ===", flush=True)
            details, runtime = evaluate_selective_repomap()
            e006.write_jsonl(sel_path, details)
            e006.write_json(ROOT / "results/logs/E007_repomap_selective_runtime.json", runtime)
        details = e006.read_jsonl_path(sel_path)
        audit = score_vector_audit(details)
        print("RepoMap score audit", json.dumps(audit, sort_keys=True), flush=True)
        if not audit["legitimate_numeric_geometry"]:
            print("STOP: RepoMap scores not usable for frozen geometry", flush=True)
            e006.write_json(
                ROOT / "results/baselines/E007_repomap_score_status.json",
                {"applicable": False, "reason": "scores failed legitimacy audit", "audit": audit},
            )
        else:
            print("=== gating RepoMap ===", flush=True)
            gated = gate_from_file_scores(
                "repomap",
                details,
                outer,
                inner,
                balanced_ids,
                "C1_OFFICIAL_TOP_SCORE_THRESHOLD",
            )
            e006.write_jsonl(ROOT / "results/raw/E007_repomap_oof.jsonl", gated["oof"])
            gated_save = {k: v for k, v in gated.items() if k != "oof"}
            gated_save["verdict"] = backend_verdict(gated)
            e006.write_json(ROOT / "results/baselines/E007_repomap_gate.json", gated_save)

    if stage in ("all", "repomap-positive", "summarize"):
        missing = [s for s in SUBSETS if not (ROOT / "results/raw" / f"E007_{s}_repomap_details.jsonl").exists()]
        if missing:
            print("RepoMap positive details not ready:", missing, flush=True)
        else:
            pos = aggregate_positive("repomap", PUBLISHED_REPOMAP)
            e006.write_json(ROOT / "results/baselines/E007_repomap_positive345.json", pos)
            print("RepoMap 345", json.dumps(pos["reproduced"], sort_keys=True), flush=True)

    if stage in ("qwen-scores", "qwen-gate"):
        qwen_details = e006.read_jsonl_path(ROOT / "results/raw/E007_natural_qwen_details.jsonl")
        cache_dir = ROOT / "results/embeddings/E007_qwen3_embedding_4b"
        shared = ROOT / "results/embeddings/E007_qwen3_embedding_4b_texts.sqlite"
        qwen_details, recover_s = recover_embedding_file_scores(qwen_details, cache_dir, shared)
        e006.write_jsonl(ROOT / "results/raw/E007_natural_qwen_details.jsonl", qwen_details)
        print("qwen score recovery s", recover_s, flush=True)
        gated = gate_from_file_scores(
            "qwen_embedding",
            qwen_details,
            outer,
            inner,
            balanced_ids,
            "C1_OFFICIAL_TOP_SCORE_THRESHOLD",
        )
        e006.write_jsonl(ROOT / "results/raw/E007_qwen_embedding_oof.jsonl", gated["oof"])
        gated_save = {k: v for k, v in gated.items() if k != "oof"}
        gated_save["verdict"] = backend_verdict(gated)
        gated_save["score_recovery_s"] = recover_s
        e006.write_json(ROOT / "results/baselines/E007_qwen_gate.json", gated_save)

    if stage in ("qwen-positive", "summarize"):
        missing = [s for s in SUBSETS if not (ROOT / "results/raw" / f"E007_{s}_qwen_details.jsonl").exists()]
        if missing:
            print("Qwen positive details not ready:", missing, flush=True)
        else:
            pos = aggregate_positive("qwen", PUBLISHED_QWEN)
            e006.write_json(ROOT / "results/baselines/E007_qwen_positive345.json", pos)
            print("Qwen 345", json.dumps(pos["reproduced"], sort_keys=True), flush=True)

    if stage in ("summarize",):
        comparison = summarize_e007()
        print("interpretation", json.dumps(comparison["interpretation"], sort_keys=True), flush=True)
        hashes = freeze_e007()
        print("froze results/frozen/E007_cross_retriever_generalization", flush=True)
        print("sha256", json.dumps(hashes, indent=2, sort_keys=True), flush=True)

    if stage in ("all",) and not (ROOT / "results/raw/E007_natural_qwen_details.jsonl").exists():
        print("stage all: RepoMap complete; Qwen official eval still required before summarize", flush=True)


if __name__ == "__main__":
    main()
