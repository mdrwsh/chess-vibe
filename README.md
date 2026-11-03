# README.md
# Simple Chess Engine

This repository contains a very small chess engine written in Python.  The engine:

* Uses the `python-chess` library for board representation.
* Implements a plain **minimax** search with a configurable depth.
* Uses a classic material evaluation function.
* Comes with a basic test suite to ensure it can generate legal moves.

> **Important** – The engine is *designed* to be extremely
> lightweight.  With a depth of 2 plies (one full move + reply), it
> will *not* be able to challenge an experienced human player.
></details>

## Installation

```bash
# Using Poetry (preferred)
poetry install
```

Alternatively, with pip:

```bash
pip install .
```

## Running the Engine

```python
from engine import ChessEngine
import chess

engine = ChessEngine(depth=2)
board = chess.Board()
print("Best move:", engine.best_move(board))
```

## Testing

```bash
pytest
```
