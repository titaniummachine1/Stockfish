#!/usr/bin/env python3
"""
Benchmark integrated `gameanalysis` vs external UCI per-ply analysis.

Modes:
  integrated   - single CLI: gameanalysis depth D ...
  uci_session  - one engine process, position + go depth per ply (typical GUI/backend)
  uci_fresh    - new engine process every ply (worst-case external app)

Usage:
  python scripts/benchmark_game_analysis.py path/to/stockfish.exe
  python scripts/benchmark_game_analysis.py path/to/stockfish.exe --json out.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parents[1]
GAMES_PATH = ROOT / "tests" / "benchmark_games.json"
RESULTS_DIR = ROOT / "scripts" / "benchmark_results"


def resolved_threads() -> int:
    """Match gameanalysis default: env STOCKFISH_THREADS or all logical CPUs."""
    env = os.environ.get("STOCKFISH_THREADS", "").strip()
    if env:
        return max(1, int(env))
    return max(1, os.cpu_count() or 1)


def thread_args() -> List[str]:
    """CLI args for gameanalysis; 0 lets the engine pick all CPUs."""
    env = os.environ.get("STOCKFISH_THREADS", "").strip()
    if env:
        return ["threads", str(max(1, int(env)))]
    return ["threads", "0"]


@dataclass
class RunResult:
    mode: str
    case: str
    depth: int
    multipv: int
    plies: int
    wall_ms: int
    nodes: int
    nps: int


def parse_summary(stdout: str) -> tuple[int, int]:
    """Return (nodes, wall_ms) from gameanalysis summary line."""
    nodes = time_ms = 0
    for line in stdout.splitlines():
        if "gameanalysis summary" not in line:
            continue
        parts = line.split()
        for i, tok in enumerate(parts):
            if tok == "nodes" and i + 1 < len(parts):
                nodes = int(parts[i + 1])
            if tok == "time" and i + 1 < len(parts):
                time_ms = int(parts[i + 1])
    return nodes, time_ms


def run_integrated(
    exe: Path,
    fen: str,
    moves: List[str],
    depth: int,
    multipv: int,
    cold: int,
    resume: int = 1,
) -> RunResult:
    args = [
        str(exe),
        "gameanalysis",
        "depth",
        str(depth),
        *thread_args(),
        "multipv",
        str(multipv),
        "cold",
        str(cold),
        "resume",
        str(resume),
        "fen",
        *fen.split(),
        "moves",
        *moves,
    ]
    t0 = time.perf_counter()
    p = subprocess.run(args, capture_output=True, text=True)
    wall_ms = int((time.perf_counter() - t0) * 1000)
    if p.returncode != 0:
        raise RuntimeError(f"integrated failed: {p.stderr or p.stdout}")
    out = p.stdout or ""
    nodes, reported_ms = parse_summary(out)
    if reported_ms > 0:
        wall_ms = reported_ms
    plies = len(moves) + 1
    nps = (nodes * 1000 // wall_ms) if wall_ms else 0
    return RunResult("integrated", "", depth, multipv, plies, wall_ms, nodes, nps)


def uci_position_line(fen: str, prefix: List[str]) -> str:
    if fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1" and not prefix:
        return "position startpos"
    if not prefix:
        return "position fen " + fen
    if fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1":
        return "position startpos moves " + " ".join(prefix)
    return "position fen " + fen + " moves " + " ".join(prefix)


class UciSession:
    def __init__(self, exe: Path, multipv: int, cold: int, threads: int) -> None:
        self.proc = subprocess.Popen(
            [str(exe)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert self.proc.stdin and self.proc.stdout
        self._write("uci")
        while True:
            line = self.proc.stdout.readline()
            if line.startswith("uciok"):
                break
        self._write(f"setoption name Threads value {threads}")
        self._write(f"setoption name MultiPV value {multipv}")
        if cold >= 1:
            self._write("ucinewgame")
        self._write("isready")
        while True:
            line = self.proc.stdout.readline()
            if line.startswith("readyok"):
                break

    def _write(self, cmd: str) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()

    def search_depth(self, fen: str, prefix: List[str], depth: int) -> int:
        self._write(uci_position_line(fen, prefix))
        self._write(f"go depth {depth}")
        ply_nodes = 0
        while True:
            line = self.proc.stdout.readline()
            if not line:
                break
            if line.startswith("info ") and " depth " in line and " nodes " in line:
                m = re.search(r"\bnodes (\d+)", line)
                if m:
                    ply_nodes = int(m.group(1))
            if line.startswith("bestmove "):
                break
        return ply_nodes

    def close(self) -> None:
        self._write("quit")
        self.proc.wait(timeout=120)


def run_uci_loop(
    exe: Path,
    fen: str,
    moves: List[str],
    depth: int,
    multipv: int,
    fresh_each_ply: bool,
    cold: int,
) -> RunResult:
    plies = len(moves) + 1
    total_nodes = 0
    t0 = time.perf_counter()

    threads = resolved_threads()
    if fresh_each_ply:
        for ply in range(plies):
            prefix = moves[:ply]
            session = UciSession(exe, multipv, cold, threads)
            total_nodes += session.search_depth(fen, prefix, depth)
            session.close()
    else:
        session = UciSession(exe, multipv, cold, threads)
        for ply in range(plies):
            prefix = moves[:ply]
            total_nodes += session.search_depth(fen, prefix, depth)
        session.close()

    wall_ms = int((time.perf_counter() - t0) * 1000)
    nps = (total_nodes * 1000 // wall_ms) if wall_ms else 0
    mode = "uci_fresh" if fresh_each_ply else "uci_session"
    return RunResult(mode, "", depth, multipv, plies, wall_ms, total_nodes, nps)


def run_integrated_pgn(
    exe: Path, pgn_path: Path, depth: int, multipv: int, resume: int = 1
) -> RunResult:
    args = [
        str(exe),
        "gameanalysis",
        "depth",
        str(depth),
        *thread_args(),
        "multipv",
        str(multipv),
        "resume",
        str(resume),
        "pgn",
        str(pgn_path),
    ]
    t0 = time.perf_counter()
    p = subprocess.run(args, capture_output=True, text=True)
    wall_ms = int((time.perf_counter() - t0) * 1000)
    if p.returncode != 0:
        raise RuntimeError(f"integrated pgn failed: {p.stderr or p.stdout}")
    nodes, reported_ms = parse_summary(p.stdout or "")
    if reported_ms > 0:
        wall_ms = reported_ms
    # sample.pgn: 6 moves -> 7 plies
    plies = 7
    nps = (nodes * 1000 // wall_ms) if wall_ms else 0
    mode = "integrated_pgn_resume" if resume else "integrated_pgn_full_id"
    return RunResult(mode, pgn_path.stem, depth, multipv, plies, wall_ms, nodes, nps)


def run_case(exe: Path, case: dict) -> List[RunResult]:
    name = case["name"]
    depth = case["depth"]
    multipv = case.get("multipv", 1)
    fen = case["fen"]
    moves = case["moves"]
    results: List[RunResult] = []

    r0 = run_integrated(exe, fen, moves, depth, multipv, cold=0, resume=1)
    r0.case = name
    r0.mode = "integrated_resume"
    results.append(r0)

    rFull = run_integrated(exe, fen, moves, depth, multipv, cold=0, resume=0)
    rFull.case = name
    rFull.mode = "integrated_full_id"
    results.append(rFull)

    r1 = run_integrated(exe, fen, moves, depth, multipv, cold=1)
    r1.case = name
    r1.mode = "integrated_cold1"
    results.append(r1)

    rs = run_uci_loop(exe, fen, moves, depth, multipv, fresh_each_ply=False, cold=0)
    rs.case = name
    results.append(rs)

    rf = run_uci_loop(exe, fen, moves, depth, multipv, fresh_each_ply=True, cold=0)
    rf.case = name
    results.append(rf)

    return results


def format_table(rows: List[RunResult]) -> str:
    by_case: dict[str, List[RunResult]] = {}
    for r in rows:
        by_case.setdefault(r.case, []).append(r)

    lines = [
        "| case | mode | plies | depth | multipv | time_ms | nodes | nps | vs integrated |",
        "|------|------|-------|-------|---------|---------|-------|-----|---------------|",
    ]
    for case, rs in by_case.items():
        base = next((x for x in rs if x.mode == "integrated_resume"), None)
        if not base:
            base = next((x for x in rs if x.mode == "integrated"), None)
        base_ms = base.wall_ms if base else 1
        for r in sorted(rs, key=lambda x: x.mode):
            ratio = f"{r.wall_ms / base_ms:.2f}x" if base and r.mode != "integrated" else "1.00x"
            if r.mode in ("integrated", "integrated_resume"):
                ratio = "baseline"
            lines.append(
                f"| {case} | {r.mode} | {r.plies} | {r.depth} | {r.multipv} | "
                f"{r.wall_ms} | {r.nodes} | {r.nps} | {ratio} |"
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stockfish", type=Path, help="Path to stockfish binary")
    parser.add_argument("--json", type=Path, help="Write JSON results")
    parser.add_argument("--cases", type=str, default="", help="Comma-separated case names")
    args = parser.parse_args()

    exe = args.stockfish.resolve()
    if not exe.is_file():
        print(f"Not found: {exe}", file=sys.stderr)
        return 1

    games = json.loads(GAMES_PATH.read_text(encoding="utf-8"))
    if args.cases:
        want = set(args.cases.split(","))
        games = [g for g in games if g["name"] in want]

    all_results: List[RunResult] = []
    th = resolved_threads()
    print(f"Benchmark: {exe}")
    print(f"Threads: {th} (set STOCKFISH_THREADS or omit for all logical CPUs)")
    print(f"Cases: {', '.join(g['name'] for g in games)}\n")

    corpus_dir = ROOT / "tests" / "benchmark_corpus"
    for pgn_path in sorted(corpus_dir.glob("*.pgn")):
        print(f"=== {pgn_path.name} (depth 10, multipv 1) ===")
        try:
            rp = run_integrated_pgn(exe, pgn_path, depth=10, multipv=1, resume=1)
            rf = run_integrated_pgn(exe, pgn_path, depth=10, multipv=1, resume=0)
            all_results.extend([rp, rf])
            print(f"  {rp.mode:22}  {rp.wall_ms:6} ms  nodes {rp.nodes:10}")
            print(f"  {rf.mode:22}  {rf.wall_ms:6} ms  nodes {rf.nodes:10}  "
                  f"({'%.0f%% nodes' % (100 * rp.nodes / rf.nodes) if rf.nodes else 'n/a'})")
        except Exception as e:
            print(f"  FAILED: {e}")
        print()

    for game in games:
        print(f"=== {game['name']} (depth {game['depth']}, multipv {game.get('multipv',1)}) ===")
        try:
            rows = run_case(exe, game)
        except Exception as e:
            print(f"  FAILED: {e}")
            continue
        for r in rows:
            all_results.append(r)
            print(
                f"  {r.mode:16}  {r.wall_ms:6} ms  nodes {r.nodes:10}  nps {r.nps:10}"
            )
        print()

    table = format_table(all_results)
    print(table)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    md_path = RESULTS_DIR / f"benchmark_{stamp}.md"
    md_path.write_text(
        f"# Game analysis benchmark\n\nBinary: `{exe}`\n\n{table}\n",
        encoding="utf-8",
    )
    print(f"\nWrote {md_path}")

    out_json = args.json or (RESULTS_DIR / f"benchmark_{stamp}.json")
    out_json.write_text(
        json.dumps([asdict(r) for r in all_results], indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
