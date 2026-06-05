#!/usr/bin/env python3
"""
Quality contract for integrated gameanalysis (not Elo — analysis correctness).

Reference = per-ply full iterative deepening to depth D (default: gameanalysis resume 0).
Candidate = default smart path (resume 2, refine 1) unless overridden.

Checks per spine ply:
  1. reported depth >= target depth D (never under-search vs requested depth)
  2. MultiPV-1 score text matches reference (same eval Stockfish would show at depth D)

Extra search depth on candidate (refine / TT) is allowed; scores must still match the
reference at D. Optional --reference uci compares against an external UCI session loop.

Usage:
  python scripts/gameanalysis_quality.py src/stockfish.exe
  python scripts/gameanalysis_quality.py src/stockfish.exe --reference uci --case opening_6
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
GAMES_PATH = ROOT / "tests" / "benchmark_games.json"
CORPUS_DIR = ROOT / "tests" / "benchmark_corpus"


@dataclass
class PlyFinal:
    depth: int
    score: str
    pv: str = ""


def resolved_threads() -> int:
    env = os.environ.get("STOCKFISH_THREADS", "").strip()
    if env:
        return max(1, int(env))
    # Single-threaded: deterministic score parity between reference and candidate runs.
    return 1


def thread_args() -> List[str]:
    return ["threads", str(resolved_threads())]


def parse_score_tokens(parts: List[str], score_idx: int) -> str:
    kind = parts[score_idx + 1]
    if kind in ("cp", "mate") and score_idx + 2 < len(parts):
        return f"{kind} {parts[score_idx + 2]}"
    return kind


def parse_gameanalysis_finals(stdout: str, multipv: int = 1) -> Dict[int, PlyFinal]:
    """Last emitted final per gameply for the given multipv."""
    by: Dict[int, PlyFinal] = {}
    needle = f" multipv {multipv} "
    for line in stdout.splitlines():
        if "gameanalysis final" not in line or needle not in line:
            continue
        parts = line.split()
        ply = depth = None
        score = pv = ""
        for i, tok in enumerate(parts):
            if tok == "gameply":
                ply = int(parts[i + 1])
            elif tok == "depth":
                depth = int(parts[i + 1])
            elif tok == "score":
                score = parse_score_tokens(parts, i)
            elif tok == "pv":
                pv = " ".join(parts[i + 1 :])
        if ply is None or depth is None:
            continue
        by[ply] = PlyFinal(depth=depth, score=score, pv=pv)
    return by


def run_gameanalysis(
    exe: Path,
    fen: str,
    moves: List[str],
    depth: int,
    multipv: int,
    resume: int,
    refine: int,
    cold: int = 0,
    strict: int = 0,
) -> str:
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
    p = subprocess.run(args, capture_output=True, text=True, timeout=600)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout or "")[-2000:])
    return p.stdout or ""


def uci_position_line(fen: str, prefix: List[str]) -> str:
    start = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    if fen == start and not prefix:
        return "position startpos"
    if not prefix:
        return "position fen " + fen
    if fen == start:
        return "position startpos moves " + " ".join(prefix)
    return "position fen " + fen + " moves " + " ".join(prefix)


def uci_per_ply_reference(
    exe: Path,
    fen: str,
    moves: List[str],
    depth: int,
    multipv: int = 1,
    fresh_each_ply: bool = False,
) -> Dict[int, PlyFinal]:
    """Per-ply `go depth D` in UCI; last info at depth D for multipv 1 defines the reference."""
    threads = resolved_threads()
    plies = len(moves) + 1
    out: Dict[int, PlyFinal] = {}

    def one_session() -> None:
        proc = subprocess.Popen(
            [str(exe)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdin and proc.stdout

        def write(cmd: str) -> None:
            proc.stdin.write(cmd + "\n")
            proc.stdin.flush()

        write("uci")
        while True:
            line = proc.stdout.readline()
            if line.startswith("uciok"):
                break
        write(f"setoption name Threads value {threads}")
        write(f"setoption name MultiPV value {multipv}")
        write("isready")
        while True:
            line = proc.stdout.readline()
            if line.startswith("readyok"):
                break

        mpv_re = re.compile(r"\bmultipv\s+(\d+)")
        depth_re = re.compile(r"\bdepth\s+(\d+)")
        score_re = re.compile(r"\bscore\s+(cp\s+-?\d+|mate\s+-?\d+)")

        for game_ply in range(plies):
            write(uci_position_line(fen, moves[:game_ply]))
            write(f"go depth {depth}")
            at_target: Optional[PlyFinal] = None
            max_depth = 0
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                if line.startswith("info "):
                    dm = depth_re.search(line)
                    if not dm:
                        continue
                    d = int(dm.group(1))
                    max_depth = max(max_depth, d)
                    mm = mpv_re.search(line)
                    mpv = int(mm.group(1)) if mm else 1
                    if mpv != 1 or d != depth:
                        continue
                    sm = score_re.search(line)
                    if not sm:
                        continue
                    pv_m = re.search(r"\bpv\s+(.+)", line)
                    pv = pv_m.group(1).strip() if pv_m else ""
                    at_target = PlyFinal(depth=d, score=sm.group(1), pv=pv)
                if line.startswith("bestmove "):
                    break
            if at_target is None:
                raise RuntimeError(f"UCI ply {game_ply}: no multipv 1 info at depth {depth}")
            # Engine may report seldepth > depth; contract uses completed ID depth line.
            out[game_ply] = at_target if at_target.depth >= depth else PlyFinal(
                depth=max_depth, score=at_target.score, pv=at_target.pv
            )

        write("quit")
        proc.wait(timeout=120)

    if fresh_each_ply:
        for game_ply in range(plies):
            sub: Dict[int, PlyFinal] = {}
            proc = subprocess.Popen(
                [str(exe)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            assert proc.stdin and proc.stdout

            def write(cmd: str) -> None:
                proc.stdin.write(cmd + "\n")
                proc.stdin.flush()

            write("uci")
            while True:
                line = proc.stdout.readline()
                if line.startswith("uciok"):
                    break
            write(f"setoption name Threads value {threads}")
            write(f"setoption name MultiPV value {multipv}")
            write("isready")
            while True:
                line = proc.stdout.readline()
                if line.startswith("readyok"):
                    break
            write(uci_position_line(fen, moves[:game_ply]))
            write(f"go depth {depth}")
            at_target = None
            depth_re = re.compile(r"\bdepth\s+(\d+)")
            score_re = re.compile(r"\bscore\s+(cp\s+-?\d+|mate\s+-?\d+)")
            mpv_re = re.compile(r"\bmultipv\s+(\d+)")
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                if line.startswith("info "):
                    dm = depth_re.search(line)
                    if not dm:
                        continue
                    d = int(dm.group(1))
                    mm = mpv_re.search(line)
                    mpv = int(mm.group(1)) if mm else 1
                    if mpv != 1 or d != depth:
                        continue
                    sm = score_re.search(line)
                    if sm:
                        pv_m = re.search(r"\bpv\s+(.+)", line)
                        pv = pv_m.group(1).strip() if pv_m else ""
                        at_target = PlyFinal(depth=d, score=sm.group(1), pv=pv)
                if line.startswith("bestmove "):
                    break
            write("quit")
            proc.wait(timeout=120)
            if at_target is None:
                raise RuntimeError(f"UCI fresh ply {game_ply}: no info at depth {depth}")
            out[game_ply] = at_target
    else:
        one_session()

    return out


def best_move_uci(pv: str) -> str:
    if not pv:
        return ""
    return pv.split()[0].lower()


def score_kind(score: str) -> str:
    return score.split()[0] if score else ""


def verify_case(
    name: str,
    target_depth: int,
    reference: Dict[int, PlyFinal],
    candidate: Dict[int, PlyFinal],
    *,
    strict_score: bool = True,
    check_best_move: bool = True,
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    notes: List[str] = []

    for ply in sorted(reference.keys()):
        ref = reference[ply]
        cand = candidate.get(ply)
        if cand is None:
            errors.append(f"{name} ply {ply}: missing candidate final")
            continue
        if cand.depth < target_depth:
            errors.append(
                f"{name} ply {ply}: depth {cand.depth} < target {target_depth} (under-searched)"
            )
        if score_kind(ref.score) != score_kind(cand.score):
            errors.append(
                f"{name} ply {ply}: score kind {score_kind(cand.score)!r} != {score_kind(ref.score)!r}"
            )
        if check_best_move:
            rb, cb = best_move_uci(ref.pv), best_move_uci(cand.pv)
            if rb and cb and rb != cb:
                errors.append(f"{name} ply {ply}: best move {cb!r} != reference {rb!r}")
        if strict_score and cand.score != ref.score:
            errors.append(
                f"{name} ply {ply}: score {cand.score!r} != reference {ref.score!r}"
            )
        if cand.depth > target_depth:
            notes.append(f"{name} ply {ply}: free depth {cand.depth} (target {target_depth})")

    return errors, notes


def run_pgn_case(
    exe: Path,
    pgn: Path,
    depth: int,
    reference_mode: str,
    candidate_resume: int,
    candidate_refine: int,
    candidate_strict: int = 1,
) -> Tuple[List[str], List[str]]:
    # Shorter depth for corpus in CI-style runs unless env overrides
    ref_out = subprocess.run(
        [
            str(exe),
            "gameanalysis",
            "depth",
            str(depth),
            *thread_args(),
            "resume",
            "0",
            "refine",
            "0",
            "strict",
            "0",
            "pgn",
            str(pgn),
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    cand_out = subprocess.run(
        [
            str(exe),
            "gameanalysis",
            "depth",
            str(depth),
            *thread_args(),
            "resume",
            str(candidate_resume),
            "refine",
            str(candidate_refine),
            "strict",
            str(candidate_strict),
            "pgn",
            str(pgn),
        ],
        capture_output=True,
        text=True,
        timeout=900,
    )
    if ref_out.returncode != 0 or cand_out.returncode != 0:
        raise RuntimeError(f"PGN run failed for {pgn.name}")

    # PGN emits multiple games — verify each block separately by re-parsing game markers
    errors: List[str] = []
    notes: List[str] = []
    name = pgn.stem

    if reference_mode == "uci":
        # Full PGN UCI compare is slow; use integrated full ID only for corpus
        reference_mode = "full_id"

    ref_by_game = _split_pgn_finals(ref_out.stdout or "")
    cand_by_game = _split_pgn_finals(cand_out.stdout or "")
    if len(ref_by_game) != len(cand_by_game):
        errors.append(f"{name}: game count ref={len(ref_by_game)} cand={len(cand_by_game)}")
        return errors, notes

    for i, (ref_f, cand_f) in enumerate(zip(ref_by_game, cand_by_game)):
        e, n = verify_case(f"{name} game {i+1}", depth, ref_f, cand_f)
        errors.extend(e)
        notes.extend(n)
    return errors, notes


def _split_pgn_finals(stdout: str) -> List[Dict[int, PlyFinal]]:
    games: List[Dict[int, PlyFinal]] = []
    buf: List[str] = []
    for line in stdout.splitlines():
        if "gameanalysis game " in line and "/" in line:
            if buf:
                games.append(parse_gameanalysis_finals("\n".join(buf), multipv=1))
            buf = [line]
        else:
            buf.append(line)
    if buf:
        games.append(parse_gameanalysis_finals("\n".join(buf), multipv=1))
    if not games and stdout.strip():
        games.append(parse_gameanalysis_finals(stdout, multipv=1))
    return games


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify gameanalysis quality contract")
    ap.add_argument("stockfish", type=Path)
    ap.add_argument(
        "--reference",
        choices=("full_id", "uci", "uci_fresh"),
        default="full_id",
        help="full_id = resume 0 gameanalysis; uci = per-ply UCI session",
    )
    ap.add_argument("--resume", type=int, default=2, help="candidate resume mode")
    ap.add_argument("--refine", type=int, default=1, help="candidate refine flag")
    ap.add_argument(
        "--strict",
        type=int,
        default=1,
        help="candidate strict (1 = full 1..D ID per ply, default for quality checks)",
    )
    ap.add_argument("--case", type=str, default="", help="comma-separated benchmark case names")
    ap.add_argument("--pgn", action="store_true", help="also verify benchmark_corpus PGNs")
    ap.add_argument("--depth-pgn", type=int, default=8, help="depth for PGN corpus checks")
    ap.add_argument("--allow-score-mismatch", action="store_true", help="only check depth floor")
    args = ap.parse_args()

    exe = args.stockfish.resolve()
    if not exe.is_file():
        print(f"Not found: {exe}", file=sys.stderr)
        return 1

    games = json.loads(GAMES_PATH.read_text(encoding="utf-8"))
    if args.case:
        want = set(args.case.split(","))
        games = [g for g in games if g["name"] in want]

    all_errors: List[str] = []
    all_notes: List[str] = []

    print(
        f"Quality contract: candidate resume={args.resume} refine={args.refine} strict={args.strict}"
    )
    print(f"Reference: {args.reference}")
    print(f"Threads: {resolved_threads()}\n")

    for case in games:
        name = case["name"]
        depth = case["depth"]
        multipv = case.get("multipv", 1)
        fen = case["fen"]
        moves = case["moves"]

        if args.reference == "full_id":
            ref_stdout = run_gameanalysis(exe, fen, moves, depth, multipv, resume=0, refine=0)
            reference = parse_gameanalysis_finals(ref_stdout, multipv=1)
        elif args.reference == "uci":
            reference = uci_per_ply_reference(exe, fen, moves, depth, multipv, fresh_each_ply=False)
        else:
            reference = uci_per_ply_reference(exe, fen, moves, depth, multipv, fresh_each_ply=True)

        cand_stdout = run_gameanalysis(
            exe,
            fen,
            moves,
            depth,
            multipv,
            resume=args.resume,
            refine=args.refine,
            strict=args.strict,
        )
        candidate = parse_gameanalysis_finals(cand_stdout, multipv=1)

        errors, notes = verify_case(
            name,
            depth,
            reference,
            candidate,
            strict_score=not args.allow_score_mismatch,
        )
        all_errors.extend(errors)
        all_notes.extend(notes)

        status = "OK" if not errors else "FAIL"
        free = sum(1 for n in notes if "free depth" in n)
        print(f"  [{status}] {name} depth {depth} multipv {multipv}  ({len(reference)} plies, {free} free-depth plies)")
        for e in errors:
            print(f"    ! {e}")

    if args.pgn and CORPUS_DIR.is_dir():
        for pgn in sorted(CORPUS_DIR.glob("*.pgn")):
            try:
                errors, notes = run_pgn_case(
                    exe, pgn, args.depth_pgn, args.reference, args.resume, args.refine
                )
                all_errors.extend(errors)
                all_notes.extend(notes)
                status = "OK" if not errors else "FAIL"
                print(f"  [{status}] PGN {pgn.name} @ depth {args.depth_pgn}")
                for e in errors:
                    print(f"    ! {e}")
            except Exception as ex:
                all_errors.append(f"PGN {pgn.name}: {ex}")
                print(f"  [FAIL] PGN {pgn.name}: {ex}")

    if all_notes and not all_errors:
        print(f"\nNotes: {len(all_notes)} plies with depth > target (free deepen allowed)")

    if all_errors:
        print(f"\nFAILED: {len(all_errors)} quality violation(s)", file=sys.stderr)
        return 1

    print("\nPASSED: every ply >= target depth and scores match reference at depth D")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
