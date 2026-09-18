#!/usr/bin/env python3
"""E000 confirmatory analysis. Run only after arms+verify complete."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path("/home/sauravsvt/Desktop/Research/R2")
sys.path.insert(0, str(ROOT / "scripts"))

from r2_lib import (  # noqa: E402
    interaction_bootstrap,
    material,
    paired_bootstrap,
    read_json,
    read_jsonl,
    write_json,
)

VERIFY = ROOT / "results/raw/E000_verify.jsonl"
OUT = ROOT / "results/raw/E000_analysis.json"


def load_cells() -> dict[tuple[str, str], dict[str, int]]:
    cells: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
    for row in read_jsonl(VERIFY):
        if row.get("source_stage") not in {"intervention", None} and row.get("arm"):
            pass
        if not row.get("arm") or not row.get("group"):
            continue
        cells[(row["task_id"], row["group"])][row["arm"]] = int(bool(row.get("plus_pass")))
    return cells


def group_delta(cells, group: str, a: str, b: str) -> np.ndarray:
    vals = []
    for (task_id, g), arms in cells.items():
        if g != group:
            continue
        if a in arms and b in arms:
            vals.append(arms[a] - arms[b])
    return np.asarray(vals, dtype=np.float64)


def group_rate(cells, group: str, arm: str) -> dict:
    vals = []
    for (task_id, g), arms in cells.items():
        if g == group and arm in arms:
            vals.append(arms[arm])
    arr = np.asarray(vals, dtype=np.float64)
    return {"n": int(arr.size), "success": float(arr.mean()) if arr.size else None}


def interpret(analysis: dict) -> str:
    n_high = analysis["rates"]["HIGH"]["A1_CONTINUE_LOCAL"]["n"]
    n_low = analysis["rates"]["LOW"]["A1_CONTINUE_LOCAL"]["n"]
    d_high = analysis["deltas"]["A4-A1_HIGH"]
    d_low = analysis["deltas"]["A4-A1_LOW"]
    inter = analysis["deltas"]["EscapeAdvantage"]
    d_a2 = analysis["deltas"]["A4-A2_HIGH"]
    d_a2_vs_a1 = analysis["deltas"]["A2-A1_HIGH"]
    if n_high < 15 or n_low < 15:
        if material(d_high):
            return "CONTINUE — MIXED SIGNAL"
        return "STOP — NO STRUCTURAL ESCAPE SIGNAL"
    if material(d_high) and inter.get("point") is not None and float(inter["point"]) > 0 and inter.get("ci_excludes_zero") and float(inter["ci95_low"]) > 0 and material(d_a2):
        return "CONTINUE — STRUCTURAL ESCAPE SIGNAL"
    if material(d_high) and material(d_a2_vs_a1) and not material(d_a2):
        return "CONTINUE — GENERIC BRANCHING SIGNAL"
    if d_high.get("point") is not None and float(d_high["point"]) > 0:
        return "CONTINUE — MIXED SIGNAL"
    return "STOP — NO STRUCTURAL ESCAPE SIGNAL"


def main() -> None:
    cells = load_cells()
    arms = ["A1_CONTINUE_LOCAL", "A2_BRANCH_LOCAL", "A4_STRUCTURAL_ESCAPE"]
    rates = {g: {a: group_rate(cells, g, a) for a in arms} for g in ("HIGH", "LOW")}
    analysis = {
        "experiment_id": "E000",
        "rates": rates,
        "deltas": {
            "A4-A1_HIGH": paired_bootstrap(group_delta(cells, "HIGH", "A4_STRUCTURAL_ESCAPE", "A1_CONTINUE_LOCAL")),
            "A4-A1_LOW": paired_bootstrap(group_delta(cells, "LOW", "A4_STRUCTURAL_ESCAPE", "A1_CONTINUE_LOCAL")),
            "A4-A2_HIGH": paired_bootstrap(group_delta(cells, "HIGH", "A4_STRUCTURAL_ESCAPE", "A2_BRANCH_LOCAL")),
            "A2-A1_HIGH": paired_bootstrap(group_delta(cells, "HIGH", "A2_BRANCH_LOCAL", "A1_CONTINUE_LOCAL")),
        },
    }
    analysis["deltas"]["EscapeAdvantage"] = interaction_bootstrap(
        group_delta(cells, "HIGH", "A4_STRUCTURAL_ESCAPE", "A1_CONTINUE_LOCAL"),
        group_delta(cells, "LOW", "A4_STRUCTURAL_ESCAPE", "A1_CONTINUE_LOCAL"),
    )
    analysis["decision"] = interpret(analysis)
    write_json(OUT, analysis)
    print(json_dumps := __import__("json").dumps(analysis, indent=2, sort_keys=True))
    print("DECISION", analysis["decision"])


if __name__ == "__main__":
    main()
