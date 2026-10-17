"""Concept-first OpticPop planning: relationships, perceptual intent and honest feasibility."""
import copy
import hashlib
import json
import random
from scene_contract import IDENTITY, entity, scene, validate_render, validate_scene, mechanism_for

VERSION = 2
THEMES = {"duality": "duality", "emotion": "emotion", "identity": "identity", "geometry": "geometry",
          "רגש": "emotion", "זהות": "identity", "ניגודים": "duality", "גאומטריה": "geometry",
          "perception": "duality"}
WEIGHTS = dict(mechanism=20, relationship=20, identity=15, novelty=15, feasibility=20, theme_fit=10)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:16]


def novelty_key(idea):
    """Colors, seed and copy changes alone do not count as a new concept."""
    s = idea.get("scene")
    if s is None:
        return digest(idea.get("requirements", []))
    geometry = [dict(shape=e["shape"], expression=e["expression"], center=e["center"],
                     turns=e["turns"], phase=e["phase"], scale=e["scale"]) for e in s["entities"]]
    return digest(dict(mechanism=idea["illusion"]["mechanism"], layout=s["layout"], entities=geometry))


def render_spec(specification, seed):
    return dict(style="opticpop", seed=seed, seconds=15, width=1080, height=1920,
                fps=30, scene=copy.deepcopy(specification))


def caption(idea):
    tags = ["#opticalillusion", "#perception", "#visualillusion", "#generativeart", "#opticpop"]
    hook = idea["hook"]
    full = (f"{hook}\n\n{idea['viewer_experience']}\n\n"
            f"{idea['illusion']['question']}\n\n{' '.join(tags)}")
    return dict(full_caption=full, short_caption=hook + "\n.\n" + " ".join(tags), hashtags=tags)


def describe(specification, seed, theme):
    entities = specification["entities"]
    masks = [e for e in entities if e["shape"] == "mask"]
    mechanism = mechanism_for(specification)
    counter = len({e["turns"] for e in entities}) > 1
    if not masks:
        title = "The circle that belongs to neither half"
        hook = "One circle, or two passing halves?"
        premise = "Two incomplete luminous arcs intermittently project into a complete outline."
        experience = "Follow one colored half as the outline closes and opens during the turn."
        question = "When the outline closes, do you see one object or two?"
        event = "Complementary semicircles align in projection, then separate into narrow profiles."
        withheld = "Opaque surface and stable ownership of the shared contour"
    elif len(masks) != len(entities):
        title = "The face inside the broken halo"
        hook = "Is the ring in front of the face?"
        premise = "A convex face and a broken halo overlap without hiding one another."
        experience = "Track the face and the arc separately, then watch their overlapping contour."
        question = "Which surface feels closer to you?"
        event = "A curved mask passes through the projected outline of an open arc."
        withheld = "Occlusion at the face/halo intersection"
    else:
        moods = {e["expression"] for e in masks}
        title = ("A smile passing through a frown" if {"smile", "frown"} <= moods
                 else "The face and its untrustworthy echo")
        if len(masks) == 3:
            title = "Three expressions, no stable front"
        elif counter:
            title += " — opposing turns" if entities[0]["turns"] * entities[1]["turns"] < 0 else " — different tempos"
        hook = "Which face is in front?"
        premise = f"{len(masks)} transparent convex masks share the same visual space."
        experience = "Follow one expression as the masks overlap; the near/far interpretation may change."
        question = "Can you keep the same face in front throughout the loop?"
        event = "Distinct facial contours overlap, separate into profiles, and return."
        withheld = "Front/back occlusion, shading differences and perspective size cues"
    motions = ", ".join(f"{e['color']} {e['expression'] or e['shape']} at {e['turns']} relative turns" for e in entities)
    premise += " Motion: " + motions + "."
    idea = dict(id="", title=title, theme=theme, premise=premise, hook=hook,
                viewer_experience=experience,
                illusion=dict(mechanism=mechanism, cue_withheld=withheld, question=question,
                              observable_event=event),
                visual_identity=IDENTITY.copy(), scene=specification, seed=seed,
                requirements=[], source="compositional_rules_v2",
                authorship_note="Reference-inspired procedural concept; uniqueness is not externally verified.")
    idea["id"] = digest(dict(scene=specification, seed=seed, theme=theme))
    idea["novelty_key"] = novelty_key(idea)
    return idea


def generate_concepts(seed=42, theme="duality", count=12):
    if theme not in THEMES:
        raise ValueError(f"theme must be one of {', '.join(THEMES)}")
    if type(seed) is not int or not 0 <= seed < 1_000_000:
        raise ValueError("seed must be an integer in 0-999999")
    if type(count) is not int or not 4 <= count <= 40:
        raise ValueError("count must be an integer in 4-40")
    theme = THEMES[theme]
    rng = random.Random(seed)
    palettes = [("coral", "electric_blue"), ("cyan", "violet"), ("amber", "electric_blue")]
    mood_pairs = {"emotion": [("smile", "frown"), ("neutral", "frown"), ("smile", "neutral")],
                  "identity": [("neutral", "neutral"), ("smile", "smile"), ("frown", "frown")],
                  "duality": [("smile", "frown"), ("neutral", "smile")],
                  "geometry": [("neutral", "neutral")]}[theme]
    concepts, seen = [], set()
    # The first candidate deliberately anchors the requested overlapping-mask family.
    attempts = 0
    while len(concepts) < count - 2 and attempts < 500:
        k = attempts
        attempts += 1
        family = "masks" if k == 0 else rng.choice(
            ["arcs", "arcs", "mixed", "masks"] if theme == "geometry" else
            ["masks", "masks", "mixed", "arcs"])
        colors = ("coral", "electric_blue") if k == 0 else rng.choice(palettes)
        turns = (1, 1) if k == 0 else rng.choice([(1, 1), (1, -1), (1, 2)])
        if family == "arcs":
            entities = [entity("arc", None, colors[0], turns=1, phase=0),
                        entity("arc", None, colors[1], turns=-1, phase=180)]
            specification = scene(entities, "coaxial")
        else:
            moods = mood_pairs[0] if k == 0 else rng.choice(mood_pairs)
            spacing = .28 if k == 0 else rng.choice([.20, .28, .38])
            entities = [
                entity("mask", moods[0], colors[0], [-.18, spacing, -.32], turns=turns[0]),
                entity("mask" if family == "masks" else "arc",
                       moods[1] if family == "masks" else None, colors[1],
                       [.18, -spacing, .32], turns=turns[1])]
            if k > 0 and family == "masks" and rng.random() < .2:
                entities.append(entity("mask", "neutral", "cyan", [0, 0, 0], turns=-1, scale=.7))
            specification = scene(entities)
        idea = describe(specification, rng.randrange(1_000_000), theme)
        if idea["novelty_key"] not in seen:
            concepts.append(idea)
            seen.add(idea["novelty_key"])
    # Keep ambitious ideas visible as development proposals, never silently substitute a cube.
    proposals = [
        ("Two profiles hiding a third identity", "negative_space_face",
         "Two side profiles enclose the silhouette of a third frontal face.",
         ["profile_contour_geometry", "negative_space_alignment_solver"]),
        ("The ribbon that changes its inside", "topology_ambiguity",
         "Two luminous ribbons appear to exchange their inner and outer surfaces.",
         ["ribbon_surface_geometry", "controlled_topology_projection"])
    ]
    for title, mechanism, premise, requirements in proposals:
        idea = dict(id=digest([seed, mechanism, theme]), title=title, theme=theme, premise=premise,
                    hook="What changes when the shapes meet?",
                    viewer_experience=premise,
                    illusion=dict(mechanism=mechanism, cue_withheld="Stable contour ownership",
                                  question="Which interpretation do you see?",
                                  observable_event=premise),
                    visual_identity=IDENTITY.copy(), scene=None, seed=rng.randrange(1_000_000),
                    requirements=requirements, source="compositional_rules_v2",
                    authorship_note="Development proposal; effect has not been implemented.")
        idea["novelty_key"] = novelty_key(idea)
        concepts.append(idea)
    return concepts


def evaluate(idea, recent=()):
    try:
        if not isinstance(idea, dict):
            raise ValueError("concept must be an object")
        for key in ("id", "title", "theme", "premise", "hook", "viewer_experience"):
            if not isinstance(idea.get(key), str) or not 1 <= len(idea[key].strip()) <= 500:
                raise ValueError(f"{key} must contain 1-500 characters")
        if len(idea["hook"]) > 52:
            raise ValueError("hook must fit in 52 characters")
        illusion = idea.get("illusion")
        if not isinstance(illusion, dict) or set(illusion) != {"mechanism", "cue_withheld", "question", "observable_event"}:
            raise ValueError("illusion needs mechanism, cue_withheld, question and observable_event")
        if any(not isinstance(v, str) or not 1 <= len(v.strip()) <= 500 for v in illusion.values()):
            raise ValueError("illusion fields must contain 1-500 characters")
        if idea.get("visual_identity") != IDENTITY:
            raise ValueError("visual identity does not match OpticPop")
        if type(idea.get("seed")) is not int or not 0 <= idea["seed"] < 1_000_000:
            raise ValueError("seed must be an integer in 0-999999")
        requirements = idea.get("requirements")
        if not isinstance(requirements, list) or any(not isinstance(r, str) or not r for r in requirements):
            raise ValueError("requirements must be a list of capability names")
        if idea.get("scene") is None and requirements:
            return dict(eligible=False, status="needs_extension", total=0, scores={},
                        reasons=["Renderer work required; no production brief will be emitted"],
                        missing_capabilities=requirements)
        if requirements:
            raise ValueError("implemented scenes cannot contain unresolved requirements")
        render = render_spec(idea["scene"], idea.get("seed"))
        validate_render(render)
        if illusion["mechanism"] != mechanism_for(idea["scene"]):
            raise ValueError("claimed mechanism differs from actual geometry")
        # Completion is promised only for exact complementary coplanar half rings.
        if illusion["mechanism"] == "overlap_completion":
            a, b, *extra = idea["scene"]["entities"]
            if extra or idea["scene"]["layout"] != "coaxial" or a["center"] != b["center"] or a["scale"] != b["scale"]:
                raise ValueError("completion needs two equally sized coaxial arcs with a shared center")
            if abs(a["phase"] - b["phase"]) != 180 or a["turns"] == b["turns"]:
                raise ValueError("completion needs complementary phases and distinct turn rates")
        key = novelty_key(idea)
        if idea.get("novelty_key") != key:
            raise ValueError("novelty signature does not match the scene")
    except (ValueError, KeyError, TypeError) as exc:
        return dict(eligible=False, status="invalid", total=0, scores={}, reasons=[str(exc)],
                    missing_capabilities=[])
    entities = idea["scene"]["entities"]
    relationships = len({e["turns"] for e in entities}) > 1
    all_masks = all(e["shape"] == "mask" for e in entities)
    theme_fit = (all_masks if idea["theme"] in ("emotion", "identity") else
                 all(e["shape"] == "arc" for e in entities) if idea["theme"] == "geometry" else True)
    scores = dict(mechanism=4, relationship=5 if relationships else 4, identity=5,
                  novelty=1 if key in recent else 4, feasibility=5, theme_fit=5 if theme_fit else 3)
    total = sum(scores[k] * WEIGHTS[k] / 5 for k in scores)
    return dict(eligible=True, status="ready_for_preview", total=total, scores=scores,
                reasons=["Geometry, motion, palette and compositing are supported by relational_scene.Scene",
                         "Color and caption changes alone do not count as concept novelty",
                         "Recent scene signature penalized" if key in recent else "No match in supplied scene history",
                         "Perceptual strength and narrative fidelity require human review"],
                missing_capabilities=[])


def normalize_proposals(ideas):
    """Fill missing derived signatures on external proposals, never replace mismatched ones."""
    if not isinstance(ideas, list):
        raise ValueError("provide a JSON list of concepts")
    result = copy.deepcopy(ideas)
    for idea in result:
        if not isinstance(idea, dict) or "novelty_key" in idea:
            continue
        try:
            if idea.get("scene") is not None:
                validate_scene(idea["scene"])
            elif not isinstance(idea.get("requirements"), list) or not idea["requirements"]:
                continue
            idea["novelty_key"] = novelty_key(idea)
        except (ValueError, KeyError, TypeError):
            pass  # Malformed proposals receive a rejection reason during evaluation.
    return result


def rank(ideas, recent=()):
    if not isinstance(ideas, list) or not 1 <= len(ideas) <= 100:
        raise ValueError("provide 1-100 concepts")
    rows = [dict(idea=i, evaluation=evaluate(i, recent)) for i in ideas]
    return sorted(rows, key=lambda r: (-r["evaluation"]["total"],
                                      str(r["idea"].get("id", "")) if isinstance(r["idea"], dict) else ""))


def production_brief(row):
    idea = row["idea"]
    evaluation = evaluate(idea)
    if not evaluation["eligible"] or not row["evaluation"]["eligible"]:
        raise ValueError("only implemented, validated concepts can become production briefs")
    return dict(schema_version=VERSION, status="needs_human_review", publishing_allowed=False,
                idea=copy.deepcopy(idea), render=render_spec(idea["scene"], idea["seed"]),
                evaluation=copy.deepcopy(row["evaluation"]), caption=caption(idea),
                direction=dict(hook_placement="Caption only; no on-screen hook",
                               beats=[{"seconds": 0, "intent": "Establish distinct colored surfaces"},
                                      {"seconds": 1.875, "intent": "Surfaces pass through narrow profiles"},
                                      {"seconds": 3.75, "intent": "Overlapping contours return from the opposite side"},
                                      {"seconds": 7.5, "intent": "Exact geometric cycle repeats"},
                                      {"seconds": 15, "intent": "Loop boundary matches opening geometry"}],
                               audio="Silent AAC for production; preview is silent without an audio track"),
                review_checks=["Verify expression and surface curvature",
                               "Check crossing contours and color separation on a phone",
                               "Check whether the intended ambiguity is perceptible",
                               "Check loop boundary and caption fidelity"])


def validate_brief(brief):
    if not isinstance(brief, dict) or type(brief.get("schema_version")) is not int or brief["schema_version"] != VERSION:
        raise ValueError("unsupported concept brief version")
    if brief.get("status") != "needs_human_review" or brief.get("publishing_allowed") is not False:
        raise ValueError("only local review briefs are accepted")
    render = validate_render(brief.get("render"))
    evaluation = evaluate(brief.get("idea"))
    if not evaluation["eligible"]:
        raise ValueError(evaluation["reasons"][0])
    if render != render_spec(brief["idea"]["scene"], brief["idea"]["seed"]):
        raise ValueError("render specification differs from concept")
    if brief.get("caption") != caption(brief["idea"]):
        raise ValueError("caption differs from concept; regenerate the production brief")
    return render
