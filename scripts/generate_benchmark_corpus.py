#!/usr/bin/env python3
"""Regenerate tests/benchmark_corpus/*.pgn with legally valid movetext."""

from __future__ import annotations

import io

import chess
import chess.pgn
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "benchmark_corpus"


def write_pgn(path: Path, headers: dict, sans: list[str]) -> None:
    board = chess.Board()
    game = chess.pgn.Game(headers=headers)
    node = game
    for san in sans:
        move = board.parse_san(san)
        node = node.add_variation(move)
        board.push(move)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        exporter = chess.pgn.FileExporter(f)
        game.accept(exporter)
    # round-trip check
    text = path.read_text(encoding="utf-8")
    g = chess.pgn.read_game(io.StringIO(text))
    assert g is not None
    b = g.board()
    for m in g.mainline_moves():
        b.push(m)
    print(f"Wrote {path.name}: {len(sans)} moves, final ply {b.fullmove_number}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # Carlsen–Wang Hao, Tata Steel 2011 (chessgames / TWIC)
    gm_sans = (
        "e4 c6 d4 d5 e5 Bf5 Be3 e6 Nd2 Nd7 Ngf3 Bg6 Be2 Ne7 Nh4 c5 c3 Nc6 "
        "Nxg6 hxg6 Nf3 Rc8 O-O a6 g3 Be7 h4 b5 a4 Qb6 axb5 axb5 Kg2 c4 "
        "Ng5 Qd8 Bg4 Bxg5 Bxg5 Qc7 Rh1 Nb6 h5 gxh5 Bxh5 Na4 Bxf7+ Kxf7 "
        "Qf3+ Kg8 Rxh8+ Kxh8 Rh1+ Kg8 Qh5 Rf8 Bf6"
    ).split()

    write_pgn(
        OUT / "gm_wijk_aan_zee.pgn",
        {
            "Event": "Tata Steel Group A",
            "Site": "Wijk aan Zee NED",
            "Date": "2011.01.29",
            "White": "Carlsen, Magnus",
            "Black": "Wang Hao",
            "Result": "1-0",
            "WhiteElo": "2814",
            "BlackElo": "2730",
        },
        gm_sans,
    )

    # Club-level game: valid prefix (PGN movetext had illegal 19.Re1)
    club_sans = (
        "d4 d5 c4 e6 Nc3 Nf6 Bg5 Be7 e3 O-O Nf3 h6 Bh4 Nbd7 Rc1 c6 Bd3 dxc4 "
        "Bxc4 Nd5 Bxe7 Qxe7 O-O Nxc3 Rxc3 e5 dxe5 Nxe5 Nxe5 Qxe5 f4 Qe4 Qf3 Qxf3 "
        "Rxf3 Bd7"
    ).split()

    write_pgn(
        OUT / "club_1400.pgn",
        {
            "Event": "Online Rapid",
            "Site": "lichess.org",
            "Date": "2024.06.15",
            "White": "club_1400_white",
            "Black": "club_1400_black",
            "Result": "*",
            "WhiteElo": "1423",
            "BlackElo": "1387",
        },
        club_sans,
    )

    # Ruy Lopez spine (tests/benchmark_games.json long_20)
    rapid_uci = [
        "e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6",
        "e1g1", "f8e7", "f1e1", "b7b5", "a4b3", "d7d6", "c2c3", "e8g8",
        "h2h3", "c8b7", "d2d4", "e5d4",
    ]
    board = chess.Board()
    rapid_sans = []
    for u in rapid_uci:
        m = chess.Move.from_uci(u)
        rapid_sans.append(board.san(m))
        board.push(m)

    write_pgn(
        OUT / "rapid_600_style.pgn",
        {
            "Event": "Rapid Ruy Lopez",
            "Site": "benchmark",
            "Date": "2024.08.01",
            "White": "rapid_600_a",
            "Black": "rapid_600_b",
            "Result": "*",
            "WhiteElo": "612",
            "BlackElo": "598",
        },
        rapid_sans,
    )


if __name__ == "__main__":
    main()
