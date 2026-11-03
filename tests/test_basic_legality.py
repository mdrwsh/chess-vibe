import chess
import pytest

from engine import ChessEngine


def test_starting_position_has_legal_moves():
    board = chess.Board()
    mv = ChessEngine(depth=2).best_move(board)
    assert mv in board.legal_moves


def test_engine_returns_legal_move_with_castling_rights():
    board = chess.Board("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    mv = ChessEngine(depth=2).best_move(board)
    assert mv in board.legal_moves


@pytest.mark.parametrize(
    "fen",
    [
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "r2q1rk1/pp1bbppp/2np1n2/2p1p3/2B1P3/2NP1N2/PPP2PPP/R1BQR1K1 w - - 0 10",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "4k3/8/8/8/8/8/8/4K3 w - - 0 1",
    ],
)
def test_returns_legal_move_in_varied_positions(fen):
    board = chess.Board(fen)
    mv = ChessEngine(depth=2).best_move(board)
    assert board.is_legal(mv)


def test_does_not_mutate_board():
    board = chess.Board()
    before = board.fen()
    ChessEngine(depth=2).best_move(board)
    assert board.fen() == before
    assert not board.move_stack


def test_game_over_raises():
    board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")  # stalemate
    assert board.is_game_over()
    with pytest.raises(ValueError):
        ChessEngine(depth=2).best_move(board)
