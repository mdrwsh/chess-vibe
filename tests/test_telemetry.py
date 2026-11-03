"""Tests for search telemetry (depth/time/nodes/pruning) and format_info."""

import time

import chess
import pytest

from engine import ChessEngine, MATE_SCORE, format_info

REQUIRED_KEYS = {
    "depth",
    "time",
    "nodes",
    "qnodes",
    "tt_hits",
    "pruning",
    "score",
    "move",
    "nps",
}


def test_last_info_populated_after_search():
    engine = ChessEngine(depth=4)
    move = engine.best_move(chess.Board())
    info = engine.last_info
    assert set(info) == REQUIRED_KEYS
    assert info["depth"] >= 1
    assert info["time"] > 0
    assert info["move"] == move.uci()
    assert info["nodes"] > 0
    assert 0.0 <= info["pruning"] <= 100.0
    assert info["nps"] > 0


def test_depth_never_exceeds_requested():
    engine = ChessEngine(depth=3)
    engine.best_move(chess.Board())
    assert engine.last_info["depth"] <= 3


def test_single_legal_move_short_circuit():
    # White king a1 boxed in by the black king on a3; only Kb1 is legal.
    board = chess.Board("8/8/8/8/8/k7/P7/K7 w - - 0 1")
    legal = list(board.legal_moves)
    assert len(legal) == 1
    engine = ChessEngine(depth=4)
    mv = engine.best_move(board)
    assert mv.uci() == legal[0].uci() == "a1b1"
    assert engine.last_info["depth"] == 0
    assert engine.last_info["nodes"] == 0


def test_time_limit_is_respected():
    engine = ChessEngine(depth=64, time_limit=0.5)
    start = time.perf_counter()
    engine.best_move(chess.Board())
    elapsed = time.perf_counter() - start
    assert elapsed < 1.5, f"time_limit overshoot: {elapsed:.2f}s"
    assert engine.last_info["depth"] >= 4


def test_format_info_normal_position():
    engine = ChessEngine(depth=3)
    engine.best_move(chess.Board())
    text = format_info(engine.last_info)
    assert "depth" in text
    assert "s |" in text  # seconds
    assert "pruned" in text
    assert "%" in text


def test_format_info_mate_in_one_does_not_say_mate_in_zero():
    engine = ChessEngine(depth=3)
    engine.best_move(chess.Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"))
    text = format_info(engine.last_info)
    assert "mate in 1" in text
    assert "mate in 0" not in text


def test_format_info_handles_mated_side():
    info = {
        "depth": 5,
        "move": "a1a8",
        "score": -(MATE_SCORE - 1),
        "time": 0.01,
        "nodes": 10,
        "qnodes": 2,
        "tt_hits": 0,
        "pruning": 50.0,
        "nps": 1200.0,
    }
    assert "mated in 1" in format_info(info)


def test_format_info_handles_zero_time():
    info = {
        "depth": 0,
        "move": "e2e4",
        "score": 0,
        "time": 0.0,
        "nodes": 0,
        "qnodes": 0,
        "tt_hits": 0,
        "pruning": 0.0,
        "nps": 0.0,
    }
    assert isinstance(format_info(info), str)


def test_pruning_percentage_is_a_real_ratio():
    # Derived from generated vs examined moves, so a normal search reports
    # a non-zero reduction.
    engine = ChessEngine(depth=4)
    engine.best_move(chess.Board())
    assert engine.last_info["pruning"] > 0.0
