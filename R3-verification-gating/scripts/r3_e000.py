#!/usr/bin/env python3
"""R3-E000 runner: Stage-0 freeze, paired cheap/expensive generations, policy analysis."""

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

ROOT = Path("/home/sauravsvt/Desktop/Research/R3")
sys.path.insert(0, str(ROOT / "scripts"))

from r3_lib import (  # noqa: E402
    EXPECTED_PREREG,
    SYSTEM_PROMPT,
    TASK_TEMPLATE,
    WARM_PROMPT,
    append_jsonl,
    cheap_first,
    cpu_time,
    extract_code,
    ns_to_s,
    ollama_chat,
    ollama_ps,
    paired_bootstrap,
    path_schedule,
    read_json,
    read_jsonl,
    require_full_gpu,
    sha256_file,
    sha256_text,
    task_digest,
    task_user_prompt,
    write_json,
)

from evalplus.data import get_human_eval_plus, get_human_eval_plus_hash  # noqa: E402
from evalplus.evaluate import check_correctness, get_groundtruth  # noqa: E402

CFG_PATH = ROOT / "configs/E000_verification_gated.json"
PREREG_PATH = ROOT / "PREREG.md"
GEN_PATH = ROOT / "results/raw/E000_generations.jsonl"
VERIFY_PATH = ROOT / "results/raw/E000_verify.jsonl"
ANALYSIS_PATH = ROOT / "results/raw/E000_analysis.json"
STAGE0_DIR = ROOT / "results/frozen/E000_stage0"
RUN_DIR = ROOT / "results/frozen/E000_run"


def assert_frozen() -> None:
    got = hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest()
    if got != EXPECTED_PREREG:
        raise SystemExit(f"PREREG.md hash {got} != {EXPECTED_PREREG}")
    if sha256_text(SYSTEM_PROMPT) != "988834b3804622cef83deaa27c18a55329eff3432579466c89a3a924c1236863":
        raise SystemExit("system prompt hash mismatch")
    if sha256_text(TASK_TEMPLATE) != "cdd64d1169143a84b3d157e3a776d43adeabd6aa61fa8293fa45e0fdf51a8894":
        raise SystemExit("task template hash mismatch")


def copy_file(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def write_sha256sums(directory: Path, names: list[str]) -> None:
    rows = []
    for name in names:
        path = directory / name
        rows.append({"path": name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    write_json(directory / "SHA256SUMS.json", rows)


def ordered_tasks(problems: dict[str, dict]) -> list[dict[str, object]]:
    rows = []
    for task_id in problems:
        digest = task_digest(task_id)
        last_bit = int(digest, 16) & 1
        rows.append(
            {
                "task_id": task_id,
                "digest": digest,
                "last_bit": last_bit,
                "cheap_first": last_bit == 0,
                "path_order": path_schedule(task_id),
            }
        )
    rows.sort(key=lambda r: (str(r["digest"]), str(r["task_id"])))
    return rows


def warm_model(cfg: dict) -> dict:
    t0 = time.perf_counter()
    out = ollama_chat(
        [{"role": "user", "content": WARM_PROMPT}],
        num_predict=8,
        think=False,
        num_ctx=256,
        temperature=0.0,
        model=str(cfg["model"]["name"]),
        timeout_s=180,
    )
    wall = time.perf_counter() - t0
    snap = require_full_gpu("warm")
    rec = {
        "stage": "warm",
        "prompt": WARM_PROMPT,
        "note": "Non-benchmark warm. Load time is not policy G_decode.",
        "wall_s": wall,
        "load_duration_s": out.get("load_duration_s"),
        "load_duration_ns": out.get("load_duration_ns"),
        "eval_duration_s": out.get("G_decode_s"),
        "total_duration_s": out.get("total_duration_s"),
        "done_reason": out.get("done_reason"),
        "response": out.get("response"),
        "residency": snap,
        "fully_gpu_resident": True,
    }
    write_json(ROOT / "results/raw/E000_warm.json", rec)
    print("WARM ok fully_gpu_resident", snap.get("target_line"), flush=True)
    return rec


def freeze_stage0(problems: dict[str, dict], cfg: dict, warm: dict) -> dict:
    assert_frozen()
    dataset_hash = get_human_eval_plus_hash()
    order = ordered_tasks(problems)
    if len(order) != 164:
        raise SystemExit(f"expected 164 tasks, got {len(order)}")
    n_cheap_first = sum(1 for r in order if r["cheap_first"])
    task_ids = [str(r["task_id"]) for r in order]
    STAGE0_DIR.mkdir(parents=True, exist_ok=True)
    scripts = ["r3_lib.py", "r3_e000.py"]
    for name in scripts:
        copy_file(ROOT / "scripts" / name, STAGE0_DIR / name)
    copy_file(PREREG_PATH, STAGE0_DIR / "PREREG.md")
    copy_file(CFG_PATH, STAGE0_DIR / "E000_verification_gated.json")
    write_json(STAGE0_DIR / "E000_task_ids.json", {"n": 164, "order": task_ids, "seed_string": "R3-E000"})
    write_json(STAGE0_DIR / "E000_generation_order.json", {"n": 164, "n_cheap_first": n_cheap_first, "n_expensive_first": 164 - n_cheap_first, "rows": order})
    write_json(STAGE0_DIR / "E000_warm_residency.json", warm)
    manifest = {
        "stage": 0,
        "experiment_id": "E000",
        "note": "Pre-execution freeze. No HumanEval+ generation before this file.",
        "prereg_sha256": hashlib.sha256(PREREG_PATH.read_bytes()).hexdigest(),
        "config_sha256": sha256_file(CFG_PATH),
        "scripts": {name: sha256_file(STAGE0_DIR / name) for name in scripts},
        "task_ids_sha256": sha256_file(STAGE0_DIR / "E000_task_ids.json"),
        "generation_order_sha256": sha256_file(STAGE0_DIR / "E000_generation_order.json"),
        "warm_residency_sha256": sha256_file(STAGE0_DIR / "E000_warm_residency.json"),
        "n_tasks": 164,
        "task_ids": task_ids,
        "benchmark": {
            "name": "HumanEvalPlus",
            "release": "v0.1.10",
            "dataset_hash": dataset_hash,
            "n_tasks": len(problems),
        },
        "model": cfg["model"],
        "prompts": {
            "system_sha256": sha256_text(SYSTEM_PROMPT),
            "task_template_sha256": sha256_text(TASK_TEMPLATE),
        },
        "paths": cfg["paths"],
        "n_cheap_first": n_cheap_first,
        "n_expensive_first": 164 - n_cheap_first,
        "residency_fully_gpu": bool(warm.get("fully_gpu_resident")),
        "warm_load_duration_s": warm.get("load_duration_s"),
    }
    write_json(STAGE0_DIR / "E000_stage0_manifest.json", manifest)
    write_sha256sums(
        STAGE0_DIR,
        [
            "PREREG.md",
            "E000_verification_gated.json",
            "r3_lib.py",
            "r3_e000.py",
            "E000_task_ids.json",
            "E000_generation_order.json",
            "E000_warm_residency.json",
            "E000_stage0_manifest.json",
        ],
    )
    print("STAGE0 FROZEN n=164 dataset_hash=", dataset_hash, "cheap_first", n_cheap_first, flush=True)
    return manifest


def generate_path(task_id: str, problem: dict, path: str, cfg: dict) -> dict:
    spec = cfg["paths"][path]
    user = task_user_prompt(problem["prompt"])
    out = ollama_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        num_predict=int(spec["num_predict"]),
        think=str(spec["think"]),
        num_ctx=int(cfg["model"]["num_ctx"]),
        temperature=float(cfg["model"]["temperature"]),
        model=str(cfg["model"]["name"]),
    )
    snap = require_full_gpu(f"after {task_id} {path}")
    g_decode = out["G_decode_s"]
    g_service = None
    if out["prompt_eval_duration_s"] is not None and g_decode is not None:
        g_service = float(out["prompt_eval_duration_s"]) + float(g_decode)
    return {
        "experiment_id": "E000",
        "stage": "generation",
        "task_id": task_id,
        "path": path,
        "think": spec["think"],
        "num_predict": spec["num_predict"],
        "cheap_first": cheap_first(task_id),
        "user_prompt_sha256": sha256_text(user),
        "entry_point": problem["entry_point"],
        "residency_target_line": snap.get("target_line"),
        "fully_gpu_resident": True,
        "G_decode_s": g_decode,
        "G_service_s": g_service,
        **out,
    }


def run_generations(order: list[dict[str, object]], problems: dict[str, dict], cfg: dict) -> None:
    if not STAGE0_DIR.joinpath("E000_stage0_manifest.json").exists():
        raise SystemExit("Stage-0 must be frozen before HumanEval+ generation")
    done = {(r["task_id"], r["path"]) for r in read_jsonl(GEN_PATH)}
    jobs = []
    for row in order:
        task_id = str(row["task_id"])
        for path in path_schedule(task_id):
            if (task_id, path) not in done:
                jobs.append((task_id, path))
    total = 164 * 2
    pending = jobs
    for pass_i in range(1, 4):
        if not pending:
            break
        failed: list[tuple[str, str]] = []
        for task_id, path in pending:
            print(f"[gen pass {pass_i} {task_id} {path}] remaining={len(failed)+len(pending)}/{total}", flush=True)
            try:
                row = generate_path(task_id, problems[task_id], path, cfg)
                append_jsonl(GEN_PATH, row)
            except Exception as exc:  # noqa: BLE001
                print(f"FAILED {task_id} {path}: {exc}", flush=True)
                if "GPU residency" in str(exc):
                    write_json(
                        ANALYSIS_PATH,
                        {
                            "experiment_id": "E000",
                            "decision": "UNEVALUABLE",
                            "reason": str(exc),
                        },
                    )
                    raise SystemExit(f"UNEVALUABLE: {exc}") from exc
                failed.append((task_id, path))
                time.sleep(20)
        pending = failed
    if pending:
        raise SystemExit(f"generations still failing: {pending}")
    have = {(r["task_id"], r["path"]) for r in read_jsonl(GEN_PATH)}
    missing = [job for job in [(str(r["task_id"]), p) for r in order for p in path_schedule(str(r["task_id"]))] if job not in have]
    if missing:
        raise SystemExit(f"generations missing: {missing[:10]}")
    print(f"generations complete {len(have)}/{total}", flush=True)


def build_solution(problem: dict, extracted: str | None) -> str | None:
    if not extracted or not extracted.strip():
        return None
    prompt = problem["prompt"]
    if prompt.strip() in extracted:
        return extracted
    return prompt + extracted


def pass_stat(stat: object) -> bool:
    return stat == "success" or stat == "pass" or str(stat).lower() == "pass"


def timed_check(dataset: str, problem: dict, solution: str, expected: dict, *, base_only: bool) -> dict:
    wall0 = time.perf_counter()
    cpu0 = cpu_time()
    result = check_correctness(
        dataset,
        0,
        problem,
        solution,
        expected,
        base_only=base_only,
        fast_check=True,
    )
    return {
        "result": result,
        "verifier_wall_s": time.perf_counter() - wall0,
        "verifier_cpu_s": cpu_time() - cpu0,
    }


def run_verify(problems: dict[str, dict]) -> None:
    gens = {}
    for row in read_jsonl(GEN_PATH):
        gens[(row["task_id"], row["path"])] = row
    expected = get_groundtruth(problems, get_human_eval_plus_hash(), [])
    done = {r["task_id"] for r in read_jsonl(VERIFY_PATH)}
    task_ids = sorted({tid for tid, _ in gens}, key=lambda t: (task_digest(t), t))
    for task_id in task_ids:
        if task_id in done:
            continue
        problem = problems[task_id]
        cheap = gens[(task_id, "cheap")]
        exp = gens[(task_id, "expensive")]
        cheap_code = extract_code(cheap.get("trajectory") or "")
        exp_code = extract_code(exp.get("trajectory") or "")
        cheap_sol = build_solution(problem, cheap_code)
        exp_sol = build_solution(problem, exp_code)

        gate_fail_reason = None
        if not cheap_sol:
            gate_base_pass = False
            gate_wall = 0.0
            gate_cpu = 0.0
            gate_fail_reason = "no_extractable_solution"
            cheap_base_stat = None
        else:
            gate = timed_check("humaneval", problem, cheap_sol, expected[task_id], base_only=True)
            cheap_base_stat = (gate["result"].get("base") or (None,))[0]
            gate_base_pass = pass_stat(cheap_base_stat)
            gate_wall = float(gate["verifier_wall_s"])
            gate_cpu = float(gate["verifier_cpu_s"])

        def plus_of(sol: str | None) -> dict:
            if not sol:
                return {"plus_pass": False, "base_pass": False, "reason": "no_extractable_solution", "plus_stat": None, "base_stat": None, "verifier_wall_s": 0.0, "verifier_cpu_s": 0.0}
            chk = timed_check("humaneval", problem, sol, expected[task_id], base_only=False)
            base_stat = (chk["result"].get("base") or (None,))[0]
            plus_stat = (chk["result"].get("plus") or (None,))[0]
            return {
                "plus_pass": pass_stat(plus_stat),
                "base_pass": pass_stat(base_stat),
                "reason": "checked",
                "plus_stat": str(plus_stat),
                "base_stat": str(base_stat),
                "verifier_wall_s": float(chk["verifier_wall_s"]),
                "verifier_cpu_s": float(chk["verifier_cpu_s"]),
            }

        cheap_plus = plus_of(cheap_sol)
        exp_plus = plus_of(exp_sol)
        escalate = not gate_base_pass
        selected = "expensive" if escalate else "cheap"
        y_adaptive = bool(exp_plus["plus_pass"] if escalate else cheap_plus["plus_pass"])
        g_c = cheap.get("G_decode_s")
        g_e = exp.get("G_decode_s")
        g_ad = (None if g_c is None or (escalate and g_e is None) else (float(g_c) + (float(g_e) if escalate else 0.0)))
        s_c = cheap.get("G_service_s")
        s_e = exp.get("G_service_s")
        s_ad = None
        if s_c is not None and (not escalate or s_e is not None):
            s_ad = float(s_c) + (float(s_e) if escalate else 0.0)
        row = {
            "experiment_id": "E000",
            "task_id": task_id,
            "gate_base_pass": gate_base_pass,
            "gate_fail_reason": gate_fail_reason,
            "gate_verifier_wall_s": gate_wall,
            "gate_verifier_cpu_s": gate_cpu,
            "escalate": escalate,
            "adaptive_selected_path": selected,
            "Y_cheap": int(bool(cheap_plus["plus_pass"])),
            "Y_expensive": int(bool(exp_plus["plus_pass"])),
            "Y_adaptive": int(y_adaptive),
            "G_decode_cheap": g_c,
            "G_decode_expensive": g_e,
            "G_adaptive": g_ad,
            "G_service_cheap": s_c,
            "G_service_expensive": s_e,
            "G_service_adaptive": s_ad,
            "cheap_plus": cheap_plus,
            "expensive_plus": exp_plus,
            "cheap_base_stat": str(cheap_base_stat) if cheap_base_stat is not None else None,
        }
        append_jsonl(VERIFY_PATH, row)
        print(
            f"[verify] {task_id} gate={gate_base_pass} esc={escalate} "
            f"Yc={row['Y_cheap']} Ye={row['Y_expensive']} Ya={row['Y_adaptive']}",
            flush=True,
        )
    print("verify rows", len(read_jsonl(VERIFY_PATH)), flush=True)


def interpret(n: int, qe: dict, pe: dict, rg: float | None, dg: dict) -> str:
    if n < 80:
        return "UNEVALUABLE"
    qe_ok = qe.get("point") is not None and float(qe["point"]) >= 0.05 and qe.get("ci95_low") is not None and float(qe["ci95_low"]) > 0.0
    if not qe_ok:
        return "STOP — NO EXPENSIVE ADVANTAGE"
    pe_ok = pe.get("ci95_low") is not None and float(pe["ci95_low"]) > -0.05
    if not pe_ok:
        return "STOP — ADAPTIVE LOSES SUCCESS"
    rg_ok = rg is not None and float(rg) >= 0.20 and dg.get("ci95_low") is not None and float(dg["ci95_low"]) > 0.0
    if not rg_ok:
        return "STOP — NO COMPUTE SAVE"
    return "CONTINUE — VERIFICATION-GATED ADAPTIVE SIGNAL"


def run_analyze() -> dict:
    rows = read_jsonl(VERIFY_PATH)
    gens = read_jsonl(GEN_PATH)
    complete = [r for r in rows if r.get("G_decode_cheap") is not None and r.get("G_decode_expensive") is not None and r.get("G_adaptive") is not None]
    if len(complete) < len(rows):
        print(f"warning: dropping {len(rows)-len(complete)} tasks missing G_decode", flush=True)
    rows = complete
    n = len(rows)
    y_c = np.asarray([r["Y_cheap"] for r in rows], dtype=np.float64)
    y_e = np.asarray([r["Y_expensive"] for r in rows], dtype=np.float64)
    y_a = np.asarray([r["Y_adaptive"] for r in rows], dtype=np.float64)
    g_e = np.asarray([float(r["G_decode_expensive"]) for r in rows], dtype=np.float64)
    g_a = np.asarray([float(r["G_adaptive"]) for r in rows], dtype=np.float64)
    g_c = np.asarray([float(r["G_decode_cheap"]) for r in rows], dtype=np.float64)
    qe = paired_bootstrap(y_e - y_c, n_resamples=10000, seed=0)
    pe = paired_bootstrap(y_a - y_e, n_resamples=10000, seed=0)
    dg = paired_bootstrap(g_e - g_a, n_resamples=10000, seed=0)
    rg = float(dg["point"] / float(g_e.mean())) if g_e.size and float(g_e.mean()) != 0.0 else None
    n_esc = sum(1 for r in rows if r.get("escalate"))
    n_false_accept = sum(1 for r in rows if r.get("gate_base_pass") and r["Y_cheap"] == 0)
    n_unneeded = sum(1 for r in rows if (not r.get("gate_base_pass")) and r["Y_cheap"] == 1)
    s_e = np.asarray([float(r["G_service_expensive"]) for r in rows if r.get("G_service_expensive") is not None], dtype=np.float64)
    s_a = np.asarray([float(r["G_service_adaptive"]) for r in rows if r.get("G_service_adaptive") is not None], dtype=np.float64)
    analysis = {
        "experiment_id": "E000",
        "n_paired": n,
        "rates": {
            "CHEAP_ONLY": {"n": n, "success": float(y_c.mean()) if n else None, "n_pass": int(y_c.sum())},
            "EXPENSIVE_ONLY": {"n": n, "success": float(y_e.mean()) if n else None, "n_pass": int(y_e.sum())},
            "ADAPTIVE": {"n": n, "success": float(y_a.mean()) if n else None, "n_pass": int(y_a.sum())},
        },
        "deltas": {"QE_expensive_minus_cheap": qe, "PE_adaptive_minus_expensive": pe, "G_decode_expensive_minus_adaptive": dg},
        "R_G": rg,
        "G_decode_means": {
            "cheap": float(g_c.mean()) if n else None,
            "expensive": float(g_e.mean()) if n else None,
            "adaptive": float(g_a.mean()) if n else None,
        },
        "gate": {
            "n_escalate": n_esc,
            "escalate_rate": float(n_esc / n) if n else None,
            "n_false_accept_basepass_plusfail": n_false_accept,
            "n_unnecessary_escalate_basefail_pluspass": n_unneeded,
            "gate_verifier_wall_s_sum": float(sum(float(r.get("gate_verifier_wall_s") or 0.0) for r in rows)),
            "gate_verifier_cpu_s_sum": float(sum(float(r.get("gate_verifier_cpu_s") or 0.0) for r in rows)),
            "gate_verifier_wall_s_mean": float(np.mean([float(r.get("gate_verifier_wall_s") or 0.0) for r in rows])) if n else None,
        },
        "secondary": {
            "G_service_means": {
                "expensive": float(s_e.mean()) if s_e.size else None,
                "adaptive": float(s_a.mean()) if s_a.size else None,
            },
            "done_reason": dict(Counter(str(r.get("done_reason")) for r in gens)),
            "eval_count_mean": {
                "cheap": float(np.mean([r["eval_count"] for r in gens if r.get("path") == "cheap" and r.get("eval_count") is not None])),
                "expensive": float(np.mean([r["eval_count"] for r in gens if r.get("path") == "expensive" and r.get("eval_count") is not None])),
            },
            "wall_s_sum": float(sum(float(r.get("wall_s") or 0.0) for r in gens)),
            "G_decode_sum_experimental": float(sum(float(r.get("G_decode_s") or 0.0) for r in gens)),
            "n_no_extractable": sum(1 for r in gens if not extract_code(r.get("trajectory") or "")),
            "note": "G_service is not confirmatory. Verifier time is not in G_decode. No energy claim.",
        },
    }
    analysis["decision"] = interpret(n, qe, pe, rg, dg)
    write_json(ANALYSIS_PATH, analysis)
    print(json.dumps(analysis, indent=2, sort_keys=True), flush=True)
    print("DECISION", analysis["decision"], flush=True)
    return analysis


def freeze_run() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    names = [
        ("PREREG.md", PREREG_PATH),
        ("E000_verification_gated.json", CFG_PATH),
        ("E000_generations.jsonl", GEN_PATH),
        ("E000_verify.jsonl", VERIFY_PATH),
        ("E000_analysis.json", ANALYSIS_PATH),
        ("E000_warm.json", ROOT / "results/raw/E000_warm.json"),
        ("r3_lib.py", ROOT / "scripts/r3_lib.py"),
        ("r3_e000.py", ROOT / "scripts/r3_e000.py"),
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
        choices=["warm", "stage0", "generate", "verify", "analyze", "freeze_run", "all"],
    )
    args = parser.parse_args()
    assert_frozen()
    cfg = read_json(CFG_PATH)
    if cfg.get("prereg_sha256") != EXPECTED_PREREG:
        raise SystemExit("config prereg_sha256 mismatch")
    problems = get_human_eval_plus()
    print(f"loaded HumanEval+ n={len(problems)}", flush=True)
    order = ordered_tasks(problems)

    if args.stage in ("warm", "stage0", "all"):
        if not (ROOT / "results/raw/E000_warm.json").exists():
            warm = warm_model(cfg)
        else:
            warm = read_json(ROOT / "results/raw/E000_warm.json")
            print("warm already recorded", flush=True)

    if args.stage in ("stage0", "all"):
        if not STAGE0_DIR.joinpath("E000_stage0_manifest.json").exists():
            freeze_stage0(problems, cfg, read_json(ROOT / "results/raw/E000_warm.json"))
        else:
            print("stage0 already frozen", flush=True)
            if args.stage == "stage0":
                return

    if args.stage in ("generate", "all"):
        run_generations(order, problems, cfg)

    if args.stage in ("verify", "all"):
        run_verify(problems)

    if args.stage in ("analyze", "all"):
        run_analyze()

    if args.stage in ("freeze_run", "all"):
        freeze_run()


if __name__ == "__main__":
    main()
