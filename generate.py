#!/usr/bin/env python3
"""
One entry point for every illusion style.

  python3 generate.py --style auto --out out/reel.mp4 --handle @yourpage

--style auto rotates through all styles by day, so the feed stays varied.
Writes reel.mp4 + reel.json (caption, hashtags) [+ reel_still.png for
stereograms].
"""
import argparse, datetime, json, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_illusion as spin
import more_illusions as more
import captions
import pointcloud

# The feed is point-cloud spins (the format that performs best); the older
# styles stay available with --style.
STYLES = ["pointspin"]
LEGACY = ["dancer", "stereogram", "blackhole", "dots", "crosseye", "chromo"]


def run(style, seed, out, handle, obj=None, text=None, scene=None, creative_caption=None):
    if style == "opticpop":
        from scene_contract import validate_scene
        validate_scene(scene)
        import relational_scene
        meta = relational_scene.render(scene, seed, out, 15, handle)
    elif style == "pointspin":
        objs = list(pointcloud.OBJECTS)
        obj = obj or objs[seed % len(objs)]
        meta = pointcloud.render(obj, seed, out, 15, handle, text)
    elif style in ("dancer", "dots"):
        meta = spin.render(style, seed, 15, handle, out)
    else:
        meta = getattr(more, f"render_{style}")(seed, out, handle)
    if style == "opticpop":
        from concept_director import caption, describe
        meta.update(creative_caption or caption(describe(scene, seed, "duality")))
    else:
        meta["full_caption"], meta["hashtags"] = captions.build(
            style, meta.get("subject", ""), seed, meta.get("text"))
        meta["short_caption"] = captions.build_short(
            style, meta.get("subject", ""), seed)
    meta.pop("caption", None)
    with open(out.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="auto", choices=STYLES + LEGACY + ["auto", "opticpop"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out", default="reel.mp4")
    ap.add_argument("--handle", default="@opticpop")
    ap.add_argument("--obj", choices=list(pointcloud.OBJECTS) +
                    ["spin text", "hidden word"])
    ap.add_argument("--text", help="word for 'spin text' / 'hidden word'")
    ap.add_argument("--slot", type=int, default=0,
                    help="post number within the day (0-3); picks the style")
    ap.add_argument("--scene", help="validated relational scene JSON; requires --style opticpop")
    a = ap.parse_args()
    if (a.style == "opticpop") != bool(a.scene):
        ap.error("--style opticpop and --scene must be supplied together")
    if a.scene and (a.obj or a.text):
        ap.error("relational scenes do not use --obj or --text")
    specification = None
    if a.scene:
        with open(a.scene, encoding="utf-8-sig") as f:
            specification = json.load(f)
    day = datetime.date.today().toordinal()
    style = a.style if a.style != "auto" else STYLES[(day * 4 + a.slot) % len(STYLES)]
    seed = a.seed if a.seed is not None else random.randrange(1_000_000)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    print(json.dumps(run(style, seed, a.out, a.handle, a.obj, a.text, scene=specification), ensure_ascii=False,
                     indent=2))
