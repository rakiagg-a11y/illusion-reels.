"""Dependency-free contract for OpticPop relational scenes."""
import math

COLORS = {"coral": (1.0, .055, .09), "electric_blue": (.07, .2, 1.0),
          "cyan": (.03, .9, 1.0), "violet": (.65, .08, 1.0),
          "amber": (1.0, .38, .035)}
OBJECT_SHAPES = ("heart", "star", "crescent", "butterfly", "ring")
SHAPES = ("mask", "arc") + OBJECT_SHAPES
IDENTITY = {"background": "black", "projection": "orthographic",
            "surface": "additive_dots", "occlusion": "none"}


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{label}: expected fields {sorted(keys)}")


def number(value, low, high, label):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label}: expected finite number in [{low}, {high}]")


def validate_scene(scene):
    exact(scene, {"version", "identity", "layout", "entities"}, "scene")
    if type(scene["version"]) is not int or scene["version"] != 1:
        raise ValueError("unsupported scene version")
    if scene["identity"] != IDENTITY:
        raise ValueError("scene must retain the OpticPop black/additive/orthographic identity")
    if scene["layout"] not in ("orbit", "coaxial"):
        raise ValueError("unsupported layout")
    entities = scene["entities"]
    if not isinstance(entities, list) or not 2 <= len(entities) <= 3:
        raise ValueError("a relational scene needs 2-3 entities")
    for entity in entities:
        exact(entity, {"shape", "expression", "color", "center", "scale", "turns", "phase"}, "entity")
        if entity["shape"] not in SHAPES:
            raise ValueError(f"geometry requires extension: {entity['shape']}")
        expressions = ("smile", "frown", "neutral") if entity["shape"] == "mask" else (None,)
        if entity["expression"] not in expressions:
            raise ValueError("expression does not match geometry")
        if not isinstance(entity["color"], str) or entity["color"] not in COLORS:
            raise ValueError("unsupported palette color")
        if type(entity["turns"]) is not int or entity["turns"] not in (-2, -1, 1, 2):
            raise ValueError("turns must be an integer in -2, -1, 1, 2")
        number(entity["scale"], .65, 1.05, "scale")
        number(entity["phase"], -180, 180, "phase")
        if not isinstance(entity["center"], list) or len(entity["center"]) != 3:
            raise ValueError("center must contain three numbers")
        for c in entity["center"]:
            number(c, -.65, .65, "center")
    return scene


def mechanism_for(scene):
    validate_scene(scene)
    shapes = {e["shape"] for e in scene["entities"]}
    return "overlap_completion" if shapes == {"arc"} else "transparent_depth_ambiguity"


def validate_render(render):
    exact(render, {"style", "seed", "seconds", "width", "height", "fps", "scene"}, "render")
    if render["style"] != "opticpop":
        raise ValueError("relational scenes require style=opticpop")
    if type(render["seed"]) is not int or not 0 <= render["seed"] < 1_000_000:
        raise ValueError("seed must be an integer in 0-999999")
    for key, expected in {"seconds": 15, "width": 1080, "height": 1920, "fps": 30}.items():
        if type(render[key]) is not int or render[key] != expected:
            raise ValueError(f"{key} must equal {expected}")
    validate_scene(render["scene"])
    return render


def entity(shape="mask", expression="smile", color="coral", center=None,
           turns=1, phase=0, scale=.9):
    return dict(shape=shape, expression=expression, color=color,
                center=center or [0, 0, 0], turns=turns, phase=phase, scale=scale)


def scene(entities, layout="orbit"):
    return dict(version=1, identity=IDENTITY.copy(), layout=layout, entities=entities)
