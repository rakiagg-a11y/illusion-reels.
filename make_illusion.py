#!/usr/bin/env python3
"""
Bistable rotation illusion reel generator.

A 3D object spins around a vertical axis and is drawn with orthographic
projection and no depth cues, so the brain can read it as spinning either
way. Mid-video, a depth cue (occlusion outlines / bright front dots) is faded
in for one direction, then for the other, then removed again so the viewer
can flip it at will.

Usage:
  python3 make_illusion.py --out reel.mp4 [--style dancer|dots] [--seed N]
                           [--seconds 15] [--handle @yourpage]
Writes reel.mp4 (1080x1920, 30 fps, H.264, Instagram Reels ready) and
reel.json (suggested caption + hashtags).
"""
import argparse, json, math, random, subprocess, sys
import numpy as np
import figures as F
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SS = 1080, 1920, 30, 2          # SS = supersampling factor
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

PALETTES = [  # (background, figure, cue)
    ((245, 240, 230), (15, 15, 20), (245, 240, 230)),
    ((12, 12, 18), (240, 240, 245), (255, 80, 110)),
    ((255, 214, 10), (20, 20, 20), (255, 214, 10)),
    ((20, 30, 60), (255, 190, 70), (20, 30, 60)),
    ((235, 245, 255), (30, 60, 160), (255, 255, 255)),
    ((15, 15, 15), (0, 220, 180), (15, 15, 15)),
]

HOOKS = [
    "Which way is it spinning?",
    "Left or right? Look again.",
    "Your brain decides the direction",
    "Can you make it switch?",
    "Most people only see one way",
]


# ---------------------------------------------------------------- geometry
def dancer_capsules(rng):
    """List of (p0, p1, radius) capsules in 3D, y up, rotation axis = y."""
    j = lambda x, y, z: np.array([x, y, z], float)
    lift = rng.uniform(-0.15, 0.25)           # how high the free leg is
    back = rng.uniform(0.15, 0.45)            # how far behind it goes
    arm = rng.uniform(0.0, 1.0)               # arm pose blend
    pelvis, neck = j(0, 0, 0), j(0.02, 0.55, 0.03)
    caps = [
        (pelvis, neck, 0.105),                            # torso
        (j(0.06, 0, 0), j(0.05, -0.42, 0.03), 0.06),      # support thigh
        (j(0.05, -0.42, 0.03), j(0.04, -0.84, 0), 0.045),  # support shin
        (j(0.04, -0.84, 0), j(0.05, -0.86, 0.11), 0.03),  # support foot
        (j(-0.06, 0, 0), j(-0.36, -0.12 + lift, back * 0.5), 0.06),  # free thigh
        (j(-0.36, -0.12 + lift, back * 0.5),
         j(-0.62, -0.3 + lift * 1.6, back), 0.045),       # free shin
        (j(-0.62, -0.3 + lift * 1.6, back),
         j(-0.72, -0.34 + lift * 1.8, back * 1.1), 0.03),  # free foot
        (neck, j(0.02, 0.66, 0.03), 0.045),               # neck
    ]
    head = (j(0.02, 0.76, 0.04), j(0.02, 0.78, 0.04), 0.085)
    caps.append(head)
    for s in (1, -1):                                     # arms
        sh = j(0.15 * s, 0.5, 0.02)
        el = j(0.25 * s, 0.5 + 0.22 * arm, 0.1 - 0.15 * arm * s)
        ha = j(0.1 * s * (1 - arm) + 0.03 * s, 0.55 + 0.45 * arm,
               0.15 - 0.1 * arm)
        caps += [(sh, el, 0.04), (el, ha, 0.033)]
    return caps


def dot_cloud(rng):
    kind = rng.choice(["sphere", "cylinder", "torus", "helix"])
    n = 650
    if kind == "sphere":
        v = rng.normal(size=(n, 3))
        pts = v / np.linalg.norm(v, axis=1, keepdims=True) * 0.8
    elif kind == "cylinder":
        a = rng.uniform(0, 2 * math.pi, n)
        pts = np.c_[0.6 * np.cos(a), rng.uniform(-0.9, 0.9, n), 0.6 * np.sin(a)]
    elif kind == "torus":
        u, v = rng.uniform(0, 2 * math.pi, (2, n))
        R, r = 0.6, 0.22
        x = (R + r * np.cos(v)) * np.cos(u)
        z = (R + r * np.cos(v)) * np.sin(u)
        y = r * np.sin(v)
        tilt = 1.2                             # stand the ring up on edge
        c, s = math.cos(tilt), math.sin(tilt)
        pts = np.c_[x, y * c - z * s, y * s + z * c]
    else:  # double helix
        t = rng.uniform(0, 1, n)
        strand = rng.integers(0, 2, n)
        a = t * 4 * math.pi + strand * math.pi
        pts = np.c_[0.45 * np.cos(a), (t - 0.5) * 1.9, 0.45 * np.sin(a)]
    return kind, pts


def rot_y(p, th):
    c, s = math.cos(th), math.sin(th)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    return np.stack([x * c + z * s, y, -x * s + z * c], axis=-1)


# ---------------------------------------------------------------- timeline
def cue_state(t, T):
    """Returns (strength 0..1, direction sign) for the depth cue at time t."""
    a, b = 0.30 * T, 0.48 * T      # cue A window
    c, d = 0.52 * T, 0.70 * T      # cue B window
    fade = 0.06 * T
    def window(lo, hi):
        if t < lo or t > hi:
            return 0.0
        return min(1.0, (t - lo) / fade, (hi - t) / fade)
    sa, sb = window(a, b), window(c, d)
    return (sa, +1) if sa > 0 else (sb, -1)


def phase_text(t, T):
    if t < 0.28 * T:
        return None
    if t < 0.50 * T:
        return "Now it spins RIGHT"
    if t < 0.72 * T:
        return "Now it spins LEFT"
    return "Now flip it with your mind"


# ---------------------------------------------------------------- drawing
def mix(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))


def draw_text(d, text, y, size, color, bold=True):
    while True:
        f = ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size * SS)
        w = d.textlength(text, font=f)
        if w <= 0.88 * W * SS or size <= 20:
            break
        size -= 2
    d.text(((W * SS - w) / 2, y * SS), text, font=f, fill=color)


def capsule(d, p0, p1, r, fill):
    d.line([tuple(p0), tuple(p1)], fill=fill, width=int(2 * r))
    for p in (p0, p1):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=fill)


def render(style, seed, seconds, handle, out):
    rng = np.random.default_rng(seed)
    bg, fg, cue = PALETTES[seed % len(PALETTES)]
    if mix(cue, bg, 0) == bg and style == "dots":
        cue = (255, 80, 110) if sum(bg) > 300 else (255, 230, 90)
    hook = HOOKS[seed % len(HOOKS)]
    period = rng.uniform(2.4, 3.6)             # seconds per revolution
    scale = (900 if style == "dancer" else 760) * SS / 2
    cx, cy = W * SS / 2, H * SS * 0.53

    if style == "dancer":
        names = list(F.FIGURES)
        fname = names[seed % len(names)]
        prims = F.build(fname, rng)
        rad, y0, y1 = F.extent(prims)
        fit = min(0.46 * W * SS / rad, 0.5 * H * SS / (y1 - y0))
        fcy = H * SS * 0.53 + (y1 + y0) / 2 * fit
        subject = "dancer" if fname.startswith("ballerina") else fname
    else:
        subject, pts = dot_cloud(rng)
        dot_r = 7 * SS

    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-shortest", "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "8M", "-bufsize", "16M",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)

    n = int(seconds * FPS)
    for i in range(n):
        t = i / FPS
        th = 2 * math.pi * t / period
        strength, sign = cue_state(t, seconds)
        img = Image.new("RGB", (W * SS, H * SS), bg)
        d = ImageDraw.Draw(img)

        if style == "dancer":
            outline = mix(fg, cue if cue != fg else bg, strength)
            F.draw(d, prims, th, cx, fcy, fit, fg, outline=outline,
                   ow=5 * SS * strength, depth_sign=sign)
        else:
            q = rot_y(pts, th)
            front = (q[:, 2] * sign) > 0
            order = np.argsort(q[:, 2] * sign)
            for k in order:
                x, y = cx + q[k, 0] * scale, cy - q[k, 1] * scale
                col = mix(fg, cue, strength) if front[k] else \
                    mix(fg, bg, 0.55 * strength)
                d.ellipse([x - dot_r, y - dot_r, x + dot_r, y + dot_r], fill=col)

        txt = mix(fg, bg, 0.0)
        draw_text(d, hook, 170, 64, txt)
        pt = phase_text(t, seconds)
        if pt:
            draw_text(d, pt, 1560, 56, txt)
        if handle:
            draw_text(d, handle, 1760, 38, mix(fg, bg, 0.45), bold=False)

        frame = img.resize((W, H), Image.LANCZOS)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()

    meta = {
        "style": style, "subject": subject, "seed": seed,
        "caption": (f"{hook} 👀\n\nThis {subject} is spinning only one way — "
                    "but with no depth cues your brain has to guess. Watch the "
                    "outlines flip it, then try switching it yourself. "
                    "Which way did you see first? Comment ⬅️ or ➡️"),
        "hashtags": ["#opticalillusion", "#illusion", "#brainteaser",
                     "#spinningdancer", "#perception", "#mindblown",
                     "#visualillusion", "#satisfying", "#reels", "#science"],
    }
    with open(out.rsplit(".", 1)[0] + ".json", "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="reel.mp4")
    ap.add_argument("--style", choices=["dancer", "dots", "random"],
                    default="random")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--seconds", type=float, default=15)
    ap.add_argument("--handle", default="")
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randrange(1_000_000)
    style = a.style if a.style != "random" else \
        ("dancer" if seed % 2 == 0 else "dots")
    print(json.dumps(render(style, seed, a.seconds, a.handle, a.out),
                     ensure_ascii=False, indent=2))
