import os
import sys

# Make the project root (parent of this test folder) importable so that
# `from engine import ChessEngine` works when pytest is run from anywhere.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
