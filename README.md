# illusion-reels

Generator for the @opticpop optical-illusion reels (1080×1920, 30 fps, Instagram-ready).

## Styles

- `dancer`: a 3D silhouette (ballerina, cat, flamingo, T-rex, shark, butterfly) that can be seen spinning either way.
- `dots`: a dot cloud (sphere, cylinder, torus, helix) that can be seen spinning either way.
- `stereogram`: a Magic Eye picture with a hidden 3D shape, plus an answer reveal.
- `crosseye`: a side-by-side 3D pair that you merge by crossing your eyes.
- `chromo`: red/blue colour depth (chromostereopsis).
- `blackhole`: a motion-aftereffect vortex (stare, then it moves on its own).

## Usage

```bash
python3 generate.py --style auto --slot 0 --out videos/today/reel0.mp4
```

This writes an `.mp4` and a `.json` file with a ready caption (5 hashtags).

`RUNBOOK.md` describes the daily automated posting.
