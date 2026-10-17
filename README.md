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

## Creative Director — relational concepts (local review only)

The default mode composes exactly two non-face objects: hearts, stars, crescents,
butterflies, rings, leaves, diamonds, lightning bolts, flowers and hourglasses. Shared rotation and transparent crossing contours follow the
visual language of the reference mask pair. Mask/arc modes remain available.
The planner ranks scene relationships and records unsupported ideas as development proposals.
See [CREATIVE_DIRECTOR.md](CREATIVE_DIRECTOR.md) for Hebrew setup, scene briefs and local previews.

```bash
python creative_director.py --theme paired_objects --out local_demo/concepts
```

This uses procedural composition rules; optional external-model proposals can be imported with --ideas.
The existing auto generator and daily runbook remain on pointspin.

Local series planning with diverse pairs and explicit review history:

```bash
python batch_director.py plan --out local_demo/batch_01 --count 6
```

This produces a review manifest and briefs; it does not record history or publish.
See the Hebrew guide for the explicit record command.
