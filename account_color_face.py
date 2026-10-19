"""Original, local-only afterimage and flashed-face stimuli for Hypnotorium.

These are perceptual experiments, not simulated perceptual results. ColorEcho's
test really is achromatic. FaceFlash changes ordinary illustrated identities;
it never deforms a face to manufacture the distortion a viewer might perceive.
Illustrations are original procedural artwork, not downloaded portraits.
"""
import itertools
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

MODES = ("color_echo", "face_flash")
ADAPT_SECONDS = 18
FACE_INTERVAL = .25


def parameters_for(mode):
    """A bounded catalogue of geometries, rather than seed/palette duplicates."""
    if mode == "color_echo":
        return [dict(scene=scene, composition=c, layers=layers, landmark=landmark)
                for scene, c, layers, landmark in itertools.product(
                    ("terrace", "mountain", "botanical"), range(5), (3, 4, 5, 6), (0, 1))]
    if mode == "face_flash":
        return [dict(jaw_family=jaw, nose_family=nose, hair_family=hair)
                for jaw, nose, hair in itertools.product(range(4), range(5), range(6))]
    raise ValueError(f"Unknown Hypnotorium stimulus: {mode}")


def seconds_for(mode):
    if mode not in MODES:
        raise ValueError(f"Unknown Hypnotorium stimulus: {mode}")
    return 24 if mode == "color_echo" else 12


def describe(mode, parameters):
    if parameters not in parameters_for(mode):
        raise ValueError("Parameters must belong to the structural catalogue")
    if mode == "color_echo":
        return dict(mechanism="chromatic adaptation / complementary afterimage",
                    artwork="original procedural geometric scene",
                    timing=dict(adapter_seconds=18, achromatic_test_seconds=6,
                                adapter_static=True, test_static=True),
                    fixation="Keep looking at the central cross through the transition.",
                    physical_control="The six-second test has R=G=B at every pixel. "
                    "The adapter and test share exactly the same scene geometry.",
                    comparison_control="control_frame(t) presents the grayscale scene for the entire clip, "
                    "removing the coloured adaptation phase.",
                    perceptual_qa="Human fixation/adaptation review is required; perceived colour is not encoded.")
    return dict(mechanism="flashed face distortion stimulus",
                artwork="original illustrated identities; perceptual strength with illustrations requires human review",
                timing=dict(identity_interval_seconds=FACE_INTERVAL, pairs_per_second=4,
                            seconds=12, blank_or_flash_frames=False),
                fixation="Look at the central cross, leaving the faces in peripheral vision.",
                physical_control="Every identity has the same eye anchors and stays geometrically static "
                "for 250 ms. Ordinary faces alternate without warping or a brightness strobe.",
                comparison_control="control_frame(t) inserts a 250 ms neutral gap after each 250 ms pair. "
                "This is a separate temporal comparison, not part of the main stimulus.",
                perceptual_qa="Do not label the result a verified illusion until a human has viewed the actual reel.")


def _cross(im):
    d = ImageDraw.Draw(im)
    c = im.width/2
    radius = max(3, round(im.width*.013))
    stroke = max(1, round(im.width*.003))
    d.ellipse((c-radius*1.35, c-radius*1.35, c+radius*1.35, c+radius*1.35),
              fill=(225, 225, 225))
    d.line((c-radius, c, c+radius, c), fill=(20, 20, 20), width=stroke)
    d.line((c, c-radius, c, c+radius), fill=(20, 20, 20), width=stroke)


def _scene(parameters, size):
    """An illustrated scene drawn once, so phase changes cannot move its edges."""
    s = size*2
    im = Image.new("RGB", (s, s), (85, 185, 219))
    d = ImageDraw.Draw(im)
    def box(coords):
        return tuple(round(x*s) for x in coords)
    def poly(points, color):
        d.polygon([(round(x*s), round(y*s)) for x, y in points], fill=color)
    c, n, landmark = parameters["composition"], parameters["layers"], parameters["landmark"]
    scene = parameters["scene"]
    sun_x = .18+.15*c
    d.ellipse(box((sun_x-.095, .10, sun_x+.095, .29)), fill=(249, 202, 85))
    # The thin architectural border and layered landscapes provide fixed
    # spatial landmarks for the transition, rather than a featureless target.
    if scene == "terrace":
        horizon = .39+.015*c
        for j in range(n):
            y = horizon+j*.080
            x = -.10+((j+c)%3)*.052
            poly([(x, y), (.78, y-.08), (1.10, y+.10), (.2, y+.25)],
                 [(63, 140, 155), (243, 166, 108), (211, 108, 120),
                  (106, 142, 120), (242, 200, 127), (142, 112, 151)][j])
            d.line([box((x, y)), box((.78, y-.08)), box((1.10, y+.10))],
                   fill=(253, 221, 173), width=max(2, round(s*.005)))
        count = 4+c
        for j in range(count):
            x = .10+j*.78/max(1, count-1)
            y = .49+(j%2)*.10
            width = .05+.008*(j%3)
            d.rectangle(box((x-width, y, x+width, y+.22)), fill=(247, 220, 175))
            d.ellipse(box((x-width, y-width, x+width, y+width)), fill=(247, 220, 175))
            d.rectangle(box((x-width*.53, y+.025, x+width*.53, y+.22)), fill=(75, 103, 142))
            d.ellipse(box((x-width*.53, y-width*.53+.025, x+width*.53, y+width*.53+.025)),
                      fill=(75, 103, 142))
        if landmark:
            poly([(.65, .76), (.72, .41), (.79, .76)], (45, 103, 91))
            d.rectangle(box((.715, .72, .725, .87)), fill=(115, 77, 75))
        else:
            d.ellipse(box((.65, .72, .82, .85)), fill=(70, 132, 159))
            d.ellipse(box((.68, .75, .79, .81)), fill=(221, 199, 162))
    elif scene == "mountain":
        for j in range(n):
            y = .38+.09*j
            peaks = [(-.10, y+.2)]
            for k in range(5+c):
                x = k/(4+c)
                peaks.append((x, y+(.14 if k%2 == 0 else -.075)-.025*((k+c+j)%3)))
            peaks.extend([(1.1, y+.2), (1.1, 1.1), (-.1, 1.1)])
            poly(peaks, [(128, 131, 179), (109, 115, 161), (79, 130, 145),
                         (65, 117, 120), (52, 102, 95), (44, 87, 89)][j])
        river = [(.52+.035*math.sin(j*.8+c), .46+j*.026) for j in range(23)]
        for j in range(1, len(river)):
            a, b = river[j-1], river[j]
            d.line((box(a), box(b)), fill=(239, 191, 139), width=round(s*(.006+j*.0014)))
        for j in range(5+c):
            x = .08+j*.11
            y = .79+.025*math.sin(j+c)
            r = .027+.006*(j%3)
            if landmark:
                poly([(x, y-r*2.4), (x-r, y+r), (x+r, y+r)], (27, 68, 75))
            else:
                d.ellipse(box((x-r, y-r*2, x+r, y+r)), fill=(192, 139, 137))
    else:
        im.paste((234, 202, 156), (0, 0, s, s))
        d = ImageDraw.Draw(im)
        d.ellipse(box((.08, .08, .92, .92)), fill=(51, 97, 113))
        rings = n
        petals = 6+c
        for ring in range(rings, 0, -1):
            radius = .035+ring*.052
            leaf_size = .033+ring*.006
            for j in range(petals):
                a = j*2*math.pi/petals+ring*.17+landmark*.23
                cx, cy = .5+radius*math.cos(a), .5+radius*math.sin(a)
                tip = (cx+leaf_size*1.4*math.cos(a), cy+leaf_size*1.4*math.sin(a))
                side = (-leaf_size*.7*math.sin(a), leaf_size*.7*math.cos(a))
                tail = (cx-leaf_size*1.2*math.cos(a), cy-leaf_size*1.2*math.sin(a))
                poly([tip, (cx+side[0], cy+side[1]), tail, (cx-side[0], cy-side[1])],
                     [(225, 134, 111), (112, 178, 151), (239, 192, 94), (174, 147, 189)][ring%4])
                d.line((box(tail), box(tip)), fill=(235, 218, 169), width=max(1, round(s*.0018)))
        d.ellipse(box((.452, .452, .548, .548)), fill=(241, 187, 105))
        for j in range(petals*2):
            a = j*math.pi/petals
            cx, cy = .5+.39*math.cos(a), .5+.39*math.sin(a)
            r = .009 if landmark else .014
            d.ellipse(box((cx-r, cy-r, cx+r, cy+r)), fill=(224, 203, 161))
    d.rounded_rectangle(box((.025, .025, .975, .975)), radius=round(.018*s),
                        outline=(244, 224, 190), width=max(2, round(.004*s)))
    return im.resize((size, size), Image.Resampling.LANCZOS)


def _portrait(parameters, identity, width, height):
    """Ordinary original illustrated portrait with fixed eye landmarks.

    The geometry is drawn once for an identity. There is no morph/deformation
    function. Differences are normal face width, hairstyle, nose and features.
    """
    w, h = width*2, height*2
    p = parameters
    im = Image.new("RGB", (w, h), (42, 47, 58))
    d = ImageDraw.Draw(im)
    def b(coords):
        return tuple(round(z*(w if i%2 == 0 else h)) for i, z in enumerate(coords))
    def pts(coords):
        return [(round(x*w), round(y*h)) for x, y in coords]
    def ellipse(coords, fill, **kw):
        d.ellipse(b(coords), fill=fill, **kw)
    skin = np.array((186, 145, 124))+np.array((identity%3-1, identity%3-1, identity%3-1))*4
    tone = tuple(map(int, skin))
    light = tuple(map(int, np.minimum(255, skin+15)))
    shadow = tuple(map(int, skin-np.array((24, 27, 25))))
    hair_colors = ((44, 35, 35), (71, 49, 39), (92, 65, 44), (55, 45, 45))
    hair = hair_colors[(identity+p["hair_family"])%len(hair_colors)]
    jaw = (p["jaw_family"]+identity//4)%4
    halfwidth = .245+.018*(identity%4)+jaw*.006
    chin_y = .775+.016*(identity%3)+.005*jaw
    # Shoulders and neck remain within every portrait, avoiding on/off flashes.
    ellipse((.05, .81, .95, 1.16), (62, 82, 102))
    d.rectangle(b((.39, .70, .61, .92)), fill=shadow)
    d.polygon(pts([(.34, .88), (.50, .97), (.66, .88), (.61, .81), (.39, .81)]), fill=light)
    ellipse((.5-halfwidth-.055, .405, .5-halfwidth+.055, .61), shadow)
    ellipse((.5+halfwidth-.055, .405, .5+halfwidth+.055, .61), shadow)
    ellipse((.5-halfwidth-.062, .16, .5+halfwidth+.062, .65), hair)
    # Curved face silhouette; jaw families change normal contour rather than
    # distorting features over time. The eyes are not attached to this contour.
    head = [( .5, .185), (.5+halfwidth*.77, .20), (.5+halfwidth, .32),
            (.5+halfwidth*.99, .56), (.5+halfwidth*(.76-.075*jaw), .70),
            (.5+.075+.013*jaw, chin_y-.01), (.5, chin_y),
            (.5-.075-.013*jaw, chin_y-.01), (.5-halfwidth*(.76-.075*jaw), .70),
            (.5-halfwidth*.99, .56), (.5-halfwidth, .32), (.5-halfwidth*.77, .20)]
    head_mask = Image.new("L", (w, h)); md = ImageDraw.Draw(head_mask)
    md.polygon(pts(head), fill=255)
    head_mask = head_mask.filter(ImageFilter.GaussianBlur(max(.5, w*.009)))
    yy, xx = np.mgrid[:h, :w]
    illumination = 10*np.exp(-((xx/w-.43)/.29)**2-((yy/h-.35)/.37)**2)
    illumination -= 13*np.clip((xx/w-.56)/.4, 0, 1)
    fill = np.clip(skin[None, None, :]+illumination[..., None], 0, 255).astype("uint8")
    im.paste(Image.fromarray(fill), (0, 0), head_mask)
    d = ImageDraw.Draw(im)
    # Hair comes in six genuine hairstyles and identity variations.
    hf = (p["hair_family"]+identity//4)%6
    if hf in (0, 1):
        d.polygon(pts([(.5-halfwidth, .36), (.5-halfwidth-.02, .24), (.34, .15),
                       (.60, .13), (.5+halfwidth+.02, .25), (.5+halfwidth, .34),
                       (.67, .24), (.43 if hf == 0 else .58, .27), (.30, .25)]), fill=hair)
    elif hf in (2, 3):
        for j in range(9):
            x = .5-halfwidth+j*2*halfwidth/8
            y = .21+.06*abs(j-4)/4
            ellipse((x-.065, y-.075, x+.065, y+.075), hair)
        if hf == 3:
            d.rectangle(b((.5-halfwidth-.035, .25, .5-halfwidth+.04, .70)), fill=hair)
            d.rectangle(b((.5+halfwidth-.04, .25, .5+halfwidth+.035, .70)), fill=hair)
    elif hf == 4:
        d.arc(b((.5-halfwidth+.01, .19, .5+halfwidth-.01, .49)), 180, 350,
              fill=hair, width=max(3, round(w*.025)))
    else:
        d.polygon(pts([(.5-halfwidth, .36), (.24, .18), (.33, .15), (.43, .12),
                       (.55, .16), (.64, .11), (.74, .21), (.5+halfwidth, .35),
                       (.63, .25), (.47, .27), (.32, .25)]), fill=hair)
    eye_y = .46
    # Fixed anatomical anchors across the whole deck and all geometries.
    for side in (-1, 1):
        x = .5+side*.135
        eye_w = .084
        aperture = .023+.002*(identity%3)
        ellipse((x-eye_w, eye_y-aperture, x+eye_w, eye_y+aperture), (222, 214, 195))
        iris = ((70, 81, 74), (93, 73, 58), (74, 84, 91))[identity%3]
        ellipse((x-.025, eye_y-.025, x+.025, eye_y+.025), iris)
        ellipse((x-.010, eye_y-.016, x+.010, eye_y+.016), (26, 29, 31))
        ellipse((x-.010, eye_y-.016, x-.002, eye_y-.008), (238, 235, 220))
        d.arc(b((x-eye_w, eye_y-aperture, x+eye_w, eye_y+aperture)), 180, 360,
              fill=(68, 48, 45), width=max(1, round(w*.008)))
        brow_y = eye_y-.065-.004*(identity%4)
        brow_points = [(x-eye_w*.96, brow_y+.004*side), (x, brow_y-.01*(1+identity%2)),
                       (x+eye_w*.96, brow_y-.004*side)]
        d.line(pts(brow_points), fill=hair, width=max(2, round(w*.018)), joint="curve")
    nose = (p["nose_family"]+identity%5)%5
    nose_base = .59+.008*nose
    nose_half = .023+.008*nose
    d.line(pts([(.50, .49), (.48-.002*nose, nose_base), (.52, nose_base+.007)]),
           fill=shadow, width=max(1, round(w*.010)))
    ellipse((.50-nose_half, nose_base-.006, .50+nose_half, nose_base+.018), shadow)
    ellipse((.49-nose_half*.55, nose_base-.008, .51+nose_half*.55, nose_base+.008), light)
    mouth_y = .685+.004*(identity%3)
    mouth_w = .075+.010*(identity%4)
    lip = (135, 82, 77)
    d.line(pts([(.5-mouth_w, mouth_y), (.47, mouth_y-.004), (.5, mouth_y),
               (.53, mouth_y-.004), (.5+mouth_w, mouth_y)]), fill=lip,
           width=max(2, round(h*.011)), joint="curve")
    d.arc(b((.5-mouth_w*.9, mouth_y-.013, .5+mouth_w*.9, mouth_y+.031)),
          12, 168, fill=(202, 151, 133), width=max(1, round(h*.009)))
    if identity%4 == 0:
        # Ordinary spectacles, drawn with the same eye coordinates.
        for x in (.365, .635):
            d.rounded_rectangle(b((x-.098, eye_y-.049, x+.098, eye_y+.050)),
                                radius=round(w*.026), outline=(54, 49, 47),
                                width=max(2, round(w*.009)))
        d.line(pts([(.463, eye_y-.005), (.537, eye_y-.005)]), fill=(54, 49, 47),
               width=max(2, round(w*.009)))
    if identity%5 == 2:
        # Freckles add normal identity detail without altering anatomy.
        for side in (-1, 1):
            for j in range(5):
                x = .5+side*(.115+.024*(j%3))
                y = .55+.015*(j//3)
                ellipse((x-.003, y-.002, x+.003, y+.002), (139, 99, 83))
    return im.resize((width, height), Image.Resampling.LANCZOS)


class Stimulus:
    def __init__(self, mode, parameters, seed, size):
        if mode not in MODES or parameters not in parameters_for(mode):
            raise ValueError("Unknown mode or parameters outside structural catalogue")
        if type(seed) is not int or not 0 <= seed < 2**64:
            raise ValueError("seed must be an unsigned 64-bit integer")
        if type(size) is not int or size < 160:
            raise ValueError("size must be an integer of at least 160 pixels")
        self.mode, self.parameters, self.seed, self.size = mode, dict(parameters), seed, size
        self.seconds = seconds_for(mode)
        self._faces = {}
        if mode == "color_echo":
            original = _scene(parameters, size)
            self._adapter = ImageOps.invert(original)
            # Pixelwise grayscale of that exact adapter gives a strict physical
            # control: same luminance structure, no hidden coloured test frame.
            self._test = ImageOps.grayscale(self._adapter).convert("RGB")
            _cross(self._adapter)
            _cross(self._test)
        else:
            self._portrait_width = round(size*.422)
            self._portrait_height = round(size*.91)
            self._y = round(size*.5-self._portrait_height*.46)
            self._x = (round(size*.035), size-round(size*.035)-self._portrait_width)

    @property
    def eye_positions(self):
        if self.mode != "face_flash":
            return ()
        return tuple((round(x+self._portrait_width*q), round(self._y+self._portrait_height*.46))
                     for x in self._x for q in (.365, .635))

    def identity_at(self, t):
        if not math.isfinite(t) or t < 0:
            raise ValueError("t must be a finite nonnegative time")
        interval = min(47, int(t/FACE_INTERVAL))
        offset = self.seed%16
        left, right = (interval*5+offset)%16, (interval*7+offset+3)%16
        if left == right:
            right = (right+1)%16
        return left, right

    def portrait(self, identity):
        """Return a copy of one fixed bitmap for anatomy/asset inspection."""
        if self.mode != "face_flash" or type(identity) is not int or not 0 <= identity < 16:
            raise ValueError("portrait requires a face identity from 0 to 15")
        if identity not in self._faces:
            self._faces[identity] = _portrait(self.parameters, identity,
                                            self._portrait_width, self._portrait_height)
        return self._faces[identity].copy()

    def control_frame(self, t):
        """A separate matched comparison clip; never used in the main stimulus."""
        if not math.isfinite(t) or t < 0:
            raise ValueError("t must be a finite nonnegative time")
        if self.mode == "color_echo":
            return self._test.copy()
        interval = int(t/FACE_INTERVAL)
        if interval%2 == 0:
            return self.frame((interval//2)*FACE_INTERVAL)
        im = Image.new("RGB", (self.size, self.size), (28, 33, 42))
        _cross(im)
        return im

    def frame(self, t):
        if not math.isfinite(t) or t < 0:
            raise ValueError("t must be a finite nonnegative time")
        if self.mode == "color_echo":
            return (self._adapter if t < ADAPT_SECONDS else self._test).copy()
        im = Image.new("RGB", (self.size, self.size), (28, 33, 42))
        for x, identity in zip(self._x, self.identity_at(t)):
            if identity not in self._faces:
                self.portrait(identity)
            im.paste(self._faces[identity], (x, self._y))
        _cross(im)
        return im
