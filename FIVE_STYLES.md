# Five-style studio — local prototype

Exactly five account profiles route to five distinct visual families. The director
uses a finite, deterministic procedural catalogue, explicit feasibility controls,
engineering scores and a machine-readable production brief. It is not a trained
AI model and does not predict reach or virality.

| Generator | Profile | Style | Working modes | Visual identity |
|---|---|---|---|---|
| AngleSpin | opticpop | reversible_depth | tilted_pair | Two luminous, curved objects on distinct tilted axes; fixed camera; additive transparent surfaces |
| HiddenShape | unassigned_hidden_shape | hidden_stereogram | hidden_relief | One full-width repeating texture hiding a depth relief |
| StereoTwin | spiralium_ | binocular_worlds | orbital_rings, helix, constellation | Two synchronized, slightly different views of one spatial scene |
| MotionShift | hypnotorium | motion_paradox | motion_form, infinite_regress, footsteps | Motion carries form or conflicts with a controlled trajectory |
| PerceptionLab | trustyoureyes_ | perception_lab | munker_white, muller_lyer, afterimage, troxler, cafe_wall | Controlled color, length, fixation and context experiments |

`five_styles.GENERATORS` is the display-name registry used by runner help and new
render manifests. Names identify generators, not Instagram handles. Stable style
IDs and the production-brief contract are retained for history/promotion compatibility.

The four page handles supplied by the user are the local defaults; HiddenShape
keeps an explicitly unassigned fifth profile with an empty handle. Defaults are
also exported in `samples/five_styles/accounts.json`. Existing plans are not
silently reassigned: use this config or a fresh `init` config to plan new content.
These assignments do not verify or connect publishing accounts. No Instagram
accounts were created or connected. Names/handles may be edited in `accounts.json`, but all five styles
must occur exactly once and nonempty handles must be unique. Style five is an
editorial umbrella containing several mechanisms, not a claim that color
adaptation and geometric context have one neural explanation.

## Setup (Windows / macOS / Linux)

Python 3.11+; FFmpeg with libx264. Use the existing `requirements-creative.txt`:

```powershell
python -m pip install -r requirements-creative.txt
python five_styles.py init --out work/accounts.json
python five_styles.py plan --accounts work/accounts.json --per-account 3 --seed 42 --history work/five_history.json --out work/plan.json
python five_styles.py render --plan work/plan.json --preview --out work/preview_01 --history work/five_history.json --ffmpeg C:/path/to/ffmpeg.exe
```

The plan writes its ranked candidate catalogue beside it as `plan_ranking.json`.
Inspect the brief, PNG and preview. For production, render **the same plan**:

```powershell
python five_styles.py render --plan work/plan.json --out work/full_01 --history work/five_history.json --ffmpeg C:/path/to/ffmpeg.exe
python -m unittest discover -s tests
```

Use `ffmpeg` instead of the full path if it is on PATH. The repository's local
development copy, when present, is `local_demo/encoder/ffmpeg.exe`; the source
package deliberately does not redistribute that binary. Font discovery supports
Windows Arial and DejaVu Sans. No Blender, network connection, API key or model
download is required after dependency setup. Never put credentials in the account
configuration. A full batch can take several minutes per 3D clip on a CPU.

Full exports are 1080×1920, 30 fps, H.264 CRF 18, 15 seconds; fixation experiments
are 24 seconds. MP4s have no audio track. This leaves native music selection for a
separate future publishing integration. A stereogram holds its pattern still to
allow fusion; Troxler keeps its stimulus physically unchanged. These are deliberate
properties of those mechanisms. Afterimage uses 18 seconds of chromatic adaptation
and 6 seconds of genuinely gray test, with an intentional restart at the loop.
Previews are 360×640 at 15 fps and cannot establish full-resolution stereo/noise
quality. Always review full exports on the intended phone.

## Perceptual controls and reuse

* `tilted_pair` reuses `relational_scene.geometry`, rotations and the existing
  `scene_contract` shape grammar. The reference-informed fixed axes are distinct;
  near/far points keep equal brightness and neither object occludes the other.
  These are original non-face objects, not recovered meshes or camera tracks.
* `hidden_relief` reuses the existing symmetric linking routine in
  `more_illusions.autostereogram` with a new non-face relief adapter and repeated
  multitone texture. It is a parallel-view autostereogram. Hard boundaries and
  codec compression can introduce local artifacts; the unit test verifies an
  encoded constant-depth plane, not that every relief is perceived perfectly.
* Binocular modes use **parallel viewing**, unlike the legacy `crosseye` renderer.
  Both eyes use the same scene/time and off-axis cameras. Zero-plane disparity is
  zero and near/far disparity signs differ. Swapping eye views reverses depth.
  Increasing camera separation is bounded rather than used as unlimited variety.
* `motion_form` uses two independent binary fields with the same distribution,
  moving in opposite directions inside/outside a fixed silhouette. A temporal
  correspondence test recovers the shape. This is an original motion-defined form
  analogue, not Eric Lu's implementation or a security/anti-AI claim. Aperture
  boundaries and compression can still leave static cues.
* `infinite_regress` keeps Gabor envelope x coordinates fixed while the envelopes
  travel vertically and their carriers drift horizontally. It is an analogue of
  local/global integration, not a frame-exact reproduction of Tse & Hsieh's stimuli.
* `footsteps` reuses the existing MIT-attributed `illusion_lab.block_positions`.
  One displacement drives both bars; only the stripes fade for the control.
* `munker_white` uses identical gray target patches on alternate stripe contexts.
  This is a luminance White variant, not a copy of the reference's colored skulls.
  Müller-Lyer shafts have equal endpoints. Café Wall mortar lines stay horizontal.
* `afterimage` never draws the claimed residual color into the gray test. `troxler`
  never fades its patches in code. Automated pixel tests cannot establish a
  viewer's adaptation, binocular fusion, spontaneous depth reversal or effect size.

## Ranking, novelty and failure behavior

The rubric reports feasibility (25), physical control (25), viewing accessibility
(20), variation (15) and originality (15). Scores are conservative engineering
heuristics. Fine noise and dense stereo scenes receive accessibility penalties.
Candidates are ranked with stable seeded tie-breaking. Plans first cover each
mode in round-robin order, then rank variations within the mode. This explicit
diversity policy prevents easy context examples from crowding out stereo or
fixation examples. Every result remains `renderable_needs_human_review`.

Changing just seed, palette, copy or account does not change structural identity.
The catalogue is finite, and changing geometry, tilt, density, layout or motion
can still feel similar to a viewer. Exhaustion raises an error; there is no promise
of infinite perceptually unique videos. The history applies to this five-style
engine. It does **not** import older `creative_library`/`batch_director` histories,
so compare those older outputs before production on an existing account.

Rendering validates the entire plan and all account/style assignments before
encoding; unknown fields and unsupported parameters are rejected. An exclusive
history lock prevents concurrent reuse. Completed outputs have SHA-256 checksums
and atomic history writes. Existing clips/folders are never overwritten. A
preview can advance to full once, only with the identical brief digest. A full
concept cannot be rendered again through the batch path. An encoder failure
removes its partial MP4 and records no completion for that clip. Earlier completed
clips remain valid; plan a fresh folder using that same history after a failure.
Do not delete a lock while another render process is active.

## Research and development boundary

See `research/biologistmichael/REPORT_HE.md`, `coverage.json`,
`inventory_1429.csv` and `visual_audit.json`. The audit distinguishes inventory,
caption inference, detail-page visual observations and scientific interpretation.
It is not a claim that every video in the account was watched in full. Some posts
are credited to other artists; source captions are not treated as scientific proof.

The five families organize the detected examples for five brands. They do not
claim implementation of every subtype. Dual-axis rotation, Schröder stairs,
color-confetti objects, motion-induced blindness, face adaptation, hybrid image
assets, photographic forced perspective and city-flyby reconstructions remain
extensions. Existing legacy/Penrose/Ebbinghaus code is retained, but not silently
relabeled as a new implemented mode. New assets must be original or licensed.

Work sequence:

1. Inventory and representative mechanism analysis; retain unresolved cases.
2. Five-profile contract and original procedural renderers; pixel/geometry tests.
3. Full HD examples and phone review of effect, readability and compression.
4. Expand approved subtypes with a new invariant test and several distinct subjects.
5. After quality approval, choose the four actual new brands and configure handles.
6. Separately resolve the external uploader and native-audio capability; approve
   a concrete draft before enabling any scheduler or live publication.

This branch adds a separate local entry point. `generate.py` auto selection,
`RUNBOOK.md`, existing account connections, `main`, Metricool and OmniSocials jobs
are not modified or activated. No publishing or scheduler calls exist in this new
engine. Source review and user approval precede any merge or live integration.

## Primary mechanism references

* [Kinetic depth demonstration and depth-cue control](https://michaelbach.de/ot/mot-sfm/index.html)
* [Thimbleby, Inglis & Witten, 1994, authors' article](https://harold.thimbleby.net/sirds/ieee3d.pdf)
* [Ghost Font, Eric Lu's original project](https://www.mixfont.com/ghost-font)
* [Tse & Hsieh, 2006, authors' paper](https://bpb-us-e1.wpmucdn.com/sites.dartmouth.edu/dist/9/2172/files/2020/01/32.pdf)
* [Munker-White interactive control](https://michaelbach.de/ot/lum-white/index.html)
* [Café Wall interactive control](https://michaelbach.de/ot/ang-cafewall/index.html)
* [Müller-Lyer demonstration](https://michaelbach.de/ot/sze-muelue/index.html)

Brief `reference` URLs are family examples from the requested Instagram account,
not claims of code provenance. Scientific and creator references are in this
document and the audit. No Instagram media, meshes or captions are copied into
the generator. Retain `THIRD_PARTY.md` and `third_party/` notices when packaging
the reused renderer modules.
