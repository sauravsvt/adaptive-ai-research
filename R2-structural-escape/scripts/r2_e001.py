#!/usr/bin/env python3
"""E001 runner: Stage-1/2 freezes, initials, A1/A4, plus-test verify, analysis."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path("/home/sauravsvt/Desktop/Research/R2")
sys.path.insert(0, str(ROOT / "scripts"))

from r2_lib import (  # noqa: E402
    ARM_INSTRUCTIONS,
    SYSTEM_PROMPT,
    TASK_TEMPLATE,
    align_prefix,
    append_jsonl,
    extract_code,
    intervention_user_prompt,
    material,
    ollama_chat,
    paired_bootstrap,
    read_json,
    read_jsonl,
    sha256_file,
    sha256_text,
    task_user_prompt,
    words,
    write_json,
)

from evalplus.data import get_mbpp_plus, get_mbpp_plus_hash  # noqa: E402
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS  # noqa: E402
from evalplus.evaluate import check_correctness, get_groundtruth  # noqa: E402

CFG_PATH = ROOT / "configs/E001_fixed_prefix.json"
PREREG_PATH = ROOT / "PREREG_E001.md"
INIT_PATH = ROOT / "results/raw/E001_initial.jsonl"
PREFIX_PATH = ROOT / "results/raw/E001_prefixes.jsonl"
ARM_PATH = ROOT / "results/raw/E001_arms.jsonl"
VERIFY_PATH = ROOT / "results/raw/E001_verify.jsonl"
ANALYSIS_PATH = ROOT / "results/raw/E001_analysis.json"
CATALOG_PATH = ROOT / "results/raw/E001_plus_testable.json"
STAGE1_DIR = ROOT / "results/frozen/E001_stage1"
STAGE2_DIR = ROOT / "results/frozen/E001_stage2"
RUN_DIR = ROOT / "results/frozen/E001_run"
EXPECTED_PREREG = "cca6fb2e20793ee7c8143e5a4c16219716f38a61fd373863bb9e44f8e4c067ad"
EXCLUDED = {"Mbpp/793"}
K = 160


def task_digest(task_id: str) -> str:
    return hashlib.sha256(f"R2-E001|{task_id}".encode("utf-8")).hexdigest()


def a1_first(task_id: str) -> bool:
    return (int(task_digest(task_id), 16) & 1) == 0


def arm_schedule(task_id: str) -> list[str]:
    if a1_first(task_id):
        return ["A1_CONTINUE_LOCAL", "A4_STRUCTURAL_ESCAPE"]
    return ["A4_STRUCTURAL_ESCAPE", "A1_CONTINUE_LOCAL"]


def prefix_has_fence(prefix: str) -> bool:
    return "```" in (prefix or "")


def assert_frozen_prompts() -> None:
    checks = {
        "system": (SYSTEM_PROMPT, "988834b3804622cef83deaa27c18a55329eff3432579466c89a3a924c1236863"),
        "task_template": (TASK_TEMPLATE, "85b7b076af2dc9d3260a96350604bbe53b1c483c8a258720e749b583f43a25af"),
        "A1": (ARM_INSTRUCTIONS["A1_CONTINUE_LOCAL"], "ea2c65a2b7be99cf3eb73923129563e2ec115d3ca558d6a260daf394b689ffcc"),
        "A4": (ARM_INSTRUCTIONS["A4_STRUCTURAL_ESCAPE"], "2bb16c2f1b2e576bf8ec5af25f2c2e8ec30a46efb1755f78b6d64286bcea7286"),
        "prereg": (PREREG_PATH.read_text(encoding="utf-8"), EXPECTED_PREREG),
    }
    for name, (text, expected) in checks.items():
        got = sha256_text(text) if name != "prereg" else hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest()
        if name == "prereg":
            got = hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest()
        else:
            got = sha256_text(text)
        if got != expected:
            raise SystemExit(f"frozen hash mismatch {name}: {got} != {expected}")


def load_problems() -> dict[str, dict]:
    return get_mbpp_plus()


def plus_testable_ids(problems: dict[str, dict]) -> list[str]:
    rows = []
    for task_id, problem in problems.items():
        if task_id in EXCLUDED:
            continue
        if len(problem.get("plus_input") or []) == 0:
            continue
        rows.append((task_digest(task_id), task_id))
    rows.sort()
    return [task_id for _, task_id in rows]


def existing_ids(path: Path, key: str = "task_id") -> set[str]:
    return {str(row[key]) for row in read_jsonl(path) if key in row}


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def write_sha256sums(directory: Path, names: list[str]) -> dict:
    rows = []
    for name in names:
        path = directory / name
        rows.append({"path": name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(directory / "SHA256SUMS.json", rows)
    return {"SHA256SUMS.json": sha256_file(directory / "SHA256SUMS.json")}


def freeze_stage1(problems: dict[str, dict], cfg: dict) -> dict:
    assert_frozen_prompts()
    ids = plus_testable_ids(problems)
    if len(ids) != 377:
        raise SystemExit(f"plus-testable catalog is {len(ids)}, expected 377")
    dataset_hash = get_mbpp_plus_hash()
    if dataset_hash != cfg["benchmark"]["dataset_hash"]:
        raise SystemExit(f"MBPP+ hash {dataset_hash} != {cfg['benchmark']['dataset_hash']}")
    catalog = {
        "excluded_a_priori": sorted(EXCLUDED),
        "n_catalog": len(problems),
        "n_plus_testable": len(ids),
        "order": ids,
        "seed_string": "R2-E001",
        "dataset_hash": dataset_hash,
    }
    write_json(CATALOG_PATH, catalog)
    STAGE1_DIR.mkdir(parents=True, exist_ok=True)
    copy_file(PREREG_PATH, STAGE1_DIR / "PREREG_E001.md")
    copy_file(CFG_PATH, STAGE1_DIR / "E001_fixed_prefix.json")
    write_json(STAGE1_DIR / "E001_plus_testable.json", catalog)
    manifest = {
        "stage": 1,
        "experiment_id": "E001",
        "note": "Pre-initial freeze. No E001 generation before this file.",
        "prereg_sha256": hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest(),
        "config_sha256": sha256_file(CFG_PATH),
        "plus_testable_sha256": sha256_file(STAGE1_DIR / "E001_plus_testable.json"),
        "model": cfg["model"],
        "benchmark": {
            "name": "MbppPlus",
            "release": "v0.2.0",
            "dataset_hash": dataset_hash,
            "n_catalog": len(problems),
            "n_plus_testable": len(ids),
            "excluded_a_priori": sorted(EXCLUDED),
        },
        "prompts": cfg["prompts"],
        "prefix_K": K,
        "arms": cfg["arms"],
    }
    write_json(STAGE1_DIR / "E001_stage1_manifest.json", manifest)
    sums = write_sha256sums(
        STAGE1_DIR,
        [
            "PREREG_E001.md",
            "E001_fixed_prefix.json",
            "E001_plus_testable.json",
            "E001_stage1_manifest.json",
        ],
    )
    print("STAGE1 FROZEN", json.dumps(manifest, sort_keys=True), flush=True)
    print("STAGE1 SHA256SUMS", json.dumps(sums, sort_keys=True), flush=True)
    return manifest


def generate_initial(task_id: str, problem: dict, cfg: dict) -> dict:
    user = task_user_prompt(problem["prompt"])
    out = ollama_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        num_predict=int(cfg["model"]["initial_num_predict"]),
        num_ctx=int(cfg["model"]["num_ctx"]),
        temperature=float(cfg["model"]["temperature"]),
        think=str(cfg["model"]["think"]),
        model=str(cfg["model"]["name"]),
    )
    n_words = len(words(out["trajectory"]))
    return {
        "experiment_id": "E001",
        "stage": "initial",
        "task_id": task_id,
        "entry_point": problem["entry_point"],
        "user_prompt_sha256": sha256_text(user),
        "n_words": n_words,
        "trajectory_sha256": sha256_text(out["trajectory"]),
        **out,
    }


def run_initials(task_ids: list[str], problems: dict[str, dict], cfg: dict) -> None:
    pending = [tid for tid in task_ids if tid not in existing_ids(INIT_PATH)]
    total = len(task_ids)
    if pending:
        pending = pending[1:] + pending[:1]
    for pass_i in range(1, 4):
        if not pending:
            break
        failed: list[str] = []
        for task_id in pending:
            i = task_ids.index(task_id) + 1
            print(f"[initial {i}/{total} pass {pass_i}] {task_id}", flush=True)
            try:
                row = generate_initial(task_id, problems[task_id], cfg)
                append_jsonl(INIT_PATH, row)
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED {task_id}: {exc}", flush=True)
                failed.append(task_id)
                time.sleep(20)
        pending = failed
    if pending:
        raise SystemExit(f"initials still failing: {pending}")
    have = existing_ids(INIT_PATH)
    missing = [tid for tid in task_ids if tid not in have]
    if missing:
        raise SystemExit(f"initials missing: {missing}")
    print(f"initials complete {len(have)}/{total}", flush=True)


def freeze_stage2(task_ids: list[str]) -> dict:
    if not STAGE1_DIR.joinpath("E001_stage1_manifest.json").exists():
        raise SystemExit("Stage 1 is not frozen")
    rows = {r["task_id"]: r for r in read_jsonl(INIT_PATH)}
    missing = [tid for tid in task_ids if tid not in rows]
    if missing:
        raise SystemExit(f"cannot Stage-2 freeze, missing initials: {missing[:10]}")

    PREFIX_PATH.write_text("", encoding="utf-8")
    usable: list[str] = []
    initial_hashes = {}
    prefixes = []
    for task_id in task_ids:
        row = rows[task_id]
        traj = row["trajectory"]
        n_words = int(row.get("n_words") or len(words(traj)))
        initial_hashes[task_id] = {
            "task_id": task_id,
            "n_words": n_words,
            "trajectory_sha256": sha256_text(traj),
            "usable": n_words >= K,
        }
        if n_words < K:
            continue
        prefix = align_prefix(traj, K)
        pref = {
            "experiment_id": "E001",
            "task_id": task_id,
            "entry_point": row["entry_point"],
            "n_words_trajectory": n_words,
            "n_words_prefix": len(words(prefix)),
            "prefix": prefix,
            "prefix_sha256": sha256_text(prefix),
            "fence_open": prefix_has_fence(prefix),
            "a1_first": a1_first(task_id),
            "arm_order": arm_schedule(task_id),
        }
        append_jsonl(PREFIX_PATH, pref)
        prefixes.append(pref)
        usable.append(task_id)

    usable_doc = {
        "K": K,
        "n_plus_testable": len(task_ids),
        "n_usable": len(usable),
        "n_unusable_short": len(task_ids) - len(usable),
        "usable_ids": usable,
        "unusable_ids": [tid for tid in task_ids if tid not in set(usable)],
        "n_a1_first": sum(1 for tid in usable if a1_first(tid)),
        "n_a4_first": sum(1 for tid in usable if not a1_first(tid)),
        "rule": "usable iff plus-testable and len(words(trajectory)) >= 160",
        "note": "Fence diagnostic is recorded on prefixes and is not an eligibility rule.",
    }
    write_json(ROOT / "results/raw/E001_usable.json", usable_doc)
    write_json(ROOT / "results/raw/E001_initial_hashes.json", initial_hashes)

    STAGE2_DIR.mkdir(parents=True, exist_ok=True)
    copy_file(PREFIX_PATH, STAGE2_DIR / "E001_prefixes.jsonl")
    copy_file(ROOT / "results/raw/E001_usable.json", STAGE2_DIR / "E001_usable.json")
    copy_file(ROOT / "results/raw/E001_initial_hashes.json", STAGE2_DIR / "E001_initial_hashes.json")
    copy_file(INIT_PATH, STAGE2_DIR / "E001_initial.jsonl")
    manifest = {
        "stage": 2,
        "experiment_id": "E001",
        "note": "Post-initial / pre-arm freeze. No plus-test labels used. No arm calls before this file.",
        "K": K,
        "n_usable": len(usable),
        "usable_ids": usable,
        "n_a1_first": usable_doc["n_a1_first"],
        "n_a4_first": usable_doc["n_a4_first"],
        "n_fence_open": sum(1 for p in prefixes if p["fence_open"]),
        "n_fence_absent": sum(1 for p in prefixes if not p["fence_open"]),
        "usable_sha256": sha256_file(STAGE2_DIR / "E001_usable.json"),
        "prefixes_sha256": sha256_file(STAGE2_DIR / "E001_prefixes.jsonl"),
        "initial_hashes_sha256": sha256_file(STAGE2_DIR / "E001_initial_hashes.json"),
        "initials_sha256": sha256_file(STAGE2_DIR / "E001_initial.jsonl"),
        "prefix_entries": [
            {
                "task_id": p["task_id"],
                "prefix_sha256": p["prefix_sha256"],
                "n_words_prefix": p["n_words_prefix"],
                "fence_open": p["fence_open"],
                "a1_first": p["a1_first"],
            }
            for p in prefixes
        ],
    }
    write_json(STAGE2_DIR / "E001_stage2_manifest.json", manifest)
    write_sha256sums(
        STAGE2_DIR,
        [
            "E001_usable.json",
            "E001_prefixes.jsonl",
            "E001_initial_hashes.json",
            "E001_initial.jsonl",
            "E001_stage2_manifest.json",
        ],
    )
    print(
        f"STAGE2 FROZEN n_usable={len(usable)} fence_open={manifest['n_fence_open']} "
        f"a1_first={usable_doc['n_a1_first']} a4_first={usable_doc['n_a4_first']}",
        flush=True,
    )
    if len(usable) < 80:
        write_json(
            ANALYSIS_PATH,
            {
                "experiment_id": "E001",
                "decision": "UNEVALUABLE",
                "reason": f"usable n={len(usable)} < 80",
                "n_usable": len(usable),
            },
        )
        raise SystemExit(f"UNEVALUABLE: usable n={len(usable)} < 80")
    return manifest


def generate_arm(problem: dict, prefix_row: dict, arm: str, cfg: dict) -> dict:
    user = intervention_user_prompt(problem["prompt"], prefix_row["prefix"], arm)
    out = ollama_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        num_predict=int(cfg["model"]["intervention_num_predict"]),
        num_ctx=int(cfg["model"]["num_ctx"]),
        temperature=float(cfg["model"]["temperature"]),
        think=str(cfg["model"]["think"]),
        model=str(cfg["model"]["name"]),
    )
    return {
        "experiment_id": "E001",
        "stage": "intervention",
        "task_id": prefix_row["task_id"],
        "arm": arm,
        "a1_first": prefix_row.get("a1_first"),
        "prefix_n_words": prefix_row.get("n_words_prefix"),
        "prefix_sha256": prefix_row["prefix_sha256"],
        "fence_open": prefix_row.get("fence_open"),
        "user_prompt_sha256": sha256_text(user),
        **out,
    }


def run_arms(problems: dict[str, dict], cfg: dict) -> None:
    if not STAGE2_DIR.joinpath("E001_stage2_manifest.json").exists():
        raise SystemExit("Stage 2 is not frozen; refusing to run arms")
    prefs = {r["task_id"]: r for r in read_jsonl(PREFIX_PATH)}
    usable = read_json(ROOT / "results/raw/E001_usable.json")["usable_ids"]
    done = {(r["task_id"], r["arm"]) for r in read_jsonl(ARM_PATH)}
    jobs: list[tuple[str, str]] = []
    for task_id in usable:
        for arm in arm_schedule(task_id):
            if (task_id, arm) not in done:
                jobs.append((task_id, arm))
    total = len(usable) * 2
    pending = jobs
    for pass_i in range(1, 4):
        if not pending:
            break
        failed: list[tuple[str, str]] = []
        for task_id, arm in pending:
            print(
                f"[arm pass {pass_i} {task_id} {arm}] remaining={len(pending)}/{total}",
                flush=True,
            )
            try:
                row = generate_arm(problems[task_id], prefs[task_id], arm, cfg)
                append_jsonl(ARM_PATH, row)
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED arm {task_id} {arm}: {exc}", flush=True)
                failed.append((task_id, arm))
                time.sleep(20)
        pending = failed
    if pending:
        raise SystemExit(f"arms still failing: {pending}")
    print(f"arms complete {len(read_jsonl(ARM_PATH))}/{total}", flush=True)


def build_solution(problem: dict, extracted: str | None) -> str | None:
    if not extracted or not extracted.strip():
        return None
    prompt = problem["prompt"]
    if prompt.strip() in extracted:
        return extracted
    return prompt + extracted


def verify_row(task_id: str, problem: dict, expected: dict, source: dict, code_text: str | None) -> dict:
    solution = build_solution(problem, code_text)
    if not solution:
        return {
            "task_id": task_id,
            "source_stage": source.get("stage"),
            "arm": source.get("arm"),
            "plus_pass": False,
            "base_pass": False,
            "reason": "no_extractable_solution",
            "prefix_sha256": source.get("prefix_sha256"),
        }
    result = check_correctness(
        "mbpp",
        0,
        problem,
        solution,
        expected[task_id],
        base_only=False,
        fast_check=True,
    )
    base_stat = (result.get("base") or (None,))[0]
    plus_stat = (result.get("plus") or (None,))[0]
    return {
        "task_id": task_id,
        "source_stage": source.get("stage"),
        "arm": source.get("arm"),
        "prefix_sha256": source.get("prefix_sha256"),
        "base_pass": base_stat == "success" or base_stat == "pass" or str(base_stat).lower() == "pass",
        "plus_pass": plus_stat == "success" or plus_stat == "pass" or str(plus_stat).lower() == "pass",
        "base_stat": str(base_stat),
        "plus_stat": str(plus_stat),
        "reason": "checked",
    }


def verify_key(row: dict) -> str:
    return "|".join([str(row.get("task_id")), str(row.get("source_stage") or row.get("stage")), str(row.get("arm") or "")])


def run_verify(problems: dict[str, dict]) -> None:
    expected = get_groundtruth(problems, get_mbpp_plus_hash(), MBPP_OUTPUT_NOT_NONE_TASKS)
    done = {verify_key(r) for r in read_jsonl(VERIFY_PATH)}
    for row in read_jsonl(ARM_PATH):
        key = verify_key({**row, "source_stage": "intervention"})
        if key in done:
            continue
        code = extract_code(row.get("trajectory") or "")
        result = verify_row(row["task_id"], problems[row["task_id"]], expected, row, code)
        append_jsonl(VERIFY_PATH, result)
        print(f"[verify] {row['task_id']} {row['arm']} plus={result['plus_pass']}", flush=True)
    print("verify rows", len(read_jsonl(VERIFY_PATH)), flush=True)


def ns_to_s(value: object) -> float | None:
    if value is None:
        return None
    return float(value) / 1e9


def summarize_calls(rows: list[dict]) -> dict:
    tokens = [float(r["eval_count"]) for r in rows if r.get("eval_count") is not None]
    walls = [float(r["wall_s"]) for r in rows if r.get("wall_s") is not None]
    gpus = [ns_to_s(r.get("eval_duration_ns")) for r in rows]
    gpus = [g for g in gpus if g is not None]
    reasons = Counter(str(r.get("done_reason")) for r in rows)
    return {
        "n": len(rows),
        "eval_tokens_mean": float(np.mean(tokens)) if tokens else None,
        "eval_tokens_sum": float(np.sum(tokens)) if tokens else None,
        "wall_s_mean": float(np.mean(walls)) if walls else None,
        "wall_s_sum": float(np.sum(walls)) if walls else None,
        "eval_gpu_s_mean": float(np.mean(gpus)) if gpus else None,
        "eval_gpu_s_sum": float(np.sum(gpus)) if gpus else None,
        "done_reason": dict(reasons),
        "n_no_extractable": sum(1 for r in rows if not extract_code(r.get("trajectory") or "")),
    }


def interpret(n: int, a1_rate: float | None, delta: dict) -> str:
    if n < 80:
        return "UNEVALUABLE"
    if material(delta):
        return "CONTINUE — FIXED-PREFIX A4 OVER A1"
    if a1_rate is not None and a1_rate >= 0.95:
        return "CEILING-LIMITED"
    return "STOP — NO A4 OVER A1 SIGNAL"


def run_analyze() -> dict:
    cells: dict[str, dict[str, int]] = {}
    for row in read_jsonl(VERIFY_PATH):
        if not row.get("arm"):
            continue
        cells.setdefault(row["task_id"], {})[row["arm"]] = int(bool(row.get("plus_pass")))
    paired = []
    a1_vals = []
    a4_vals = []
    n10 = n01 = n11 = n00 = 0
    for task_id, arms in cells.items():
        if "A1_CONTINUE_LOCAL" not in arms or "A4_STRUCTURAL_ESCAPE" not in arms:
            continue
        a1 = arms["A1_CONTINUE_LOCAL"]
        a4 = arms["A4_STRUCTURAL_ESCAPE"]
        paired.append(a4 - a1)
        a1_vals.append(a1)
        a4_vals.append(a4)
        if a4 == 1 and a1 == 0:
            n10 += 1
        elif a4 == 0 and a1 == 1:
            n01 += 1
        elif a4 == 1 and a1 == 1:
            n11 += 1
        else:
            n00 += 1
    delta_arr = np.asarray(paired, dtype=np.float64)
    delta = paired_bootstrap(delta_arr, n_resamples=10000, seed=0)
    a1_rate = float(np.mean(a1_vals)) if a1_vals else None
    a4_rate = float(np.mean(a4_vals)) if a4_vals else None
    initials = read_jsonl(INIT_PATH)
    arms = read_jsonl(ARM_PATH)
    a1_rows = [r for r in arms if r.get("arm") == "A1_CONTINUE_LOCAL"]
    a4_rows = [r for r in arms if r.get("arm") == "A4_STRUCTURAL_ESCAPE"]
    usable = read_json(ROOT / "results/raw/E001_usable.json")
    analysis = {
        "experiment_id": "E001",
        "n_usable": int(usable["n_usable"]),
        "n_paired": int(delta_arr.size),
        "rates": {
            "A1_CONTINUE_LOCAL": {"n": len(a1_vals), "success": a1_rate, "n_pass": int(sum(a1_vals))},
            "A4_STRUCTURAL_ESCAPE": {"n": len(a4_vals), "success": a4_rate, "n_pass": int(sum(a4_vals))},
        },
        "deltas": {"A4-A1": delta},
        "mcnemar_descriptive": {
            "n_A4pass_A1fail": n10,
            "n_A4fail_A1pass": n01,
            "n_both_pass": n11,
            "n_both_fail": n00,
        },
        "secondary": {
            "initials": summarize_calls(initials),
            "arms_all": summarize_calls(arms),
            "arms_A1": summarize_calls(a1_rows),
            "arms_A4": summarize_calls(a4_rows),
            "n_fence_open": sum(1 for r in read_jsonl(PREFIX_PATH) if r.get("fence_open")),
            "note": "Fence diagnostic is not a stratum. No efficiency claim.",
        },
    }
    analysis["decision"] = interpret(int(delta_arr.size), a1_rate, delta)
    write_json(ANALYSIS_PATH, analysis)
    print(json.dumps(analysis, indent=2, sort_keys=True), flush=True)
    print("DECISION", analysis["decision"], flush=True)
    return analysis


def freeze_run() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    names = [
        ("E001_initial.jsonl", INIT_PATH),
        ("E001_prefixes.jsonl", PREFIX_PATH),
        ("E001_usable.json", ROOT / "results/raw/E001_usable.json"),
        ("E001_initial_hashes.json", ROOT / "results/raw/E001_initial_hashes.json"),
        ("E001_arms.jsonl", ARM_PATH),
        ("E001_verify.jsonl", VERIFY_PATH),
        ("E001_analysis.json", ANALYSIS_PATH),
        ("E001_plus_testable.json", CATALOG_PATH),
        ("E001_fixed_prefix.json", CFG_PATH),
        ("PREREG_E001.md", PREREG_PATH),
    ]
    copied = []
    for name, src in names:
        if src.exists():
            copy_file(src, RUN_DIR / name)
            copied.append(name)
    write_sha256sums(RUN_DIR, copied)
    print("RUN FROZEN", RUN_DIR, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        default="all",
        choices=["stage1", "initials", "stage2", "arms", "verify", "analyze", "freeze_run", "all"],
    )
    args = parser.parse_args()
    assert_frozen_prompts()
    cfg = read_json(CFG_PATH)
    if cfg.get("prereg_sha256") != EXPECTED_PREREG:
        raise SystemExit("config prereg_sha256 does not match frozen PREREG_E001.md")
    problems = load_problems()
    print(f"loaded MBPP+ n={len(problems)}", flush=True)
    ids = plus_testable_ids(problems)
    print(f"plus-testable n={len(ids)}", flush=True)

    if args.stage in ("stage1", "all"):
        if not STAGE1_DIR.joinpath("E001_stage1_manifest.json").exists():
            freeze_stage1(problems, cfg)
        else:
            print("stage1 already frozen", flush=True)
            if args.stage == "stage1":
                return

    if args.stage in ("initials", "all"):
        if not STAGE1_DIR.joinpath("E001_stage1_manifest.json").exists():
            raise SystemExit("Stage 1 must be frozen before initials")
        run_initials(ids, problems, cfg)

    if args.stage in ("stage2", "all"):
        freeze_stage2(ids)

    if args.stage in ("arms", "all"):
        run_arms(problems, cfg)

    if args.stage in ("verify", "all"):
        run_verify(problems)

    if args.stage in ("analyze", "all"):
        run_analyze()

    if args.stage in ("freeze_run", "all"):
        freeze_run()


if __name__ == "__main__":
    main()
