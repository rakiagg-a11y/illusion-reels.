"""Brainrot meme characters as transparent particle figures for ambiguous rotation.

Each character is an original procedural build from simple primitives
(ellipsoids, tubes, discs and strokes), drawn as particles with no occlusion,
so it can be spun with the bistable_spin projection and read turning either way.
"""
import math

import numpy as np

from bistable_spin import EDGE

# Denser, brighter dust than the geometric shapes: the figure reads as a solid
# particle sculpture (as in Rakia's reference), with only the eyes drawn as lines.
DUST = (.10, .30)
TILTS = (0, 6, 12)

CHARACTERS = ("tung_tung_sahur", "tralalero_tralala", "ballerina_cappuccina",
              "bombardiro_crocodilo", "lirili_larila")


class Figure:
    def __init__(self, rng):
        self.rng, self.parts = rng, []

    def add(self, points, layer, weight=None):
        points = np.asarray(points, float)
        w = self.rng.uniform(*DUST, len(points)) if weight is None else np.full(len(points), weight)
        self.parts.append((points, w, np.full(len(points), layer)))

    def ellipsoid(self, center, radii, n, layer=0, outline=False):
        v = self.rng.normal(size=(n, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        self.add(np.asarray(center)+v*radii, layer)
        if outline:
            # Silhouette rings in the three body planes keep the shape readable.
            a = np.linspace(0, 2*math.pi, 700)
            rx, ry, rz = radii
            self.add(np.asarray(center)+np.c_[rx*np.cos(a), ry*np.sin(a), 0*a], 1, EDGE*.75)
            self.add(np.asarray(center)+np.c_[rx*np.cos(a), 0*a, rz*np.sin(a)], 1, EDGE*.75)

    def tube(self, a, b, radius, n, layer=0, rings=False):
        a, b = np.asarray(a, float), np.asarray(b, float)
        axis = b-a
        length = np.linalg.norm(axis)
        axis /= length
        helper = np.array([1., 0, 0]) if abs(axis[0]) < .9 else np.array([0, 1., 0])
        u = np.cross(axis, helper); u /= np.linalg.norm(u)
        w = np.cross(axis, u)
        t, ang = self.rng.random(n), self.rng.uniform(0, 2*math.pi, n)
        r = np.broadcast_to(radius, n) if np.isscalar(radius) else radius[0]+(radius[1]-radius[0])*t
        self.add(a+t[:, None]*(b-a)+r[:, None]*(np.cos(ang)[:, None]*u+np.sin(ang)[:, None]*w), layer)
        if rings:
            c = np.linspace(0, 2*math.pi, 400)
            for end, rr in ((a, r.max() if np.isscalar(radius) else radius[0]),
                            (b, r.max() if np.isscalar(radius) else radius[1])):
                self.add(end+rr*(np.cos(c)[:, None]*u+np.sin(c)[:, None]*w), 1, EDGE*.75)

    def curve(self, points, weight=EDGE):
        self.add(points, 1, weight)

    def ring(self, center, radius, normal, weight=EDGE, n=500):
        normal = np.asarray(normal, float); normal /= np.linalg.norm(normal)
        helper = np.array([1., 0, 0]) if abs(normal[0]) < .9 else np.array([0, 1., 0])
        u = np.cross(normal, helper); u /= np.linalg.norm(u)
        w = np.cross(normal, u)
        c = np.linspace(0, 2*math.pi, n)
        self.curve(np.asarray(center)+radius*(np.cos(c)[:, None]*u+np.sin(c)[:, None]*w), weight)

    def triangle(self, a, b, c, n, layer=0):
        u, v = self.rng.random((2, n))
        flip = u+v > 1
        u[flip], v[flip] = 1-u[flip], 1-v[flip]
        a, b, c = map(np.asarray, (a, b, c))
        self.add(a+u[:, None]*(b-a)+v[:, None]*(c-a), layer)
        for p, q in ((a, b), (b, c), (c, a)):
            s = np.linspace(0, 1, 300)[:, None]
            self.curve(p*(1-s)+q*s, EDGE*.8)

    def face(self, center, normal_z, spread=.11, eye=.06, mouth=.12, mood=1):
        """Eyes, pupils, brows and mouth on a surface facing +z (or -z)."""
        cx, cy, cz = center
        for side in (-1, 1):
            self.ring((cx+side*spread, cy, cz), eye, (0, 0, normal_z))
            self.ring((cx+side*spread, cy, cz), eye*.8, (0, 0, normal_z), EDGE*.8)
            a, r = self.rng.uniform(0, 2*math.pi, 400), np.sqrt(self.rng.random(400))*eye*.38
            self.add(np.c_[cx+side*spread+r*np.cos(a), cy+r*np.sin(a), np.full(400, cz)], 1, EDGE*.9)
        s = np.linspace(-1, 1, 300)
        self.curve(np.c_[cx+mouth*s, cy-.17-mood*.05*(1-s*s), np.full(300, cz)])

    def build(self):
        pts = np.vstack([p for p, _, _ in self.parts])
        w = np.concatenate([w for _, w, _ in self.parts])
        layers = np.concatenate([l for _, _, l in self.parts]).astype(int)
        return pts, w, layers


def geometry(rng, character):
    f = Figure(rng)
    if character == "tung_tung_sahur":
        # A wooden log with a face, stick arms and a baseball bat.
        f.tube((0, -.45, 0), (0, .62, 0), .27, 22000)
        f.ellipsoid((0, .62, 0), (.27, .10, .27), 3000)
        f.ellipsoid((0, -.45, 0), (.27, .06, .27), 2000)
        f.face((0, .40, .28), 1, spread=.10, eye=.075, mouth=.07)
        for side in (-1, 1):
            f.tube((side*.27, .15, 0), (side*.33, -.22, .08), .03, 1200)
            f.tube((side*.11, -.48, 0), (side*.12, -.95, 0), .04, 1400)
            f.ellipsoid((side*.12, -.97, .04), (.06, .03, .09), 500)
        # Bat held in the right hand, swung across the front at waist height.
        f.tube((.36, -.24, .12), (-.62, -.24, .42), (.035, .08), 4500)
        f.ellipsoid((-.64, -.24, .43), (.08, .08, .08), 600)
    elif character == "tralalero_tralala":
        # A shark standing on three legs in sneakers.
        f.ellipsoid((0, .30, 0), (.78, .27, .25), 15000)
        f.triangle((-.70, .30, 0), (-1.0, .62, 0), (-.98, .02, 0), 1500)
        f.triangle((-.10, .52, 0), (.10, .52, 0), (-.18, .85, 0), 1200)
        for z in (-.25, .25):
            f.ring((.52, .40, z), .045, (0, 0, 1))
            f.triangle((.05, .20, z*.95), (.25, .20, z*.95), (.0, .02, z*1.6), 600)
        s = np.linspace(-1, 1, 300)
        for z in (-.2, .2):
            f.curve(np.c_[.62+.12*s, .20+.03*s*s, np.full(300, z)])
        for x, z in ((-.35, .12), (.0, -.12), (.32, .12)):
            f.tube((x, .08, z), (x, -.62, z), .04, 900, rings=False)
            f.ellipsoid((x+.07, -.68, z), (.15, .07, .08), 700)
    elif character == "ballerina_cappuccina":
        # A cappuccino cup head on a ballerina in a tutu.
        f.tube((0, .45, 0), (0, .85, 0), (.17, .24), 5000)
        f.ellipsoid((0, .85, 0), (.24, .02, .24), 1500, outline=False)
        f.ring((.30, .66, 0), .09, (0, 0, 1))
        f.face((0, .66, .21), 1, spread=.08, eye=.045, mouth=.08)
        f.ellipsoid((0, .18, 0), (.14, .25, .11), 3500)
        a, r = rng.uniform(0, 2*math.pi, 6000), np.sqrt(rng.uniform(.04, 1, 6000))*.62
        f.add(np.c_[r*np.cos(a), -.02-.08*r, r*np.sin(a)], 0)
        f.ring((0, -.07, 0), .62, (0, 1, 0), EDGE*.8)
        t = np.linspace(0, 1, 400)
        for side in (-1, 1):
            f.curve(np.c_[side*(.13+.25*np.sin(t*math.pi*.8)), .32+.55*t, 0*t])
        f.tube((-.06, -.05, 0), (-.08, -.95, 0), .035, 900, rings=False)
        f.tube((.06, -.05, 0), (.30, -.55, .05), .035, 700, rings=False)
        f.tube((.30, -.55, .05), (.10, -.70, .05), .032, 400, rings=False)
    elif character == "bombardiro_crocodilo":
        # A crocodile with airplane wings and a tail fin.
        f.ellipsoid((0, .05, 0), (.85, .17, .17), 11000)
        f.ellipsoid((.85, .02, 0), (.32, .07, .12), 3000)
        for z in (-.09, .09):
            f.ring((.62, .18, z), .045, (0, 1, 0))
        s = np.linspace(0, 1, 300)
        f.curve(np.c_[.55+.62*s, .0*s, .11-.03*s])
        f.curve(np.c_[.55+.62*s, .0*s, -.11+.03*s])
        for side in (-1, 1):
            f.triangle((.25, .02, 0), (-.25, .02, 0), (-.10, .02, side*.95), 2500)
        f.triangle((-.70, .10, 0), (-.95, .10, 0), (-.92, .48, 0), 900)
        for side in (-1, 1):
            f.ellipsoid((.0, -.25, side*.35), (.16, .05, .05), 700)
    elif character == "lirili_larila":
        # An elephant head on a cactus body wearing sandals.
        f.ellipsoid((0, .62, 0), (.26, .24, .24), 6000)
        for side in (-1, 1):
            # Big flat ears facing forward, like a cartoon elephant.
            a, r = rng.uniform(0, 2*math.pi, 1500), np.sqrt(rng.random(1500))*.2
            f.add(np.c_[side*.40+r*np.cos(a), .64+r*np.sin(a)*1.2, np.full(1500, -.04)], 0)
            f.add(np.c_[side*.40+.2*np.cos(np.linspace(0, 2*math.pi, 500)),
                        .64+.24*np.sin(np.linspace(0, 2*math.pi, 500)), np.full(500, -.04)], 1, EDGE*.8)
            f.ring((side*.10, .70, .22), .04, (0, 0, 1))
        t = np.linspace(0, 1, 500)
        f.curve(np.c_[.03*np.sin(t*5), .58-.42*t, .24+.12*np.sin(t*math.pi)])
        f.tube((0, -.75, 0), (0, .40, 0), .18, 9000)
        for side, y in ((-1, .05), (1, -.15)):
            f.tube((side*.18, y, 0), (side*.42, y, 0), .07, 900, rings=False)
            f.tube((side*.42, y, 0), (side*.42, y+.28, 0), .07, 900)
        for side in (-1, 1):
            f.ellipsoid((side*.10, -.82, .06), (.08, .03, .14), 500)
    else:
        raise ValueError("unknown brainrot character")
    pts, w, layers = f.build()
    pts -= (pts.max(0)+pts.min(0))/2*[1, 1, 0]
    return pts, w, layers
