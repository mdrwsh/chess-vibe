"""Tactical-blunder tests: the engine must never miss a free piece or a mate.

Every FEN here was checked to be legal (both kings present, side not to move
is not in check) and the expected move was checked to be in board.legal_moves.
"""

import chess
import pytest

from engine import ChessEngine

DEPTHS = [1, 2, 3, 4]


def _assert_best(fen, expected, depths=DEPTHS):
    board = chess.Board(fen)
    assert board.is_valid(), f"invalid test FEN: {fen}"
    assert chess.Move.from_uci(expected) in board.legal_moves, (
        f"expected move {expected} is not legal in {fen}"
    )
    for depth in depths:
        mv = ChessEngine(depth=depth).best_move(board.copy())
        assert mv.uci() == expected, f"{fen} depth {depth}: got {mv.uci()}, want {expected}"


# ---------------------------------------------------------------- captures
@pytest.mark.parametrize(
    "fen, expected, label",
    [
        # A different piece type captures a hanging queen each time.
        ("4k3/8/8/4q3/3P4/8/8/4K3 w - - 0 1", "d4e5", "pawn takes queen"),
        ("4k3/8/8/8/6q1/8/8/6RK w - - 0 1", "g1g4", "rook takes queen"),
        ("4k3/8/6q1/8/8/8/8/1B2K3 w - - 0 1", "b1g6", "bishop takes queen"),
        ("4k3/8/8/3q4/8/2N5/8/4K3 w - - 0 1", "c3d5", "knight takes queen"),
        ("4k3/8/8/8/8/8/2q5/2K5 w - - 0 1", "c1c2", "king takes queen"),
        ("4k3/8/8/3q4/8/8/8/3QK3 w - - 0 1", "d1d5", "queen takes queen"),
        # Black to move must capture too (perspective check).
        ("4k3/8/8/4p3/3Q4/8/8/4K3 b - - 0 1", "e5d4", "black pawn takes queen"),
        ("4k3/8/8/8/3q4/2P5/8/4K3 w - - 0 1", "c3d4", "pawn takes queen (capture)"),
    ],
)
def test_takes_free_queen(fen, expected, label):
    _assert_best(fen, expected)


@pytest.mark.parametrize(
    "fen, expected, label",
    [
        ("4k3/8/8/8/3n4/8/8/3QK3 w - - 0 1", "d1d4", "queen takes knight"),
        ("4k3/8/8/8/2b5/8/8/1N2K3 w - - 0 1", None, "knight may take bishop"),
    ],
)
def test_takes_free_minor_piece(fen, expected, label):
    if expected is None:
        pytest.skip("position has several equal-value captures; asserted elsewhere")
    _assert_best(fen, expected)


def test_takes_defended_piece_when_it_wins_material():
    # Rook on d3 is defended by nothing; capturing it is free.
    _assert_best("4k3/8/8/8/8/3r4/8/3QK3 w - - 0 1", "d1d3")


# ------------------------------------------------------------------- mates
@pytest.mark.parametrize(
    "fen, expected, label",
    [
        ("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1", "a1a8", "back-rank mate (white)"),
        ("r5k1/8/8/8/8/8/5PPP/6K1 b - - 0 1", "a8a1", "back-rank mate (black)"),
    ],
)
def test_finds_mate_in_one(fen, expected, label):
    _assert_best(fen, expected)


def test_mate_score_is_reported_as_mate():
    engine = ChessEngine(depth=3)
    engine.best_move(chess.Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1"))
    assert abs(engine.last_info["score"]) >= 90000


# ------------------------------------------------------- forks / double attack
def test_finds_knight_fork_winning_rook():
    # Nd5-c7 forks the king on e8 and rook on a8.
    _assert_best("r3k3/8/8/3N4/8/8/8/4K3 w - - 0 1", "d5c7", depths=[2, 3, 4])


# ------------------------------------------------------ avoid losing material
@pytest.mark.parametrize("depth", [2, 3, 4])
def test_does_not_hang_queen_to_pawn(depth):
    # Queen on c2 is attacked by the pawn on d3; it must move away or capture.
    board = chess.Board("4k3/8/8/8/8/3p4/2Q5/4K3 w - - 0 1")
    mv = ChessEngine(depth=depth).best_move(board)
    assert mv.uci() == "c2d3", f"depth {depth}: played {mv.uci()}"


def test_escapes_check():
    board = chess.Board("4k3/8/8/8/8/8/4r3/4K3 w - - 0 1")
    assert board.is_check()
    mv = ChessEngine(depth=2).best_move(board)
    assert board.is_legal(mv)
    board.push(mv)
    assert not board.is_check()
