"""Ambiguous-rotation objects: transparent particle shapes whose spin can be read both ways.

Every object is drawn with orthographic projection, additive particles and no
occlusion or depth shading. Mirroring depth (z -> -z) together with the view
tilt then yields exactly the same frame for the opposite spin, so the image
itself never settles which way the object turns.
"""
import math

import numpy as np

SHAPES = ("planet_wedge", "necker_cube", "arrow_disc", "crossed_arrows",
          "chevron_band", "twin_masks", "arrow_globe")
TILTS = (10, 18, 26)
# Surface dust is dim; edges, strokes and arrows carry the readable form.
DUST, EDGE = (.12, .34), .62


def _segment(a, b, n):
    u = np.linspace(0, 1, n)[:, None]
    return np.asarray(a)*(1-u)+np.asarray(b)*u


def _polyline(vertices, density=900, closed=True):
    vertices = np.asarray(vertices, float)
    if closed:
        vertices = np.vstack([vertices, vertices[:1]])
    return np.vstack([_segment(a, b, max(8, round(np.linalg.norm(b-a)*density)))
                      for a, b in zip(vertices[:-1], vertices[1:])])


def _circle(radius, n=1600, start=0., stop=2*math.pi):
    a = np.linspace(start, stop, n)
    return np.c_[radius*np.cos(a), radius*np.sin(a), np.zeros(n)]


def _arrow(length=1.1, shaft=.16, head=.42, head_length=.38):
    """Flat arrow outline in the xy plane, pointing to +x and centred on the origin."""
    x0, x1, x2 = -length/2, length/2-head_length, length/2
    return np.array([[x0, -shaft/2], [x1, -shaft/2], [x1, -head/2], [x2, 0],
                     [x1, head/2], [x1, shaft/2], [x0, shaft/2]])


def _fill(rng, outline, n):
    """Uniform dust inside a closed 2D polygon (rejection sampling)."""
    lo, hi = outline.min(0), outline.max(0)
    samples = rng.uniform(lo, hi, (n*3, 2))
    x, y = samples[:, :1], samples[:, 1:]
    ax, ay = outline[:, 0], outline[:, 1]
    bx, by = np.roll(ax, -1), np.roll(ay, -1)
    crosses = ((ay > y) != (by > y)) & (x < (bx-ax)*(y-ay)/np.where(by == ay, 1e-12, by-ay)+ax)
    inside = samples[crosses.sum(1) % 2 == 1][:n]
    return np.c_[inside, np.zeros(len(inside))]


def _sphere(rng, n, radius=1.):
    v = rng.normal(size=(n, 3))
    return radius*v/np.linalg.norm(v, axis=1, keepdims=True)


def _flat(points):
    return np.c_[points, np.zeros(len(points))]


def _ry(points, degrees):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return points @ np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])


def _rx(points, degrees):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return points @ np.array([[1, 0, 0], [0, c, s], [0, -s, c]])


def geometry(rng, shape):
    """Return (points, weights, layer) with layer 0/1 selecting the palette color."""
    parts = []

    def add(points, layer, weight=None):
        points = np.asarray(points, float)
        w = rng.uniform(*DUST, len(points)) if weight is None else np.full(len(points), weight)
        parts.append((points, w, np.full(len(points), layer)))

    if shape == "planet_wedge":
        # A sphere with one octant removed; the cut faces and edges outline the wedge.
        s = _sphere(rng, 26000)
        add(s[~((s[:, 0] > 0) & (s[:, 1] > 0) & (s[:, 2] > 0))], 0)
        for axis in range(3):
            u = rng.uniform(0, 1, (2500, 2))
            r, a = np.sqrt(u[:, 0]), u[:, 1]*math.pi/2
            face = np.zeros((2500, 3))
            face[:, (axis+1) % 3], face[:, (axis+2) % 3] = r*np.cos(a), r*np.sin(a)
            add(face, 0)
            arc = np.zeros((900, 3))
            a = np.linspace(0, math.pi/2, 900)
            arc[:, (axis+1) % 3], arc[:, (axis+2) % 3] = np.cos(a), np.sin(a)
            add(arc, 1, EDGE)
            add(_segment(np.zeros(3), np.eye(3)[axis], 700), 1, EDGE)
    elif shape == "necker_cube":
        c = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])*.62
        for i in range(8):
            for j in range(i+1, 8):
                if np.abs(c[i]-c[j]).sum() == 1.24:
                    add(_segment(c[i], c[j], 900), 1, EDGE)
        for axis in range(3):
            for side in (-.62, .62):
                face = rng.uniform(-.62, .62, (3200, 3))
                face[:, axis] = side
                add(face, 0)
    elif shape in ("arrow_disc", "crossed_arrows"):
        for k, turn in enumerate((0, 90) if shape == "crossed_arrows" else (0,)):
            arrow = _arrow()*(.9 if shape == "crossed_arrows" else 1.15)
            disc = _fill(rng, _circle(.95, 400)[:, :2], 9000)
            ring = _circle(.95)
            if shape == "crossed_arrows":
                # Second disc points its arrow the other way so the pair stays symmetric.
                arrow = arrow*[1 if k == 0 else -1, 1]
            add(_ry(disc, turn), k)
            add(_ry(ring, turn), k, EDGE)
            add(_ry(_flat(_polyline(arrow, 1100)), turn), k, EDGE*1.15)
            add(_ry(_fill(rng, arrow, 2500), turn), k, .16)
    elif shape == "chevron_band":
        # A vertical cylinder band with chevrons pointing along its circumference.
        a = rng.uniform(0, 2*math.pi, 16000)
        add(np.c_[np.cos(a), rng.uniform(-.38, .38, 16000), np.sin(a)], 0)
        for y in (-.38, .38):
            ring = _circle(1.)
            add(np.c_[ring[:, 0], np.full(len(ring), y), ring[:, 1]], 1, EDGE)
        for i in range(6):
            a0 = 2*math.pi*i/6
            u = np.linspace(-1, 1, 500)
            # Chevron "<" in band coordinates: angle offset follows |height|.
            ang = a0+.22*(np.abs(u)-.5)
            add(np.c_[np.cos(ang), .24*u, np.sin(ang)], 1, EDGE*1.1)
    elif shape == "twin_masks":
        from relational_scene import mask
        for k, mood in enumerate(("smile", "frown")):
            pts, weights = mask(rng, mood)
            pts = pts*[1.15, 1.15, 1.15]+[0, 0, .05]
            if k:
                pts = _ry(pts, 180)
            n = len(weights)
            parts.append((pts, weights*.9, np.full(n, k)))
    elif shape == "arrow_globe":
        add(_sphere(rng, 18000, .95), 0)
        equator = _circle(.95)
        add(np.c_[equator[:, 0], np.zeros(len(equator)), equator[:, 1]], 1, EDGE)
        add(_circle(.95), 0, EDGE*.7)
        for i in range(4):
            a0 = 2*math.pi*i/4
            for side in (-1, 1):
                tip, tail = a0, a0-.30
                u = np.linspace(0, 1, 300)
                ang = tip+(tail-tip)*u
                h = side*.20*u
                r = np.sqrt(.95**2-h**2)
                add(np.c_[r*np.cos(ang), h, r*np.sin(ang)], 1, EDGE*1.1)
    else:
        raise ValueError("unknown bistable shape")
    points = np.vstack([p for p, _, _ in parts])
    weights = np.concatenate([w for _, w, _ in parts])
    layers = np.concatenate([l for _, _, l in parts]).astype(int)
    return points, weights, layers


def project(points, angle, tilt_degrees):
    """Spin about the vertical axis, tilt toward the viewer, then drop depth."""
    # Start a third of the way into a quarter turn so no clip opens face-on.
    return _rx(_ry(points, math.degrees(angle)+30), tilt_degrees)[:, :2]
