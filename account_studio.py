"""Approved account routing and local-only production briefs (Python, no Blender).

Legacy rendering contracts are imported intact. TrustYourEyes is intentionally
absent: its entry point, defaults, assets and history semantics stay with Claude.
"""
import argparse
import copy
from functools import lru_cache
import hashlib
import importlib
import json
from pathlib import Path
import random
import secrets
import shutil
import subprocess
import uuid

import five_styles as legacy
from five_style_render import (Renderer as LegacyRenderer, atomic_json, centered,
                               encode, history_lock, load_history, render_one as render_legacy)

ROUTES = {
    "hypnotorium": ("color_echo", "face_flash"),
    "spiralium_": ("mirror_flip", "still_wobble"),
    "opticpop": ("bistable_spin", "tilted_pair", "depth_flip"),
}
NAMES = dict(color_echo="ColorEcho", face_flash="FaceFlash", mirror_flip="MirrorFlip",
             still_wobble="StillWobble", depth_flip="DepthFlip",
             bistable_spin="AngleSpin", tilted_pair="AngleSpin")
MODULES = dict(color_echo="account_color_face", face_flash="account_color_face",
               mirror_flip="account_mirror_wobble", still_wobble="account_mirror_wobble",
               depth_flip="account_depth_flip")
COPY = {
    "color_echo": ("Can your eyes bring back the color?", "Keep looking at the center dot.", "18 seconds of color, then grayscale."),
    "face_flash": ("Keep your eyes on the center cross", "Let the faces stay in your side vision.", "Illustrated faces; the images are not warped."),
    "mirror_flip": ("Two faces, or one vase?", "Switch between the light and dark shapes.", "An original figure / ground illusion."),
    "still_wobble": ("Does the center seem to move?", "Gently move your phone a little.", "Every frame of this pattern is identical."),
    "depth_flip": ("Inside a bowl, or outside a sphere?", "Can you reverse the depth in your mind?", "One continuous turn. No direction switch."),
}
# Public counters are rounded snapshots, not expected performance or share data.
REFERENCES = {
    "depth_flip": dict(reel="DebEtM_uAdj", likes_display="3.9M", comments_display="29.5K"),
    "mirror_flip": dict(reel="DKanwbnS2JR", likes_display="3.5M", comments_display="12.2K"),
    "face_flash": dict(reel="DFrbrWMxBB6", likes_display="1.7M", comments_display="14.4K"),
    "color_echo": dict(reel="C-MtvEAx5mF", likes_display="2.4M", comments_display="18.8K"),
    "still_wobble": dict(reel="DNEnh7iScpb", likes_display="551.6K", comments_display="5.3K"),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


@lru_cache(maxsize=7)
def _catalog(mode):
    if mode in MODULES:
        return tuple(importlib.import_module(MODULES[mode]).parameters_for(mode))
    if mode in ROUTES["opticpop"]:
        return tuple(legacy.parameters_for(mode))
    raise ValueError("unknown account generator mode")


def parameters_for(mode):
    return copy.deepcopy(list(_catalog(mode)))


def validate_route(account, mode=None):
    if not isinstance(account, str) or account not in ROUTES:
        raise ValueError("account is outside these approved routes; TrustYourEyes is managed separately")
    if mode is not None and (not isinstance(mode, str) or mode not in ROUTES[account]):
        raise ValueError("mode belongs to a different generator; old Hypno/Spiral modes have been replaced")


def structural_key(mode, parameters):
    if mode in ("bistable_spin", "tilted_pair"):
        return legacy.structural_key("reversible_depth", mode, parameters)
    return digest(dict(contract="account_optics_v1", mode=mode, parameters=parameters))


def evaluate(mode, parameters):
    # Scores describe implementation properties, never audience or virality.
    scores = dict(python_feasibility=5, mechanism_controls=5, original_assets=5,
                  perceptual_validation=2 if mode == "face_flash" else 3)
    return dict(basis="Engineering checklist; human perception not automatically verified. Not a performance prediction.",
                scores=scores, total=sum(scores.values()), maximum=20,
                requires_visual_approval=True)


def make_brief(account, mode, parameters, seed):
    validate_route(account, mode)
    if type(seed) is not int or not 0 <= seed < 1_000_000:
        raise ValueError("seed must be an integer in 0-999999")
    if not isinstance(parameters, dict) or json.dumps(parameters, sort_keys=True) not in {
            json.dumps(p, sort_keys=True) for p in _catalog(mode)}:
        raise ValueError("parameters are outside the structural catalogue")
    parameters = copy.deepcopy(parameters)
    # Reuse the existing production brief unchanged for both existing OpticPop modes.
    old = None
    if mode not in MODULES:
        profile = next(a for a in legacy.default_accounts()["accounts"] if a["id"] == account)
        old = legacy.make_brief(profile, mode, parameters, seed)
        seconds = old["render"]["seconds"]
        mechanism = dict(mechanism="existing AngleSpin geometry", control="existing renderer and tests retained")
        caption = old["caption"]
        reference = dict(status="existing generator retained")
    else:
        module = importlib.import_module(MODULES[mode])
        seconds = module.seconds_for(mode)
        mechanism = module.describe(mode, parameters)
        caption = dict(hook=COPY[mode][0], instruction=COPY[mode][1],
                       text="\n".join(COPY[mode])+"\n@"+account,
                       hashtags=["#OpticalIllusion", "#VisualPerception", "#"+NAMES[mode]])
        reference = dict(REFERENCES[mode], shares=None, measured_date="2026-10-19",
            url="https://www.instagram.com/biologistmichael/reel/"+REFERENCES[mode]["reel"]+"/",
            interpretation="Inspiration and rounded public counters only; original procedural analogue, no media copied. No shares ranking or causal prediction.")
    return dict(kind="account_production_brief", version=1, account=account, handle="@"+account,
        mode=mode, generator=NAMES[mode], parameters=parameters, seed=seed,
        id=structural_key(mode, parameters)[:16],
        render=dict(width=1080, height=1920, fps=30, seconds=seconds),
        mechanism=mechanism, caption=caption, evaluation=evaluate(mode, parameters), reference=reference,
        legacy_brief=old, local_only=True, publishing_allowed=False, review_status="pending_visual_approval")


def validate_brief(value):
    if not isinstance(value, dict) or value.get("kind") != "account_production_brief":
        raise ValueError("brief belongs to a different generator contract")
    try:
        canonical = make_brief(value["account"], value["mode"], value["parameters"], value["seed"])
    except (KeyError, TypeError) as e:
        raise ValueError("invalid production brief") from e
    if type(value.get("version")) is not int or digest(value) != digest(canonical):
        raise ValueError("production brief was modified or contains unsupported settings")
    return value


def plan(account, count=6, seed=42, used=(), mode=None):
    validate_route(account, mode)
    if type(count) is not int or not 1 <= count <= 744:
        raise ValueError("count must be in 1-744")
    if type(seed) is not int or not 0 <= seed < 1_000_000:
        raise ValueError("seed must be in 0-999999")
    seen, rng = set(used), random.Random(seed)
    pools = {}
    for name in ((mode,) if mode else ROUTES[account]):
        rows = parameters_for(name)
        rng.shuffle(rows)
        rows.sort(key=lambda p: -evaluate(name, p)["total"])
        pools[name] = [p for p in rows if structural_key(name, p) not in seen]
    # Equal coverage of approved modes; no ranking can silently starve a mode.
    briefs = []
    while len(briefs) < count:
        progress = False
        # Balance across separate one-video invocations too, not just a batch.
        ordered = sorted(pools, key=lambda name: len(_catalog(name))-len(pools[name]))
        for name in ordered:
            rows = pools[name]
            if not rows:
                continue
            p = rows.pop()
            briefs.append(make_brief(account, name, p, (seed+len(briefs)) % 1_000_000))
            seen.add(structural_key(name, p))
            progress = True
            if len(briefs) == count:
                break
        if not progress:
            raise ValueError("structural catalogue exhausted; add geometry, do not recycle seeds or colors")
    return dict(kind="account_production_plan", version=1, account=account, local_only=True,
                selection="equal mode coverage, then engineering checklist within mode", briefs=briefs)


class Renderer:
    def __init__(self, brief, width=1080, height=1920):
        from PIL import Image
        validate_brief(brief)
        if width < 180 or width*16 != height*9:
            raise ValueError("render dimensions must be portrait 9:16")
        self.b, self.w, self.h = brief, width, height
        self.seconds = brief["render"]["seconds"]
        self.legacy = LegacyRenderer(brief["legacy_brief"], width, height) if brief["legacy_brief"] else None
        if not self.legacy:
            self.size = round(width*.86)
            module = importlib.import_module(MODULES[brief["mode"]])
            self.stimulus = module.Stimulus(brief["mode"], brief["parameters"], brief["seed"], self.size)

    def frame(self, t):
        from PIL import Image, ImageDraw
        if self.legacy:
            return self.legacy.frame(t)
        image = Image.new("RGB", (self.w, self.h), (7, 10, 18))
        draw = ImageDraw.Draw(image)
        hook, instruction, detail = COPY[self.b["mode"]]
        centered(draw, hook, self.h*.16, self.w, ratio=.042)
        centered(draw, instruction, self.h*.20, self.w, ratio=.031)
        image.paste(self.stimulus.frame(t), ((self.w-self.size)//2, round(self.h*.255)))
        # Static wording even in adaptation mode: the observer's gaze stays put.
        centered(draw, detail, self.h*.755, self.w, (170, 181, 200), .026)
        centered(draw, self.b["handle"]+"  /  "+self.b["generator"], self.h*.79, self.w, (135, 151, 175), .027)
        return image


def encode_with_phase_boundary(renderer, target, fps, ffmpeg):
    """Restart prediction at the achromatic test; avoid retained adapter chroma.

    The shared encoder remains unchanged for every other mode, including all
    TrustYourEyes/Brainrot and historical OpticPop work.
    """
    if renderer.b['mode'] != 'color_echo':
        return encode(renderer, target, fps, ffmpeg)
    target = Path(target)
    exe = shutil.which(ffmpeg)
    if target.exists() or exe is None:
        raise ValueError('choose a new output file and provide a working FFmpeg path')
    temporary = target.with_name(target.stem+'.'+uuid.uuid4().hex+'.partial.mp4')
    error_file = temporary.with_suffix('.log')
    try:
        with error_file.open('wb') as err:
            proc = subprocess.Popen([exe, '-n', '-loglevel', 'error', '-f', 'rawvideo',
                '-pix_fmt', 'rgb24', '-s', f'{renderer.w}x{renderer.h}', '-r', str(fps), '-i', '-',
                '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
                '-force_key_frames', '18', '-movflags', '+faststart', str(temporary)],
                stdin=subprocess.PIPE, stderr=err)
            try:
                for i in range(renderer.seconds*fps):
                    proc.stdin.write(renderer.frame(i/fps).tobytes())
            except BaseException:
                proc.stdin.close(); proc.terminate(); proc.wait()
                raise
            proc.stdin.close()
            if proc.wait() != 0:
                raise RuntimeError('encoding failed: '+error_file.read_text(encoding='utf-8', errors='replace')[-1000:])
        if not temporary.exists() or temporary.stat().st_size < 1000:
            raise RuntimeError('encoder produced no usable file')
        temporary.rename(target)
    finally:
        temporary.unlink(missing_ok=True)
        error_file.unlink(missing_ok=True)


def render_brief(brief, output, history_path, preview=False, ffmpeg="ffmpeg"):
    validate_brief(brief)
    output, quality = Path(output), "preview" if preview else "full"
    if output.exists():
        raise ValueError("choose a new output folder")
    key = structural_key(brief["mode"], brief["parameters"])
    with history_lock(history_path):
        history = load_history(history_path)
        previous = [e for e in history["entries"] if e["key"] == key]
        if any(e["quality"] in (quality, "full") for e in previous):
            raise ValueError("concept already rendered")
        if any(e["brief_digest"] != digest(brief) for e in previous):
            raise ValueError("preview promotion requires the identical reviewed brief")
        for e in previous:
            path = Path(e["output"])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != e["sha256"]:
                raise ValueError("preview missing or checksum changed")
        output.mkdir(parents=True)
        target = output/(brief["account"]+"_"+brief["id"]+".mp4")
        w, h, fps = (360, 640, 15) if preview else (1080, 1920, 30)
        renderer = Renderer(brief, w, h)
        encode_with_phase_boundary(renderer, target, fps, ffmpeg)
        renderer.frame(2).save(target.with_suffix(".png"))
        atomic_json(target.with_suffix(".json"), brief)
        checksum = hashlib.sha256(target.read_bytes()).hexdigest()
        history["entries"].append(dict(key=key, brief_digest=digest(brief), quality=quality,
            sha256=checksum, output=str(target.resolve())))
        atomic_json(history_path, history)
        manifest = dict(kind="account_local_render", version=1, account=brief["account"], mode=brief["mode"],
            generator=brief["generator"], quality=quality, width=w, height=h, fps=fps,
            seconds=renderer.seconds, video=target.name, poster=target.with_suffix(".png").name,
            brief=target.with_suffix(".json").name, sha256=checksum,
            review_status="pending_visual_approval", publishing_allowed=False, local_only=True)
        atomic_json(output/"manifest.json", manifest)
        return manifest


def main(fixed_account=None):
    ap = argparse.ArgumentParser(description="Current approved account generators; local review only. Old Hypno/Spiral generation is replaced.")
    if fixed_account:
        validate_route(fixed_account)
        ap.description += " Account: @"+fixed_account
    else:
        ap.add_argument("--account", required=True, choices=ROUTES)
    modes = ROUTES[fixed_account] if fixed_account else tuple(NAMES)
    ap.add_argument("--mode", choices=modes)
    ap.add_argument("--out", required=True, help="new output directory (or new JSON file with --plan)")
    ap.add_argument("--history", default=str(Path(__file__).resolve().parent/"local_demo"/"ready_generators_history.json"))
    ap.add_argument("--seed", type=int)
    ap.add_argument("--brief", help="exact reviewed account brief; no overrides")
    ap.add_argument("--plan", action="store_true", help="write production briefs only")
    ap.add_argument("--count", type=int, default=6, help="brief count for --plan; not a posting schedule")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()
    account = fixed_account or a.account
    try:
        validate_route(account, a.mode)
        if a.brief:
            if a.seed is not None or a.mode is not None or a.plan:
                raise ValueError("--brief cannot be combined with seed, mode or plan")
            raw = json.loads(Path(a.brief).read_text(encoding="utf-8-sig"))
            # Preserve exact-brief promotion for OpticPop previews created before
            # this addition, including the original digest and shared history.
            if account == "opticpop" and isinstance(raw, dict) and raw.get("kind") == "five_style_production_brief":
                legacy.validate_brief(raw)
                if raw["account"]["id"] != account or raw["style"] != "reversible_depth":
                    raise ValueError("brief belongs to a different generator account")
                print(json.dumps(render_legacy(raw, a.out, a.history, a.preview, a.ffmpeg)))
                return
            brief = validate_brief(raw)
            if brief["account"] != account:
                raise ValueError("brief belongs to a different generator account")
        else:
            history = load_history(a.history)
            proposal = plan(account, a.count if a.plan else 1,
                a.seed if a.seed is not None else secrets.randbelow(1_000_000),
                [e["key"] for e in history["entries"]], a.mode)
            if a.plan:
                target = Path(a.out)
                if target.exists():
                    raise ValueError("choose a new plan file")
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_json(target, proposal)
                print(str(target.resolve()))
                return
            brief = proposal["briefs"][0]
        print(json.dumps(render_brief(brief, a.out, a.history, a.preview, a.ffmpeg)))
    except (ValueError, OSError, RuntimeError) as error:
        ap.error(str(error))


if __name__ == "__main__":
    main()
