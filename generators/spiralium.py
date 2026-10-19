"""Spiralium: MirrorFlip and StillWobble (replaces StereoTwin routing)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from account_studio import main

if __name__ == "__main__":
    main("spiralium_")
