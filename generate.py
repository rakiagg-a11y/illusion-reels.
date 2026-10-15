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

STYLES = ["dancer", "stereogram", "blackhole", "dots", "crosseye", "chromo"]


def run(style, seed, out, handle):
    if style in ("dancer", "dots"):
        meta = spin.render(style, seed, 15, handle, out)
    else:
        meta = getattr(more, f"render_{style}")(seed, out, handle)
    meta["full_caption"], meta["hashtags"] = captions.build(
        style, meta.get("subject", ""), seed)
    meta.pop("caption", None)
    with open(out.rsplit(".", 1)[0] + ".json", "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default="auto", choices=STYLES + ["auto"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out", default="reel.mp4")
    ap.add_argument("--handle", default="@opticpop")
    ap.add_argument("--slot", type=int, default=0,
                    help="post number within the day (0-3); picks the style")
    a = ap.parse_args()
    day = datetime.date.today().toordinal()
    style = a.style if a.style != "auto" else STYLES[(day * 4 + a.slot) % len(STYLES)]
    seed = a.seed if a.seed is not None else random.randrange(1_000_000)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    print(json.dumps(run(style, seed, a.out, a.handle), ensure_ascii=False,
                     indent=2))
