"""
Extra illusion styles for the reels generator:

  stereogram  - "Magic Eye" autostereogram with a hidden 3D shape + reveal
  crosseye    - side-by-side 3D pair (cross your eyes to merge)
  chromo      - red/blue chromostereopsis (red floats above blue)
  blackhole   - motion aftereffect: stare at a spinning particle vortex, then
                the still image appears to move the other way

Each render_* function writes an MP4 (1080x1920, 30fps, H.264 + silent AAC)
and returns a metadata dict with caption + hashtags.
"""
import math, subprocess
from scipy.ndimage import distance_transform_edt
import figures as F
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ------------------------------------------------------------------ helpers
class Writer:
    def __init__(self, out, w=W, h=H):
        self.p = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
             "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
             "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
             "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "8M", "-bufsize", "16M",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-movflags", "+faststart",
             out], stdin=subprocess.PIPE)

    def write(self, img, times=1):
        b = img.tobytes()
        for _ in range(times):
            self.p.stdin.write(b)

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def text_c(d, text, y, size, color, bold=True, maxw=0.9):
    """Centered text, shrunk to fit; supports '\n' for several lines."""
    for i, line in enumerate(text.split("\n")):
        s = size
        while True:
            f = font(s, bold)
            w = d.textlength(line, font=f)
            if w <= maxw * W or s <= 18:
                break
            s -= 2
        d.text(((W - w) / 2, y + i * int(size * 1.25)), line, font=f, fill=color)


def handle_text(d, handle, color):
    if handle:
        text_c(d, handle, 1790, 36, color, bold=False)


def hsv(h, s=1.0, v=1.0):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r, g, b = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v),
               (v, p, q)][i]
    return int(r * 255), int(g * 255), int(b * 255)


# ------------------------------------------------------------ stereogram
HIDDEN = ["shark", "heart", "cat", "star", "butterfly", "sphere", "t-rex",
          "WOW", "flamingo", "ring", "ballerina arabesque", "3D", "moon",
          "LOVE", "smile", "arrow"]


def depth_map(kind, size):
    img = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(img)
    c = size / 2
    if kind in F.FIGURES:
        prims = F.build(kind, np.random.default_rng(0))
        rad, y0, y1 = F.extent(prims)
        sc = min(0.44 * size / rad, 0.8 * size / (y1 - y0))
        F.draw(d, prims, 0.0, c, c + (y1 + y0) / 2 * sc, sc, 255)
        m = np.asarray(img) > 0
        dist = distance_transform_edt(m)
        return np.where(m, 0.25 + 0.75 * np.sqrt(dist / dist.max()), 0.0)
    if kind == "heart":
        pts = []
        for t in np.linspace(0, 2 * math.pi, 200):
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) \
                - math.cos(4 * t)
            pts.append((c + x * size / 42, c - y * size / 42))
        d.polygon(pts, fill=255)
    elif kind == "star":
        pts = []
        for k in range(10):
            r = size * (0.42 if k % 2 == 0 else 0.18)
            a = -math.pi / 2 + k * math.pi / 5
            pts.append((c + r * math.cos(a), c + r * math.sin(a)))
        d.polygon(pts, fill=255)
    elif kind == "sphere":
        yy, xx = np.mgrid[0:size, 0:size]
        r = np.sqrt((xx - c) ** 2 + (yy - c) ** 2) / (size * 0.38)
        z = np.sqrt(np.clip(1 - r ** 2, 0, 1))
        return z
    elif kind == "ring":
        d.ellipse([c - size * .4, c - size * .4, c + size * .4, c + size * .4],
                  fill=255)
        d.ellipse([c - size * .22, c - size * .22, c + size * .22,
                   c + size * .22], fill=0)
    elif kind == "smile":
        d.ellipse([c - size * .42] * 2 + [c + size * .42] * 2, fill=170)
        for sx in (-1, 1):
            d.ellipse([c + sx * size * .15 - 40, c - size * .15 - 50,
                       c + sx * size * .15 + 40, c - size * .15 + 50], fill=255)
        d.arc([c - size * .25, c - size * .15, c + size * .25, c + size * .28],
              20, 160, fill=255, width=40)
    elif kind == "arrow":
        d.polygon([(c - size * .38, c - 70), (c + size * .05, c - 70),
                   (c + size * .05, c - 170), (c + size * .4, c),
                   (c + size * .05, c + 170), (c + size * .05, c + 70),
                   (c - size * .38, c + 70)], fill=255)
    elif kind == "moon":
        d.ellipse([c - size * .38] * 2 + [c + size * .38] * 2, fill=255)
        d.ellipse([c - size * .2, c - size * .45, c + size * .5,
                   c + size * .3], fill=0)
    else:  # a word
        s = int(size * (0.55 if len(kind) <= 2 else 0.32))
        f = font(s)
        w = d.textlength(kind, font=f)
        d.text(((size - w) / 2, c - s * 0.62), kind, font=f, fill=255)
    return np.asarray(img, float) / 255.0


def texture(rng, P, h):
    """Colourful busy 'floral' tile, P px wide, repeated horizontally."""
    base = hsv(rng.random(), 0.5, 0.35)
    tile = Image.new("RGB", (P, h), base)
    d = ImageDraw.Draw(tile)
    hue0 = rng.random()
    for _ in range(int(P * h / 140)):
        x, y = rng.uniform(-10, P + 10), rng.uniform(0, h)
        r = rng.uniform(3, 13)
        col = hsv((hue0 + rng.normal(0, 0.18)) % 1, rng.uniform(.5, 1),
                  rng.uniform(.5, 1))
        for dx in (-P, 0, P):  # wrap so the tile is seamless
            d.ellipse([x + dx - r, y - r, x + dx + r, y + r], fill=col)
            d.ellipse([x + dx - r / 3, y - r / 3, x + dx + r / 3, y + r / 3],
                      fill=hsv(rng.random(), .3, 1))
    return np.asarray(tile)


def autostereogram_flat(depth, tex, P, max_shift):
    """Left-to-right copy: clean for hard-edged depth maps."""
    h, w = depth.shape
    out = np.zeros((h, w, 3), np.uint8)
    rows = np.arange(h)
    sep = (P - np.round(depth * max_shift)).astype(int)
    for x in range(w):
        src = x - sep[:, x]
        ok = src >= 0
        out[:, x] = tex[rows, x % P]
        out[ok, x] = out[rows[ok], src[ok]]
    return out


def autostereogram(depth, tex, P, max_shift):
    """Thimbleby-Inglis-Witten symmetric linking: no smearing artifacts."""
    h, w = depth.shape
    out = np.zeros((h, w, 3), np.uint8)
    seps = (P - np.round(depth * max_shift)).astype(int)
    for y in range(h):
        same = list(range(w))
        sep = seps[y].tolist()
        for x in range(w):
            s = sep[x]
            l = x - s // 2
            r = l + s
            if l < 0 or r >= w:
                continue
            k = same[l]
            while k != l and k != r:
                if k < r:
                    l = k
                else:
                    same[l] = r
                    l, r = r, k
                k = same[l]
            same[l] = r
        row = out[y]
        trow = tex[y]
        for x in range(w - 1, -1, -1):
            row[x] = trow[x % P] if same[x] == x else row[same[x]]
    return out


def render_stereogram(seed, out, handle="", seconds=16):
    rng = np.random.default_rng(seed)
    kind = HIDDEN[seed % len(HIDDEN)]
    S, P = 1080, 150
    dep = depth_map(kind, S)
    algo = autostereogram if (kind == "sphere" or kind in F.FIGURES) \
        else autostereogram_flat
    sg = Image.fromarray(algo(dep, texture(rng, P, S), P, 22))
    sg.save(out.rsplit(".", 1)[0] + "_still.png")       # also a photo post

    bg, fg = (10, 10, 14), (240, 240, 240)
    base = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(base)
    text_c(d, "Can you see the hidden 3D image?", 150, 60, fg)
    text_c(d, "Relax your eyes and look THROUGH the screen", 250, 38,
           (170, 170, 180), bold=False)
    handle_text(d, handle, (130, 130, 140))
    y0 = (H - S) // 2 + 40
    base.paste(sg, (0, y0))

    # reveal image: shaded depth map
    shade = (np.stack([dep] * 3, -1) * np.array([255, 210, 90]) +
             (1 - np.stack([dep] * 3, -1)) * 25).astype(np.uint8)
    reveal = base.copy()
    reveal.paste(Image.fromarray(shade), (0, y0))
    dr = ImageDraw.Draw(reveal)
    dr.rectangle([0, 120, W, 320], fill=bg)
    nice = "ballerina" if kind.startswith("ballerina") else kind
    answer = kind if kind.isupper() else \
        ("an " if nice[0] in "aeiou" else "a ") + nice
    text_c(dr, f"Answer: {answer}!", 170, 64, (255, 210, 90))

    wr = Writer(out)
    hold = seconds - 3
    wr.write(base, int(hold * FPS))
    for i in range(int(0.7 * FPS)):                     # crossfade
        wr.write(Image.blend(base, reveal, i / (0.7 * FPS)))
    wr.write(reveal, int(2.3 * FPS))
    wr.close()
    return {
        "style": "stereogram", "subject": kind, "seed": seed,
        "caption": ("Hidden 3D image 👁️ Hold your phone close, let your eyes "
                    "go unfocused like you're looking far behind the screen, "
                    "then slowly pull back. Did you find it before the answer? "
                    "Comment what you saw 👇 (no spoilers!)"),
        "hashtags": ["#magiceye", "#stereogram", "#autostereogram",
                     "#opticalillusion", "#hiddenimage", "#3dart", "#illusion",
                     "#brainteaser", "#eyetest", "#reels"],
    }


# ---------------------------------------------------------- cross-eye 3D
def scene_points(rng):
    kind = rng.choice(["knot", "galaxy", "helix", "cube"])
    n = 1400
    if kind == "knot":
        t = np.linspace(0, 2 * math.pi, n)
        p, q = 2, 3
        r = 0.5 + 0.22 * np.cos(q * t)
        pts = np.c_[r * np.cos(p * t), 0.22 * np.sin(q * t), r * np.sin(p * t)]
        pts += rng.normal(0, 0.025, pts.shape)
        hue = t / (2 * math.pi)
    elif kind == "galaxy":
        arm = rng.integers(0, 3, n)
        rr = rng.uniform(0.05, 0.85, n)
        a = rr * 5 + arm * 2 * math.pi / 3 + rng.normal(0, .25, n)
        pts = np.c_[rr * np.cos(a), rng.normal(0, .05, n) * (1 - rr),
                    rr * np.sin(a)]
        pts = pts @ np.array([[1, 0, 0], [0, .8, -.6], [0, .6, .8]]).T
        hue = 0.55 + rr * 0.4
    elif kind == "helix":
        t = rng.uniform(0, 1, n)
        s = rng.integers(0, 2, n)
        a = t * 5 * math.pi + s * math.pi
        pts = np.c_[0.4 * np.cos(a), (t - .5) * 1.6, 0.4 * np.sin(a)]
        hue = 0.0 + s * 0.5 + t * 0.15
    else:
        e = rng.integers(0, 12, n)
        t = rng.uniform(-1, 1, n)
        corners = np.array([[a, b] for a in (-1, 1) for b in (-1, 1)])
        pts = np.zeros((n, 3))
        for k in range(n):
            axis, c = e[k] // 4, corners[e[k] % 4]
            v = np.insert(c.astype(float), axis, t[k])
            pts[k] = v * 0.5
        hue = 0.08 + e / 40
    return kind, pts, hue % 1


def project(pts, eye_x, cam=3.2, f=2.4):
    z = pts[:, 2] + cam
    x = (pts[:, 0] - eye_x) * f / z
    y = pts[:, 1] * f / z
    return x, y, z


def render_crosseye(seed, out, handle="", seconds=15):
    rng = np.random.default_rng(seed)
    kind, pts, hue = scene_points(rng)
    stars = np.c_[rng.uniform(-3, 3, 250), rng.uniform(-3, 3, 250),
                  rng.uniform(2, 5, 250)]
    cols = [hsv(h, .8, 1) for h in hue]
    period = rng.uniform(7, 10)
    panel, gap = 520, 20
    py = 700
    bg = (0, 0, 0)
    wr = Writer(out)
    for i in range(int(seconds * FPS)):
        t = i / FPS
        th = 2 * math.pi * t / period
        c, s = math.cos(th), math.sin(th)
        R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        tilt = np.array([[1, 0, 0], [0, math.cos(.35), -math.sin(.35)],
                         [0, math.sin(.35), math.cos(.35)]])
        q = pts @ R.T @ tilt.T
        img = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(img)
        text_c(d, "Cross your eyes until the\ntwo pictures merge into one", 170,
               56, (240, 240, 240))
        text_c(d, "Line up the two white dots → see it pop out in 3D", 340,
               34, (160, 160, 170), bold=False)
        # cross-eyed viewing: LEFT panel shows the RIGHT eye's view
        for pi, eye in enumerate((+0.13, -0.13)):
            ox = (W - 2 * panel - gap) // 2 + pi * (panel + gap)
            d.rectangle([ox, py, ox + panel, py + panel], outline=(40, 40, 50),
                        width=2)
            d.ellipse([ox + panel / 2 - 9, py - 50, ox + panel / 2 + 9,
                       py - 32], fill=(255, 255, 255))
            sx, sy, sz = project(stars, eye)
            for x, y in zip(sx, sy):
                X, Y = ox + panel / 2 + x * panel * .45, py + panel / 2 - y * panel * .45
                if ox < X < ox + panel and py < Y < py + panel:
                    d.point((X, Y), fill=(120, 120, 140))
            x, y, z = project(q, eye)
            order = np.argsort(-z)
            for k in order:
                X = ox + panel / 2 + x[k] * panel * .62
                Y = py + panel / 2 - y[k] * panel * .62
                r = 2.6 * 3.2 / z[k]
                d.ellipse([X - r, Y - r, X + r, Y + r], fill=cols[k])
        handle_text(d, handle, (110, 110, 120))
        wr.write(img)
    wr.close()
    return {
        "style": "crosseye", "subject": kind, "seed": seed,
        "caption": ("Cross-eye 3D 🤯 Slowly cross your eyes until a third "
                    "picture appears between the two, then hold it — it "
                    "floats right out of your screen. Took me a minute the "
                    "first time. Did it work for you?"),
        "hashtags": ["#crosseye", "#stereoscopic", "#3d", "#opticalillusion",
                     "#illusion", "#3dart", "#mindblown", "#satisfying",
                     "#science", "#reels"],
    }


# ------------------------------------------------- chromostereopsis
def render_chromo(seed, out, handle="", seconds=15):
    rng = np.random.default_rng(seed)
    kind = ["heart", "star", "WOW", "3D", "ring", "arrow"][seed % 6]
    S = 900
    mask = depth_map(kind, S) > 0.5
    red, blue = (255, 0, 0), (0, 40, 255)
    flip = seed % 2 == 1                      # sometimes blue shape on red
    wr = Writer(out)
    period = rng.uniform(9, 14)
    for i in range(int(seconds * FPS)):
        t = i / FPS
        img = Image.new("RGB", (W, H), (0, 0, 0))
        d = ImageDraw.Draw(img)
        # rotating concentric stripes behind the shape
        stripes = Image.new("RGB", (S, S), (0, 0, 0))
        sd = ImageDraw.Draw(stripes)
        ph = (t / period) % 1
        for k in range(30, -1, -1):
            r = (k + ph) * S / 40
            col = (blue if not flip else red) if k % 2 == 0 else (0, 0, 0)
            sd.ellipse([S / 2 - r, S / 2 - r, S / 2 + r, S / 2 + r], fill=col)
        arr = np.asarray(stripes).copy()
        fgc = np.array(red if not flip else blue, np.uint8)
        arr[mask] = fgc
        img.paste(Image.fromarray(arr), ((W - S) // 2, 520))
        text_c(d, "Is the " + ("red" if not flip else "blue") +
               " shape floating\nABOVE the screen?", 170, 58, (240, 240, 240))
        text_c(d, "Turn your brightness all the way up", 1480, 40, (170, 170, 180),
               bold=False)
        handle_text(d, handle, (110, 110, 120))
        wr.write(img)
    wr.close()
    return {
        "style": "chromo", "subject": kind, "seed": seed,
        "caption": ("Red and blue sit at different depths for your eyes 🔴🔵 "
                    "Your lens focuses red and blue light differently, so "
                    "most people see one colour float above the other "
                    "(chromostereopsis). Which one is closer for you?"),
        "hashtags": ["#chromostereopsis", "#opticalillusion", "#illusion",
                     "#3d", "#colorillusion", "#eyetest", "#science",
                     "#perception", "#mindblown", "#reels"],
    }


# --------------------------------------------- motion aftereffect vortex
def render_blackhole(seed, out, handle="", seconds=24):
    rng = np.random.default_rng(seed)
    n = 2600
    r0 = rng.uniform(0.12, 1.0, n) ** 0.7
    a0 = rng.uniform(0, 2 * math.pi, n)
    hue0 = rng.random()
    cols = [hsv((hue0 + r * 0.6) % 1, .75, 1) for r in r0]
    sizes = rng.uniform(1.5, 3.5, n)
    spin = 1.8 * (1 if seed % 2 else -1)          # rad/s at r = 0.3
    inflow = 0.10
    cx, cy, R = W / 2, 960, 480
    stare = seconds - 7
    wr = Writer(out)
    frozen = None
    for i in range(int(seconds * FPS)):
        t = i / FPS
        if t < stare:
            r = (r0 - inflow * t) % 0.9 + 0.12
            a = a0 + spin * t * (0.3 / r)
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            xs, ys = cx + r * R * np.cos(a), cy + r * R * np.sin(a)
            for x, y, s, c in zip(xs, ys, sizes, cols):
                d.ellipse([x - s, y - s, x + s, y + s], fill=c)
            d.ellipse([cx - 55, cy - 55, cx + 55, cy + 55], fill=(0, 0, 0))
            d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 255, 255))
            left = math.ceil(stare - t)
            text_c(d, "Stare at the white dot\ndon't look away…", 160, 60,
                   (240, 240, 240))
            text_c(d, str(left), 1560, 90, (255, 255, 255))
            handle_text(d, handle, (110, 110, 120))
            frozen = (xs, ys)
        else:
            img = Image.new("RGB", (W, H), (0, 0, 0))
            d = ImageDraw.Draw(img)
            xs, ys = frozen
            for x, y, s in zip(xs, ys, sizes):
                d.ellipse([x - s, y - s, x + s, y + s], fill=(200, 200, 210))
            d.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 255, 255))
            text_c(d, "Now… it's NOT moving.\nWhy is it still spinning?",
                   160, 60, (255, 210, 90))
            handle_text(d, handle, (110, 110, 120))
        wr.write(img)
    wr.close()
    return {
        "style": "blackhole", "subject": "vortex", "seed": seed,
        "caption": ("Stare at the dot until the countdown ends 🌀 When it "
                    "stops, the picture keeps moving the OTHER way. That's "
                    "the motion aftereffect: the motion-detecting neurons in "
                    "your brain get tired and the opposite ones take over. "
                    "Did it work on you?"),
        "hashtags": ["#motionaftereffect", "#opticalillusion", "#illusion",
                     "#trippy", "#brainteaser", "#mindblown", "#perception",
                     "#science", "#hypnotic", "#reels"],
    }
