import threading

import tkinter as tk
from tkinter import messagebox
import chess
from engine import ChessEngine, format_info

# Unicode chess symbols for rendering pieces
UNICODE_PIECES = {
    "R": "♜", "N": "♞", "B": "♝", "Q": "♛", "K": "♚", "P": "♟",
    "r": "♖", "n": "♘", "b": "♗", "q": "♕", "k": "♔", "p": "♙",
}

PROMOTION_CHOICES = [
    ("Queen", chess.QUEEN),
    ("Rook", chess.ROOK),
    ("Bishop", chess.BISHOP),
    ("Knight", chess.KNIGHT),
]

class ChessGUI:
    def __init__(self, master):
        self.master = master
        master.title("Advanced Chess Engine GUI")

        self.board = chess.Board()
        # Time-budgeted so the engine never stalls; iterative deepening
        # searches as deep as it can within the budget.
        self.engine = ChessEngine(depth=64, time_limit=1.0)
        self.selected_sq = None
        self.thinking = False

        self.canvas = tk.Canvas(master, width=480, height=480)
        self.canvas.pack()

        self.status = tk.Label(master, text="Your move (White)")
        self.status.pack(fill="x")

        # Engine telemetry for the last search.
        self.info = tk.Label(master, text="", anchor="w", justify="left",
                             font=("Consolas", 9))
        self.info.pack(fill="x")

        self.draw_board()
        self.update_board()

    def draw_board(self):
        colors = ["#F0D9B5", "#B58863"]
        square_size = 60
        for rank in range(8):
            for file in range(8):
                color = colors[(rank + file) % 2]
                x1, y1 = file * square_size, rank * square_size
                x2, y2 = x1 + square_size, y1 + square_size
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, tags="square")
        self.canvas.bind("<Button-1>", self.on_click)

    def update_board(self):
        self.canvas.delete("piece")
        for sq, piece in self.board.piece_map().items():
            char = piece.symbol()
            symbol = UNICODE_PIECES.get(char, "?")
            x = chess.square_file(sq) * 60 + 30
            y = (7 - chess.square_rank(sq)) * 60 + 30
            self.canvas.create_text(x, y, text=symbol, font=("Arial", 32), tags="piece")

    def on_click(self, event):
        if self.thinking or self.board.is_game_over():
            return
        file_ = event.x // 60
        rank_ = 7 - (event.y // 60)
        if 0 <= file_ < 8 and 0 <= rank_ < 8:
            sq = chess.square(file_, rank_)
            if self.selected_sq is None:
                piece = self.board.piece_at(sq)
                if piece and piece.color == chess.WHITE:
                    self.selected_sq = sq
                    self.highlight_square(sq)
            else:
                move = self._build_move(self.selected_sq, sq)
                if move is not None and move in self.board.legal_moves:
                    self.board.push(move)
                    self.update_board()
                    self.selected_sq = None
                    self.canvas.delete("highlight")
                    if not self.board.is_game_over():
                        self.engine_move()
                    else:
                        self.show_result()
                else:
                    self.selected_sq = None
                    self.canvas.delete("highlight")

    def _build_move(self, from_sq, to_sq):
        """Build a move, asking which piece on pawn promotion. None = invalid."""
        piece = self.board.piece_at(from_sq)
        if (
            piece is not None
            and piece.piece_type == chess.PAWN
            and chess.square_rank(to_sq) in (0, 7)
        ):
            promotion = self._ask_promotion()
            if promotion is None:
                return None
            return chess.Move(from_sq, to_sq, promotion=promotion)
        return chess.Move(from_sq, to_sq)

    def _ask_promotion(self):
        dialog = tk.Toplevel(self.master)
        dialog.title("Promote pawn")
        dialog.transient(self.master)
        dialog.resizable(False, False)
        choice = {"value": None}

        tk.Label(dialog, text="Promote to:", font=("Arial", 11)).pack(padx=12, pady=(12, 6))
        buttons = tk.Frame(dialog)
        buttons.pack(padx=12, pady=(0, 12))

        def pick(value):
            choice["value"] = value
            dialog.destroy()

        for label, piece_type in PROMOTION_CHOICES:
            symbol = UNICODE_PIECES[chess.Piece(piece_type, chess.WHITE).symbol()]
            tk.Button(
                buttons, text=f"{symbol} {label}", width=10,
                command=lambda p=piece_type: pick(p),
            ).pack(side="left", padx=3)

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        # Keep focus and block input until a choice is made.
        dialog.grab_set()
        self.master.wait_window(dialog)
        return choice["value"]

    def highlight_square(self, sq):
        x = chess.square_file(sq) * 60
        y = (7 - chess.square_rank(sq)) * 60
        self.canvas.create_rectangle(x, y, x+60, y+60, outline="red", width=3, tags="highlight")

    def engine_move(self):
        self.thinking = True
        self.status.config(text="Engine thinking...")
        board_copy = self.board.copy()
        threading.Thread(target=self._search, args=(board_copy,), daemon=True).start()

    def _search(self, board):
        """Runs on a worker thread; must not touch Tk widgets."""
        try:
            move = self.engine.best_move(board)
            # Snapshot telemetry on the worker thread; Tk reads it later.
            info = dict(self.engine.last_info)
            self.master.after(0, self._apply_engine_move, move, None, info)
        except Exception as e:
            self.master.after(0, self._apply_engine_move, None, str(e), None)

    def _apply_engine_move(self, move, error, info):
        """Runs on the Tk main thread."""
        self.thinking = False
        if error:
            print(f"Engine error: {error}")
            self.status.config(text="Engine error")
            return
        self.board.push(move)
        self.update_board()
        if info:
            # self.info.config(text=format_info(info))
            print(format_info(info))
        if self.board.is_game_over():
            self.show_result()
        else:
            self.status.config(text="Your move (White)")

    def show_result(self):
        result = self.board.result()
        self.status.config(text=f"Game over: {result}")
        messagebox.showinfo("Result", f"Game Over! Result: {result}")

root = tk.Tk()
app = ChessGUI(root)
root.mainloop()
