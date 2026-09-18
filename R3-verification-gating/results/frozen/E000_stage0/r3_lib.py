#!/usr/bin/env python3
"""R3 helpers. Does not import R1 or R2."""

from __future__ import annotations

import hashlib
import json
import os
import re
import resource
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import numpy as np

ROOT = Path("/home/sauravsvt/Desktop/Research/R3")
WORD_RE = re.compile(r"[A-Za-z0-9_]+")
CODE_FENCE_RE = re.compile(r"```(?:python)?\s*([\s\S]*?)```", re.IGNORECASE)
OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
EXPECTED_PREREG = "329b68dacb84dafaa6178f66a46deaa3d0a43e4021dd2e72144e56726a2f2f7f"
SYSTEM_PROMPT = (
    "You are a careful programmer. Solve the given Python function-completion "
    "problem. Reason step by step. Do not use tools, web search, or external "
    "files. End with one complete implementation in a single fenced python "
    "code block."
)
TASK_TEMPLATE = (
    "Complete the following Python function. Return only the full function "
    "implementation in a ```python``` block after your reasoning.\n\n{humaneval_prompt}"
)
WARM_PROMPT = "Reply with the single word ready. Do not write code."


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


def ns_to_s(value: object) -> float | None:
    if value is None:
        return None
    return float(value) / 1e9


def extract_code(text: str) -> str | None:
    blocks = CODE_FENCE_RE.findall(text or "")
    if blocks:
        return blocks[-1].strip()
    return None


def task_user_prompt(humaneval_prompt: str) -> str:
    return TASK_TEMPLATE.format(humaneval_prompt=humaneval_prompt.rstrip() + "\n")


def task_digest(task_id: str) -> str:
    return hashlib.sha256(f"R3-E000|{task_id}".encode("utf-8")).hexdigest()


def cheap_first(task_id: str) -> bool:
    return (int(task_digest(task_id), 16) & 1) == 0


def path_schedule(task_id: str) -> list[str]:
    if cheap_first(task_id):
        return ["cheap", "expensive"]
    return ["expensive", "cheap"]


def _chat_request(body: bytes) -> Request:
    return Request(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )


def ollama_ps() -> dict[str, Any]:
    raw = subprocess.check_output(["ollama", "ps"], text=True)
    lines = [ln.rstrip() for ln in raw.splitlines() if ln.strip()]
    rows = []
    target = None
    for ln in lines[1:]:
        rows.append(ln)
        if "gpt-oss:20b" in ln.split()[0:1] or ln.startswith("gpt-oss:20b") or "gpt-oss:20b" in ln:
            target = ln
    fully_gpu = bool(target and "100% GPU" in target)
    return {
        "raw": raw,
        "lines": lines,
        "target_line": target,
        "fully_gpu_resident": fully_gpu,
        "ts": time.time(),
    }


def require_full_gpu(context: str) -> dict[str, Any]:
    snap = ollama_ps()
    if not snap["fully_gpu_resident"]:
        raise RuntimeError(f"GPU residency not fully GPU at {context}: {snap.get('target_line') or snap['raw']!r}")
    return snap


def wait_for_ollama(model: str, timeout_s: int = 180) -> None:
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
    think: str | bool,
    num_ctx: int = 8192,
    temperature: float = 0.0,
    model: str = "gpt-oss:20b",
    timeout_s: int = 900,
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
    eval_duration_ns = data.get("eval_duration")
    prompt_eval_duration_ns = data.get("prompt_eval_duration")
    return {
        "thinking": thinking,
        "response": content,
        "trajectory": (thinking + "\n" + content).strip(),
        "eval_count": data.get("eval_count"),
        "prompt_eval_count": data.get("prompt_eval_count"),
        "prompt_eval_cached_count": data.get("prompt_eval_cached_count"),
        "eval_duration_ns": eval_duration_ns,
        "prompt_eval_duration_ns": prompt_eval_duration_ns,
        "total_duration_ns": data.get("total_duration"),
        "load_duration_ns": data.get("load_duration"),
        "G_decode_s": ns_to_s(eval_duration_ns),
        "prompt_eval_duration_s": ns_to_s(prompt_eval_duration_ns),
        "total_duration_s": ns_to_s(data.get("total_duration")),
        "load_duration_s": ns_to_s(data.get("load_duration")),
        "done_reason": data.get("done_reason"),
        "model": data.get("model"),
        "wall_s": wall,
        "created_at": data.get("created_at"),
        "raw_keys": sorted(data.keys()),
    }


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


def cpu_time() -> float:
    ru = resource.getrusage(resource.RUSAGE_SELF)
    return float(ru.ru_utime + ru.ru_stime)
