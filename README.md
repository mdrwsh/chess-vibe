# Chess Engine

A fast, tactical chess engine written in pure Python.  It focuses on speed and accurate tactical play by using a small but powerful search algorithm while keeping the code lean and readable.

## Features

- **Negamax search with alpha‑beta pruning** – the core search routine.
- **Principal‑variation search (PVS)** – rescans the first child with a zero‑window to cut branches early.
- **Late‑move reductions (LMR)** – reduces depth for quiet moves that come late in the ordering.
- **Transposition table** – cache of previously evaluated positions to avoid re‑searching.
- **MVV‑LVA move ordering** – captures first, then promotions, then quiet moves.
- **Bounded quiescence search** – continues searching captures until the position is quiet, up to a configurable depth.
- **Iterative deepening** with an optional hard time‑limit.  The engine stops exploring deeper depths once the deadline is reached.
- **Telemetry** – after every `best_move()` call the engine exposes a `last_info` dictionary containing:
  ```
  {
      "depth": <int>,          # deepest depth reached
      "time": <float>,        # elapsed seconds
      "nodes": <int>,         # nodes evaluated in the main search
      "qnodes": <int>,        # nodes evaluated in quiescence
      "tt_hits": <int>,       # transposition‑table hits
      "pruning": <float>,     # pruning % (0–100)
      "score": <int>,         # material score at the root
      "move": <str>,          # best UCI move string
      "nps": <float>,         # nodes per second
  }
  ```
- **Simple material‑only evaluation** – the engine uses a conventional material table and does not employ complex positional heuristics.
- **GUI support (Tkinter)** – a lightweight GUI demonstrates the engine with promotion dialogs and non‑blocking search.

## Installation

```bash
# Using Poetry (preferred)
poetry install
```

Or, with `pip`:

```bash
pip install .
```

## Usage

```python
from engine import ChessEngine
import chess

# Create an engine with depth 4 and an optional 1‑second hard time limit
engine = ChessEngine(depth=4, time_limit=1.0)

board = chess.Board()
print("Best move:", engine.best_move(board))
print("Telemetry:", engine.last_info)
```

The `best_move()` method returns a `chess.Move`; `last_info` contains telemetry as described above.

## Testing

Run the test suite with `pytest`:

```bash
pytest
```

The tests cover legality, tactical blunders, promotion handling, performance regressions, and telemetry.

## Performance

The engine was tuned to finish a depth‑4 search of a typical opening in **under 0.1 s** on a standard laptop.  In the performance test suite the following limits are enforced:

- Depth 3 opening: < 0.5 s
- Depth 4 mid‑game: < 5 s
- 1‑second time‑limited search: < 1.6 s and at least depth 5 reached
- Transposition‑table usage is verified.

All tests pass on the latest commit.

---

Feel free to fork, modify, or use this engine for your own projects.
