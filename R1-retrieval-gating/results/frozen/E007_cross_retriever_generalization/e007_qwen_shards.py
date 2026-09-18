#!/usr/bin/env python3
"""E007 official Qwen selective recovery by per-corpus CLI shards.

Outer orchestration only. Does not modify nested ARB. Does not change
Qwen scoring. The abandoned monolithic eval-selective-embedding command
must not be restarted.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path("/home/sauravsvt/Desktop/Research/R1")
ARB = ROOT / "agent-retrieval-bench"
SRC = ARB / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_retrieval_bench.baseline import load_corpus_manifest  # noqa: E402
from agent_retrieval_bench.io import read_jsonl  # noqa: E402

MODEL = "Qwen/Qwen3-Embedding-4B"
CACHE = ROOT / "results/embeddings/E007_qwen3_embedding_4b"
SHARED = ROOT / "results/embeddings/E007_qwen3_embedding_4b_texts.sqlite"
SHARD_ROOT = ROOT / "results/raw/E007_qwen_shards"
ID_DIR = SHARD_ROOT / "sample_ids"
DETAIL_DIR = SHARD_ROOT / "details"
SUMMARY_DIR = SHARD_ROOT / "summaries"
SWEEP_DIR = SHARD_ROOT / "sweeps"
REPORT_DIR = SHARD_ROOT / "reports"
TIME_DIR = SHARD_ROOT / "time"
MANIFEST_PATH = SHARD_ROOT / "manifest.json"
VALIDATION_PATH = ROOT / "results/raw/E007_qwen_shard_validation.json"
SMOKE_PATH = ROOT / "results/raw/E007_qwen_equivalence_smoke.json"
MERGE_PATH = ROOT / "results/raw/E007_natural_qwen_details.jsonl"
MERGE_REPORT_PATH = ROOT / "results/raw/E007_natural_qwen_merge_report.json"
SAMPLES_PATH = ARB / "data/benchmark/v2_selective_retrieval_natural/samples.jsonl"
CORPUS_DIR = ARB / "data/corpus/v2_selective_mixed"
ARB_BIN = ARB / ".venv/bin/arb"
LOCK_PATH = SHARD_ROOT / "queue.lock"
QUEUE_LOG = ROOT / "results/logs/E007_qwen_shards.txt"
POSITIVE_SUBSETS = ("v2_code2test", "v2_comment2context", "v2_trace2code", "v2_edit2ripple")
SMOKE_CORPUS_ID = "gin-gonic__gin__0cbb30aa940a643e31874f8ad8e355219d306756"


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def corpus_id_for(repo: str, base_commit: str) -> str:
    return f"{repo.replace('/', '__')}__{base_commit}"


def load_selective_samples() -> list[dict[str, Any]]:
    rows = list(read_jsonl(SAMPLES_PATH))
    if len(rows) != 427:
        raise SystemExit(f"ABORT: official selective-natural has {len(rows)} != 427 samples")
    return rows


def load_positive_qwen_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for subset in POSITIVE_SUBSETS:
        path = ROOT / "results/raw" / f"E007_{subset}_qwen_details.jsonl"
        if not path.exists():
            raise SystemExit(f"ABORT: missing official positive Qwen details {path}")
        for row in read_jsonl(path):
            sample_id = str(row["sample_id"])
            if sample_id in index:
                raise SystemExit(f"ABORT: duplicate positive Qwen sample_id {sample_id}")
            index[sample_id] = {"subset": subset, "row": row}
    return index


def build_shards() -> dict[str, Any]:
    cwd = os.getcwd()
    os.chdir(ARB)
    try:
        samples = load_selective_samples()
        manifest_map = load_corpus_manifest(CORPUS_DIR)
        if not manifest_map:
            raise SystemExit("ABORT: mixed corpus manifest empty; run from ARB with chunks present")
        expected_ids = [str(row["id"]) for row in samples]
        expected_set = set(expected_ids)
        if len(expected_set) != 427:
            raise SystemExit(f"ABORT: selective IDs not unique: {len(expected_set)}")

        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        missing_corpus: list[str] = []
        for row in samples:
            key = (str(row["repo"]), str(row["base_commit"]))
            chunks_path = manifest_map.get(key)
            if chunks_path is None:
                missing_corpus.append(str(row["id"]))
                continue
            groups[key].append(row)
        if missing_corpus:
            raise SystemExit(f"ABORT: {len(missing_corpus)} samples missing corpus mapping")

        for directory in (ID_DIR, DETAIL_DIR, SUMMARY_DIR, SWEEP_DIR, REPORT_DIR, TIME_DIR):
            directory.mkdir(parents=True, exist_ok=True)

        existing = {}
        if MANIFEST_PATH.exists():
            existing = {item["corpus_id"]: item for item in json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["shards"]}

        shards: list[dict[str, Any]] = []
        assigned: list[str] = []
        for (repo, base_commit), group in sorted(groups.items(), key=lambda item: corpus_id_for(*item[0])):
            cid = corpus_id_for(repo, base_commit)
            sample_ids = [str(row["id"]) for row in group]
            assigned.extend(sample_ids)
            id_file = ID_DIR / f"{cid}.txt"
            id_file.write_text("\n".join(sample_ids) + "\n", encoding="utf-8")
            chunks_path = manifest_map[(repo, base_commit)]
            prev = existing.get(cid, {})
            status = prev.get("status", "pending")
            if status not in {"complete", "pending", "running", "failed", "invalid"}:
                status = "pending"
            if status == "complete":
                out_path = ROOT / prev["output_path"]
                if not _details_valid(out_path, set(sample_ids)):
                    status = "invalid"
            shards.append(
                {
                    "corpus_id": cid,
                    "repo": repo,
                    "base_commit": base_commit,
                    "chunks_path": str(chunks_path),
                    "sample_id_file": str(id_file.relative_to(ROOT)),
                    "sample_count": len(sample_ids),
                    "sample_ids": sample_ids,
                    "status": status,
                    "output_path": str((DETAIL_DIR / f"{cid}.jsonl").relative_to(ROOT)),
                    "summary_path": str((SUMMARY_DIR / f"{cid}.json").relative_to(ROOT)),
                    "smoke_candidate": cid == SMOKE_CORPUS_ID,
                    "exit_code": prev.get("exit_code"),
                    "elapsed_s": prev.get("elapsed_s"),
                    "peak_rss_kb": prev.get("peak_rss_kb"),
                    "gpu_memory_used_mib": prev.get("gpu_memory_used_mib"),
                    "started_at": prev.get("started_at"),
                    "finished_at": prev.get("finished_at"),
                }
            )

        assigned_set = set(assigned)
        duplicates = len(assigned) - len(assigned_set)
        missing = sorted(expected_set - assigned_set)
        extra = sorted(assigned_set - expected_set)
        validation = {
            "n_selective": 427,
            "n_shards": len(shards),
            "n_assigned": len(assigned),
            "union_equals_selective_427": assigned_set == expected_set,
            "duplicates": duplicates,
            "missing": missing,
            "extra": extra,
            "missing_count": len(missing),
            "extra_count": len(extra),
            "validated_at": utc_now(),
        }
        write_json(VALIDATION_PATH, validation)
        if not validation["union_equals_selective_427"] or duplicates or missing or extra:
            raise SystemExit(f"ABORT: shard ID validation failed: {json.dumps(validation, sort_keys=True)}")

        doc = {
            "experiment_id": "E007",
            "model": MODEL,
            "official_cli": "arb eval-selective-embedding",
            "derived": "data/benchmark/v2_selective_retrieval_natural",
            "corpus": "data/corpus/v2_selective_mixed",
            "batch_size": 1,
            "query_batch_size": 1,
            "candidate_filter": "all_files",
            "normalize_embeddings": True,
            "query_prefix": "",
            "passage_prefix": "",
            "device": "cuda",
            "trust_remote_code": True,
            "monolithic_run": "permanently_abandoned_unbounded_inprocess_cache",
            "n_samples": 427,
            "n_shards": len(shards),
            "smoke_corpus_id": SMOKE_CORPUS_ID,
            "shards": shards,
            "validation": validation,
            "updated_at": utc_now(),
        }
        write_json(MANIFEST_PATH, doc)
        return doc
    finally:
        os.chdir(cwd)


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        return build_shards()
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(doc: dict[str, Any]) -> None:
    doc["updated_at"] = utc_now()
    write_json(MANIFEST_PATH, doc)


def _details_valid(path: Path, expected_ids: set[str]) -> bool:
    if not path.exists():
        return False
    try:
        rows = list(read_jsonl(path))
    except Exception:
        return False
    got = [str(row.get("sample_id")) for row in rows]
    return set(got) == expected_ids and len(got) == len(expected_ids)


def gpu_memory_used_mib() -> int | None:
    try:
        raw = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            text=True,
        ).strip()
        return int(float(raw.splitlines()[0]))
    except Exception:
        return None


def parse_time_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, Any] = {"raw_tail": text.strip().splitlines()[-20:]}
    match = re.search(r"Maximum resident set size \(kbytes\): (\d+)", text)
    if match:
        out["peak_rss_kb"] = int(match.group(1))
    match = re.search(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([0-9:.]+)", text)
    if match:
        out["time_elapsed"] = match.group(1)
    match = re.search(r"Exit status: (\d+)", text)
    if match:
        out["time_exit_status"] = int(match.group(1))
    return out


def official_shard_command(shard: dict[str, Any]) -> list[str]:
    cid = shard["corpus_id"]
    return [
        "/usr/bin/time",
        "-v",
        "-o",
        str(TIME_DIR / f"{cid}.time.txt"),
        str(ARB_BIN),
        "eval-selective-embedding",
        "--derived",
        "data/benchmark/v2_selective_retrieval_natural",
        "--corpus",
        "data/corpus/v2_selective_mixed",
        "--model",
        MODEL,
        "--device",
        "cuda",
        "--trust-remote-code",
        "--batch-size",
        "1",
        "--query-batch-size",
        "1",
        "--candidate-filter",
        "all_files",
        "--no-keep-list",
        "--cache",
        str(CACHE),
        "--shared-text-cache",
        str(SHARED),
        "--sample-id-file",
        str(ROOT / shard["sample_id_file"]),
        "--out",
        str(ROOT / shard["summary_path"]),
        "--details",
        str(ROOT / shard["output_path"]),
        "--sweep",
        str(SWEEP_DIR / f"{cid}.jsonl"),
        "--report",
        str(REPORT_DIR / f"{cid}.md"),
    ]


def run_one_shard(corpus_id: str, *, force: bool = False) -> dict[str, Any]:
    doc = load_manifest()
    shard = next((item for item in doc["shards"] if item["corpus_id"] == corpus_id), None)
    if shard is None:
        raise SystemExit(f"ABORT: unknown corpus_id {corpus_id}")
    details_path = ROOT / shard["output_path"]
    expected = set(shard["sample_ids"])
    if shard["status"] == "complete" and not force and _details_valid(details_path, expected):
        print(f"[skip] {corpus_id} already complete n={shard['sample_count']}", flush=True)
        return shard
    if details_path.exists() and not force:
        details_path.unlink()

    shard["status"] = "running"
    shard["started_at"] = utc_now()
    shard["exit_code"] = None
    save_manifest(doc)

    env = os.environ.copy()
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    env["PYTHONUNBUFFERED"] = "1"
    cmd = official_shard_command(shard)
    print(f"[run] {corpus_id} n={shard['sample_count']} started {shard['started_at']}", flush=True)
    t0 = time.perf_counter()
    gpu_before = gpu_memory_used_mib()
    with QUEUE_LOG.open("a", encoding="utf-8") as log:
        log.write(f"\n===== SHARD {corpus_id} {shard['started_at']} =====\n")
        log.write(" ".join(cmd) + "\n")
        log.flush()
        proc = subprocess.run(cmd, cwd=ARB, env=env, stdout=log, stderr=subprocess.STDOUT)
    elapsed = time.perf_counter() - t0
    gpu_after = gpu_memory_used_mib()
    timing = parse_time_file(TIME_DIR / f"{corpus_id}.time.txt")
    shard["exit_code"] = int(proc.returncode)
    shard["elapsed_s"] = elapsed
    shard["finished_at"] = utc_now()
    shard["peak_rss_kb"] = timing.get("peak_rss_kb")
    shard["gpu_memory_used_mib"] = gpu_after
    shard["gpu_memory_used_mib_before"] = gpu_before
    shard["time_elapsed"] = timing.get("time_elapsed")

    if proc.returncode != 0:
        shard["status"] = "failed"
        save_manifest(doc)
        raise SystemExit(f"ABORT: official CLI failed corpus={corpus_id} exit={proc.returncode}")
    if not _details_valid(details_path, expected):
        shard["status"] = "invalid"
        save_manifest(doc)
        raise SystemExit(f"ABORT: details invalid after success exit corpus={corpus_id}")
    shard["status"] = "complete"
    save_manifest(doc)
    print(
        f"[done] {corpus_id} n={shard['sample_count']} exit=0 "
        f"rss_kb={shard['peak_rss_kb']} vram={gpu_after} elapsed={elapsed:.1f}s",
        flush=True,
    )
    return shard


def compare_overlap(shard_rows: list[dict[str, Any]], positive_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    comparisons = []
    unexplained = []
    for row in shard_rows:
        sample_id = str(row["sample_id"])
        pos = positive_index.get(sample_id)
        if pos is None:
            continue
        pos_row = pos["row"]
        shard_files = list(row.get("top_files") or [])
        pos_files = list(pos_row.get("top_files") or [])
        files_match = shard_files == pos_files
        order_match = files_match
        numeric = {
            "positive_has_top_score": "top_score" in pos_row or "confidence" in pos_row,
            "selective_top_score": row.get("top_score"),
            "selective_second_score": row.get("second_score"),
            "numeric_comparable": False,
            "numeric_match": None,
            "note": (
                "Official eval-embedding positive details store top_files only; "
                "they do not serialize top_score/second_score. Numeric equality "
                "is therefore not observable against that artifact."
            ),
        }
        item = {
            "sample_id": sample_id,
            "subset": pos["subset"],
            "task_type_selective": row.get("task_type"),
            "task_type_positive": pos_row.get("task_type"),
            "repo": row.get("repo"),
            "base_commit": row.get("base_commit"),
            "ranked_files_match": files_match,
            "top20_order_match": order_match,
            "numeric": numeric,
        }
        comparisons.append(item)
        if not files_match:
            unexplained.append(
                {
                    "sample_id": sample_id,
                    "selective_top_files": shard_files[:5],
                    "positive_top_files": pos_files[:5],
                }
            )
    return {
        "n_overlap": len(comparisons),
        "n_file_match": sum(1 for item in comparisons if item["ranked_files_match"]),
        "n_order_match": sum(1 for item in comparisons if item["top20_order_match"]),
        "unexplained_discrepancies": unexplained,
        "comparisons": comparisons,
    }


def run_smoke() -> dict[str, Any]:
    doc = load_manifest()
    shard = next(item for item in doc["shards"] if item["corpus_id"] == SMOKE_CORPUS_ID)
    positive_index = load_positive_qwen_index()
    overlap_ids = [sid for sid in shard["sample_ids"] if sid in positive_index]
    if not overlap_ids:
        raise SystemExit("ABORT: smoke corpus has no overlap with completed official positive Qwen")
    run_one_shard(SMOKE_CORPUS_ID, force=True)
    rows = list(read_jsonl(ROOT / shard["output_path"]))
    comparison = compare_overlap(rows, positive_index)
    smoke = {
        "corpus_id": SMOKE_CORPUS_ID,
        "chunks_path": shard["chunks_path"],
        "sample_count": shard["sample_count"],
        "overlap_ids": overlap_ids,
        "same_query_text_all_345_positives": True,
        "comparison": comparison,
        "pass": comparison["n_overlap"] >= 1
        and comparison["n_file_match"] == comparison["n_overlap"]
        and not comparison["unexplained_discrepancies"],
        "recorded_at": utc_now(),
        "note": (
            "Smoke uses official eval-selective-embedding --sample-id-file on one "
            "corpus that already appears in official eval-embedding positive details. "
            "Query texts match for all 345 overlapping IDs. Mixed-corpus chunks_path "
            "points at the same subset snapshot file used for the positive run."
        ),
    }
    write_json(SMOKE_PATH, smoke)
    if not smoke["pass"]:
        raise SystemExit(
            "STOP: unexplained smoke discrepancy vs official positive Qwen: "
            + json.dumps(comparison["unexplained_discrepancies"][:3], sort_keys=True)
        )
    print(
        f"[smoke] PASS overlap={comparison['n_overlap']} "
        f"files_match={comparison['n_file_match']} order_match={comparison['n_order_match']}",
        flush=True,
    )
    return smoke


def run_queue() -> None:
    if not SMOKE_PATH.exists():
        raise SystemExit("ABORT: smoke report missing; run smoke before the queue")
    smoke = json.loads(SMOKE_PATH.read_text(encoding="utf-8"))
    if not smoke.get("pass"):
        raise SystemExit("ABORT: smoke did not pass; queue will not start")
    doc = load_manifest()
    pending = [item["corpus_id"] for item in doc["shards"] if item["status"] != "complete"]
    print(f"[queue] remaining={len(pending)} / {len(doc['shards'])}", flush=True)
    for corpus_id in pending:
        run_one_shard(corpus_id, force=False)
    doc = load_manifest()
    leftover = [item["corpus_id"] for item in doc["shards"] if item["status"] != "complete"]
    if leftover:
        raise SystemExit(f"ABORT: queue finished with incomplete shards: {leftover[:10]}")
    print("[queue] all 271 corpora complete", flush=True)


def merge_details() -> dict[str, Any]:
    samples = load_selective_samples()
    order = [str(row["id"]) for row in samples]
    order_index = {sample_id: i for i, sample_id in enumerate(order)}
    doc = load_manifest()
    incomplete = [item["corpus_id"] for item in doc["shards"] if item["status"] != "complete"]
    if incomplete:
        raise SystemExit(f"ABORT: merge requires all shards complete; leftover={len(incomplete)}")
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for shard in doc["shards"]:
        rows = list(read_jsonl(ROOT / shard["output_path"]))
        got = [str(row["sample_id"]) for row in rows]
        if set(got) != set(shard["sample_ids"]) or len(got) != len(shard["sample_ids"]):
            raise SystemExit(f"ABORT: merge shard integrity failed {shard['corpus_id']}")
        for row in rows:
            sample_id = str(row["sample_id"])
            if sample_id in seen:
                raise SystemExit(f"ABORT: duplicate sample_id during merge {sample_id}")
            seen.add(sample_id)
            merged.append(row)
    missing = [sample_id for sample_id in order if sample_id not in seen]
    extra = sorted(seen - set(order))
    if missing or extra or len(merged) != 427:
        raise SystemExit(
            f"ABORT: merge ID check failed n={len(merged)} missing={len(missing)} extra={len(extra)}"
        )
    merged.sort(key=lambda row: order_index[str(row["sample_id"])])
    MERGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MERGE_PATH.open("w", encoding="utf-8") as handle:
        for row in merged:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")
    report = {
        "n": len(merged),
        "unique_ids": len(seen),
        "missing": [],
        "duplicates": 0,
        "extra": [],
        "order": "official v2_selective_retrieval_natural samples.jsonl",
        "source": "official arb eval-selective-embedding per unique (repo, base_commit) corpus, lossless concat",
        "not_a_monolithic_official_invocation": True,
        "reason": (
            "Monolithic official eval-selective-embedding keeps unbounded chunk/vector "
            "caches and only writes details at the end. Per-corpus official CLI shards "
            "were required to finish on 32 GB RAM. Scores and rankings are official "
            "ARB output; this file is aggregation only."
        ),
        "shard_count": len(doc["shards"]),
        "written": str(MERGE_PATH.relative_to(ROOT)),
        "merged_at": utc_now(),
    }
    write_json(MERGE_REPORT_PATH, report)
    print(f"[merge] wrote {MERGE_PATH} n=427", flush=True)
    return report


def status() -> dict[str, Any]:
    doc = load_manifest() if MANIFEST_PATH.exists() else {"shards": []}
    counts: dict[str, int] = defaultdict(int)
    samples_done = 0
    for shard in doc.get("shards", []):
        counts[shard["status"]] += 1
        if shard["status"] == "complete":
            samples_done += int(shard["sample_count"])
    summary = {
        "n_shards": len(doc.get("shards", [])),
        "status_counts": dict(counts),
        "samples_complete": samples_done,
        "samples_total": 427,
        "smoke_exists": SMOKE_PATH.exists(),
        "merge_exists": MERGE_PATH.exists(),
    }
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return summary


def main() -> None:
    stage = sys.argv[1] if len(sys.argv) > 1 else "status"
    if stage == "build":
        doc = build_shards()
        print(f"built {doc['n_shards']} shards; validation OK", flush=True)
        return
    if stage == "smoke":
        build_shards()
        run_smoke()
        return
    if stage == "run-one":
        if len(sys.argv) < 3:
            raise SystemExit("usage: e007_qwen_shards.py run-one CORPUS_ID")
        run_one_shard(sys.argv[2], force="--force" in sys.argv)
        return
    if stage == "queue":
        build_shards()
        run_queue()
        return
    if stage == "merge":
        merge_details()
        return
    if stage == "status":
        status()
        return
    raise SystemExit(f"unknown stage {stage}")


if __name__ == "__main__":
    main()
