"""Original procedural renderers with adapters to the existing Python geometry.

No Blender, model download, external media or publishing API is used.
Footsteps trajectory and the existing stereogram/shape algorithms retain the
repository's upstream notices. Other new drawing routines are original.
"""
from contextlib import contextmanager
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import uuid

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter

import five_styles as director

COLORS = {"coral_blue": ((255, 55, 70), (45, 100, 255)),
          "mint_violet": ((70, 235, 180), (175, 85, 255)),
          "amber_cyan": ((255, 170, 45), (30, 215, 240))}


@lru_cache(maxsize=40)
def font(size):
    for name in ("C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def centered(draw, text, y, width, color=(235, 238, 245), ratio=.038):
    size = max(9, round(width*ratio))
    while size > 8:
        f = font(size)
        box = draw.textbbox((0, 0), text, font=f)
        if box[2]-box[0] <= width*.9:
            break
        size -= 1
    draw.text(((width-box[2]+box[0])/2, y), text, font=f, fill=color)


def mask(subject, size):
    """Use the existing non-face shape grammar, with one explicit ring hole."""
    from relational_scene import outline
    im = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(im)
    if subject == "ring":
        d.ellipse((size*.10, size*.10, size*.90, size*.90), fill=255)
        d.ellipse((size*.28, size*.28, size*.72, size*.72), fill=0)
    else:
        points = outline(subject)
        d.polygon([tuple(v) for v in (points * .48 + .5)*size], fill=255)
    return np.asarray(im, dtype=float)/255


def relief(subject, size):
    from scipy.ndimage import distance_transform_edt
    inside = mask(subject, size)
    distance = distance_transform_edt(inside > .5)
    return np.where(inside > .5, .30+.70*np.sqrt(distance/max(1., distance.max())), 0)


def stereo_project(points, eye, zero_plane=4., focal=1.55):
    """Parallel, off-axis stereo. A point at zero_plane has zero disparity."""
    points = np.asarray(points)
    z = zero_plane + points[:, 2]
    if np.any(z <= 0):
        raise ValueError("points must stay in front of both cameras")
    return np.c_[focal*((points[:, 0]-eye)/z + eye/zero_plane),
                 focal*points[:, 1]/z]


def pair_spec(parameters):
    from scene_contract import entity, scene, PAIR_ORIENTATIONS
    tilts = (PAIR_ORIENTATIONS, ((-28, 12, -20), (22, -18, 15)),
             ((-12, -10, -28), (20, 16, 14)))
    orientations = tilts[parameters["tilt"]]
    return scene([entity(shape=s, expression=None, color=c, center=center,
                         orientation=orientation, turns=turn, phase=phase, scale=.9)
                  for s, c, center, orientation, turn, phase in zip(
                      parameters["subjects"], ("coral", "electric_blue"),
                      ([-.20, .16, 0], [.20, -.16, 0]), orientations,
                      (1, parameters["turns"]), (-25, 35))], parameters["layout"])


def fade_context(t, seconds=15):
    phase = t % seconds
    reveal = max(0., min(1., (phase/seconds-.67)/.05, (.92-phase/seconds)/.05))
    return 1-reveal*reveal*(3-2*reveal)


def gabor_centers(parameters, t, seconds=15):
    return [(i, row, (i+.5)/parameters["columns"],
             .5+row*.22+.065*math.sin(2*math.pi*t/seconds*parameters["cycles"]))
            for row in (-1, 1) for i in range(parameters["columns"])]


def splat(points, colors, size, gain=1., pixel_scale=1.):
    """Bilinear additive splat, no z buffer or depth-dependent luminance."""
    xy = np.asarray(points)*size + size/2
    x, y = np.floor(xy[:, 0]).astype(int), np.floor(xy[:, 1]).astype(int)
    ax, ay = xy[:, 0]-x, xy[:, 1]-y
    canvas = np.zeros((size, size, 3), np.float32)
    for dx, dy, weight in ((0, 0, (1-ax)*(1-ay)), (1, 0, ax*(1-ay)),
                           (0, 1, (1-ax)*ay), (1, 1, ax*ay)):
        ok = (x+dx >= 0) & (x+dx < size) & (y+dy >= 0) & (y+dy < size)
        index = (y[ok]+dy)*size+x[ok]+dx
        # Sparse scatter avoids allocating twelve full-resolution bincount arrays
        # for a cloud containing only a few thousand samples.
        np.add.at(canvas.reshape(-1, 3), index, colors[ok]*weight[ok, None])
    # Match apparent dot width and integrated luminance across preview/full sizes.
    # A fixed point cloud has 1/scale^2 samples per pixel after resolution grows.
    dots = gaussian_filter(canvas, (.65*pixel_scale, .65*pixel_scale, 0))*gain*pixel_scale**2
    glow = gaussian_filter(canvas, (2.5*pixel_scale, 2.5*pixel_scale, 0))*.35*pixel_scale**2
    return Image.fromarray(np.uint8(np.clip(1-np.exp(-(dots+glow)), 0, 1)*255))


class Renderer:
    def __init__(self, brief, width=1080, height=1920):
        self.b = director.validate_brief(brief)
        self.w, self.h, self.mode = width, height, brief["mode"]
        if type(width) is not int or type(height) is not int or width < 180 or height*9 != width*16:
            raise ValueError("render size must be portrait 9:16 and at least 180 pixels wide")
        self.p, self.rng = brief["parameters"], np.random.default_rng(brief["seed"])
        self.seconds = brief["render"]["seconds"]
        self.colors = COLORS[brief["palette"]]
        self.cache = {}
        self._prepare()

    def _prepare(self):
        p, mode = self.p, self.mode
        if mode in ("bistable_spin", "brainrot_spin"):
            if mode == "bistable_spin":
                from bistable_spin import geometry
                points, weights, layers = geometry(self.rng, p["shape"])
                self.point_colors = weights[:, None]*np.array(self.colors)[layers]/255
            else:
                # Brainrot figures carry their own avatar colours per particle.
                from brainrot import geometry
                points, self.point_colors = geometry(self.rng, p["character"])
            self.points = points
            self.bound = np.linalg.norm(points, axis=1).max()
            if mode == "brainrot_spin":
                # Tall figures spin about y: size them by height and turning radius,
                # not the 3D diagonal, so they fill the frame like the reference.
                self.bound = max(np.abs(points[:, 1]).max(),
                                 np.hypot(points[:, 0], points[:, 2]).max())*1.08
        elif mode == "tilted_pair":
            from relational_scene import geometry, orientation_matrix
            self.layers, bound = [], 0.
            for i, e in enumerate(pair_spec(p)["entities"]):
                points, weights = geometry(self.rng, e["shape"])
                points *= e["scale"]
                center = np.array(e["center"])
                bound = max(bound, np.linalg.norm(points, axis=1).max()+np.linalg.norm(center))
                self.layers.append((points, weights[:, None]*np.array(self.colors[i])/255,
                    center, orientation_matrix(e["orientation"]), e["turns"], math.radians(e["phase"])))
            self.bound = bound
        elif mode == "hidden_relief":
            from more_illusions import autostereogram
            size = self.w
            self.depth = relief(p["subject"], size)
            repeat = round(p["repeat"]*size)
            # Random dots have matching local statistics, unlike a luminance stencil.
            cell = max(1, round(size/360))
            tex = self.rng.integers(0, 5, (math.ceil(size/cell), math.ceil(repeat/cell), 1), dtype=np.uint8)
            tex = np.repeat(np.repeat(tex, cell, 0), cell, 1)[:size, :repeat]/4
            a, b = np.array(self.colors[0]), np.array(self.colors[1])
            tex = np.uint8(tex*a+(1-tex)*b)
            pattern = autostereogram(self.depth, tex, repeat, round(repeat*p["relief"]))
            self.cache["pattern"] = Image.fromarray(pattern)
        elif mode in director.MODES["binocular_worlds"]:
            n = p["complexity"]
            u = np.linspace(0, 2*math.pi, 1600, endpoint=False)
            if mode == "orbital_rings":
                points = []
                for i in range(n):
                    a = i*math.pi/n
                    points.append(np.c_[.8*np.cos(u), .8*np.sin(u)*math.cos(a), .8*np.sin(u)*math.sin(a)])
                self.points = np.vstack(points)
            elif mode == "helix":
                u = np.linspace(0, n*2*math.pi, 6000)
                self.points = np.c_[.6*np.cos(u), (u/u.max()-.5)*1.6, .6*np.sin(u)]
            else:
                a = self.rng.uniform(0, 2*math.pi, 8000)
                r = np.sqrt(self.rng.random(8000))*.85
                a += r*n*2
                self.points = np.c_[r*np.cos(a), r*np.sin(a)*.65, self.rng.normal(0, .16, 8000)]
            hues = np.linspace(0, 1, len(self.points))[:, None]
            self.point_colors = ((1-hues)*np.array(self.colors[0])+hues*np.array(self.colors[1]))/255*.8
        elif mode == "motion_form":
            # A fixed aperture, two independent equal-distribution textures.
            self.cells = max(60, round(self.w*.86/p["dot_size"]))
            self.motion_mask = mask(p["subject"], self.cells) > .5
            self.noise_a = self.rng.integers(0, 2, (self.cells, self.cells), dtype=np.uint8)
            self.noise_b = self.rng.integers(0, 2, (self.cells, self.cells), dtype=np.uint8)
        elif mode in ("afterimage", "troxler"):
            size = round(self.w*.90)
            yy, xx = np.mgrid[0:size, 0:size]
            x, y = (xx-size/2)/size, (yy-size/2)/size
            if mode == "afterimage":
                shape = mask(p["subject"], size)
                angle = np.arctan2(y, x)
                # Procedural chromatic regions; test frame is truly achromatic.
                hue = ((angle+math.pi)/(2*math.pi)*p["segments"]) % 1
                import colorsys
                lookup = np.array([colorsys.hsv_to_rgb(i/255, .85, .9) for i in range(256)])
                rgb = lookup[np.uint8(hue*255)]
                rgb = rgb*shape[:, :, None]+.55*(1-shape[:, :, None])
                self.cache["adaptor"] = Image.fromarray(np.uint8(rgb*255))
                self.cache["test"] = Image.new("RGB", (size, size), (140, 140, 140))
            else:
                rgb = np.ones((size, size, 3))*.94
                for i in range(p["patches"]):
                    a = 2*math.pi*i/p["patches"]
                    gaussian = np.exp(-((x-.31*math.cos(a))**2+(y-.31*math.sin(a))**2)/.006)
                    col = np.array(self.colors[i % 2])/255
                    rgb += gaussian[:, :, None]*(col-.94)*p["contrast"]
                self.cache["troxler"] = Image.fromarray(np.uint8(np.clip(rgb, 0, 1)*255))

    def motion_noise(self, t):
        # Integer cell translations complete exactly one traversal each loop.
        shift = round((t % self.seconds)/self.seconds*self.cells)*self.p["direction"]
        a = np.roll(self.noise_a, shift, axis=0)
        b = np.roll(self.noise_b, -shift, axis=0)
        return np.where(self.motion_mask, a, b)

    def _panel(self, image, panel, y=None):
        image.paste(panel, ((self.w-panel.width)//2, round(self.h*.48-panel.height/2) if y is None else y))

    def frame(self, t):
        t = t % self.seconds
        w, h, p, mode = self.w, self.h, self.p, self.mode
        light = mode in ("munker_white", "muller_lyer", "troxler", "cafe_wall")
        image = Image.new("RGB", (w, h), (245, 245, 245) if light else (0, 0, 0))
        if mode in ("bistable_spin", "brainrot_spin"):
            from bistable_spin import project
            xy = project(self.points, 2*math.pi*p["turns"]*t/self.seconds, p["tilt"])
            # Smaller field than the other modes so the whole object stays above
            # the Reels/Shorts caption overlay (bottom ~35% of the frame).
            size = round(w*.80)*2
            panel = splat(xy*[1, -1]/(2.25*self.bound), self.point_colors, size, 3.4, w/360)
            panel = panel.resize((size//2, size//2), Image.Resampling.LANCZOS)
            self._panel(image, panel, round(h*.445-panel.height/2))
        elif mode == "tilted_pair":
            from relational_scene import rotate
            angle = 2*math.pi*t/self.seconds
            points, colors = [], []
            for cloud, color, center, base, turns, phase in self.layers:
                offset = rotate(center[None], angle)[0] if p["layout"] == "orbit" else center
                xyz = rotate(cloud, angle*turns+phase) @ base + offset
                points.append(xyz[:, :2]*[1, -1]/(2.3*self.bound))
                colors.append(color)
            # Supersampled geometry; camera remains fixed throughout.
            size = round(w*.96)*2
            panel = splat(np.vstack(points), np.vstack(colors), size, 3.4, w/360).resize((size//2, size//2), Image.Resampling.LANCZOS)
            self._panel(image, panel)
        elif mode == "hidden_relief":
            self._panel(image, self.cache["pattern"])
            d = ImageDraw.Draw(image)
            for x in ((.5-p["repeat"]/2)*w, (.5+p["repeat"]/2)*w):
                r = max(2, w*.004)
                d.ellipse((x-r, h*.48-w/2-w*.035-r, x+r, h*.48-w/2-w*.035+r), fill="white")
        elif mode in director.MODES["binocular_worlds"]:
            from relational_scene import rotate
            xyz = rotate(self.points, 2*math.pi*t/self.seconds)
            size = round(w*.46)
            for i, eye in enumerate((-p["eye_separation"]/2, p["eye_separation"]/2)):
                xy = stereo_project(xyz, eye)*[1, -1]
                panel = splat(xy, self.point_colors, size*2, 4., w/360).resize((size, size), Image.Resampling.LANCZOS)
                image.paste(panel, (round(w*.025+i*w*.49), round(h*.49-size/2)))
            d = ImageDraw.Draw(image)
            for x in (w*.255, w*.745):
                r = max(2, w*.004)
                d.ellipse((x-r, h*.49-size/2-w*.04-r, x+r, h*.49-size/2-w*.04+r), fill="white")
        elif mode == "motion_form":
            noise = self.motion_noise(t)
            rgb = np.repeat((noise*160+45)[:, :, None], 3, axis=2).astype(np.uint8)
            panel = Image.fromarray(rgb).resize((round(w*.90),)*2, Image.Resampling.NEAREST)
            self._panel(image, panel)
        elif mode == "infinite_regress":
            size = round(w*.94)
            yy, xx = np.mgrid[0:size, 0:size]/size
            arr = np.ones((size, size))*.5
            for i, row, cx, cy in gabor_centers(p, t, self.seconds):
                gaussian = np.exp(-((xx-cx)**2+(yy-cy)**2)/.0009)
                carrier = np.cos(2*math.pi*(xx*size/(size*.025)-row*p["carrier"]*t*2))
                arr += .45*gaussian*carrier
            self._panel(image, Image.fromarray(np.uint8(np.clip(arr, 0, 1)*255)).convert("RGB"))
            d = ImageDraw.Draw(image)
            r = max(2, w*.004)
            d.ellipse((w/2-r, h*.48-r, w/2+r, h*.48+r), fill="black")
        elif mode == "footsteps":
            from illusion_lab import block_positions
            size = round(w*.90)
            panel = Image.new("RGB", (size, size), (128,)*3)
            d = ImageDraw.Draw(panel)
            opacity = fade_context(t)
            for i in range(p["stripes"]):
                v = round(128+((255 if i % 2 else 0)-128)*opacity)
                d.rectangle((i*size/p["stripes"], 0, (i+1)*size/p["stripes"]-1, size), fill=(v,)*3)
            params = dict(stripes=p["stripes"], cycles=p["cycles"], bar_width=2, lanes=2)
            for i, (x, y, bw, bh) in enumerate(block_positions(params, t)):
                d.rectangle((x*size, y*size, (x+bw)*size, (y+bh)*size), fill=(255, 235, 30) if i == 0 else (8, 15, 85))
            if p["axis"] == "vertical":
                panel = panel.transpose(Image.Transpose.ROTATE_90)
            self._panel(image, panel)
        elif mode in ("munker_white", "muller_lyer", "cafe_wall"):
            self._context_frame(image, t)
        elif mode in ("afterimage", "troxler"):
            panel = self.cache["troxler"] if mode == "troxler" else self.cache["adaptor" if t < 18 else "test"]
            self._panel(image, panel)
            d = ImageDraw.Draw(image)
            r = max(2, w*.005)
            d.ellipse((w/2-r, h*.48-r, w/2+r, h*.48+r), fill="black", outline="white", width=max(1, round(w*.001)))
        d = ImageDraw.Draw(image)
        textcolor = (25, 30, 40) if light else (235, 238, 245)
        # Reels/Shorts overlay the top ~14% and bottom ~35% of the frame, so all
        # text sits in the band between the top UI and the optical field.
        centered(d, self.b["caption"]["hook"], h*.15, w, textcolor, .044)
        # Short lines preserve phone legibility without covering the optical field.
        instruction = self.b["caption"]["instruction"]
        words, lines, line = instruction.split(), [], ""
        for word in words:
            if len(line)+len(word) > 52:
                lines.append(line); line = word
            else:
                line += (" " if line else "")+word
        lines.append(line)
        for i, line in enumerate(lines):
            centered(d, line, h*.185+i*w*.036, w, textcolor, .028)
        if mode == "afterimage":
            centered(d, f"{max(0, 18-int(t))}s on the dot" if t < 18 else "Keep your gaze on the dot", h*.75, w, textcolor, .034)
        label = self.b["account"]["handle"] or self.b["account"]["id"]
        centered(d, label, h*.78, w, textcolor, .027)
        return image

    def _context_frame(self, image, t):
        w, h, p, mode = self.w, self.h, self.p, self.mode
        size = round(w*.92)*2
        panel = Image.new("RGB", (size, size), (245,)*3)
        d = ImageDraw.Draw(panel)
        opacity = fade_context(t)
        if mode == "munker_white":
            step = size/p["stripes"]
            for j in range(p["stripes"]):
                v = round(245+((15 if j % 2 == 0 else 235)-245)*opacity)
                d.rectangle((0, j*step, size, (j+1)*step-1), fill=(v,)*3)
            for i in (0, 1):
                for j in range(3+i, p["stripes"]-3, 2):
                    d.rectangle((size*(.21+i*.43), j*step, size*(.36+i*.43), (j+1)*step-1), fill=(p["target"],)*3)
        elif mode == "muller_lyer":
            left, right = size*.20, size*.80
            wing = size*p["wing_length"]
            angle = math.radians(p["wing_angle"])
            for i, cy in enumerate((size*.30, size*.70)):
                v = round(245*(1-opacity)+25*opacity)
                for x, sign in ((left, 1), (right, -1)):
                    sign *= 1 if i == 0 else -1
                    for sy in (-1, 1):
                        d.line((x+sign*wing*math.cos(angle), cy+sy*wing*math.sin(angle), x, cy), fill=(v,)*3, width=max(2, round(size*.006)))
                d.line((left, cy, right, cy), fill=(235, 65, 80), width=max(2, round(size*.006)))
        else:
            tile = size/p["columns"]
            mortar = max(2, round(tile*.055))
            for row in range(p["columns"]+1):
                shift = (p["offset"] if row % 2 else 0)*tile
                for col in range(-1, p["columns"]+1):
                    v = round(128+((245 if col % 2 else 10)-128)*opacity)
                    d.rectangle((col*tile+shift, row*tile, (col+1)*tile+shift, (row+1)*tile), fill=(v,)*3)
            for row in range(p["columns"]+1):
                y = round(row*tile)
                d.rectangle((0, y-mortar/2, size, y+mortar/2), fill=(128,)*3)
        self._panel(image, panel.resize((size//2, size//2), Image.Resampling.LANCZOS))


def load_history(path):
    path = Path(path)
    if not path.exists():
        return dict(kind="five_style_history", version=1, entries=[])
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    director.exact(value, ("kind", "version", "entries"), "history")
    if value["kind"] != "five_style_history" or type(value["version"]) is not int or value["version"] != 1 or not isinstance(value["entries"], list):
        raise ValueError("invalid history")
    seen = set()
    for e in value["entries"]:
        director.exact(e, ("key", "brief_digest", "quality", "sha256", "output"), "history entry")
        for field in ("key", "brief_digest", "sha256"):
            if not isinstance(e[field], str) or len(e[field]) != 64 or any(c not in "0123456789abcdef" for c in e[field]):
                raise ValueError("invalid history digest")
        if e["quality"] not in ("preview", "full") or not isinstance(e["output"], str) or not e["output"] or (e["key"], e["quality"]) in seen:
            raise ValueError("invalid or duplicate history entry")
        seen.add((e["key"], e["quality"]))
    return value


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    try:
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def history_lock(path):
    lock = Path(str(path)+".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("history is locked by another render; inspect it before removing a stale lock") from None
    try:
        os.close(fd)
        yield
    finally:
        lock.unlink(missing_ok=True)


def encode(renderer, target, fps, ffmpeg):
    """Never overwrite a clip; only rename complete, successfully encoded output."""
    target = Path(target)
    if target.exists():
        raise ValueError("output already exists")
    exe = shutil.which(ffmpeg)
    if exe is None:
        raise ValueError("FFmpeg is required; pass --ffmpeg with its full path")
    temporary = target.with_name(target.stem+"."+uuid.uuid4().hex+".partial.mp4")
    error_file = temporary.with_suffix(".log")
    try:
        with error_file.open("wb") as err:
            proc = subprocess.Popen([exe, "-n", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{renderer.w}x{renderer.h}", "-r", str(fps), "-i", "-", "-an",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(temporary)], stdin=subprocess.PIPE, stderr=err)
            try:
                for i in range(renderer.seconds*fps):
                    proc.stdin.write(renderer.frame(i/fps).tobytes())
                    if i and i % (fps*3) == 0:
                        print(json.dumps(dict(rendering=target.name, frame=i,
                            frames=renderer.seconds*fps)), flush=True)
            except BaseException:
                proc.stdin.close(); proc.terminate(); proc.wait()
                raise
            proc.stdin.close()
            if proc.wait() != 0:
                raise RuntimeError("encoding failed: "+error_file.read_text(encoding="utf-8", errors="replace")[-1000:])
        if not temporary.exists() or temporary.stat().st_size < 1000:
            raise RuntimeError("encoder produced no usable file")
        temporary.rename(target)
    finally:
        temporary.unlink(missing_ok=True)
        error_file.unlink(missing_ok=True)


def render_plan(plan_path, output, history_path, preview=False, ffmpeg="ffmpeg"):
    plan = json.loads(Path(plan_path).read_text(encoding="utf-8-sig"))
    director.exact(plan, ("kind", "version", "local_only", "seed", "account_count", "selection", "briefs"), "plan")
    if plan["kind"] != "five_style_plan" or type(plan["version"]) is not int or plan["version"] != 1 or plan["local_only"] is not True or plan["account_count"] != 5:
        raise ValueError("unsupported plan")
    if not isinstance(plan["briefs"], list) or not 5 <= len(plan["briefs"]) <= 500:
        raise ValueError("plan requires at least one brief per account")
    account_rows = {}
    for b in plan["briefs"]:
        director.validate_brief(b)
        key = b["account"]["id"]
        if key in account_rows and account_rows[key] != b["account"]:
            raise ValueError("account identity changed within plan")
        account_rows[key] = b["account"]
    director.validate_accounts(dict(version=1, accounts=list(account_rows.values())))
    return _render_validated(plan["briefs"], output, history_path, preview, ffmpeg)


def render_one(brief, output, history_path, preview=False, ffmpeg="ffmpeg"):
    """Independent generator path; retains all brief and history safeguards."""
    director.validate_brief(brief)
    return _render_validated([brief], output, history_path, preview, ffmpeg)


def _render_validated(briefs, output, history_path, preview, ffmpeg):
    keys = [director.structural_key(b["style"], b["mode"], b["parameters"]) for b in briefs]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate concepts within plan")
    quality = "preview" if preview else "full"
    output = Path(output)
    if output.exists():
        raise ValueError("choose a new render folder")
    # All validation and collision checks precede folder creation or encoding.
    with history_lock(history_path):
        history = load_history(history_path)
        for b, key in zip(briefs, keys):
            previous = [e for e in history["entries"] if e["key"] == key]
            if any(e["quality"] == quality or e["quality"] == "full" for e in previous):
                raise ValueError("concept already rendered; plan with the same history")
            if previous and any(e["brief_digest"] != director.digest(b) for e in previous):
                raise ValueError("preview promotion requires the identical reviewed brief")
            for entry in previous:
                preview_path = Path(entry["output"])
                if not preview_path.is_file() or hashlib.sha256(preview_path.read_bytes()).hexdigest() != entry["sha256"]:
                    raise ValueError("reviewed preview is missing or its checksum changed")
        output.mkdir(parents=True)
        manifest = dict(kind="five_style_render", quality=quality, local_only=True, outputs=[])
        for b, key in zip(briefs, keys):
            target = output/(b["account"]["id"]+"_"+b["id"]+".mp4")
            size = (360, 640, 15) if preview else (1080, 1920, 30)
            renderer = Renderer(b, size[0], size[1])
            encode(renderer, target, size[2], ffmpeg)
            renderer.frame(2).save(target.with_suffix(".png"))
            atomic_json(target.with_suffix(".json"), b)
            checksum = hashlib.sha256(target.read_bytes()).hexdigest()
            history["entries"].append(dict(key=key, brief_digest=director.digest(b), quality=quality,
                                          sha256=checksum, output=str(target.resolve())))
            atomic_json(history_path, history)
            manifest["outputs"].append(dict(account=b["account"]["id"], style=b["style"], mode=b["mode"],
                handle=b["account"]["handle"],
                generator=director.GENERATORS[b["style"]]["name"], generator_label=director.GENERATORS[b["style"]]["label"],
                video=target.name, poster=target.with_suffix(".png").name, brief=target.with_suffix(".json").name,
                width=size[0], height=size[1], fps=size[2], seconds=renderer.seconds, sha256=checksum))
            atomic_json(output/"manifest.json", manifest)
            print(json.dumps(dict(completed=len(manifest["outputs"]), total=len(keys), file=target.name)), flush=True)
        return manifest
