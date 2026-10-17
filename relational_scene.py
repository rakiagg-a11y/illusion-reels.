"""Procedural convex masks and complementary arcs using the existing point splatter."""
import math
import shutil
import subprocess
from pathlib import Path
import numpy as np
import pointcloud as pc
from scene_contract import COLORS, validate_scene


def rotate(points, angle):
    c, s = math.cos(angle), math.sin(angle)
    return points @ np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])


def mask(rng, expression):
    """Elliptical open convex shell with facial strokes on its surface."""
    rx, ry, depth = .63, .84, .30
    n = 11000
    a, r = rng.uniform(0, 2 * math.pi, n), np.sqrt(rng.random(n))
    x, y = rx * r * np.cos(a), ry * r * np.sin(a)
    shell = np.c_[x, y, depth * np.sqrt(np.maximum(0, 1 - r * r))]
    strokes = []

    def curve(x, y):
        z = depth * np.sqrt(np.clip(1 - (x / rx) ** 2 - (y / ry) ** 2, 0, 1))
        strokes.append(np.c_[x, y, z + .004])

    a = np.linspace(0, 2 * math.pi, 1400)
    curve(rx * np.cos(a), ry * np.sin(a))
    u = np.linspace(-1, 1, 350)
    mood = {"smile": 1, "frown": -1, "neutral": 0}[expression]
    for side in (-1, 1):
        curve(side * .235 + .13 * u, .23 + mood * .055 * (1 - u * u))
        curve(side * .235 + .16 * u, .39 + mood * .07 * (1 - u * u))
    curve(.36 * u, -.29 - mood * .18 * (1 - u * u))
    if expression == "smile":
        curve(.36 * u, -.29 + .025 * (1 - u * u))
    # A small nose ridge gives the side view a readable curved profile.
    u2 = np.linspace(0, 1, 180)
    curve(.045 * np.sin(math.pi * u2), .13 - .24 * u2)
    lines = np.vstack(strokes)
    return np.vstack([shell, lines]), np.r_[rng.uniform(.025, .10, n), np.full(len(lines), .60)]


def arc(rng):
    a = np.linspace(-math.pi / 2, math.pi / 2, 3200)
    curve = np.c_[.84 * np.cos(a), .84 * np.sin(a), np.zeros(len(a))]
    a2 = rng.uniform(-math.pi / 2, math.pi / 2, 6500)
    r = rng.uniform(.77, .84, len(a2))
    band = np.c_[r * np.cos(a2), r * np.sin(a2), rng.normal(0, .008, len(a2))]
    return np.vstack([curve, band]), np.r_[np.full(len(curve), .48),
                                           rng.uniform(.04, .13, len(band))]


class Scene(pc.Scene):
    """A scene graph of independently turning surfaces; never depth-sorted."""
    def __init__(self, specification, seed, seconds=15):
        validate_scene(specification)
        self.specification = specification
        rng = np.random.default_rng(seed)
        self.layers, colors = [], []
        bound = 0
        for e in specification["entities"]:
            points, weights = mask(rng, e["expression"]) if e["shape"] == "mask" else arc(rng)
            points *= e["scale"]
            center = np.array(e["center"], dtype=float)
            bound = max(bound, np.linalg.norm(points, axis=1).max() + np.linalg.norm(center))
            self.layers.append((points, center, e["turns"], math.radians(e["phase"])))
            colors.append(weights[:, None] * np.array(COLORS[e["color"]]))
        self.Cw = np.vstack(colors)
        self.P = self.positions(0)
        self.scale = min(.43 * pc.W / bound, .34 * pc.H / bound)
        self.static, self.tilt = None, 0.0
        self.phase, self.direction, self.period = 0.0, 1, seconds / 2

    def positions(self, angle):
        result = []
        for points, center, turns, phase in self.layers:
            offset = rotate(center[None, :], angle)[0] if self.specification["layout"] == "orbit" else center
            result.append(rotate(points, angle * turns + phase) + offset)
        return np.vstack(result)

    def splat(self, th, buf, ss=1):
        self.P = self.positions(th)
        super().splat(0, buf, ss)


def frame(scene, angle):
    return scene.frame_crisp(angle, dot=1.1 * pc.W / 1080)


def render(specification, seed, out, seconds=15, handle="", ffmpeg="ffmpeg"):
    """Full local MP4 path used by generate.run. Reuses its 1080x1920 defaults."""
    validate_scene(specification)
    executable = shutil.which(ffmpeg)
    if executable is None:
        raise ValueError("FFmpeg is required for local rendering")
    scene = Scene(specification, seed, seconds)
    wm = pc.watermark(handle)
    with subprocess.Popen(
        [executable, "-n", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{pc.W}x{pc.H}", "-r", str(pc.FPS), "-i", "-",
         "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
         "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-movflags", "+faststart", str(out)],
        stdin=subprocess.PIPE
    ) as proc:
        try:
            for i in range(int(seconds * pc.FPS)):
                image = frame(scene, 2 * math.pi * (i / pc.FPS) / scene.period)
                if wm is not None:
                    image = np.maximum(image, wm)
                proc.stdin.write(image.tobytes())
        finally:
            proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("relational scene encoding failed")
    return dict(style="opticpop", subject="relational illusion", seed=seed, scene=specification)
