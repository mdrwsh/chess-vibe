"""Performance tests: guards against the search getting slow again.

History: a plain alpha-beta version took 25.4s on the depth-4 opening move.
After adding TT / PVS / LMR / ordering it was 0.07s. These bounds are loose
on purpose so the tests stay stable on slow CI machines, but tight enough to
catch an order-of-magnitude regression.
"""

import time

import chess
import pytest

from engine import ChessEngine

OPENING = chess.Board()
MIDGAME_FEN = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
LATE_MIDGAME_FEN = "r2q1rk1/pp1bbppp/2np1n2/2p1p3/2B1P3/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 10"


def _timed_move(engine, fen):
    board = chess.Board(fen)
    start = time.perf_counter()
    move = engine.best_move(board)
    return move, time.perf_counter() - start


@pytest.mark.parametrize(
    "depth, budget_seconds",
    [
        (3, 0.5),
        (4, 2.0),
        (5, 5.0),
    ],
)
def test_opening_search_is_fast(depth, budget_seconds):
    # Was 25.4s at depth 4 before pruning; must never regress to that.
    _, elapsed = _timed_move(ChessEngine(depth=depth), OPENING.fen())
    assert elapsed < budget_seconds, f"depth {depth} opening took {elapsed:.2f}s"


def test_midgame_search_is_fast():
    _, elapsed = _timed_move(ChessEngine(depth=4), MIDGAME_FEN)
    assert elapsed < 5.0, f"midgame depth 4 took {elapsed:.2f}s"


def test_time_limited_search_returns_quickly():
    engine = ChessEngine(depth=64, time_limit=1.0)
    _, elapsed = _timed_move(engine, LATE_MIDGAME_FEN)
    assert elapsed < 1.6, f"1.0s budget took {elapsed:.2f}s"


def test_time_limited_goes_deep_quickly():
    engine = ChessEngine(depth=64, time_limit=1.0)
    _, elapsed = _timed_move(engine, OPENING.fen())
    assert elapsed < 1.6
    assert engine.last_info["depth"] >= 5, "iterative deepening should reach depth 5+ in 1s"


def test_transposition_table_gets_used():
    engine = ChessEngine(depth=5)
    engine.best_move(chess.Board())
    assert engine.last_info["tt_hits"] > 0, "TT should produce cutoffs in the opening"


def test_node_counts_are_reported():
    engine = ChessEngine(depth=4)
    engine.best_move(chess.Board())
    info = engine.last_info
    assert info["nodes"] + info["qnodes"] > 0
    assert info["nps"] > 0


def test_search_is_deterministic():
    # Same position and depth must yield the same move (no randomness, and the
    # TT is per-instance so it cannot leak between engines).
    fen = MIDGAME_FEN
    first = ChessEngine(depth=4).best_move(chess.Board(fen)).uci()
    second = ChessEngine(depth=4).best_move(chess.Board(fen)).uci()
    assert first == second
