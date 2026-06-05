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


def parse_summary(stdout: str) -> tuple[int, int, int]:
    """Return (nodes, wall_ms, plies) from gameanalysis summary line."""
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


def run_integrated(
    exe: Path,
    fen: str,
    moves: List[str],
    depth: int,
    multipv: int,
    cold: int,
    resume: int = 1,
    refine: int = 1,
    strict: int = 0,
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
        "refine",
        str(refine),
        "strict",
        str(strict),
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
    nodes, reported_ms, plies = parse_summary(out)
    if reported_ms > 0:
        wall_ms = reported_ms
    if plies <= 0:
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


def load_pgn_start_fen_and_moves(pgn_path: Path) -> tuple[str, List[str]]:
    import chess.pgn

    with pgn_path.open(encoding="utf-8") as f:
        game = chess.pgn.read_game(f)
    if game is None:
        raise ValueError(f"no game in {pgn_path}")
    board = game.board()
    fen = board.fen()
    moves = [m.uci() for m in game.mainline_moves()]
    return fen, moves


def run_integrated_pgn(
    exe: Path,
    pgn_path: Path,
    depth: int,
    multipv: int,
    resume: int = 1,
    refine: int = 1,
    strict: int = 0,
    mode_name: str = "",
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
        "0",
        "resume",
        str(resume),
        "refine",
        str(refine),
        "strict",
        str(strict),
        "pgn",
        str(pgn_path),
    ]
    t0 = time.perf_counter()
    p = subprocess.run(args, capture_output=True, text=True)
    wall_ms = int((time.perf_counter() - t0) * 1000)
    if p.returncode != 0:
        raise RuntimeError(f"integrated pgn failed: {p.stderr or p.stdout}")
    nodes, reported_ms, plies = parse_summary(p.stdout or "")
    if reported_ms > 0:
        wall_ms = reported_ms
    if plies <= 0:
        raise RuntimeError("no gameanalysis summary in PGN run")
    nps = (nodes * 1000 // wall_ms) if wall_ms else 0
    if mode_name:
        mode = mode_name
    else:
        suffix = {0: "full_id", 1: "legacy", 2: "smart"}.get(resume, str(resume))
        mode = f"integrated_pgn_{suffix}"
    return RunResult(mode, pgn_path.stem, depth, multipv, plies, wall_ms, nodes, nps)


def run_pgn_case(exe: Path, pgn_path: Path, depth: int, multipv: int = 1) -> List[RunResult]:
    """Full comparison: integrated parity/smart/full + naive UCI (ChessKit-style)."""
    fen, moves = load_pgn_start_fen_and_moves(pgn_path)
    name = pgn_path.stem
    results: List[RunResult] = []

    rParity = run_integrated_pgn(
        exe,
        pgn_path,
        depth,
        multipv,
        resume=2,
        refine=1,
        strict=1,
        mode_name="integrated_parity",
    )
    rParity.case = name
    results.append(rParity)

    rSmart = run_integrated_pgn(
        exe,
        pgn_path,
        depth,
        multipv,
        resume=2,
        refine=1,
        strict=0,
        mode_name="integrated_smart",
    )
    rSmart.case = name
    results.append(rSmart)

    rMerge = run_integrated_pgn(
        exe,
        pgn_path,
        depth,
        multipv,
        resume=3,
        refine=1,
        strict=0,
        mode_name="integrated_merge",
    )
    rMerge.case = name
    results.append(rMerge)

    rFull = run_integrated_pgn(
        exe,
        pgn_path,
        depth,
        multipv,
        resume=0,
        refine=0,
        strict=0,
        mode_name="integrated_full_id",
    )
    rFull.case = name
    results.append(rFull)

    rs = run_uci_loop(exe, fen, moves, depth, multipv, fresh_each_ply=False, cold=0)
    rs.case = name
    rs.mode = "uci_session"
    results.append(rs)

    rf = run_uci_loop(exe, fen, moves, depth, multipv, fresh_each_ply=True, cold=0)
    rf.case = name
    rf.mode = "uci_fresh"
    results.append(rf)

    return results


def run_case(exe: Path, case: dict) -> List[RunResult]:
    name = case["name"]
    depth = case["depth"]
    multipv = case.get("multipv", 1)
    fen = case["fen"]
    moves = case["moves"]
    results: List[RunResult] = []

    rParity = run_integrated(
        exe, fen, moves, depth, multipv, cold=0, resume=2, refine=1, strict=1
    )
    rParity.case = name
    rParity.mode = "integrated_parity"
    results.append(rParity)

    rSmart = run_integrated(
        exe, fen, moves, depth, multipv, cold=0, resume=2, refine=1, strict=0
    )
    rSmart.case = name
    rSmart.mode = "integrated_smart"
    results.append(rSmart)

    rMerge = run_integrated(
        exe, fen, moves, depth, multipv, cold=0, resume=3, refine=1, strict=0
    )
    rMerge.case = name
    rMerge.mode = "integrated_merge"
    results.append(rMerge)

    rLegacy = run_integrated(exe, fen, moves, depth, multipv, cold=0, resume=1)
    rLegacy.case = name
    rLegacy.mode = "integrated_legacy"
    results.append(rLegacy)

    rFull = run_integrated(
        exe, fen, moves, depth, multipv, cold=0, resume=0, refine=0, strict=0
    )
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
        base = next((x for x in rs if x.mode == "integrated_parity"), None)
        if not base:
            base = next((x for x in rs if x.mode == "integrated_smart"), None)
        if not base:
            base = next((x for x in rs if x.mode == "integrated_full_id"), None)
        base_ms = base.wall_ms if base else 1
        for r in sorted(rs, key=lambda x: x.mode):
            ratio = f"{r.wall_ms / base_ms:.2f}x" if base and r.mode != base.mode else "1.00x"
            if base and r.mode == base.mode:
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
    parser.add_argument(
        "--pgn-only",
        type=str,
        default="",
        help="Comma-separated PGN filenames in benchmark_corpus (empty = all)",
    )
    parser.add_argument("--pgn-depth", type=int, default=10, help="Depth for PGN corpus runs")
    parser.add_argument("--skip-json", action="store_true", help="Only run PGN corpus")
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
    if not args.skip_json:
        print(f"JSON cases: {', '.join(g['name'] for g in games)}")
    print(f"PGN depth: {args.pgn_depth}\n")

    corpus_dir = ROOT / "tests" / "benchmark_corpus"
    pgn_want = set(args.pgn_only.split(",")) if args.pgn_only else None
    for pgn_path in sorted(corpus_dir.glob("*.pgn")):
        if pgn_want and pgn_path.stem not in pgn_want and pgn_path.name not in pgn_want:
            continue
        print(f"=== {pgn_path.name} (depth {args.pgn_depth}, {pgn_path.stem}) ===")
        try:
            rows = run_pgn_case(exe, pgn_path, depth=args.pgn_depth, multipv=1)
            all_results.extend(rows)
            base = next((x for x in rows if x.mode == "integrated_smart"), rows[0])
            for r in sorted(rows, key=lambda x: x.mode):
                vs = "baseline" if r.mode == "integrated_smart" else f"{r.wall_ms / base.wall_ms:.2f}x"
                if r.mode == "uci_session":
                    vs = f"{r.wall_ms / base.wall_ms:.2f}x vs smart"
                print(
                    f"  {r.mode:22}  {r.wall_ms:6} ms  nodes {r.nodes:10}  "
                    f"plies {r.plies}  {vs}"
                )
        except Exception as e:
            print(f"  FAILED: {e}")
        print()

    if args.skip_json:
        games = []

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
