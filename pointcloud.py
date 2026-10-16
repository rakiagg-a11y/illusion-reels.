"""
Point-cloud spin illusions: neon dot objects on black that can be seen
spinning either way ("reverse the spin with your mind").

Each object is a set of 3D points (with colours) that rotates about the
vertical axis under orthographic projection. Front and back points are drawn
identically (no size, brightness or occlusion difference), so the direction
of rotation is ambiguous. Points are splatted additively and given a soft
glow so they read like light, not dots of paint.

  python3 pointcloud.py --obj sphere --out test.mp4
"""
import argparse, math, subprocess, sys
import numpy as np
from scipy.ndimage import gaussian_filter

W, H, FPS = 1080, 1920, 30


# ---------------------------------------------------------------- helpers
def hue_rgb(h, s=1.0, v=1.0):
    h = np.asarray(h, float) % 1.0
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    v = np.broadcast_to(v, h.shape)
    p, q, t = [np.broadcast_to(x, h.shape) for x in (p, q, t)]
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)


NEON = {
    "red": (1.0, 0.12, 0.12), "blue": (0.2, 0.35, 1.0),
    "orange": (1.0, 0.62, 0.15), "purple": (0.55, 0.3, 1.0),
    "gold": (1.0, 0.8, 0.35), "cyan": (0.2, 0.9, 1.0),
    "pink": (1.0, 0.3, 0.75), "green": (0.3, 1.0, 0.45),
    "white": (0.9, 0.9, 1.0),
}


def col(name, n):
    return np.tile(np.array(NEON[name]), (n, 1))


def line_pts(a, b, n):
    t = np.linspace(0, 1, n)[:, None]
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def polyline_pts(pts, per_unit=900):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        n = max(2, int(np.linalg.norm(np.subtract(b, a)) * per_unit))
        out.append(line_pts(a, b, n))
    return np.vstack(out)


# ---------------------------------------------------------------- objects
# Each returns (points Nx3, colours Nx3, weights N) in a ~[-1,1] box, y up.

def streak_sphere(rng):
    """Sphere textured with short rainbow streaks (dashes)."""
    n, k = 4200, 26
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    # streak direction: random tangent, biased diagonally for a "flow" look
    ref = np.array([0.6, 1.0, 0.2])
    t1 = np.cross(v, ref)
    t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    t2 = np.cross(v, t1)
    ang = rng.normal(0.4, 0.5, n)[:, None]
    d = t1 * np.cos(ang) + t2 * np.sin(ang)
    L = rng.uniform(0.03, 0.08, n)[:, None]
    s = np.linspace(-0.5, 0.5, k)
    pts = (v[:, None, :] + d[:, None, :] * L[:, None, :] * s[None, :, None])
    pts = (pts / np.linalg.norm(pts, axis=2, keepdims=True)).reshape(-1, 3)
    hue = np.repeat(rng.random(n), k)
    val = np.repeat(rng.uniform(0.35, 1.0, n), k)
    c = hue_rgb(hue, 0.8, val)
    # thin grey rim so the sphere's edge reads clearly (rotation-invariant)
    a = np.linspace(0, 2 * np.pi, 2500)
    rim = np.c_[np.cos(a), np.sin(a), np.zeros_like(a)] * 0.81
    return (pts * 0.8, c * 1.3, np.full(len(pts), 0.45),
            {"static": (rim, np.full((len(rim), 3), 0.5)), "tilt": 0.0})


def arrow_arc(rng, a0, a1, R, h, cname, head_len=0.5, head_w=2.3):
    """Dotted band from angle a0 to a1 ending in an arrowhead."""
    pts, cols = [], []
    n = int(9000 * (a1 - a0) / np.pi)
    a = rng.uniform(a0, a1, n)
    pts.append(np.c_[R * np.cos(a), rng.uniform(-h, h, n), R * np.sin(a)])
    cols.append(col(cname, n) * rng.uniform(0.4, 1.0, (n, 1)))
    aa = np.linspace(a0, a1, int(900 * (a1 - a0)))
    for yy in (-h, h):
        pts.append(np.c_[R * np.cos(aa), np.full_like(aa, yy), R * np.sin(aa)])
        cols.append(col(cname, len(aa)) * 1.5)
    tri = [(a1, -h * head_w), (a1 + head_len, 0.0), (a1, h * head_w)]
    for (b1, y1), (b2, y2) in zip(tri, tri[1:] + tri[:1]):
        t = np.linspace(0, 1, 600)
        bb, yy = b1 + (b2 - b1) * t, y1 + (y2 - y1) * t
        pts.append(np.c_[R * np.cos(bb), yy, R * np.sin(bb)])
        cols.append(col(cname, len(t)) * 1.5)
    m = 6000
    u, w = rng.random(m), rng.random(m)
    f = u + w > 1
    u[f], w[f] = 1 - u[f], 1 - w[f]
    (b1, y1), (b2, y2), (b3, y3) = tri
    bb = b1 + u * (b2 - b1) + w * (b3 - b1)
    yy = y1 + u * (y2 - y1) + w * (y3 - y1)
    pts.append(np.c_[R * np.cos(bb), yy, R * np.sin(bb)])
    cols.append(col(cname, m) * rng.uniform(0.4, 1.0, (m, 1)))
    return pts, cols


def band_arrows(rng, c1="purple", c2="orange"):
    """Two curved dotted arrows chasing each other around a circle."""
    R, h = 0.7, 0.22
    p1, k1 = arrow_arc(rng, 0.15, np.pi - 0.55, R, h, c1)
    p2, k2 = arrow_arc(rng, np.pi + 0.15, 2 * np.pi - 0.55, R, h, c2)
    P = np.vstack(p1 + p2)
    return P, np.vstack(k1 + k2), np.full(len(P), 0.5), {"tilt": 0.42}


def crown(rng):
    """Golden dotted ring with alternating red/blue light pillars."""
    pts, cols = [], []
    n = 7000
    a = rng.uniform(0, 2 * np.pi, n)
    r = 0.62 + rng.normal(0, 0.035, n)
    pts.append(np.c_[r * np.cos(a), rng.normal(-0.55, 0.03, n), r * np.sin(a)])
    cols.append(col("gold", n) * rng.uniform(0.4, 1.0, (n, 1)))
    k = 10
    for i in range(k):
        ang = 2 * np.pi * i / k
        m = 2400
        y = -0.55 + rng.random(m) ** 0.7 * rng.uniform(0.8, 1.35)
        rr = rng.normal(0, 0.03, (m, 2))
        x0, z0 = 0.62 * np.cos(ang), 0.62 * np.sin(ang)
        pts.append(np.c_[x0 + rr[:, 0], y, z0 + rr[:, 1]])
        cols.append(col("red" if i % 2 else "blue", m) *
                    rng.uniform(0.4, 1.0, (m, 1)))
        tip = y.max()
        pts.append(np.c_[np.full(60, x0), np.linspace(tip, tip + 0.06, 60),
                         np.full(60, z0)])
        cols.append(col("white", 60) * 1.5)
    P = np.vstack(pts)
    return P, np.vstack(cols), np.full(len(P), 0.5), {"tilt": 0.3}


def wedge_sphere(rng):
    """Red dotted sphere with a blue wireframe wedge (orange-slice cut)."""
    n = 26000
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    lon = np.arctan2(v[:, 2], v[:, 0])
    keep = ~((lon > 0.2) & (lon < 1.3) & (v[:, 1] > -0.1))
    P = v[keep] * 0.8
    C = col("red", len(P)) * rng.uniform(0.35, 1.0, (len(P), 1))
    edges = []
    for a in (0.2, 1.3):
        t = np.linspace(-0.1, 1, 600)
        th = np.arcsin(np.clip(t, -1, 1))
        edges.append(np.c_[np.cos(th) * np.cos(a), np.sin(th),
                           np.cos(th) * np.sin(a)])
        edges.append(line_pts((0, 0, 0), (math.cos(a), 0, math.sin(a)), 400)
                     * np.array([1, 1, 1]))
        edges.append(line_pts((0, 0, 0), (0, 1, 0), 400))
    aa = np.linspace(0.2, 1.3, 500)
    edges.append(np.c_[np.cos(aa) * math.cos(-0.1), np.full_like(aa, -0.1),
                       np.sin(aa) * math.cos(-0.1)])
    E = np.vstack(edges) * 0.8
    return (np.vstack([P, E]), np.vstack([C, col("blue", len(E)) * 1.5]),
            np.full(len(P) + len(E), 0.55), {"tilt": 0.25})


def chevron_ring(rng):
    """Red dotted ring band that ends in an arrow, with glowing chevrons."""
    pts, cols = [], []
    R, h = 0.62, 0.17
    n = 16000
    a = rng.uniform(0.25, 2 * np.pi - 0.15, n)
    y = rng.uniform(-h, h, n)
    pts.append(np.c_[R * np.cos(a), y, R * np.sin(a)])
    cols.append(col("red", n) * rng.uniform(0.35, 1.0, (n, 1)))
    for yy in (-h, h):
        aa = np.linspace(0.25, 2 * np.pi - 0.15, 3000)
        pts.append(np.c_[R * np.cos(aa), np.full_like(aa, yy), R * np.sin(aa)])
        cols.append(col("red", len(aa)) * 1.5)
    # arrow head at angle 0.25 pointing in the -angle direction
    head = [(0.25, -h * 2.2), (-0.35, 0.0), (0.25, h * 2.2)]
    for (a1, y1), (a2, y2) in zip(head, head[1:] + head[:1]):
        t = np.linspace(0, 1, 500)
        aa, yy = a1 + (a2 - a1) * t, y1 + (y2 - y1) * t
        pts.append(np.c_[R * np.cos(aa), yy, R * np.sin(aa)])
        cols.append(col("red", len(t)) * 1.5)
    # chevrons
    for a0 in np.arange(0.9, 2 * np.pi - 0.4, 0.55):
        for (a1, y1), (a2, y2) in (((a0, -h * .6), (a0 - .12, 0)),
                                   ((a0 - .12, 0), (a0, h * .6))):
            t = np.linspace(0, 1, 160)
            aa, yy = a1 + (a2 - a1) * t, y1 + (y2 - y1) * t
            pts.append(np.c_[R * np.cos(aa), yy, R * np.sin(aa)])
            cols.append(col("cyan", len(t)) * 1.3)
    P = np.vstack(pts)
    return P * 1.2, np.vstack(cols), np.full(len(P), 0.5), {"tilt": 0.4}


def dot_cube(rng):
    """Blue dotted cube volume with red glowing edges."""
    n = 30000
    P = rng.uniform(-1, 1, (n, 3))
    face = rng.integers(0, 3, n)
    P[np.arange(n), face] = np.sign(P[np.arange(n), face]) * 1.0
    C = col("blue", n) * rng.uniform(0.3, 1.0, (n, 1))
    E = []
    for a in (-1, 1):
        for b in (-1, 1):
            E += [line_pts((-1, a, b), (1, a, b), 500),
                  line_pts((a, -1, b), (a, 1, b), 500),
                  line_pts((a, b, -1), (a, b, 1), 500)]
    E = np.vstack(E)
    P = np.vstack([P, E]) * 0.5
    return (P, np.vstack([C, col("red", len(E)) * 1.5]),
            np.full(len(P), 0.5), {"tilt": 0.5})


def dna(rng):
    """Double helix of dots with glowing rungs."""
    pts, cols = [], []
    n = 9000
    for s, cname in ((0, "cyan"), (np.pi, "pink")):
        t = rng.uniform(0, 1, n)
        a = t * 4 * np.pi + s
        r = 0.35 + rng.normal(0, 0.02, n)
        pts.append(np.c_[r * np.cos(a), (t - 0.5) * 1.8, r * np.sin(a)])
        cols.append(col(cname, n) * rng.uniform(0.4, 1.0, (n, 1)))
    for t in np.linspace(0.02, 0.98, 22):
        a = t * 4 * np.pi
        p1 = (0.35 * np.cos(a), (t - .5) * 1.8, 0.35 * np.sin(a))
        p2 = (0.35 * np.cos(a + np.pi), (t - .5) * 1.8, 0.35 * np.sin(a + np.pi))
        pts.append(line_pts(p1, p2, 160))
        cols.append(col("white", 160) * 0.9)
    P = np.vstack(pts)
    return P, np.vstack(cols), np.full(len(P), 0.5), {"tilt": 0.15}


def saturn(rng):
    """Dotted planet with a tilted dotted ring."""
    n = 18000
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    P1 = v * 0.5
    C1 = hue_rgb(0.08 + 0.05 * v[:, 1], 0.7, rng.uniform(0.35, 1.0, n))
    m = 16000
    a = rng.uniform(0, 2 * np.pi, m)
    r = rng.uniform(0.68, 0.98, m)
    P2 = np.c_[r * np.cos(a), rng.normal(0, 0.008, m), r * np.sin(a)]
    C2 = col("gold", m) * rng.uniform(0.3, 1.0, (m, 1))
    P = np.vstack([P1, P2])
    return P, np.vstack([C1, C2]), np.full(len(P), 0.5), {"tilt": 0.38}


def Rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def text_mask_points(text, n, rng, height=0.32):
    """Sample n points uniformly inside the glyphs of `text` (bold font).
    Returns x, y in object units, centred, plus the outline points."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 220)
    lines = text.split("\n")
    tmp = ImageDraw.Draw(Image.new("L", (10, 10)))
    w = int(max(tmp.textlength(l, font=font) for l in lines)) + 40
    h = 260 * len(lines) + 20
    im = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        lw = tmp.textlength(l, font=font)
        d.text(((w - lw) / 2, 10 + i * 260), l, font=font, fill=255)
    m = np.asarray(im) > 128
    ys, xs = np.nonzero(m)
    k = rng.integers(0, len(xs), n)
    px = xs[k] + rng.random(n)
    py = ys[k] + rng.random(n)
    # outline: mask pixels with an empty neighbour
    edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) &
                 np.roll(m, 1, 1) & np.roll(m, -1, 1))
    ey, ex = np.nonzero(edge)
    sc = height * len(lines) / h * (h / (260 * len(lines)))
    cx, cy = w / 2, h / 2
    to = lambda X, Y: ((X - cx) * sc / 1.0, -(Y - cy) * sc / 1.0)
    fx, fy = to(px, py)
    gx, gy = to(ex + 0.5, ey + 0.5)
    span = max(np.abs(fx).max(), 1e-6)
    return fx, fy, gx, gy, span


def spin_text(text, rng):
    """Extruded neon dot lettering that spins both ways ("your name")."""
    fx, fy, gx, gy, span = text_mask_points(text, 26000, rng)
    k = 0.85 / span                       # fit width to ~1.7 units
    fx, fy, gx, gy = fx * k, fy * k, gx * k, gy * k
    depth = 0.07
    fz = rng.uniform(-depth, depth, len(fx))
    hue0 = rng.random()
    C = hue_rgb(hue0 + 0.25 * (fx - fx.min()) / (np.ptp(fx) + 1e-9), 0.85,
                rng.uniform(0.4, 1.0, len(fx)))
    E = np.vstack([np.c_[gx, gy, np.full_like(gx, z)] for z in (-depth, depth)])
    CE = np.tile(hue_rgb(np.array([hue0 + 0.1]), 0.6, 1.0), (len(E), 1)) * 1.3
    P = np.vstack([np.c_[fx, fy, fz], E])
    return P, np.vstack([C, CE]), np.r_[np.full(len(fx), 0.5),
                                         np.full(len(E), 0.35)], {"tilt": 0.12}


def hidden_word(text, rng):
    """A spinning cylinder of random-looking dots whose dots line up into
    `text` at one angle (and mirrored half a turn later). Pause in time."""
    R, Hh = 0.85, 0.6
    fx, fy, gx, gy, span = text_mask_points(text.replace(" ", "\n"), 26000,
                                            rng)
    k = min(0.7 / span, (Hh * 0.85) / max(np.abs(fy).max(), 1e-6))
    fx, fy = fx * k, fy * k
    # each word dot gets a random depth inside the cylinder along the view
    zmax = np.sqrt(np.clip(R ** 2 - fx ** 2, 0, None))
    fz = rng.uniform(-1, 1, len(fx)) * zmax
    # decoys fill the cylinder; their density per height band tops up the
    # word's own dots so every row has the same count and no band gives the
    # word away while it's scrambled
    bins = np.linspace(-Hh, Hh, 81)
    cw, _ = np.histogram(fy, bins)
    target = cw.max() + 120
    D = []
    for b in range(len(cw)):
        m = target - cw[b]
        a = rng.uniform(0, 2 * np.pi, m)
        r = R * np.sqrt(rng.random(m))
        D.append(np.c_[r * np.cos(a), rng.uniform(bins[b], bins[b + 1], m),
                       r * np.sin(a)])
    D = np.vstack(D)
    # spread word dots across the same disc shape as the decoys
    P = np.vstack([np.c_[fx, fy, fz], D])
    hue = rng.random()
    C = hue_rgb(hue + rng.normal(0, 0.07, len(P)), 0.75,
                rng.uniform(0.45, 1.0, len(P)))
    return P, C, np.full(len(P), 0.22), {"tilt": 0.0, "revs": 1,
                                         "phase": math.pi / 2, "dir": 1}


OBJECTS = {
    "rainbow sphere": streak_sphere,
    "arrow band": band_arrows,
    "crown": crown,
    "dark star": wedge_sphere,
    "arrow ring": chevron_ring,
    "cube": dot_cube,
    "DNA helix": dna,
    "planet": saturn,
}


# ---------------------------------------------------------------- render
class Scene:
    def __init__(self, obj, seed, seconds=15, text=None):
        rng = np.random.default_rng(seed)
        if obj == "spin text":
            P, C, wts, meta = spin_text(text or "OPTICPOP", rng)
        elif obj == "hidden word":
            P, C, wts, meta = hidden_word(text or "FOUND ME", rng)
        else:
            P, C, wts, meta = OBJECTS[obj](rng)
        self.tilt = meta.get("tilt", 0.3)
        P = P - np.array([0, (P[:, 1].max() + P[:, 1].min()) / 2, 0])
        rad = np.sqrt((P ** 2).sum(1)).max()
        self.scale = min(0.44 * W / rad, 0.36 * H / rad)
        self.P, self.Cw = P, C * wts[:, None]
        self.static = meta.get("static")
        # whole number of turns in the clip -> the reel loops seamlessly
        revs = meta.get("revs") or int(rng.choice([2, 3]))
        self.period = seconds / revs
        self.direction = meta.get("dir") or (1 if rng.random() < 0.5 else -1)
        self.phase = meta.get("phase", 0.0)

    def splat(self, th, buf, ss=1):
        """Add one sub-frame at angle th into buf, with bilinear splatting
        so points move smoothly between pixels. ss = supersampling factor
        (buf is (H*ss, W*ss, 3))."""
        c, s = math.cos(th), math.sin(th)
        P = self.P
        x = P[:, 0] * c + P[:, 2] * s
        z = -P[:, 0] * s + P[:, 2] * c
        ct, st = math.cos(self.tilt), math.sin(self.tilt)
        y = P[:, 1] * ct + z * st          # look slightly from above
        X, Y, Cw = [x], [y], [self.Cw]
        if self.static is not None:
            sp, scol = self.static
            X.append(sp[:, 0]); Y.append(sp[:, 1]); Cw.append(scol)
        x, y, Cw = np.concatenate(X), np.concatenate(Y), np.vstack(Cw)
        Wb, Hb = W * ss, H * ss
        fx = Wb / 2 + x * self.scale * ss
        fy = Hb / 2 - y * self.scale * ss
        x0, y0 = np.floor(fx).astype(int), np.floor(fy).astype(int)
        ax, ay = (fx - x0)[:, None], (fy - y0)[:, None]
        for dx, dy, wgt in ((0, 0, (1 - ax) * (1 - ay)), (1, 0, ax * (1 - ay)),
                            (0, 1, (1 - ax) * ay), (1, 1, ax * ay)):
            px, py = x0 + dx, y0 + dy
            ok = (px >= 0) & (px < Wb) & (py >= 0) & (py < Hb)
            idx = py[ok] * Wb + px[ok]
            cw = (Cw * wgt)[ok]
            flat = buf.reshape(-1, 3)
            for ch in range(3):                      # bincount >> add.at
                flat[:, ch] += np.bincount(idx, cw[:, ch], minlength=Wb * Hb)

    def frame(self, th, dth=0.0, sub=4, shutter=0.5):
        """Render angle th; with dth, average `sub` angles across the frame
        interval for a light motion blur."""
        buf = np.zeros((H, W, 3), np.float32)
        angles = [th] if dth == 0 or sub <= 1 else \
            [th + dth * shutter * (k / (sub - 1) - 0.5) for k in range(sub)]
        for a in angles:
            self.splat(a, buf)
        buf /= len(angles)
        core = gaussian_filter(buf, sigma=(0.8, 0.8, 0))
        g1 = gaussian_filter(buf[::2, ::2], sigma=(3, 3, 0))
        g2 = gaussian_filter(buf[::4, ::4], sigma=(6, 6, 0))
        up = lambda g, k: np.repeat(np.repeat(g, k, 0), k, 1)[:H, :W]
        img = core * 3.6 + up(g1, 2) * 3.0 + up(g2, 4) * 2.2   # layered bloom
        img = 1 - np.exp(-img * 1.7)                           # soft tone-map
        lum = img.mean(2, keepdims=True)
        img = np.clip(lum + (img - lum) * 1.25, 0, 1)          # punchier colour
        return (img * 255).astype(np.uint8)


    def frame_crisp(self, th, ss=2, dot=1.1, gain=2.2):
        """Sharp mode: render at ss x resolution with round, solid dots and
        only a faint glow, then downsample. Individual particles stay
        distinct (and survive Instagram's compression) instead of melting
        into a soft haze."""
        buf = np.zeros((H * ss, W * ss, 3), np.float32)
        self.splat(th, buf, ss)
        dots = gaussian_filter(buf, sigma=(dot * ss, dot * ss, 0))
        dots *= gain * (2 * np.pi * (dot * ss) ** 2) / 4   # keep each dot bright
        small = dots.reshape(H, ss, W, ss, 3).mean((1, 3))  # box downsample
        glow = gaussian_filter(small[::2, ::2], sigma=(4, 4, 0))
        glow = np.repeat(np.repeat(glow, 2, 0), 2, 1)[:H, :W]
        img = small + glow * 0.6
        img = 1 - np.exp(-img * 2.2)
        lum = img.mean(2, keepdims=True)
        img = np.clip(lum + (img - lum) * 1.35, 0, 1)
        return (img * 255).astype(np.uint8)


def render(obj, seed, out, seconds=15, handle="@opticpop", text=None):
    sc = Scene(obj, seed, seconds, text)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-maxrate", "10M", "-bufsize", "20M", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-movflags", "+faststart", out],
        stdin=subprocess.PIPE)
    wm = watermark(handle)
    for i in range(int(seconds * FPS)):
        step = sc.direction * 2 * np.pi / FPS / sc.period
        frame = sc.frame_crisp(sc.phase + step * i)   # sharp 4K-supersampled
        if wm is not None:
            frame = np.maximum(frame, wm)
        ff.stdin.write(frame.tobytes())
    ff.stdin.close()
    ff.wait()
    return {"style": "pointspin", "subject": obj, "seed": seed,
            "text": text}


def watermark(handle):
    if not handle:
        return None
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 34)
    w = d.textlength(handle, font=f)
    # top of the frame, just below Instagram's Reels header bar
    d.text(((W - w) / 2, 250), handle, font=f, fill=(95, 95, 105))
    return np.asarray(im)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--obj", default="rainbow sphere", choices=list(OBJECTS))
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="spin.mp4")
    ap.add_argument("--seconds", type=float, default=15)
    a = ap.parse_args()
    print(render(a.obj, a.seed, a.out, a.seconds))
