"""
Fast tactical chess engine.

Search: negamax + alpha-beta, principal-variation search, late-move
reductions, transposition table, MVV-LVA move ordering and a bounded
quiescence search. Iterative deepening with an optional time budget.

The evaluation stays material-only so the engine never has to trade
material for positional noise; all speed comes from pruning.
"""

from __future__ import annotations

import time

import chess

MATE_SCORE = 100000
INF = float("inf")

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Transposition-table bound types.
EXACT, LOWER, UPPER = 0, 1, 2

TT_MAX_ENTRIES = 400_000


class ChessEngine:
    def __init__(
        self,
        depth: int = 4,
        time_limit: float | None = None,
        quiescence_depth: int = 3,
    ) -> None:
        self.depth = depth
        self.time_limit = time_limit
        self.quiescence_depth = quiescence_depth
        self.tt: dict = {}
        self._deadline: float | None = None
        self._aborted = False
        # Search telemetry, reset at the start of every best_move() call.
        self._nodes = 0
        self._qnodes = 0
        self._tt_hits = 0
        self._moves_generated = 0
        self._moves_examined = 0
        self.last_info: dict = {}

    # ----------------------------------------------------------- evaluation
    def _piece_value(self, piece: chess.Piece) -> int:
        return PIECE_VALUES[piece.piece_type]

    def evaluate(self, board: chess.Board) -> int:
        """Material score from White's perspective (fast bitboard version)."""
        score = 0
        for piece_type, value in PIECE_VALUES.items():
            if not value:
                continue
            score += value * (
                len(board.pieces(piece_type, chess.WHITE))
                - len(board.pieces(piece_type, chess.BLACK))
            )
        return score

    def _eval_stm(self, board: chess.Board) -> int:
        """Material score from the side-to-move perspective (negamax)."""
        score = self.evaluate(board)
        return score if board.turn == chess.WHITE else -score

    # -------------------------------------------------------- move ordering
    def _move_key(self, board: chess.Board, move: chess.Move, tt_move) -> int:
        if move == tt_move:
            return 1 << 30
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            # En passant has no piece on the target square.
            victim_value = (
                PIECE_VALUES[victim.piece_type] if victim else PIECE_VALUES[chess.PAWN]
            )
            attacker = board.piece_at(move.from_square)
            attacker_value = PIECE_VALUES[attacker.piece_type] if attacker else 0
            # MVV-LVA: prefer valuable victims, then cheap attackers.
            return 100_000 + victim_value * 10 - attacker_value
        if move.promotion:
            return 90_000 + PIECE_VALUES[move.promotion]
        return 0

    def _order_moves(self, board: chess.Board, tt_move=None):
        return sorted(
            board.legal_moves,
            key=lambda m: self._move_key(board, m, tt_move),
            reverse=True,
        )

    # ------------------------------------------------------------ qsearch
    def _quiescence(self, board: chess.Board, alpha: float, beta: float, qdepth: int) -> int:
        """Search captures (and check evasions) until the position is quiet."""
        self._qnodes += 1
        if board.is_check():
            moves = self._order_moves(board)
            if not moves:
                return -MATE_SCORE + qdepth  # checkmate
            if qdepth >= self.quiescence_depth:
                return self._eval_stm(board)
        else:
            stand_pat = self._eval_stm(board)
            if stand_pat >= beta:
                return stand_pat
            if stand_pat > alpha:
                alpha = stand_pat
            if qdepth >= self.quiescence_depth:
                return stand_pat
            moves = [m for m in board.legal_moves if board.is_capture(m)]
            if not moves:
                return stand_pat
            moves.sort(
                key=lambda m: self._move_key(board, m, None), reverse=True
            )

        best = -INF
        for move in moves:
            board.push(move)
            score = -self._quiescence(board, -beta, -alpha, qdepth + 1)
            board.pop()
            if score > best:
                best = score
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
        return best

    # ------------------------------------------------------------- negamax
    def _negamax(
        self, board: chess.Board, depth: int, alpha: float, beta: float, ply: int
    ) -> int:
        self._nodes += 1
        if (
            self._deadline is not None
            and (self._nodes & 1023) == 0
            and time.perf_counter() >= self._deadline
        ):
            self._aborted = True
        if self._aborted:
            return 0

        alpha_orig = alpha
        key = board._transposition_key()
        entry = self.tt.get(key)
        tt_move = None
        if entry is not None:
            entry_depth, entry_flag, entry_score, tt_move = entry
            if entry_depth >= depth:
                if entry_flag == EXACT:
                    self._tt_hits += 1
                    return entry_score
                if entry_flag == LOWER:
                    if entry_score > alpha:
                        alpha = entry_score
                elif entry_flag == UPPER:
                    if entry_score < beta:
                        beta = entry_score
                if alpha >= beta:
                    self._tt_hits += 1
                    return entry_score

        if depth <= 0:
            return self._quiescence(board, alpha, beta, 0)

        moves = self._order_moves(board, tt_move)
        self._moves_generated += len(moves)
        if not moves:
            return (-MATE_SCORE + ply) if board.is_check() else 0

        best_score = -INF
        best_move = None
        for index, move in enumerate(moves):
            self._moves_examined += 1
            is_quiet = not board.is_capture(move) and move.promotion is None
            board.push(move)
            if index == 0:
                score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            else:
                # Late-move reduction for quiet moves late in the ordering.
                if depth >= 3 and index >= 4 and is_quiet:
                    score = -self._negamax(
                        board, depth - 2, -alpha - 1, -alpha, ply + 1
                    )
                else:
                    score = -self._negamax(
                        board, depth - 1, -alpha - 1, -alpha, ply + 1
                    )
                if alpha < score < beta:  # fail-high, re-search at full depth
                    score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break

        flag = EXACT
        if best_score <= alpha_orig:
            flag = UPPER
        elif best_score >= beta:
            flag = LOWER
        if len(self.tt) >= TT_MAX_ENTRIES:
            self.tt.clear()
        self.tt[key] = (depth, flag, best_score, best_move)
        return best_score

    # ---------------------------------------------------------- root search
    def _search_root(self, board: chess.Board, depth: int):
        key = board._transposition_key()
        entry = self.tt.get(key)
        tt_move = entry[3] if entry is not None else None
        moves = self._order_moves(board, tt_move)

        best_score = -INF
        best_move = moves[0]
        alpha, beta = -INF, INF
        completed = True
        for index, move in enumerate(moves):
            if (
                self._deadline is not None
                and index > 0
                and time.perf_counter() >= self._deadline
            ):
                completed = False
                break
            board.push(move)
            if index == 0:
                score = -self._negamax(board, depth - 1, -beta, -alpha, 1)
            else:
                score = -self._negamax(board, depth - 1, -alpha - 1, -alpha, 1)
                if alpha < score < beta:
                    score = -self._negamax(board, depth - 1, -beta, -alpha, 1)
            board.pop()

            if score > best_score:
                best_score = score
                best_move = move
            if score > alpha:
                alpha = score

        if completed:
            self.tt[key] = (depth, EXACT, best_score, best_move)
        return best_move, best_score

    def best_move(self, board: chess.Board) -> chess.Move:
        if board.is_game_over():
            raise ValueError("Game is already over")

        legal = list(board.legal_moves)
        if not legal:
            raise ValueError("No legal moves")
        if len(legal) == 1:
            self.last_info = {
                "depth": 0,
                "time": 0.0,
                "nodes": 0,
                "qnodes": 0,
                "tt_hits": 0,
                "pruning": 0.0,
                "score": 0,
            }
            return legal[0]

        start = time.perf_counter()
        self._deadline = start + self.time_limit if self.time_limit else None
        self._aborted = False
        self._nodes = 0
        self._qnodes = 0
        self._tt_hits = 0
        self._moves_generated = 0
        self._moves_examined = 0
        best = legal[0]
        best_score = 0
        reached_depth = 0
        for depth in range(1, self.depth + 1):
            move, score = self._search_root(board, depth)
            if self._aborted:
                break  # discard partial iteration
            best, best_score, reached_depth = move, score, depth
            if abs(score) >= MATE_SCORE - 1000:
                break
            if self._deadline is not None and time.perf_counter() >= self._deadline:
                break

        elapsed = time.perf_counter() - start
        examined = self._moves_examined
        generated = self._moves_generated
        self.last_info = {
            "depth": reached_depth,
            "time": elapsed,
            "nodes": self._nodes,
            "qnodes": self._qnodes,
            "tt_hits": self._tt_hits,
            "pruning": (1.0 - examined / generated) * 100.0 if generated else 0.0,
            "score": best_score,
            "move": best.uci(),
            "nps": (self._nodes + self._qnodes) / elapsed if elapsed > 0 else 0.0,
        }
        return best


def format_info(info: dict) -> str:
    """One-line human readable summary of the last search."""
    score = info["score"]
    if abs(score) >= MATE_SCORE - 1000:
        plies = MATE_SCORE - abs(score)
        mate_in = plies // 2 + 1
        score_text = f"mate in {mate_in}" if score > 0 else f"mated in {mate_in}"
    else:
        score_text = f"{score / 100:+.2f}"

    return (
        f"depth {info['depth']} | {info['move']} | eval {score_text} | "
        f"{info['time']:.2f}s | "
        f"{(info['nodes'] + info['qnodes']) / 1000:.1f}k nodes | "
        f"{info['tt_hits']} tt hits | "
        f"pruned {info['pruning']:.0f}% of generated moves"
    )


if __name__ == "__main__":
    engine = ChessEngine(depth=4)
    board = chess.Board()
    move = engine.best_move(board)
    print("Best move:", move)
    print(format_info(engine.last_info))
