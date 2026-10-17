"""Strict, dependency-free briefs for licensed optical-illusion adaptations."""
import copy
import hashlib
import itertools
import json
import math
import random

SOURCES = {
    "ebbinghaus": dict(repository="RealityBending/Pyllusion",
        commit="8fff53efd783e666ea29262b8d0c671c088c0453",
        path="pyllusion/Ebbinghaus/ebbinghaus_parameters.py", license="MIT"),
    "footsteps": dict(repository="altunenes/sorceress",
        commit="1186eba2af2a9e151e0712662c8315a57b4548a8", path="docs/js/steps.js", license="MIT"),
    "penrose": dict(repository="llop/penrose-triangle-js",
        commit="af94cf09cdd2900a3b9ee753cd8526db5ab94a83", path="penrose-triangle.js", license="MIT"),
}
OPTIONS = {
    "ebbinghaus": dict(target_radius=(.04,.05,.06), small_radius=(.025,.035,.045),
        large_radius=(.08,.10,.12), small_count=(8,10,12), large_count=(4,5,6), gap=(.03,.05,.07), cycles=(1,2)),
    "footsteps": dict(stripes=(12,16,20,24,28,32), bar_width=(2,3,4), lanes=(2,4),
        axis=("horizontal","vertical"), cycles=(1,2,3)),
    "penrose": dict(cubes=(4,5,6,7,8,9), fill=(.55,.65,.75,.85),
        rotation=(-30,-15,0,15,30), direction=(-1,1), cycles=(1,2,3)),
}
COPY = {
    "ebbinghaus": ("Same circles, different surroundings", "Which orange circle is larger?",
        "size_context", "Compare the two orange circles while their surroundings move. Both targets keep the same radius.",
        "The surrounding circles fade for a direct comparison, then return."),
    "footsteps": ("The footsteps that never change speed", "Are these blocks moving together?",
        "contrast_motion", "Track the yellow and blue blocks. Their positions and speed match even when the stripes suggest otherwise.",
        "The stripes fade to gray, exposing the identical motion, then return."),
    "penrose": ("Cubes on an impossible triangle", "Where does the impossible path join?",
        "impossible_occlusion", "Follow a cube around the triangle and inspect which face passes in front at the crossing.",
        "The drawing order closes a path that cannot exist as these solid cubes in ordinary 3D space."),
}
WEIGHTS = dict(feasibility=25,loop=20,mechanism=25,identity=15,novelty=15)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{label}: expected fields {sorted(keys)}")


def validate_scene(scene):
    exact(scene, ("version","family","parameters","palette"), "library scene")
    if type(scene["version"]) is not int or scene["version"] != 1:
        raise ValueError("unsupported library scene version")
    family = scene["family"]
    if not isinstance(family, str) or family not in OPTIONS:
        raise ValueError("unsupported library family")
    options = OPTIONS[family]
    exact(scene["parameters"], options, "parameters")
    for key, value in scene["parameters"].items():
        expected = options[key]
        if type(value) not in {type(v) for v in expected} or value not in expected:
            raise ValueError(f"unsupported {family} parameter: {key}")
    palettes = ("classic",) if family == "footsteps" else ("neon","ice","amber")
    if scene["palette"] not in palettes:
        raise ValueError("palette would violate the illusion's contrast constraints")
    if family == "ebbinghaus":
        p = scene["parameters"]
        for side in ("small","large"):
            r, n = p[side+"_radius"], p[side+"_count"]
            distance = p["target_radius"] + r + p["gap"]
            if 2 * distance * math.sin(math.pi/n) < 2*r*1.02:
                raise ValueError("surrounding circles would overlap")
    return scene


def novelty_key(scene):
    validate_scene(scene)
    # Speed, reversal, screen rotation and palette alone do not earn a new concept.
    structure = {k:v for k,v in scene["parameters"].items() if k not in ("cycles","direction","rotation")}
    return "library:" + digest(dict(family=scene["family"], structure=structure))


def render_spec(scene, seed):
    return dict(style="illusion_lab", scene=copy.deepcopy(scene), seed=seed,
                width=1080, height=1920, fps=30, seconds=15)


def validate_render(render):
    exact(render, ("style","scene","seed","width","height","fps","seconds"), "render")
    if render["style"] != "illusion_lab":
        raise ValueError("library scenes require illusion_lab")
    if type(render["seed"]) is not int or not 0 <= render["seed"] < 1_000_000:
        raise ValueError("seed must be an integer in 0-999999")
    for key, expected in dict(width=1080,height=1920,fps=30,seconds=15).items():
        if type(render[key]) is not int or render[key] != expected:
            raise ValueError(f"{key} must equal {expected}")
    validate_scene(render["scene"])
    return render


def idea_for(scene, seed):
    validate_render(render_spec(scene, seed))
    family = scene["family"]
    title, hook, mechanism, experience, event = COPY[family]
    return dict(id=digest(dict(scene=scene,seed=seed))[:16], title=title, family=family,
        hook=hook, viewer_experience=experience, mechanism=mechanism, observable_event=event,
        scene=copy.deepcopy(scene), seed=seed, novelty_key=novelty_key(scene),
        source=copy.deepcopy(SOURCES[family]))


def evaluate(idea):
    try:
        if not isinstance(idea, dict) or idea != idea_for(idea["scene"], idea["seed"]):
            raise ValueError("idea, signature or source does not match implemented scene")
    except (ValueError, KeyError, TypeError) as exc:
        return dict(eligible=False,total=0,status="invalid",reasons=[str(exc)])
    scores = dict(feasibility=5,loop=5,mechanism=5,identity=4,novelty=4)
    return dict(eligible=True,total=sum(scores[k]*weight/5 for k,weight in WEIGHTS.items()),status="ready_for_preview",
        scores=scores,
        reasons=["Validated against explicit renderer capabilities and loop controls",
                 "Structural signature excludes color, speed, reversal and screen rotation",
                 "Illusion strength still requires human viewing; ranking is editorial"])


def caption(idea):
    tags = ["#opticalillusion","#perception","#visualillusion","#generativeart","#opticpop"]
    return dict(full_caption=f"{idea['hook']}\n\n{idea['viewer_experience']}\n\n"+" ".join(tags),
                short_caption=idea["hook"]+"\n"+" ".join(tags),hashtags=tags)


def production_brief(idea):
    evaluation = evaluate(idea)
    if not evaluation["eligible"]:
        raise ValueError(evaluation["reasons"][0])
    return dict(schema_version=3,status="needs_human_review",publishing_allowed=False,
        idea=copy.deepcopy(idea),render=render_spec(idea["scene"],idea["seed"]),
        caption=caption(idea),evaluation=evaluation,
        direction=dict(opening=idea["hook"],event=idea["observable_event"],
                       ending="Return to opening configuration at 15 seconds",audio="Silent AAC"),
        review_checks=["Compare the illusion and its control on a phone", "Check loop and legibility"])


def validate_brief(brief):
    if not isinstance(brief, dict) or type(brief.get("schema_version")) is not int or brief["schema_version"] != 3:
        raise ValueError("unsupported library brief")
    if brief.get("publishing_allowed") is not False or brief.get("status") != "needs_human_review":
        raise ValueError("only non-publishing review briefs are accepted")
    render = validate_render(brief.get("render"))
    evaluation = evaluate(brief.get("idea"))
    if not evaluation["eligible"]:
        raise ValueError(evaluation["reasons"][0])
    if render != render_spec(brief["idea"]["scene"],brief["idea"]["seed"]) or brief.get("caption") != caption(brief["idea"]):
        raise ValueError("render or caption differs from the validated idea")
    return render


def candidates(family, seed):
    """Finite, deterministic catalogue. Exhaustion is explicit; never recycle a seed."""
    if family not in OPTIONS or type(seed) is not int or not 0 <= seed < 1_000_000:
        raise ValueError("unsupported family or seed")
    options = OPTIONS[family]
    variants = list(itertools.product(*options.values()))
    rng = random.Random(seed)
    rng.shuffle(variants)
    seen = set()
    for values in variants:
        scene = dict(version=1,family=family,parameters=dict(zip(options,values)),
                     palette="classic" if family=="footsteps" else rng.choice(("neon","ice","amber")))
        try:
            key = novelty_key(scene)
        except ValueError:
            continue
        if key in seen:
            continue
        seen.add(key)
        yield idea_for(scene,rng.randrange(1_000_000))
