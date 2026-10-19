"""Generator 1: two transparent objects rotating about separate tilted axes."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from single_generator import main

if __name__ == "__main__":
    main("reversible_depth")
