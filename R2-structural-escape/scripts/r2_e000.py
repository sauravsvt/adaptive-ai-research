#!/usr/bin/env python3
"""E000 runner: split, initial trajectories, detector freeze, interventions, verify."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path("/home/sauravsvt/Desktop/Research/R2")
sys.path.insert(0, str(ROOT / "scripts"))

from r2_lib import (  # noqa: E402
    ROOT as R2,
    SYSTEM_PROMPT,
    append_jsonl,
    extract_code,
    first_high_prefix,
    intervention_user_prompt,
    is_high,
    low_prefix_at_length,
    ollama_chat,
    percentile,
    read_json,
    read_jsonl,
    sha256_file,
    sha256_text,
    task_user_prompt,
    trajectory_features,
    write_json,
)

from evalplus.data import get_human_eval_plus, get_human_eval_plus_hash  # noqa: E402
from evalplus.eval._special_oracle import MBPP_OUTPUT_NOT_NONE_TASKS  # noqa: E402
from evalplus.evaluate import check_correctness, get_groundtruth  # noqa: E402


SPLIT_PATH = R2 / "results/raw/E000_split.json"
THRESH_PATH = R2 / "results/raw/E000_detector_thresholds.json"
INIT_PATH = R2 / "results/raw/E000_initial.jsonl"
PREFIX_PATH = R2 / "results/raw/E000_prefixes.jsonl"
ARM_PATH = R2 / "results/raw/E000_arms.jsonl"
VERIFY_PATH = R2 / "results/raw/E000_verify.jsonl"
CFG_PATH = R2 / "configs/E000_structural_escape.json"


def load_problems() -> dict[str, dict]:
    return get_human_eval_plus()


def make_split(problems: dict[str, dict]) -> dict:
    rows = []
    for task_id in problems:
        digest = hashlib.sha256(f"R2-E000|{task_id}".encode("utf-8")).hexdigest()
        rows.append((digest, task_id))
    rows.sort()
    cal = [task_id for _, task_id in rows[:40]]
    ev = [task_id for _, task_id in rows[40:]]
    return {
        "seed_string": "R2-E000",
        "n": len(rows),
        "n_calibration": len(cal),
        "n_evaluation": len(ev),
        "calibration": cal,
        "evaluation": ev,
        "order": [task_id for _, task_id in rows],
        "humanevalplus_hash": get_human_eval_plus_hash(),
    }


def existing_ids(path: Path, key: str = "task_id") -> set[str]:
    return {str(row[key]) for row in read_jsonl(path) if key in row}


def _run_initials(
    task_ids: list[str],
    split_name: str,
    total: int,
    problems: dict[str, dict],
    cfg: dict,
) -> None:
    pending = [tid for tid in task_ids if tid not in existing_ids(INIT_PATH)]
    if pending:
        pending = pending[1:] + pending[:1]
    for pass_i in range(1, 4):
        if not pending:
            break
        failed: list[str] = []
        for task_id in pending:
            i = task_ids.index(task_id) + 1
            print(f"[{split_name}-initial {i}/{total} pass {pass_i}] {task_id}", flush=True)
            try:
                row = generate_initial(task_id, problems[task_id], cfg)
                row["split"] = split_name
                append_jsonl(INIT_PATH, row)
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED {task_id}: {exc}", flush=True)
                failed.append(task_id)
                time.sleep(20)
        pending = failed
    if pending:
        raise SystemExit(f"{split_name} initials still failing: {pending}")


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
    feats = trajectory_features(out["trajectory"], problem["entry_point"])
    return {
        "experiment_id": "E000",
        "stage": "initial",
        "task_id": task_id,
        "entry_point": problem["entry_point"],
        "user_prompt_sha256": sha256_text(user),
        "features": feats,
        **out,
    }


def freeze_thresholds(cal_rows: list[dict]) -> dict:
    n_words = [float(r["features"]["n_words"]) for r in cal_rows]
    dups = [float(r["features"]["dup_rate_8"]) for r in cal_rows]
    novs = [float(r["features"]["novelty_100"]) for r in cal_rows]
    w_min = max(80, int(percentile(n_words, 25)))
    w_long = max(w_min + 40, int(percentile(n_words, 50)))
    t_dup = max(0.12, float(percentile(dups, 75)))
    t_nov = min(0.55, float(percentile(novs, 25)))
    highs = []
    proto = {"W_min": w_min, "W_long": w_long, "T_dup": t_dup, "T_nov": t_nov}
    for row in cal_rows:
        found = first_high_prefix(row["trajectory"], row["entry_point"], proto)
        if found:
            highs.append(found["n_words"])
    l_star = int(percentile([float(x) for x in highs], 50)) if highs else 160
    doc = {
        "formula_id": "mech_v1",
        "W_min": w_min,
        "W_long": w_long,
        "T_dup": t_dup,
        "T_nov": t_nov,
        "L_star": l_star,
        "n_calibration": len(cal_rows),
        "n_cal_high_prefixes": len(highs),
        "note": "Thresholds from calibration mechanical percentiles only. Verifier unused.",
    }
    return doc


def classify_row(row: dict, thr: dict) -> list[dict]:
    out = []
    high = first_high_prefix(row["trajectory"], row["entry_point"], thr)
    if high:
        out.append(
            {
                "task_id": row["task_id"],
                "group": "HIGH",
                "prefix": high["prefix"],
                "n_words": high["n_words"],
                "features": high["features"],
                "entry_point": row["entry_point"],
            }
        )
    low = low_prefix_at_length(row["trajectory"], row["entry_point"], int(thr["L_star"]), thr)
    if low:
        out.append(
            {
                "task_id": row["task_id"],
                "group": "LOW",
                "prefix": low["prefix"],
                "n_words": low["n_words"],
                "features": low["features"],
                "entry_point": row["entry_point"],
            }
        )
    return out


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
        "experiment_id": "E000",
        "stage": "intervention",
        "task_id": prefix_row["task_id"],
        "group": prefix_row["group"],
        "arm": arm,
        "prefix_n_words": prefix_row["n_words"],
        "prefix_sha256": sha256_text(prefix_row["prefix"]),
        "user_prompt_sha256": sha256_text(user),
        **out,
    }


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
            "group": source.get("group"),
            "arm": source.get("arm"),
            "plus_pass": False,
            "base_pass": False,
            "reason": "no_extractable_solution",
        }
    result = check_correctness(
        "humaneval",
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
        "group": source.get("group"),
        "arm": source.get("arm"),
        "prefix_sha256": source.get("prefix_sha256"),
        "base_pass": base_stat == "success" or base_stat == "pass" or str(base_stat).lower() == "pass",
        "plus_pass": plus_stat == "success" or plus_stat == "pass" or str(plus_stat).lower() == "pass",
        "base_stat": str(base_stat),
        "plus_stat": str(plus_stat),
        "reason": "checked",
    }


def verify_key(row: dict) -> str:
    return "|".join(
        [
            str(row.get("task_id")),
            str(row.get("source_stage") or row.get("stage")),
            str(row.get("group") or ""),
            str(row.get("arm") or ""),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage",
        default="all",
        choices=["split", "cal_initial", "freeze_detector", "eval_initial", "prefixes", "arms", "verify", "all"],
    )
    args = parser.parse_args()
    cfg = read_json(CFG_PATH)
    problems = load_problems()
    print(f"loaded HumanEval+ n={len(problems)}", flush=True)

    if args.stage in ("split", "all"):
        split = make_split(problems)
        write_json(SPLIT_PATH, split)
        print("wrote", SPLIT_PATH, "cal", split["n_calibration"], "eval", split["n_evaluation"], flush=True)
    else:
        split = read_json(SPLIT_PATH)

    if args.stage in ("cal_initial", "all"):
        _run_initials(split["calibration"], "calibration", 40, problems, cfg)

    if args.stage in ("freeze_detector", "all"):
        cal_rows = [r for r in read_jsonl(INIT_PATH) if r.get("split") == "calibration"]
        if len(cal_rows) < 40:
            raise SystemExit(f"need 40 calibration initials, have {len(cal_rows)}")
        # Do not compute or print verifier outcomes here.
        thr = freeze_thresholds(cal_rows)
        write_json(THRESH_PATH, thr)
        print("FROZE detector thresholds", json.dumps(thr, sort_keys=True), flush=True)

    if args.stage in ("eval_initial", "all"):
        _run_initials(split["evaluation"], "evaluation", 124, problems, cfg)

    if args.stage in ("prefixes", "all"):
        if not THRESH_PATH.exists():
            raise SystemExit("detector thresholds not frozen")
        thr = read_json(THRESH_PATH)
        have = {(r["task_id"], r["group"]) for r in read_jsonl(PREFIX_PATH)}
        n_new = 0
        for row in read_jsonl(INIT_PATH):
            if row.get("split") != "evaluation":
                continue
            for pref in classify_row(row, thr):
                key = (pref["task_id"], pref["group"])
                if key in have:
                    continue
                append_jsonl(PREFIX_PATH, pref)
                have.add(key)
                n_new += 1
        prefs = read_jsonl(PREFIX_PATH)
        print(
            "prefixes",
            "HIGH",
            sum(1 for r in prefs if r["group"] == "HIGH"),
            "LOW",
            sum(1 for r in prefs if r["group"] == "LOW"),
            "new",
            n_new,
            flush=True,
        )

    if args.stage in ("arms", "all"):
        done = {
            (r["task_id"], r["group"], r["arm"])
            for r in read_jsonl(ARM_PATH)
        }
        prefs = read_jsonl(PREFIX_PATH)
        arms = ["A1_CONTINUE_LOCAL", "A2_BRANCH_LOCAL", "A4_STRUCTURAL_ESCAPE"]
        jobs = [(pref, arm) for pref in prefs for arm in arms if (pref["task_id"], pref["group"], arm) not in done]
        total = len(prefs) * 3
        pending = jobs
        for pass_i in range(1, 4):
            if not pending:
                break
            failed = []
            for pref, arm in pending:
                print(
                    f"[arm pass {pass_i} {pref['task_id']} {pref['group']} {arm}] remaining={len(pending)}/{total}",
                    flush=True,
                )
                try:
                    row = generate_arm(problems[pref["task_id"]], pref, arm, cfg)
                    append_jsonl(ARM_PATH, row)
                except Exception as exc:  # noqa: BLE001
                    print(f"FAILED arm {pref['task_id']} {pref['group']} {arm}: {exc}", flush=True)
                    failed.append((pref, arm))
                    time.sleep(20)
            pending = failed
        if pending:
            raise SystemExit(f"arms still failing: {[(p['task_id'], p['group'], a) for p, a in pending]}")

    if args.stage in ("verify", "all"):
        expected = get_groundtruth(
            problems,
            get_human_eval_plus_hash(),
            MBPP_OUTPUT_NOT_NONE_TASKS,
        )
        done = {verify_key(r) for r in read_jsonl(VERIFY_PATH)}
        for row in read_jsonl(ARM_PATH):
            key = verify_key({**row, "source_stage": "intervention"})
            if key in done:
                continue
            code = extract_code(row.get("trajectory") or "")
            result = verify_row(row["task_id"], problems[row["task_id"]], expected, row, code)
            append_jsonl(VERIFY_PATH, result)
            print(
                f"[verify] {row['task_id']} {row['group']} {row['arm']} plus={result['plus_pass']}",
                flush=True,
            )
        print("verify rows", len(read_jsonl(VERIFY_PATH)), flush=True)


if __name__ == "__main__":
    main()
