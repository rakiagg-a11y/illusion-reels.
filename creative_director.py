"""OpticPop local creative planning. Standard library only; never publishes."""
import argparse
import ast
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = 1
TEXT_OBJECTS = ("spin text", "hidden word")


def capabilities():
    """Read actual renderer keys without importing numpy/scipy or rendering."""
    tree = ast.parse((ROOT / "pointcloud.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "OBJECTS" for t in node.targets
        ):
            return tuple(ast.literal_eval(k) for k in node.value.keys) + TEXT_OBJECTS
    raise ValueError("pointcloud.OBJECTS registry missing")


def validate_render(render):
    expected = {"style", "obj", "text", "seed", "seconds", "width", "height", "fps"}
    if not isinstance(render, dict) or set(render) != expected:
        raise ValueError("render must contain exactly the supported renderer fields")
    if render["style"] != "pointspin" or render["obj"] not in capabilities():
        raise ValueError("v1 supports existing pointspin objects only")
    if type(render["seed"]) is not int or not 0 <= render["seed"] < 1_000_000:
        raise ValueError("seed must be an integer from 0 to 999999")
    if any(type(render[k]) is not int for k in ("seconds", "width", "height", "fps")):
        raise ValueError("timing and dimensions must be integers")
    if tuple(render[k] for k in ("seconds", "width", "height", "fps")) != (15, 1080, 1920, 30):
        raise ValueError("generate.run currently fixes output at 15s, 1080x1920, 30fps")
    text = render["text"]
    if render["obj"] in TEXT_OBJECTS:
        if not isinstance(text, str) or not 1 <= len(text) <= 12:
            raise ValueError("text objects need 1-12 uppercase ASCII characters")
        if not text.strip() or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 " for c in text):
            raise ValueError("text must use uppercase ASCII letters, digits and spaces")
    elif text is not None:
        raise ValueError("text is only supported by text objects")
    return render


def render_spec(obj, seed, text=None):
    return dict(style="pointspin", obj=obj, text=text, seed=seed,
                seconds=15, width=1080, height=1920, fps=30)


def generate_ideas(seed=42, theme="perception"):
    """Reproducible template recombination; no remote model or API key."""
    rng = random.Random(seed)
    ideas = []
    for obj in capabilities():
        text = rng.choice(["LOOK AGAIN", "FOUND ME", "OPTICPOP"]) if obj in TEXT_OBJECTS else None
        hidden = obj == "hidden word"
        mechanism = "anamorphic word alignment" if hidden else "ambiguous orthographic rotation"
        ideas.append(dict(
            id=hashlib.sha256(f"{seed}:{obj}:{text}".encode()).hexdigest()[:12],
            title=f"{theme}: " + ("Catch the secret word" if hidden else f"Reverse the {obj}"),
            hook="Pause when the dots form a word" if hidden else "Can you make it spin the other way?",
            mechanism=mechanism,
            payoff=f"Read {text} at alignment" if hidden else "Try perceiving the opposite rotation",
            render=render_spec(obj, rng.randrange(1_000_000), text),
            requires_blender=False,
        ))
    rng.shuffle(ideas)
    return ideas


def evaluate(idea, recent=()):
    reasons = []
    try:
        validate_render(idea.get("render"))
        for key in ("id", "title", "hook", "mechanism", "payoff"):
            if not isinstance(idea.get(key), str) or not idea[key].strip() or len(idea[key]) > 240:
                raise ValueError(f"{key} must be a nonempty string up to 240 characters")
        if idea.get("requires_blender") is not False:
            raise ValueError("Blender concepts require a separate renderer")
        expected = ("anamorphic word alignment" if idea["render"]["obj"] == "hidden word"
                    else "ambiguous orthographic rotation")
        if idea["mechanism"] != expected:
            raise ValueError("claimed mechanism does not match the existing renderer")
    except (ValueError, TypeError, KeyError) as exc:
        return dict(eligible=False, total=0, scores={}, reasons=[str(exc)])
    obj = idea["render"]["obj"]
    # Editorial heuristics, not measured virality or scientific guarantees.
    scores = dict(feasibility=5, hook=5 if obj == "hidden word" else 4,
                  participation=5 if obj in TEXT_OBJECTS else 4,
                  novelty=1 if obj in recent else 4,
                  loop=4 if obj in TEXT_OBJECTS else 5)
    weights = dict(feasibility=30, hook=20, participation=20, novelty=20, loop=10)
    reasons.append("Existing pointcloud.Scene and generate.run accept this specification")
    reasons.append("Exact repeats of recent subjects are penalized" if obj in recent
                   else "Subject absent from supplied recent history")
    reasons.append("Perceptual effect and text legibility require human preview review")
    return dict(eligible=True, total=sum(scores[k] * weights[k] / 5 for k in scores),
                scores=scores, reasons=reasons)


def rank(ideas, recent=()):
    if not isinstance(ideas, list) or not ideas or len(ideas) > 100:
        raise ValueError("provide 1-100 idea objects")
    if any(not isinstance(i, dict) for i in ideas):
        raise ValueError("each idea must be an object")
    rows = [dict(idea=i, evaluation=evaluate(i, recent)) for i in ideas]
    return sorted(rows, key=lambda r: (-r["evaluation"]["total"], str(r["idea"].get("id", ""))))


def production_brief(row):
    if not row["evaluation"]["eligible"]:
        raise ValueError("cannot brief an infeasible idea")
    idea = row["idea"]
    validate_render(idea["render"])
    import captions
    r = idea["render"]
    full, tags = captions.build(r["style"], r["obj"], r["seed"], r["text"])
    return dict(schema_version=VERSION, status="needs_human_review",
                publishing_allowed=False, idea=idea, evaluation=row["evaluation"],
                render=r.copy(),
                caption=dict(full_caption=full, hashtags=tags,
                             short_caption=captions.build_short(r["style"], r["obj"], r["seed"])),
                direction=dict(
                    hook_placement="Caption only; current pointspin renderer has no hook overlay",
                    opening="0-3s: establish the rotating dot object",
                    interaction="3-12s: inspect alignment or try reversing perceived rotation",
                    ending="12-15s: continue rotation into the loop",
                    audio="Existing silent AAC track; music is outside this local workflow"),
                review_checks=["Verify effect on a phone", "Check loop seam and text legibility",
                               "Review caption claims and any implied promises before publishing"])


def validate_brief(brief):
    if not isinstance(brief, dict) or type(brief.get("schema_version")) is not int or brief["schema_version"] != VERSION:
        raise ValueError("unsupported brief schema")
    if brief.get("publishing_allowed") is not False or brief.get("status") != "needs_human_review":
        raise ValueError("only non-publishing review briefs are accepted")
    validate_render(brief.get("render"))
    if not isinstance(brief.get("idea"), dict) or brief["idea"].get("render") != brief["render"]:
        raise ValueError("idea and render specifications differ")
    evaluation = evaluate(brief["idea"])
    if not evaluation["eligible"]:
        raise ValueError(evaluation["reasons"][0])
    return brief["render"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--theme", default="perception")
    ap.add_argument("--ideas", type=Path, help="optional JSON list from a human or external model")
    ap.add_argument("--recent", type=Path, help="JSON list of recently used object names")
    ap.add_argument("--out", type=Path, default=Path("local_demo"))
    a = ap.parse_args()
    if not 0 <= a.seed < 1_000_000 or not 1 <= len(a.theme.strip()) <= 100:
        ap.error("seed must be 0-999999 and theme 1-100 characters")
    try:
        recent = json.loads(a.recent.read_text(encoding="utf-8")) if a.recent else []
        if not isinstance(recent, list) or any(not isinstance(x, str) for x in recent):
            raise ValueError("recent history must be a JSON list of subject names")
        ideas = json.loads(a.ideas.read_text(encoding="utf-8")) if a.ideas else generate_ideas(a.seed, a.theme)
        rows = rank(ideas, recent)
        eligible = [r for r in rows if r["evaluation"]["eligible"]]
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / "ranking.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        if not eligible:
            (a.out / "production_brief.json").unlink(missing_ok=True)
            raise ValueError("no feasible ideas; inspect ranking.json")
        brief = production_brief(eligible[0])
        validate_brief(brief)
        (a.out / "production_brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(dict(winner=brief["idea"]["title"], score=brief["evaluation"]["total"],
                              render=brief["render"], publishing_allowed=False), indent=2))
    except (ValueError, OSError) as exc:
        ap.error(str(exc))


if __name__ == "__main__":
    main()
