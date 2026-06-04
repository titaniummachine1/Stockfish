#!/usr/bin/env python3
"""
Multi-hour game-analysis experiment runner (quality + speed).

Runs until --hours elapsed (default 10). Logs JSONL + periodic markdown summaries.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "tests" / "benchmark_games.json"
CORPUS = ROOT / "tests" / "benchmark_corpus"
OUT = ROOT / "scripts" / "benchmark_results" / "experiments"


def threads_arg() -> List[str]:
    env = os.environ.get("STOCKFISH_THREADS", "").strip()
    return ["threads", str(max(1, int(env)))] if env else ["threads", "0"]


@dataclass
class Sample:
    ts: str
    round: int
    label: str
    case: str
    depth: int
    multipv: int
    resume: int
    resume_horizon: int
    wall_ms: int
    nodes: int
    plies: int
    quality_match: Optional[float] = None  # fraction plies matching full ID


def parse_summary(stdout: str) -> Tuple[int, int, int]:
    nodes = time_ms = plies = 0
    for line in stdout.splitlines():
        if "gameanalysis summary" not in line:
            continue
        parts = line.split()
        for i, tok in enumerate(parts):
            if tok == "plies" and i + 1 < len(parts):
                plies = int(parts[i + 1])
            if tok == "nodes" and i + 1 < len(parts):
                nodes = int(parts[i + 1])
            if tok == "time" and i + 1 < len(parts):
                time_ms = int(parts[i + 1])
    return nodes, time_ms, plies


def parse_finals(stdout: str) -> dict[int, Tuple[str, str]]:
    """gameply -> (score_text, pv_first_uci) for multipv 1 at best depth."""
    by_ply: dict[int, dict] = {}
    for line in stdout.splitlines():
        if "gameanalysis final" not in line:
            continue
        parts = line.split()
        ply = depth = mpv = 0
        score = ""
        pv_first = ""
        for i, tok in enumerate(parts):
            if tok == "gameply" and i + 1 < len(parts):
                ply = int(parts[i + 1])
            if tok == "depth" and i + 1 < len(parts):
                depth = int(parts[i + 1])
            if tok == "multipv" and i + 1 < len(parts):
                mpv = int(parts[i + 1])
            if tok == "score" and i + 1 < len(parts):
                score = parts[i + 1]
            if tok == "pv" and i + 1 < len(parts):
                pv_first = parts[i + 1]
        if mpv != 1 or ply <= 0:
            continue
        cur = by_ply.get(ply)
        if cur is None or depth >= cur["depth"]:
            by_ply[ply] = {"depth": depth, "score": score, "move": pv_first}
    return {p: (v["score"], v["move"]) for p, v in by_ply.items()}


def run_gameanalysis(
    exe: Path, args: List[str], timeout_s: int = 600
) -> Tuple[int, str, int]:
    cmd = [str(exe), "gameanalysis", *args]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    wall = int((time.perf_counter() - t0) * 1000)
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0:
        raise RuntimeError(f"exit {p.returncode}: {out[-2000:]}")
    nodes, rep_ms, plies = parse_summary(out)
    if rep_ms > 0:
        wall = rep_ms
    return wall, out, plies


def quality_vs_full(
    exe: Path, fen: str, moves: List[str], depth: int, multipv: int, resume: int, horizon: int
) -> float:
    base = [
        "depth",
        str(depth),
        *threads_arg(),
        "multipv",
        str(multipv),
        "cold",
        "0",
        "fen",
        *fen.split(),
        "moves",
        *moves,
    ]
    _, out_full, _ = run_gameanalysis(exe, base + ["resume", "0"])
    _, out_smart, _ = run_gameanalysis(
        exe, base + ["resume", str(resume), "resumehorizon", str(horizon)]
    )
    f = parse_finals(out_full)
    s = parse_finals(out_smart)
    common = set(f) & set(s)
    if not common:
        return 0.0
    match = sum(1 for p in common if f[p] == s[p])
    return match / len(common)


def bench_case(exe: Path, case: dict, resume: int, horizon: int) -> Sample:
    args = [
        "depth",
        str(case["depth"]),
        *threads_arg(),
        "multipv",
        str(case.get("multipv", 1)),
        "cold",
        "0",
        "resume",
        str(resume),
        "resumehorizon",
        str(horizon),
        "fen",
        *case["fen"].split(),
        "moves",
        *case["moves"],
    ]
    wall, out, plies = run_gameanalysis(exe, args)
    nodes, _, _ = parse_summary(out)
    return Sample(
        ts=datetime.now(timezone.utc).isoformat(),
        round=0,
        label=f"resume{resume}_h{horizon}",
        case=case["name"],
        depth=case["depth"],
        multipv=case.get("multipv", 1),
        resume=resume,
        resume_horizon=horizon,
        wall_ms=wall,
        nodes=nodes,
        plies=plies,
    )


def bench_pgn(exe: Path, pgn: Path, depth: int, resume: int, horizon: int) -> Sample:
    args = [
        "depth",
        str(depth),
        *threads_arg(),
        "multipv",
        "1",
        "resume",
        str(resume),
        "resumehorizon",
        str(horizon),
        "pgn",
        str(pgn),
    ]
    wall, out, plies = run_gameanalysis(exe, args)
    nodes, _, _ = parse_summary(out)
    return Sample(
        ts=datetime.now(timezone.utc).isoformat(),
        round=0,
        label=f"resume{resume}_h{horizon}",
        case=pgn.stem,
        depth=depth,
        multipv=1,
        resume=resume,
        resume_horizon=horizon,
        wall_ms=wall,
        nodes=nodes,
        plies=plies,
    )


def write_round_summary(log_path: Path, samples: List[Sample], round_n: int) -> None:
    md = OUT / f"round_{round_n:04d}.md"
    lines = [f"# Experiment round {round_n}\n", f"Log: `{log_path.name}`\n\n"]
    lines.append("| case | resume | horizon | ms | nodes | nps |\n")
    lines.append("|------|--------|---------|-----|-------|-----|\n")
    for s in samples:
        nps = (s.nodes * 1000 // s.wall_ms) if s.wall_ms else 0
        lines.append(
            f"| {s.case} | {s.resume} | {s.resume_horizon} | {s.wall_ms} | {s.nodes} | {nps} |\n"
        )
    md.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stockfish", type=Path)
    ap.add_argument("--hours", type=float, default=10.0)
    ap.add_argument("--quality-every", type=int, default=3, help="rounds between quality probes")
    args = ap.parse_args()

    exe = args.stockfish.resolve()
    if not exe.is_file():
        print(f"Missing: {exe}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = OUT / f"experiment_{stamp}.jsonl"
    games = json.loads(GAMES.read_text(encoding="utf-8"))
    pgns = sorted(CORPUS.glob("*.pgn"))

    configs = [
        (0, 2),
        (2, 2),
        (2, 3),
        (2, 4),
    ]

    deadline = time.time() + args.hours * 3600
    round_n = 0
    print(f"Experiments until {args.hours}h — log {log_path}", flush=True)

    with log_path.open("a", encoding="utf-8") as log:
        while time.time() < deadline:
            round_n += 1
            round_samples: List[Sample] = []
            print(f"\n=== Round {round_n} ===", flush=True)

            for resume, horizon in configs:
                for case in games:
                    try:
                        s = bench_case(exe, case, resume, horizon)
                        s.round = round_n
                        if round_n % args.quality_every == 0 and resume == 2 and case["name"] == "opening_6":
                            s.quality_match = quality_vs_full(
                                exe,
                                case["fen"],
                                case["moves"],
                                case["depth"],
                                case.get("multipv", 1),
                                resume,
                                horizon,
                            )
                        round_samples.append(s)
                        log.write(json.dumps(asdict(s)) + "\n")
                        log.flush()
                        print(
                            f"  {s.case} r{resume} h{horizon}: {s.wall_ms}ms {s.nodes}n"
                            + (
                                f" quality={s.quality_match:.0%}"
                                if s.quality_match is not None
                                else ""
                            ),
                            flush=True,
                        )
                    except Exception as e:
                        print(f"  FAIL {case['name']} r{resume} h{horizon}: {e}", flush=True)

                for pgn in pgns:
                    try:
                        s = bench_pgn(exe, pgn, depth=10, resume=resume, horizon=horizon)
                        s.round = round_n
                        round_samples.append(s)
                        log.write(json.dumps(asdict(s)) + "\n")
                        log.flush()
                        print(
                            f"  {pgn.stem} r{resume} h{horizon}: {s.wall_ms}ms {s.nodes}n",
                            flush=True,
                        )
                    except Exception as e:
                        print(f"  FAIL {pgn.name}: {e}", flush=True)

            write_round_summary(log_path, round_samples, round_n)
            (OUT / "latest_log.txt").write_text(str(log_path), encoding="utf-8")

            # Run standard benchmark script once per 2 rounds
            if round_n % 2 == 1:
                try:
                    subprocess.run(
                        [
                            sys.executable,
                            str(ROOT / "scripts" / "benchmark_game_analysis.py"),
                            str(exe),
                            "--json",
                            str(OUT / f"benchmark_round_{round_n:04d}.json"),
                        ],
                        cwd=str(ROOT),
                        timeout=1800,
                        check=False,
                    )
                except Exception as e:
                    print(f"  benchmark script: {e}", flush=True)

            time.sleep(5)

    print(f"\nDone. Log: {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
