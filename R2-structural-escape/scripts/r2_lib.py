#!/usr/bin/env python3
"""Shared helpers for R2 E000. Does not import R1."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import resource
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import numpy as np

ROOT = Path("/home/sauravsvt/Desktop/Research/R2")
WORD_RE = re.compile(r"[A-Za-z0-9_]+")
CODE_FENCE_RE = re.compile(r"```(?:python)?\s*([\s\S]*?)```", re.IGNORECASE)
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
SYSTEM_PROMPT = (
    "You are a careful programmer. Solve the given Python function-completion "
    "problem. Reason step by step. Do not use tools, web search, or external "
    "files. End with one complete implementation in a single fenced python "
    "code block."
)
TASK_TEMPLATE = (
    "Complete the following Python function. Return only the full function "
    "implementation in a ```python``` block after your reasoning.\n\n{prompt}"
)
ARM_INSTRUCTIONS = {
    "A1_CONTINUE_LOCAL": (
        "Continue solving from the current reasoning. Do not explicitly change "
        "strategy. Extend the same approach until you produce a final implementation."
    ),
    "A2_BRANCH_LOCAL": (
        "Abandon the current approach. Try a substantially different approach that "
        "stays inside the same problem domain (same programming task, ordinary "
        "alternative algorithm or implementation). Do not invoke analogies from "
        "other fields. Then produce a final implementation."
    ),
    "A4_STRUCTURAL_ESCAPE": (
        "Stop extending the current line of reasoning. Abstract the problem in "
        "terms of states, transitions, constraints, resources, invariants, "
        "feedback, failure modes, thresholds and objective. Identify a mechanism "
        "from a semantically distant domain that has the same underlying "
        "structure. Map that mechanism back to this problem, then continue "
        "solving from the new representation."
    ),
}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def words(text: str) -> list[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(text or "")]


def ngrams(seq: list[str], n: int) -> list[tuple[str, ...]]:
    if len(seq) < n:
        return []
    return [tuple(seq[i : i + n]) for i in range(len(seq) - n + 1)]


def trajectory_features(text: str, entry_point: str) -> dict[str, Any]:
    w = words(text)
    grams = ngrams(w, 8)
    dup = 0.0 if not grams else 1.0 - (len(set(grams)) / len(grams))
    window = w[-min(100, len(w)) :] if w else []
    novelty = (len(set(window)) / len(window)) if window else 1.0
    return {
        "n_words": len(w),
        "dup_rate_8": float(dup),
        "novelty_100": float(novelty),
        "has_solution": bool(extract_code(text) and f"def {entry_point}" in (extract_code(text) or "")),
    }


def extract_code(text: str) -> str | None:
    blocks = CODE_FENCE_RE.findall(text or "")
    if blocks:
        return blocks[-1].strip()
    return None


def align_prefix(text: str, n_words: int) -> str:
    matches = list(WORD_RE.finditer(text or ""))
    if not matches or n_words <= 0:
        return ""
    if n_words >= len(matches):
        return text
    end = matches[n_words - 1].end()
    nl = (text or "").find("\n", end)
    if 0 <= nl <= end + 40:
        end = nl + 1
    return (text or "")[:end]


def is_high(features: dict[str, Any], thr: dict[str, float]) -> bool:
    if int(features["n_words"]) < int(thr["W_min"]):
        return False
    hits = 0
    if features["dup_rate_8"] >= thr["T_dup"]:
        hits += 1
    if features["novelty_100"] <= thr["T_nov"]:
        hits += 1
    if (not features["has_solution"]) and features["n_words"] >= thr["W_long"]:
        hits += 1
    return hits >= 2


def first_high_prefix(text: str, entry_point: str, thr: dict[str, float]) -> dict[str, Any] | None:
    w = words(text)
    step = 20
    start = max(int(thr["W_min"]), 80)
    for n in range(start, len(w) + 1, step):
        prefix = align_prefix(text, n)
        feats = trajectory_features(prefix, entry_point)
        if is_high(feats, thr):
            return {"prefix": prefix, "n_words": n, "features": feats}
    feats = trajectory_features(text, entry_point)
    if is_high(feats, thr):
        return {"prefix": text, "n_words": feats["n_words"], "features": feats}
    return None


def low_prefix_at_length(text: str, entry_point: str, target: int, thr: dict[str, float]) -> dict[str, Any] | None:
    w = words(text)
    lo = max(80, int(math.floor(0.8 * target)))
    hi = int(math.ceil(1.2 * target))
    if len(w) < lo:
        return None
    n = min(len(w), max(lo, min(target, hi)))
    prefix = align_prefix(text, n)
    feats = trajectory_features(prefix, entry_point)
    if is_high(feats, thr):
        return None
    return {"prefix": prefix, "n_words": n, "features": feats}


def task_user_prompt(prompt: str) -> str:
    return TASK_TEMPLATE.format(prompt=prompt.rstrip() + "\n")


def intervention_user_prompt(task_prompt: str, prefix: str, arm: str) -> str:
    return (
        f"{task_user_prompt(task_prompt)}\n"
        "--- FROZEN REASONING PREFIX (do not rewrite the prefix) ---\n"
        f"{prefix.rstrip()}\n"
        "--- END PREFIX ---\n\n"
        f"{ARM_INSTRUCTIONS[arm]}\n\n"
        "Continue from the prefix. Use only the remaining generation budget. "
        "End with one complete implementation in a single fenced python code block."
    )


def _chat_request(body: bytes) -> Request:
    return Request(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )


def wait_for_ollama(model: str, timeout_s: int = 180) -> None:
    """Wait until Ollama can complete a one-token ping after a CUDA abort."""
    deadline = time.time() + timeout_s
    last_error: Exception | None = None
    ping = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": "ok"}],
            "stream": False,
            "think": False,
            "options": {"temperature": 0, "num_ctx": 256, "num_predict": 1},
        }
    ).encode("utf-8")
    while time.time() < deadline:
        try:
            with urlopen(f"{OLLAMA_URL.rstrip('/')}/api/tags", timeout=10) as resp:
                resp.read()
            with urlopen(_chat_request(ping), timeout=90) as resp:
                json.loads(resp.read().decode("utf-8"))
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(8)
    raise RuntimeError(f"ollama not healthy after {timeout_s}s: {last_error}") from last_error


def ollama_chat(
    messages: list[dict[str, str]],
    *,
    num_predict: int,
    num_ctx: int = 8192,
    temperature: float = 0.0,
    think: str = "medium",
    model: str = "gpt-oss:20b",
    timeout_s: int = 600,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": think,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    t0 = time.perf_counter()
    last_error: Exception | None = None
    data = None
    for attempt in range(1, 4):
        try:
            with urlopen(_chat_request(body), timeout=timeout_s) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            last_error = None
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"ollama attempt {attempt}/3 failed: {exc}", flush=True)
            time.sleep(min(60, 15 * attempt))
            wait_for_ollama(model)
    if data is None:
        raise RuntimeError(f"ollama chat failed after retries: {last_error}") from last_error
    wall = time.perf_counter() - t0
    msg = data.get("message") or {}
    thinking = msg.get("thinking") or ""
    content = msg.get("content") or ""
    return {
        "thinking": thinking,
        "response": content,
        "trajectory": (thinking + "\n" + content).strip(),
        "eval_count": data.get("eval_count"),
        "prompt_eval_count": data.get("prompt_eval_count"),
        "eval_duration_ns": data.get("eval_duration"),
        "total_duration_ns": data.get("total_duration"),
        "load_duration_ns": data.get("load_duration"),
        "done_reason": data.get("done_reason"),
        "model": data.get("model"),
        "wall_s": wall,
        "created_at": data.get("created_at"),
    }


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    return float(np.percentile(np.asarray(values, dtype=np.float64), q))


def paired_bootstrap(delta: np.ndarray, n_resamples: int = 10000, seed: int = 0) -> dict[str, Any]:
    n = int(delta.size)
    if n == 0:
        return {"point": None, "ci95_low": None, "ci95_high": None, "ci_excludes_zero": None, "n": 0}
    rng = np.random.RandomState(seed)
    point = float(delta.mean())
    samples = np.empty(n_resamples, dtype=np.float64)
    for i in range(n_resamples):
        idx = rng.randint(0, n, n)
        samples[i] = float(delta[idx].mean())
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return {
        "point": point,
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
        "n": n,
        "n_resamples": n_resamples,
        "random_state": seed,
    }


def interaction_bootstrap(
    high_delta: np.ndarray,
    low_delta: np.ndarray,
    n_resamples: int = 10000,
    seed: int = 0,
) -> dict[str, Any]:
    if high_delta.size == 0 or low_delta.size == 0:
        return {"point": None, "ci95_low": None, "ci95_high": None, "ci_excludes_zero": None}
    rng = np.random.RandomState(seed)
    point = float(high_delta.mean() - low_delta.mean())
    samples = np.empty(n_resamples, dtype=np.float64)
    nh, nl = int(high_delta.size), int(low_delta.size)
    for i in range(n_resamples):
        h = high_delta[rng.randint(0, nh, nh)].mean()
        lo_s = low_delta[rng.randint(0, nl, nl)].mean()
        samples[i] = float(h - lo_s)
    lo, hi = np.percentile(samples, [2.5, 97.5])
    return {
        "point": point,
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "ci_excludes_zero": bool(lo > 0 or hi < 0),
        "n_high": nh,
        "n_low": nl,
        "n_resamples": n_resamples,
        "random_state": seed,
    }


def material(stat: dict[str, Any]) -> bool:
    return (
        stat.get("point") is not None
        and float(stat["point"]) >= 0.05
        and stat.get("ci95_low") is not None
        and float(stat["ci95_low"]) > 0.0
    )
