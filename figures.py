"""
3D figure library for silhouette illusions.

Figures are built from two primitives whose orthographic silhouettes can be
drawn exactly in 2D:
  * cone(p0, r0, p1, r1)  - sphere-swept cone (tapered limb). Its projection
                            is the convex hull of two circles.
  * ell(c, M)             - ellipsoid {c + M u : |u| <= 1}. Its projection is
                            an ellipse with shape matrix N N^T, N = top rows.
Coordinates: y up, figure faces +x, rotation is about the vertical (y) axis.
"""
import math
import numpy as np

V = lambda *a: np.array(a, float)


def Rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.]])


def Ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def Rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def cone(p0, r0, p1, r1):
    return ("cone", V(*p0), r0, V(*p1), r1)


def ell(c, semi, R=None):
    M = np.diag(semi)
    if R is not None:
        M = R @ M
    return ("ell", V(*c), M)


def chain(points, r0, r1):
    """Tapered tube through a list of points, radius r0 -> r1."""
    n = len(points) - 1
    rs = np.linspace(r0, r1, n + 1)
    return [cone(points[i], rs[i], points[i + 1], rs[i + 1]) for i in range(n)]


def mirror_z(prims):
    out = []
    for p in prims:
        if p[0] == "cone":
            f = lambda v: v * V(1, 1, -1)
            out.append(("cone", f(p[1]), p[2], f(p[3]), p[4]))
        else:
            out.append(("ell", p[1] * V(1, 1, -1), np.diag([1, 1, -1.]) @ p[2]))
    return out


# ------------------------------------------------------------ figures
def ballerina(pose, rng):
    j = lambda x: rng.normal(0, x)
    P = []
    # support leg on pointe
    P += chain([(0, .98, .07), (0, .52, .07), (0, .09, .07)], .082, .034)
    P += [cone((0, .09, .07), .03, (.02, 0, .07), .012)]
    lean = .06 if pose == "arabesque" else 0
    # pelvis, torso, head
    P += [ell((0, 1.02, 0), (.11, .11, .15)),
          cone((.01, 1.06, 0), .085, (lean, 1.36, 0), .1),
          ell((lean, 1.35, 0), (.085, .11, .125)),
          cone((lean + .01, 1.46, 0), .036, (lean + .02, 1.56, 0), .031),
          ell((lean + .04, 1.66, 0), (.075, .095, .068)),
          ell((lean - .03, 1.71, 0), (.045, .045, .045)),          # bun
          ell((0, .96, 0), (.34, .035, .34), Rz(-.08))]           # tutu
    sh = lambda s: (lean, 1.44, .13 * s)
    if pose == "arabesque":
        P += chain([(0, .98, -.07), (-.42, 1.02 + j(.03), -.08),
                    (-.82, 1.1 + j(.04), -.09), (-.95, 1.12, -.09)],
                   .066, .012)
        P += chain([sh(1), (.33, 1.5, .16), (.6, 1.57, .13), (.68, 1.58, .12)],
                   .036, .008)
        P += chain([sh(-1), (lean, 1.45, -.42), (-.03, 1.45, -.68),
                    (-.04, 1.45, -.75)], .036, .008)
    elif pose == "passe":
        P += chain([(0, .98, -.07), (.12, .84, -.42), (.03, .57, -.11),
                    (.03, .52, .02)], .08, .012)
        for s in (1, -1):
            P += chain([sh(s), (.05, 1.72, .23 * s), (.08, 1.87, .09 * s),
                        (.08, 1.9, .03 * s)], .036, .008)
    else:  # a la seconde: leg to the side, arms open
        P += chain([(0, .98, -.07), (.02, 1.02, -.46), (.03, 1.08, -.88),
                    (.03, 1.1, -.98)], .08, .012)
        P += chain([sh(1), (.06, 1.46, .4), (.1, 1.43, .66), (.11, 1.42, .74)],
                   .036, .008)
        P += chain([sh(-1), (.12, 1.55, -.3), (.24, 1.68, -.4),
                    (.27, 1.7, -.43)], .036, .008)
    return P, (0, 0)                  # spin around the supporting foot


def cat(rng):
    s = rng.uniform(-.08, .08)        # walking stride
    P = [ell((0, .42, 0), (.38, .15, .14)),
         ell((.25, .45, 0), (.15, .16, .13)),
         ell((.5, .63, 0), (.13, .11, .12)),
         ell((.6, .6, 0), (.05, .04, .05))]
    for z in (1, -1):
        P += [cone((.48, .7, .07 * z), .045, (.47, .83, .085 * z), .006)]
    for z, d in ((1, s), (-1, -s)):
        P += chain([(.28, .4, .08 * z), (.3 + d, .08, .08 * z),
                    (.33 + d, .02, .08 * z)], .05, .03)
        P += chain([(-.28, .42, .08 * z), (-.18 - d, .22, .08 * z),
                    (-.3 - d, .07, .08 * z), (-.26 - d, .02, .08 * z)],
                   .075, .03)
    P += chain([(-.36, .45, 0), (-.56, .55, 0), (-.62, .78, .05),
                (-.53, .96, .1), (-.45, 1.0, .12)], .042, .022)
    return P, None


def flamingo(rng):
    tilt = Rz(.25)
    P = [cone((0, 0, 0), .02, (0, .5, 0), .016),
         cone((0, .5, 0), .02, (-.02, .98, 0), .018),
         cone((-.02, .02, 0), .012, (.12, 0, 0), .006),
         ell((0, 1.06, 0), (.3, .16, .15), tilt),
         cone((-.25, 1.02, 0), .1, (-.42, 1.0, 0), .03)]
    P += chain([(.2, 1.12, 0), (.33, 1.33, 0), (.22, 1.54, 0), (.3, 1.73, 0),
                (.4, 1.77, 0)], .045, .03)
    P += [ell((.43, 1.77, 0), (.065, .045, .045)),
          cone((.47, 1.76, 0), .026, (.57, 1.66, 0), .008)]
    P += chain([(0, 1.0, -.05), (.12, .72, -.06), (-.18, .9, -.07),
                (-.25, .9, -.07)], .02, .012)
    return P, (0, 0)


def trex(rng):
    s = rng.uniform(-.12, .12)
    P = [ell((0, 1.0, 0), (.45, .27, .24), Rz(.18)),
         cone((.32, 1.12, 0), .17, (.55, 1.36, 0), .13),
         ell((.72, 1.43, 0), (.25, .13, .12)),
         ell((.73, 1.31, 0), (.2, .06, .09), Rz(-.1))]
    P += chain([(-.35, 1.0, 0), (-.85, .95, 0), (-1.3, .86, 0),
                (-1.5, .8, 0)], .21, .02)
    for z, d in ((1, s), (-1, -s)):
        P += [ell((d * .5, .82, .18 * z), (.17, .25, .1))]
        P += chain([(.05 + d, .68, .18 * z), (-.05 + d, .2, .18 * z),
                    (.15 + d, .03, .18 * z)], .1, .03)
        P += chain([(.42, 1.05, .15 * z), (.52, .96, .18 * z),
                    (.56, .98, .18 * z)], .035, .015)
    return P, None


def shark(rng):
    P = [ell((0, 0, 0), (.9, .2, .21)),
         ell((.72, .02, 0), (.28, .14, .15)),
         cone((-.8, 0, 0), .13, (-1.15, .02, 0), .05),
         cone((-1.15, .02, 0), .06, (-1.42, .38, 0), .01),
         cone((-1.15, .02, 0), .06, (-1.36, -.22, 0), .01),
         cone((.05, .15, 0), .1, (-.18, .55, 0), .01),
         cone((-.65, .12, 0), .03, (-.72, .25, 0), .008)]
    for z in (1, -1):
        P += [cone((.3, -.1, .14 * z), .07, (.02, -.35, .55 * z), .01)]
    return P, None


def butterfly(rng):
    P = [cone((0, -.4, 0), .045, (0, .38, 0), .045),
         ell((0, .47, 0), (.07, .07, .07))]
    for s in (1, -1):
        P += [cone((0, .5, 0), .012, (.16 * s, .85, .05), .008),
              ell((.16 * s, .86, .05), (.025, .025, .025)),
              ell((.42 * s, .25, .1), (.46, .3, .02), Ry(-.35 * s) @ Rz(.6 * s)),
              ell((.3 * s, -.24, .06), (.3, .21, .02), Ry(-.3 * s) @ Rz(-.5 * s))]
    return P, None


FIGURES = {
    "ballerina arabesque": lambda r: ballerina("arabesque", r),
    "ballerina passe": lambda r: ballerina("passe", r),
    "ballerina seconde": lambda r: ballerina("seconde", r),
    "cat": cat, "flamingo": flamingo, "t-rex": trex, "shark": shark,
    "butterfly": butterfly,
}


def build(name, rng):
    prims, pivot = FIGURES[name](rng)
    if pivot is None:     # spin about the middle of the figure
        pts = np.array([p[1] for p in prims])
        pivot = ((pts[:, 0].max() + pts[:, 0].min()) / 2,
                 (pts[:, 2].max() + pts[:, 2].min()) / 2)
    off = V(pivot[0], 0, pivot[1])
    out = []
    for p in prims:
        if p[0] == "cone":
            out.append(("cone", p[1] - off, p[2], p[3] - off, p[4]))
        else:
            out.append(("ell", p[1] - off, p[2]))
    return out


def extent(prims):
    """(max horizontal radius, ymin, ymax) over any rotation about y."""
    rad, ymin, ymax = 0, 1e9, -1e9
    for p in prims:
        if p[0] == "cone":
            for c, r in ((p[1], p[2]), (p[3], p[4])):
                rad = max(rad, math.hypot(c[0], c[2]) + r)
                ymin, ymax = min(ymin, c[1] - r), max(ymax, c[1] + r)
        else:
            c, M = p[1], p[2]
            ext = np.sqrt((M ** 2).sum(1))
            rad = max(rad, math.hypot(c[0], c[2]) + max(ext[0], ext[2]))
            ymin, ymax = min(ymin, c[1] - ext[1]), max(ymax, c[1] + ext[1])
    return rad, ymin, ymax


# ------------------------------------------------------------ drawing
def _hull(c0, r0, c1, r1, n=10):
    d = np.linalg.norm(c1 - c0)
    if d <= abs(r1 - r0) + 1e-9:
        return None
    u = (c1 - c0) / d
    a = math.acos(max(-1, min(1, (r0 - r1) / d)))
    rot = lambda v, t: np.array([v[0] * math.cos(t) - v[1] * math.sin(t),
                                 v[0] * math.sin(t) + v[1] * math.cos(t)])
    n1, n2 = rot(u, a), rot(u, -a)
    return [tuple(c0 + r0 * n1), tuple(c1 + r1 * n1),
            tuple(c1 + r1 * n2), tuple(c0 + r0 * n2)]


def _ellipse_pts(c, N, grow=0.0, n=72):
    S = N @ N.T
    w, U = np.linalg.eigh(S)
    ax = np.sqrt(np.maximum(w, 1e-12)) + grow
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    pts = (U @ (ax[:, None] * np.vstack([np.cos(t), np.sin(t)]))).T + c
    return [tuple(p) for p in pts]


def draw(d, prims, theta, cx, cy, scale, fill, outline=None, ow=0.0,
         depth_sign=1, extra_rot=None):
    """Draw silhouette rotated by theta about y. With outline, pieces are
    painted back-to-front (using depth_sign to choose which way is 'front')
    with a ring of width ow, which acts as an occlusion depth cue."""
    R = Ry(theta) if extra_rot is None else extra_rot @ Ry(theta)
    items = []
    for p in prims:
        if p[0] == "cone":
            a, b = R @ p[1], R @ p[3]
            items.append(((a[2] + b[2]) / 2, "cone", a, p[2], b, p[4]))
        else:
            c, M = R @ p[1], R @ p[2]
            items.append((c[2], "ell", c, M))
    items.sort(key=lambda it: it[0] * depth_sign)
    to2 = lambda v: np.array([cx + v[0] * scale, cy - v[1] * scale])
    for it in items:
        layers = ([(outline, ow)] if outline is not None and ow > 0 else []) + \
            [(fill, 0.0)]
        for col, g in layers:
            if it[1] == "cone":
                c0, c1 = to2(it[2]), to2(it[4])
                r0, r1 = it[3] * scale + g, it[5] * scale + g
                for c, r in ((c0, r0), (c1, r1)):
                    d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=col)
                h = _hull(c0, r0, c1, r1)
                if h:
                    d.polygon(h, fill=col)
            else:
                c = to2(it[2])
                N = it[3][:2, :] * scale * np.array([[1], [-1]])
                d.polygon(_ellipse_pts(c, N, g), fill=col)
