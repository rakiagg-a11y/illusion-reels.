# illusion-reels

Generator for the @opticpop optical-illusion reels (1080×1920, 30 fps, Instagram-ready).

## Five-account local studio

The separate [five-style studio](FIVE_STYLES.md) routes exactly five account
profiles to distinct illusion families, with 13 procedural modes, ranked
production briefs and local-only rendering. Start with the [Hebrew setup guide](SETUP_HE.md).
Its [reference audit](research/biologistmichael/REPORT_HE.md) states the actual
inventory and visual-review coverage. This path does not activate publishing.

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
visual language of the reference mask pair. Each object has its own fixed 3D tilt;
the default pair has about 37 degrees between spin axes against a fixed camera.
Mask/arc modes remain available. Older briefs without orientation preserve their original motion.
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

## Extended illusion library

The local mixed-batch workflow combines existing tilted pairs with MIT-licensed
ports of Ebbinghaus size context, footsteps motion and impossible Penrose cubes.
It selects across families and rejects previously rendered structures, including
color/seed/speed-only repeats. Explicit preview-to-full promotion retains one concept.
See [CREATIVE_LIBRARY.md](CREATIVE_LIBRARY.md) for Hebrew setup and history handling,
and [THIRD_PARTY.md](THIRD_PARTY.md) for pinned sources, adaptations and notices.

```bash
python creative_library.py plan --count 12 --out local_demo/library_plan_01
python creative_library.py render local_demo/library_plan_01/manifest.json --out local_demo/library_preview_01
```

Outputs are local review files. The existing auto generation and posting workflow are unchanged.

## Native Instagram audio preflight

The user's requested example, `moths (over slowed)` by Navjaxx and Staarz, has a
read-only request template and brand-specific audio check. Exact audio identity,
version, artist, duration and auto-publish access must pass before a settings
preview is emitted. Unavailable audio holds the automatic route. This does not
upload, schedule, change account type or activate posting.
See [AUDIO_AUTOMATION.md](AUDIO_AUTOMATION.md) for Hebrew setup and current limits.

## OmniSocials migration

The requested target provider has a read-only native-audio adapter and trending
catalogue lookup in `omnisocials_audio.py`. It reuses the exact MOTHS request,
emits native `instagram.audio_id` settings for review, and holds mismatched or
unverified audio. It never downloads music, creates posts or changes the current
posting route. See [OMNISOCIALS_MIGRATION.md](OMNISOCIALS_MIGRATION.md) for account
connection, MCP setup, and the queue backup/review required before cutover.
