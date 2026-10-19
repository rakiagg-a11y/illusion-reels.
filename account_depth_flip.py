"""Original open rainbow shells, rendered without occlusion or depth cues.

Depth reflection + reversed rotation/tilt produces the identical projection.
This is an additive, ambiguous surface; no fake direction switch is animated.
"""
import colorsys
import itertools
import math

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def parameters_for(mode="depth_flip"):
    if mode != "depth_flip":
        raise ValueError("unknown depth mode")
    return [dict(ribs=r, rings=n, opening=o, tilt=t)
            for r, n, o, t in itertools.product((7, 9, 11, 13), (5, 7, 9), (210, 250, 290, 330), (12, 24, 36))]


def geometry(p):
    """A sphere sector, with visible meridians and parallels; no sampled dust."""
    parts, colors = [], []
    span = math.radians(p["opening"])
    for i, a in enumerate(np.linspace(-span/2, span/2, p["ribs"])):
        lat = np.linspace(-1.42, 1.42, 360)
        parts.append(np.c_[np.cos(lat)*math.sin(a), np.sin(lat), np.cos(lat)*math.cos(a)])
        colors.extend([colorsys.hsv_to_rgb((i/p["ribs"]*.8+.53) % 1, .70, .98)]*len(lat))
    for i, lat in enumerate(np.linspace(-1.3, 1.3, p["rings"])):
        a = np.linspace(-span/2, span/2, 480)
        parts.append(np.c_[math.cos(lat)*np.sin(a), np.full(len(a), math.sin(lat)), math.cos(lat)*np.cos(a)])
        colors.extend([colorsys.hsv_to_rgb((i/p["rings"]*.8+.1) % 1, .70, .98)]*len(a))
    return np.vstack(parts), np.asarray(colors)


def project(points, angle, tilt):
    from bistable_spin import _rx, _ry
    return _rx(_ry(points, math.degrees(angle)), tilt)[:, :2]


class Stimulus:
    def __init__(self, mode, parameters, seed, size):
        if mode != "depth_flip" or parameters not in parameters_for():
            raise ValueError("invalid depth-flip geometry")
        self.p, self.size = parameters, size
        self.points, self.colors = geometry(parameters)

    def frame(self, t):
        xy = project(self.points, t*math.tau/12+.35, self.p["tilt"])
        ix = np.rint((.5+.40*xy[:, 0])*self.size).astype(int)
        iy = np.rint((.5-.40*xy[:, 1])*self.size).astype(int)
        good = (ix >= 0) & (ix < self.size) & (iy >= 0) & (iy < self.size)
        canvas = np.zeros((self.size, self.size, 3), dtype=np.float32)
        for c in range(3):
            np.add.at(canvas[:, :, c], (iy[good], ix[good]), self.colors[good, c])
        sigma = max(.45, self.size/650)
        glow = gaussian_filter(canvas, (sigma*3, sigma*3, 0))
        core = gaussian_filter(canvas, (sigma, sigma, 0))
        rgb = (1-np.exp(-(core*2.1+glow*2.8)))*255
        return Image.fromarray(rgb.clip(0, 255).astype(np.uint8), "RGB")


def seconds_for(mode):
    if mode != "depth_flip":
        raise ValueError("unknown depth mode")
    return 12


def describe(mode, parameters):
    return dict(mechanism="orthographic depth and rotation ambiguity in an open transparent shell",
                control="depth-reflected geometry with opposite rotation and tilt has identical 2D coordinates",
                animation="one continuous rotation, no programmed reversal; additive lines without occlusion",
                human_review="Check whether both concave/convex or spin readings can be perceived.")
