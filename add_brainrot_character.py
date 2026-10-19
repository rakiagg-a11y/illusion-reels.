"""Add a character to the brainrot rotation from a reference picture.

    python add_brainrot_character.py <slug> <picture> [--crop x0,y0,x1,y1]

Transparent PNGs are used as they are; pictures with a background are cut
out with rembg (pip install "rembg[cpu]"). The result is cropped to the
figure and saved as assets/brainrot/<slug>.png; add the slug and display
name to brainrot.NAMES so the generator picks it up.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ASSETS = Path(__file__).resolve().parent/"assets"/"brainrot"


def cutout(picture, crop=None):
    im = Image.open(picture).convert("RGBA")
    if crop:
        im = im.crop(crop)
    alpha = np.asarray(im.getchannel("A"))
    if (alpha < 128).mean() < .05:
        from rembg import new_session, remove
        im = remove(im.convert("RGB"), session=new_session("isnet-general-use"))
    mask = im.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    im = im.crop(mask.getbbox())
    scale = 420/max(im.size)
    return im.resize((round(im.width*scale), round(im.height*scale)), Image.Resampling.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("picture")
    ap.add_argument("--crop", help="x0,y0,x1,y1 region of the picture to keep")
    args = ap.parse_args()
    crop = tuple(int(v) for v in args.crop.split(",")) if args.crop else None
    ASSETS.mkdir(parents=True, exist_ok=True)
    target = ASSETS/f"{args.slug}.png"
    cutout(args.picture, crop).save(target)
    print(target)


if __name__ == "__main__":
    main()
