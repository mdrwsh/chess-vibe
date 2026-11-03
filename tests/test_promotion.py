import chess
import pytest

from engine import ChessEngine


@pytest.mark.parametrize(
    "fen, expected",
    [
        ("4k3/3P4/8/8/8/8/8/4K3 w - - 0 1", "d7d8"),
        ("2r1k3/3P4/8/8/8/8/8/4K3 w - - 0 1", "d7c8"),  # promotion capture
    ],
)
def test_engine_promotes_a_pawn(fen, expected):
    board = chess.Board(fen)
    mv = ChessEngine(depth=3).best_move(board)
    assert board.is_legal(mv)
    assert mv.uci()[:4] == expected
    assert mv.promotion == chess.QUEEN


def test_engine_generates_all_four_promotion_pieces():
    board = chess.Board("4k3/3P4/8/8/8/8/8/4K3 w - - 0 1")
    promotions = {
        m.promotion
        for m in board.legal_moves
        if chess.square_name(m.from_square) == "d7"
        and chess.square_name(m.to_square) == "d8"
    }
    assert promotions == {chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT}


def test_underpromotion_to_knight_is_legal_in_move_builder():
    # Mirrors the GUI's move construction for a promotion.
    board = chess.Board("4k3/3P4/8/8/8/8/8/4K3 w - - 0 1")
    mv = chess.Move(chess.D7, chess.D8, promotion=chess.KNIGHT)
    assert mv in board.legal_moves
