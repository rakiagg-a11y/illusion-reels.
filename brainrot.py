"""Brainrot meme characters as transparent particle sculptures for ambiguous rotation.

Each character is modelled as a union of smooth signed-distance primitives
(rounded boxes, tapered capsules, ellipsoids, cylinders, tori), and particles
are scattered on the resulting surface. That gives joined, anatomical shapes
(shoulders, elbows, hands, knees, feet) like a sculpted figure, while the
rendering stays additive and occlusion-free, so the figure still reads as
spinning either way under orthographic projection.
"""
import math
from pathlib import Path

import numpy as np

# Display names for captions. A character joins the rotation once it has a
# reference picture in assets/brainrot/ (or a hand-built sculpture below).
NAMES = {
    "tung_tung_sahur": "Tung Tung Tung Sahur", "tralalero_tralala": "Tralalero Tralala",
    "ballerina_cappuccina": "Ballerina Cappuccina", "bombardiro_crocodilo": "Bombardiro Crocodilo",
    "lirili_larila": "Lirili Larila", "brr_brr_patapim": "Brr Brr Patapim",
    "chimpanzini_bananini": "Chimpanzini Bananini", "cappuccino_assassino": "Cappuccino Assassino",
    "trippi_troppi": "Trippi Troppi", "boneca_ambalabu": "Boneca Ambalabu",
    "la_vaca_saturno_saturnita": "La Vaca Saturno Saturnita", "udin_din_din_dun": "Udin Din Din Dun",
    "frigo_camelo": "Frigo Camelo", "bobrito_bandito": "Bobrito Bandito",
    "tric_trac_baraboom": "Tric Trac Baraboom", "mario": "Mario", "tom": "Tom", "jerry": "Jerry",
}
TILTS = (0, 6, 12)

WOOD = (255, 125, 35)
EYE_WHITE = (255, 235, 200)
IRIS = (120, 80, 40)


# ---------------------------------------------------------------- primitives
def sphere(c, r):
    c = np.asarray(c, float)
    return lambda p: np.linalg.norm(p-c, axis=1)-r


def _turn(axis, degrees):
    a = math.radians(degrees)
    co, si = math.cos(a), math.sin(a)
    i = "xyz".index(axis)
    j, k = [n for n in range(3) if n != i]
    m = np.eye(3)
    m[j, j], m[j, k], m[k, j], m[k, k] = co, -si, si, co
    return m


def ellipsoid(c, radii, axis="z", degrees=0):
    """Ellipsoid, optionally turned about one axis (fins, ears, wings)."""
    c, radii = np.asarray(c, float), np.asarray(radii, float)
    m = _turn(axis, degrees)

    def d(p):
        q = ((p-c) @ m)/radii
        k = np.linalg.norm(q, axis=1)
        return (k-1)*radii.min()
    return d


def round_box(c, half, r):
    c, half = np.asarray(c, float), np.asarray(half, float)-r

    def d(p):
        q = np.abs(p-c)-half
        return np.linalg.norm(np.maximum(q, 0), axis=1)+np.minimum(q.max(1), 0)-r
    return d


def capsule(a, b, ra, rb=None):
    """Tapered capsule from a (radius ra) to b (radius rb)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rb = ra if rb is None else rb
    ab = b-a

    def d(p):
        t = np.clip(((p-a) @ ab)/(ab @ ab), 0, 1)
        return np.linalg.norm(p-(a+t[:, None]*ab), axis=1)-(ra+(rb-ra)*t)
    return d


def limb(points, radii):
    """Chain of tapered capsules through joints (shoulder-elbow-wrist etc.)."""
    parts = [capsule(points[i], points[i+1], radii[i], radii[i+1]) for i in range(len(points)-1)]
    return lambda p: np.min([f(p) for f in parts], axis=0)


def cylinder_y(c, r, h, round_r=.02):
    c = np.asarray(c, float)

    def d(p):
        q = p-c
        dx = np.hypot(q[:, 0], q[:, 2])-(r-round_r)
        dy = np.abs(q[:, 1])-(h/2-round_r)
        return np.minimum(np.maximum(dx, dy), 0)+np.hypot(np.maximum(dx, 0), np.maximum(dy, 0))-round_r
    return d


def cone_y(c, r_bottom, r_top, h):
    """Truncated cone along y (cup shapes)."""
    c = np.asarray(c, float)

    def d(p):
        q = p-c
        t = np.clip(q[:, 1]/h+.5, 0, 1)
        r = r_bottom+(r_top-r_bottom)*t
        dx = np.hypot(q[:, 0], q[:, 2])-r
        dy = np.abs(q[:, 1])-h/2
        return np.minimum(np.maximum(dx, dy), 0)+np.hypot(np.maximum(dx, 0), np.maximum(dy, 0))
    return d


def torus(c, axis, R, r):
    c = np.asarray(c, float)
    i = "xyz".index(axis)
    j, k = [n for n in range(3) if n != i]

    def d(p):
        q = p-c
        return np.hypot(np.hypot(q[:, j], q[:, k])-R, q[:, i])-r
    return d


def flat(c, half, r=.01):
    """Thin plate (fins, wings, ears)."""
    return round_box(c, half, r)


# ---------------------------------------------------------------- sampler
class Sculpture:
    def __init__(self, rng):
        self.rng, self.parts = rng, []

    def add(self, sdf, color, density=1., weight=(.10, .30)):
        self.parts.append((sdf, np.asarray(color, float), density, weight))

    def sample(self, lo, hi, total=70000, shell=.006):
        """Scatter particles on each part's surface, but only where no other
        part covers it, so joints read as one continuous skin."""
        lo, hi = np.asarray(lo, float), np.asarray(hi, float)
        out_p, out_c = [], []
        n = max(1, len(self.parts))
        candidates = int(total*90)
        p = self.rng.uniform(lo, hi, (candidates, 3))
        dists = np.stack([sdf(p) for sdf, *_ in self.parts])
        union = dists.min(0)
        near = np.abs(union) < shell
        owner = dists.argmin(0)
        for k, (sdf, color, density, weight) in enumerate(self.parts):
            mask = near & (owner == k)
            pts = p[mask]
            keep = self.rng.random(len(pts)) < min(1., density)
            pts = pts[keep]
            w = self.rng.uniform(*weight, len(pts))
            out_p.append(pts)
            out_c.append(w[:, None]*color/255)
        return np.vstack(out_p), np.vstack(out_c)


def _eye(s, c, r, facing, iris_frac=.42, pupil_frac=.30):
    """Protruding eyeball: bright sclera, coloured iris ring, empty pupil."""
    c = np.asarray(c, float)
    facing = np.asarray(facing, float)/np.linalg.norm(facing)
    ball = ellipsoid(c, r) if np.ndim(r) else sphere(c, r)

    def angle(p):
        v = p-c
        return np.arccos(np.clip((v @ facing)/np.maximum(np.linalg.norm(v, axis=1), 1e-9), -1, 1))
    iris_a, pupil_a = math.asin(iris_frac), math.asin(pupil_frac)
    # Bright sclera, a faint iris ring and an empty (dark) pupil.
    s.add(lambda p: np.where(angle(p) > iris_a, ball(p), 1.), EYE_WHITE, 1., (.45, .75))
    s.add(lambda p: np.where((angle(p) <= iris_a) & (angle(p) > pupil_a), ball(p), 1.), IRIS, 1., (.15, .30))


# ---------------------------------------------------------------- characters
def _tung_tung(s):
    # Tall rounded wooden log; the face is carved in profile on the front.
    s.add(round_box((0, .25, 0), (.28, .50, .245), .09), WOOD)
    for x in (-.11, .11):
        _eye(s, (x, .55, .21), (.065, .10, .05), (0, 0, 1))
    # Long protruding nose, lips and a small chin.
    s.add(capsule((0, .52, .23), (0, .40, .34), .05, .03), WOOD)
    s.add(sphere((0, .395, .335), .04), WOOD)
    s.add(ellipsoid((0, .31, .255), (.10, .022, .035)), WOOD)
    s.add(ellipsoid((0, .265, .25), (.085, .02, .03)), WOOD)
    s.add(ellipsoid((0, .21, .245), (.07, .035, .025)), WOOD)
    for side in (-1, 1):
        # Thin arms hang from the upper sides, elbows slightly back.
        x = side*.32
        s.add(limb([(side*.27, .45, 0), (x, .08, -.05), (x, -.24, .05)], [.05, .042, .036]), WOOD)
        s.add(ellipsoid((x, -.29, .05), (.032, .06, .045)), WOOD)
        if side < 0:
            # Open hand, fingers hanging down.
            for f in range(4):
                z = .02+f*.022
                s.add(limb([(x, -.33, z), (x, -.38, z+.005), (x+.005, -.42, z)], [.012, .011, .009]), WOOD)
            s.add(capsule((x+.02, -.30, .09), (x+.025, -.36, .11), .012, .009), WOOD)
        else:
            # Fist wrapped around the bat handle.
            for f in range(4):
                s.add(torus((x, -.33, -.01+f*.026), "z", .038, .012), WOOD)
        # Long legs with knees, ankles and big bare feet.
        s.add(limb([(side*.13, -.20, 0), (side*.14, -.60, .04), (side*.13, -.94, -.03)], [.065, .05, .04]), WOOD)
        s.add(sphere((side*.13, -.97, -.06), .055), WOOD)
        s.add(ellipsoid((side*.13, -.985, .07), (.075, .04, .15)), WOOD)
        for t in range(5):
            s.add(sphere((side*(.08+.025*t), -.99, .21-.012*t), .025-.003*t), WOOD)
    # Baseball bat held horizontally at hip height: knob, handle, thick barrel.
    s.add(sphere((.32, -.33, -.34), .045), WOOD)
    s.add(capsule((.32, -.33, -.32), (.32, -.33, .25), .025, .04), WOOD)
    s.add(capsule((.32, -.33, .25), (.32, -.33, .78), .04, .07), WOOD)
    return (-.5, -1.05, -.45), (.5, .80, .90)


def _tralalero(s):
    blue, white, belly, swoosh = (70, 150, 255), (235, 240, 255), (175, 215, 255), (40, 90, 230)
    # Streamlined shark: thick head, body tapering into the tail stalk.
    s.add(ellipsoid((.05, .30, 0), (.55, .20, .18)), blue)
    s.add(capsule((-.35, .32, 0), (-.80, .36, 0), .13, .035), blue)
    s.add(ellipsoid((.15, .21, 0), (.42, .09, .14)), belly, .7)
    # Crescent tail, dorsal and pectoral fins as thin swept blades.
    s.add(ellipsoid((-.88, .50, 0), (.06, .19, .015), "z", -25), blue)
    s.add(ellipsoid((-.86, .24, 0), (.05, .12, .015), "z", 35), blue)
    s.add(ellipsoid((-.05, .52, 0), (.07, .16, .015), "z", -35), blue)
    for z in (-1, 1):
        s.add(ellipsoid((.10, .15, z*.20), (.13, .015, .07), "y", z*30), blue)
        _eye(s, (.40, .38, z*.12), .04, (.4, .1, z))
        for g in range(3):
            s.add(ellipsoid((.22-.05*g, .32, z*.17), (.006, .06, .006)), belly, 1., (.2, .4))
    # Open jaw lined with teeth.
    s.add(ellipsoid((.48, .18, 0), (.10, .025, .10)), (255, 120, 150), 1., (.15, .3))
    for i in range(9):
        a = -1.1+2.2*i/8
        x, z = .48+.09*math.cos(a), .09*math.sin(a)
        s.add(capsule((x, .20, z), (x, .16, z), .01, .003), white, 1., (.45, .7))
    # Three legs ending in high-top sneakers with a swoosh.
    for x, z in ((-.22, .09), (.03, -.09), (.28, .09)):
        s.add(limb([(x, .16, z), (x+.02, -.12, z+.01), (x, -.40, z)], [.055, .045, .04]), blue)
        s.add(cylinder_y((x, -.43, z), .055, .08), white, 1., (.3, .5))
        s.add(round_box((x+.05, -.50, z), (.13, .045, .07), .035), white, 1., (.3, .5))
        s.add(round_box((x+.05, -.555, z), (.135, .012, .072), .008), blue)
        for side in (-1, 1):
            s.add(capsule((x-.04, -.49, z+side*.072), (x+.10, -.46, z+side*.072), .008, .004), swoosh, 1., (.4, .6))
    return (-1.0, -.6, -.45), (.7, .72, .45)


def _ballerina(s):
    cup, foam, pink, skin, coffee = (200, 125, 70), (255, 238, 215), (255, 140, 190), (255, 205, 170), (150, 90, 50)
    # Cappuccino cup head: saucer rim, handle, foam with a heart of coffee.
    s.add(cone_y((0, .72, 0), .12, .18, .24), cup)
    s.add(torus((0, .84, 0), "y", .18, .015), foam, 1., (.3, .5))
    s.add(ellipsoid((0, .845, 0), (.17, .03, .17)), foam, 1., (.25, .45))
    s.add(ellipsoid((0, .87, 0), (.06, .01, .05)), coffee, 1., (.3, .5))
    s.add(torus((.20, .72, 0), "z", .055, .018), cup)
    for x in (-.06, .06):
        _eye(s, (x, .73, .16), .035, (0, 0, 1))
    s.add(capsule((-.04, .65, .17), (.04, .65, .17), .008), (255, 120, 120), 1., (.35, .55))
    # Slim neck, bodice and hips.
    s.add(capsule((0, .60, 0), (0, .50, 0), .035), skin)
    s.add(capsule((0, .46, 0), (0, .24, 0), .11, .085), pink)
    s.add(ellipsoid((0, .17, 0), (.12, .07, .09)), pink)
    # Layered, scalloped tutu.
    for y, r in ((.17, .40), (.12, .36)):
        s.add(ellipsoid((0, y, 0), (r, .035, r)), pink, .45, (.10, .22))
    for k in range(12):
        a = 2*math.pi*k/12
        s.add(sphere((.40*math.cos(a), .14, .40*math.sin(a)), .045), pink, 1., (.15, .32))
    for side in (-1, 1):
        # Arms arched over the head (fifth position), hands nearly touching.
        s.add(limb([(side*.12, .46, 0), (side*.27, .66, .02), (side*.20, .97, .02), (side*.05, 1.04, 0)],
                   [.035, .03, .025, .02]), skin)
        s.add(ellipsoid((side*.03, 1.05, 0), (.03, .02, .02)), skin)
    # Standing leg on pointe and a bent passé leg, both in pink shoes.
    s.add(limb([(-.05, .12, 0), (-.06, -.38, .02), (-.06, -.86, 0)], [.06, .042, .03]), skin)
    s.add(capsule((-.06, -.86, 0), (-.06, -1.0, .01), .03, .02), pink)
    s.add(limb([(.05, .12, 0), (.28, -.28, .06), (-.03, -.40, .02)], [.06, .042, .03]), skin)
    s.add(capsule((-.03, -.40, .02), (-.08, -.44, .02), .03, .02), pink)
    return (-.55, -1.05, -.5), (.55, 1.10, .5)


def _bombardiro(s):
    green, belly, metal, white, dark = (90, 200, 90), (190, 230, 150), (175, 185, 200), (240, 240, 230), (60, 120, 60)
    # Crocodile head and body form the fuselage.
    s.add(ellipsoid((-.05, 0, 0), (.62, .22, .22)), green)
    s.add(ellipsoid((0, -.07, 0), (.55, .14, .18)), belly, .7)
    s.add(capsule((-.55, .02, 0), (-1.0, .10, 0), .16, .04), green)
    for k in range(7):
        x = -.55+.17*k
        s.add(ellipsoid((x, .21, 0), (.04, .035, .03)), dark)
    # Long snout with nostrils, eye bumps and interlocking teeth.
    s.add(round_box((.80, .05, 0), (.30, .07, .13), .05), green)
    s.add(round_box((.78, -.08, 0), (.29, .04, .12), .03), belly)
    for z in (-1, 1):
        s.add(sphere((.48, .20, z*.09), .07), green)
        _eye(s, (.50, .23, z*.10), .045, (.3, .6, z))
        s.add(sphere((1.05, .11, z*.05), .02), dark)
    for i in range(9):
        x = .58+.055*i
        for z in (-.12, .12):
            s.add(capsule((x, -.02, z), (x, -.07, z), .008, .003), white, 1., (.4, .6))
    # Swept bomber wings with engines and spinning propellers; tail plane and fin.
    for z in (-1, 1):
        s.add(ellipsoid((.0, .0, z*.60), (.20, .025, .48), "y", z*8), metal)
        for e in (.32, .62):
            s.add(capsule((.32, -.05, z*e), (-.10, -.05, z*e), .065, .045), metal)
            s.add(ellipsoid((.36, -.05, z*e), (.03, .14, .022), "x", 0), white, 1., (.3, .5))
            s.add(ellipsoid((.36, -.05, z*e), (.03, .022, .14), "x", 0), white, 1., (.3, .5))
        s.add(ellipsoid((-.88, .10, z*.22), (.11, .018, .20)), metal)
    s.add(ellipsoid((-.90, .30, 0), (.12, .20, .018), "z", -20), metal)
    # Bombs slung under the belly.
    for x in (-.15, .15):
        s.add(capsule((x-.10, -.26, 0), (x+.10, -.26, 0), .045), dark)
    return (-1.1, -.35, -1.15), (1.15, .55, 1.15)


def _lirili(s):
    grey, cactus, spine, sandal, flower = (190, 190, 205), (90, 200, 110), (230, 255, 200), (200, 140, 80), (255, 120, 170)
    # Elephant head with big rounded fan ears, curling trunk and tusks.
    s.add(sphere((0, .72, 0), .20), grey)
    for side in (-1, 1):
        s.add(ellipsoid((side*.25, .72, -.04), (.14, .19, .02), "y", side*-20), grey)
        _eye(s, (side*.08, .78, .17), .03, (side*.3, 0, 1))
        s.add(capsule((side*.07, .60, .15), (side*.11, .50, .26), .018, .006), (255, 250, 235), 1., (.4, .6))
    s.add(limb([(0, .66, .19), (0, .50, .27), (.02, .34, .26), (.09, .27, .20), (.12, .30, .14)],
               [.07, .055, .04, .028, .02]), grey)
    # Saguaro cactus body with ribbed arms, spines and a flower.
    s.add(capsule((0, -.45, 0), (0, .50, 0), .17, .16), cactus)
    for k in range(8):
        a = 2*math.pi*k/8
        s.add(capsule((.17*math.cos(a), -.45, .17*math.sin(a)), (.16*math.cos(a), .45, .16*math.sin(a)), .012),
              (70, 170, 90), 1., (.15, .3))
    for side, y in ((-1, .10), (1, -.08)):
        s.add(limb([(side*.15, y, 0), (side*.36, y, 0), (side*.38, y+.32, 0)], [.065, .065, .06]), cactus)
    for k in range(26):
        a, y = k*2.4, -.40+.035*k
        s.add(capsule((.17*math.cos(a), y, .17*math.sin(a)), (.23*math.cos(a), y+.02, .23*math.sin(a)), .004),
              spine, 1., (.35, .55))
    s.add(sphere((-.38, .45, 0), .04), flower, 1., (.35, .55))
    # Elephant legs in strappy sandals.
    for side in (-1, 1):
        s.add(limb([(side*.08, -.55, 0), (side*.09, -.86, 0)], [.07, .065]), grey)
        s.add(round_box((side*.09, -.92, .04), (.07, .015, .12), .01), sandal)
        for z in (-.02, .08):
            s.add(torus((side*.09, -.88, z), "z", .072, .01), sandal)
    return (-.55, -.98, -.35), (.55, .95, .45)


BUILDERS = {"tung_tung_sahur": _tung_tung, "tralalero_tralala": _tralalero,
            "ballerina_cappuccina": _ballerina, "bombardiro_crocodilo": _bombardiro,
            "lirili_larila": _lirili}


ASSETS = Path(__file__).resolve().parent/"assets"/"brainrot"
CHARACTERS = tuple(c for c in NAMES if c in BUILDERS or (ASSETS/f"{c}.png").is_file())


def hook(character):
    return f"Which way is {NAMES[character]} {'turning' if CHARACTERS.index(character) % 2 else 'spinning'}?"


def from_image(path, rng, per_pixel=3, depth=.9):
    """Turn a cut-out character picture into a particle sculpture.

    Every opaque pixel becomes particles carrying its colour on the front
    surface. Depth comes from the silhouette: each part is inflated into a
    round tube whose radius is its local half-width, so the log, arms, bat
    and legs keep their real shape when the figure turns. The back is a dim,
    featureless copy of the wood tone, so the face is only on the front.
    """
    from PIL import Image
    from scipy import ndimage
    im = np.asarray(Image.open(path).convert("RGBA"), float)/255
    rgb, mask = im[..., :3], im[..., 3] > .5
    ys, xs = np.nonzero(mask)
    scale = 2/(ys.max()-ys.min())
    dist = ndimage.distance_transform_edt(mask)
    ridge = ndimage.maximum_filter(dist, size=int(dist.max()*2)+1)
    thick = np.sqrt(np.clip(dist*(2*ridge-dist), 0, None))*depth*scale
    plain = np.stack([ndimage.gaussian_filter(rgb[..., c]*mask, 6)/np.maximum(ndimage.gaussian_filter(mask*1., 6), 1e-3)
                      for c in range(3)], -1)
    n = len(xs)*per_pixel
    k = rng.integers(0, len(xs), n)
    px, py = xs[k]+rng.random(n), ys[k]+rng.random(n)
    at = [py-.5, px-.5]
    front = np.stack([ndimage.map_coordinates(rgb[..., c], at, order=1) for c in range(3)], 1)
    back = np.stack([ndimage.map_coordinates(plain[..., c], at, order=1) for c in range(3)], 1)
    side = rng.choice([-1., 1.], n)
    z = side*ndimage.map_coordinates(thick, at, order=1)
    points = np.c_[(px-(xs.min()+xs.max())/2)*scale, -(py-(ys.min()+ys.max())/2)*scale, z]
    col = np.where(side[:, None] > 0, front, back)
    lum = col.mean(1, keepdims=True)
    colors = np.clip(col*1.25, 0, 1)*np.where(side > 0, 1., .45)[:, None]*(.20+.45*lum)
    return points, colors


def geometry(rng, character, total=70000):
    """Return (points, rgb) for a character, centred on its vertical spin axis."""
    if character not in CHARACTERS:
        raise ValueError("unknown brainrot character")
    picture = ASSETS/(character+".png")
    if picture.is_file():
        # A reference picture of the character beats the hand-built sculpture.
        return from_image(picture, rng)
    s = Sculpture(rng)
    lo, hi = BUILDERS[character](s)
    pts, rgb = s.sample(lo, hi, total)
    pts -= (pts.max(0)+pts.min(0))/2*[1, 1, 0]
    return pts, rgb
