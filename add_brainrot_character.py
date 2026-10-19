"""Add a character to the brainrot rotation from a reference picture.

    python add_brainrot_character.py <slug> <picture> [--crop x0,y0,x1,y1] [--largest]

Transparent PNGs are used as they are; pictures with a background are cut
out with rembg (pip install "rembg[cpu]"). The result is cropped to the
figure and saved as assets/brainrot/<slug>.png (--largest keeps only the
biggest connected piece, e.g. to drop a sticker outline); add the slug and display
name to brainrot.NAMES so the generator picks it up.
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ASSETS = Path(__file__).resolve().parent/"assets"/"brainrot"


def cutout(picture, crop=None, largest=False):
    im = Image.open(picture).convert("RGBA")
    if crop:
        im = im.crop(crop)
    alpha = np.asarray(im.getchannel("A"))
    if (alpha < 128).mean() < .05:
        from rembg import new_session, remove
        im = remove(im.convert("RGB"), session=new_session("isnet-general-use"))
    if largest:
        from scipy import ndimage
        labels, count = ndimage.label(np.asarray(im.getchannel("A")) > 128)
        if count > 1:
            keep = labels == np.argmax(np.bincount(labels.ravel())[1:])+1
            pixels = np.asarray(im).copy()
            pixels[..., 3] = np.where(keep, pixels[..., 3], 0)
            im = Image.fromarray(pixels)
    mask = im.getchannel("A").point(lambda v: 255 if v > 128 else 0)
    im = im.crop(mask.getbbox())
    scale = 420/max(im.size)
    return im.resize((round(im.width*scale), round(im.height*scale)), Image.Resampling.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("slug")
    ap.add_argument("picture")
    ap.add_argument("--crop", help="x0,y0,x1,y1 region of the picture to keep")
    ap.add_argument("--largest", action="store_true", help="keep only the biggest connected piece")
    args = ap.parse_args()
    crop = tuple(int(v) for v in args.crop.split(",")) if args.crop else None
    ASSETS.mkdir(parents=True, exist_ok=True)
    target = ASSETS/f"{args.slug}.png"
    cutout(args.picture, crop, args.largest).save(target)
    print(target)


if __name__ == "__main__":
    main()
