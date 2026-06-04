#!/usr/bin/env python3
"""~12 min experiment cycle: speed + quality vs full ID. Writes one JSON summary."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
GAMES = json.loads((ROOT / "tests" / "benchmark_games.json").read_text(encoding="utf-8"))
OUT = ROOT / "scripts" / "benchmark_results" / "quick"
CASES = ["opening_6", "long_20", "opening_6_multipv3"]


def threads() -> List[str]:
    e = os.environ.get("STOCKFISH_THREADS", "").strip()
    return ["threads", str(max(1, int(e)))] if e else ["threads", "0"]


def parse_summary(stdout: str) -> Tuple[int, int]:
    nodes = ms = 0
    for line in stdout.splitlines():
        if "gameanalysis summary" not in line:
            continue
        p = line.split()
        for i, t in enumerate(p):
            if t == "nodes" and i + 1 < len(p):
                nodes = int(p[i + 1])
            if t == "time" and i + 1 < len(p):
                ms = int(p[i + 1])
    return nodes, ms


def parse_finals(stdout: str) -> dict[int, str]:
    by: dict[int, tuple[int, str]] = {}
    for line in stdout.splitlines():
        if "gameanalysis final" not in line or " multipv 1 " not in line:
            continue
        ply = depth = 0
        score = ""
        p = line.split()
        for i, t in enumerate(p):
            if t == "gameply":
                ply = int(p[i + 1])
            if t == "depth":
                depth = int(p[i + 1])
            if t == "score":
                score = p[i + 1]
        if ply and (ply not in by or depth >= by[ply][0]):
            by[ply] = (depth, score)
    return {k: v[1] for k, v in by.items()}


@dataclass
class Config:
    name: str
    resume: int
    horizon: int


CONFIGS = [
    Config("full", 0, 2),
    Config("smart_h1", 2, 1),   # default after experiments
    Config("merge_h1", 3, 1),   # TT-merge mode
]


def run(exe: Path, case: dict, cfg: Config) -> Tuple[int, int, str]:
    args = [
        str(exe),
        "gameanalysis",
        "depth",
        str(case["depth"]),
        *threads(),
        "multipv",
        str(case.get("multipv", 1)),
        "cold",
        "0",
        "resume",
        str(cfg.resume),
        "resumehorizon",
        str(cfg.horizon),
        "fen",
        *case["fen"].split(),
        "moves",
        *case["moves"],
    ]
    t0 = time.perf_counter()
    p = subprocess.run(args, capture_output=True, text=True, timeout=300)
    wall = int((time.perf_counter() - t0) * 1000)
    if p.returncode != 0:
        raise RuntimeError((p.stdout or "")[-1500:])
    nodes, rep = parse_summary(p.stdout or "")
    if rep > 0:
        wall = rep
    return nodes, wall, p.stdout or ""


def quality(exe: Path, case: dict, cfg: Config) -> float:
    if cfg.resume == 0:
        return 1.0
    _, _, out = run(exe, case, cfg)
    _, _, full = run(exe, case, Config("full", 0, 2))
    a, b = parse_finals(out), parse_finals(full)
    common = set(a) & set(b)
    if not common:
        return 0.0
    return sum(1 for p in common if a[p] == b[p]) / len(common)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stockfish", type=Path)
    ap.add_argument("--minutes", type=float, default=12.0)
    args = ap.parse_args()
    exe = args.stockfish.resolve()
    OUT.mkdir(parents=True, exist_ok=True)

    games = [g for g in GAMES if g["name"] in CASES]
    deadline = time.time() + args.minutes * 60
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUT / f"quick_{stamp}.json"

    results = []
    print(f"Quick experiments ~{args.minutes} min -> {out_path}", flush=True)

    while time.time() < deadline:
        for cfg in CONFIGS:
            if time.time() >= deadline:
                break
            for case in games:
                if time.time() >= deadline:
                    break
                try:
                    nodes, wall, _ = run(exe, case, cfg)
                    q = None
                    if case["name"] == "opening_6" and cfg.resume != 0:
                        q = quality(exe, case, cfg)
                    row = {
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "config": cfg.name,
                        "case": case["name"],
                        "nodes": nodes,
                        "wall_ms": wall,
                        "quality": q,
                    }
                    results.append(row)
                    qs = f" q={q:.0%}" if q is not None else ""
                    print(f"  {cfg.name:12} {case['name']:22} {wall:5}ms {nodes:9}{qs}", flush=True)
                except Exception as e:
                    print(f"  FAIL {cfg.name} {case['name']}: {e}", flush=True)

    full_nodes = {}
    for r in results:
        if r["config"] == "full":
            full_nodes[r["case"]] = r["nodes"]

    summary = {}
    for cfg in {c.name for c in CONFIGS}:
        rows = [r for r in results if r["config"] == cfg]
        if not rows:
            continue
        avg_q = [r["quality"] for r in rows if r["quality"] is not None]
        summary[cfg] = {
            "mean_ms": sum(r["wall_ms"] for r in rows) // len(rows),
            "mean_node_pct_of_full": (
                sum(100 * r["nodes"] / full_nodes[r["case"]] for r in rows if r["case"] in full_nodes)
                // max(1, sum(1 for r in rows if r["case"] in full_nodes))
            ),
            "mean_quality": sum(avg_q) / len(avg_q) if avg_q else None,
        }

    payload = {"results": results, "summary": summary, "minutes": args.minutes}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (OUT / "latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print("\nSummary:", json.dumps(summary, indent=2), flush=True)
    print(f"Wrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
