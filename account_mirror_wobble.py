"""Original dual-reading artwork and stationary relative-motion stimuli.

These are procedural analogues of two reference families, not reproductions of
the reference artwork.  In particular, an ordinary reflected image does not
become ambiguous merely by being reflected: MirrorFlip constructs a Rubin
figure first.  StillWobble never moves its centre relative to its surround.
"""
from __future__ import annotations

from functools import lru_cache
import math

import numpy as np
from PIL import Image, ImageDraw, ImageOps


MODES = ("mirror_flip", "still_wobble")


def parameters_for(mode: str) -> list[dict]:
    """Return finite, structurally distinct compositions, rather than recolours."""
    if mode == "mirror_flip":
        return [dict(profile=profile, throat=throat, rim_width=rim)
                for profile in ("classical", "soft", "angular", "aquiline")
                for throat in (0.08, 0.11, 0.14, 0.17, 0.20)
                for rim in (0.34, 0.40, 0.46, 0.52, 0.58)]
    if mode == "still_wobble":
        return [dict(element_length=length, aspect_ratio=ratio,
                     surround_angle=angle, centre_radius=radius)
                for length in (18, 22, 26, 30, 34)
                for ratio in (3, 4, 5, 6)
                for angle in (0, 15, 30, 45)
                for radius in (0.21, 0.25, 0.29)]
    raise ValueError(f"Unknown mirror/wobble mode: {mode}")


def seconds_for(mode: str) -> int:
    if mode not in MODES:
        raise ValueError(f"Unknown mirror/wobble mode: {mode}")
    return 15


def describe(mode: str, parameters: dict) -> dict:
    _validate_parameters(mode, parameters)
    if mode == "mirror_flip":
        return {
            "mechanism": "Rubin figure-ground ambiguity: the same boundary defines a vase and two facing profiles.",
            "control": "The lower artwork is an exact vertical reflection of the upper artwork; no semantic image morph is encoded.",
            "instruction": "Find the vase, then the two faces. Compare the reflected image.",
            "reference_relationship": "Original Rubin-style analogue of semantic reversible art. It does not reproduce Ocampo's artwork or claim the same image-reversal effect.",
            "perceptual_qa": "Human review required: semantic alternation cannot be certified from pixels alone.",
            "reference_url": "https://www.instagram.com/biologistmichael/reel/DKanwbnS2JR/",
            "physical_motion": False,
        }
    return {
        "mechanism": "Ouchi-inspired relative-motion illusion: orthogonal elongated checker elements bias perceived motion of centre and surround during small viewer/image movements.",
        "control": "control_frame() uses the surround orientation throughout, while retaining the same palette, cell size, phase and centre region.",
        "instruction": "Look near the centre and gently move the phone. Does the centre seem to slide?",
        "reference_relationship": "Original Ouchi-inspired analogue of the static-motion family. The exact mechanism of the truffle/foil reference is not established here.",
        "perceptual_qa": "Human review required at normal phone size; strength varies with display and viewing motion.",
        "reference_url": "https://www.instagram.com/biologistmichael/reel/DNEnh7iScpb/",
        "mechanism_source": "https://www.sciencedirect.com/science/article/pii/S0042698999001625",
        "physical_motion": False,
    }


@lru_cache(maxsize=2)
def _catalogue(mode: str) -> tuple[tuple, ...]:
    return tuple(tuple(sorted(p.items())) for p in parameters_for(mode))


def _validate_parameters(mode: str, parameters: dict) -> None:
    if mode not in MODES or not isinstance(parameters, dict):
        raise ValueError("A supported mode and parameter object are required")
    if tuple(sorted(parameters.items())) not in _catalogue(mode):
        raise ValueError(f"Parameters are outside the {mode} composition catalogue")


def _smooth(points: list[tuple[float, float]], steps: int = 12) -> list[tuple[float, float]]:
    """Catmull-Rom profile; all features share a single figure/ground boundary."""
    extended = [points[0], *points, points[-1]]
    result = []
    for index in range(1, len(extended) - 2):
        p0, p1, p2, p3 = (np.array(p, dtype=float) for p in extended[index-1:index+3])
        for t in np.linspace(0, 1, steps, endpoint=False):
            p = 0.5 * ((2*p1) + (-p0+p2)*t
                       + (2*p0-5*p1+4*p2-p3)*t*t
                       + (-p0+3*p1-3*p2+p3)*t*t*t)
            result.append(tuple(p))
    result.append(points[-1])
    return result


def _profile(parameters: dict) -> list[tuple[float, float]]:
    """Left face looking right; the exact reflected curve forms the right face."""
    profile = parameters["profile"]
    rim_left = (1 - parameters["rim_width"]) / 2
    nose = (1 - parameters["throat"]) / 2
    shapes = {
        # Forehead, bridge, nose, nostril, philtrum, lips and chin remain readable
        # silhouettes; changes affect actual contour geometry, not a seed label.
        "classical": [(0.350,.22),(.363,.30),(.375,.34),(nose,.44),
                      (nose-.045,.477),(.386,.494),(.397,.526),(.425,.548),
                      (.406,.569),(.421,.595),(.391,.645),(.365,.684)],
        "soft": [(0.340,.22),(.361,.29),(.371,.35),(nose,.445),
                 (nose-.040,.478),(.385,.506),(.400,.540),(.419,.559),
                 (.403,.580),(.412,.607),(.382,.657),(.350,.700)],
        "angular": [(0.345,.22),(.360,.29),(.381,.34),(nose,.438),
                    (nose-.034,.480),(.384,.495),(.394,.530),(.426,.545),
                    (.399,.571),(.421,.598),(.397,.656),(.345,.705)],
        "aquiline": [(0.345,.22),(.362,.29),(.387,.34),(nose-.012,.39),
                     (nose,.448),(nose-.033,.483),(.382,.507),(.397,.535),
                     (.426,.555),(.407,.579),(.421,.605),(.380,.669)],
    }
    points = [(rim_left,.08), (rim_left-.025,.115), (.330,.16),
              *shapes[profile], (.330,.745), (.325,.805),
              (.270,.854), (.245,.905)]
    # A modest nose must still remain in front of the bridge for every profile.
    # This matters at the widest throat variants of the vase.
    lip_shift = max(0, .435-nose)
    points = [(min(x, nose-.012) if .20 < y < .37 else
               x-lip_shift if .49 <= y <= .67 else x, y) for x, y in points]
    return points if profile == "angular" else _smooth(points)


class Stimulus:
    """Square RGB panel.  Header, instructions and social safe-zone are external.

    Exposed region/orientation metadata supports meaningful geometry controls.
    No fonts, downloaded media, live services, publishing or account state occur
    in this module.  A seed is accepted for the shared renderer interface but is
    deliberately not used to manufacture artificial structural diversity.
    """

    def __init__(self, mode: str, parameters: dict, seed: int, size: int):
        _validate_parameters(mode, parameters)
        if isinstance(size, bool) or not isinstance(size, int) or not 96 <= size <= 2400:
            raise ValueError("Panel size must be an integer from 96 to 2400")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("Seed must be an integer")
        self.mode, self.parameters, self.seed, self.size = mode, dict(parameters), seed, size
        self.seconds = seconds_for(mode)
        self.source_box = self.reflection_box = None
        self.surround_orientation = self.centre_orientation = None
        if mode == "mirror_flip":
            self._image = self._mirror()
            self._control = self._image.copy()
        else:
            self.surround_orientation = parameters["surround_angle"]
            self.centre_orientation = (self.surround_orientation + 90) % 180
            self._image = self._wobble(control=False)
            self._control = self._wobble(control=True)

    def frame(self, t: float) -> Image.Image:
        if not isinstance(t, (int, float)) or not math.isfinite(t):
            raise ValueError("Frame time must be finite")
        return self._image.copy()

    def control_frame(self) -> Image.Image:
        return self._control.copy()

    def _mirror(self) -> Image.Image:
        s = self.size
        canvas = Image.new("RGB", (s, s), (9, 13, 23))
        width, height = round(s*.84), round(s*.365)
        left, top = (s-width)//2, round(s*.065)
        reflection_top = s-top-height
        self.source_box = (left, top, left+width, top+height)
        self.reflection_box = (left, reflection_top, left+width, reflection_top+height)
        # Supersampling improves the common boundary without independent face
        # overlays.  Both interpretations use exactly the same polygon edge.
        aa = 3
        art = Image.new("RGB", (width*aa, height*aa), (240, 230, 207))
        draw = ImageDraw.Draw(art)
        left_curve = _profile(self.parameters)
        right_curve = [(1-x,y) for x,y in reversed(left_curve)]
        polygon = [(round(x*width*aa), round(y*height*aa)) for x,y in left_curve+right_curve]
        draw.polygon(polygon, fill=(25, 32, 44))
        art = art.resize((width, height), Image.Resampling.LANCZOS)
        canvas.paste(art, (left, top))
        canvas.paste(ImageOps.flip(art), (left, reflection_top))
        edge = ImageDraw.Draw(canvas)
        # Borders stay outside the image crop, preserving pixel-exact reflection.
        for box in (self.source_box, self.reflection_box):
            x0,y0,x1,y1 = box
            edge.rectangle((x0-2,y0-2,x1+1,y1+1), outline=(173,144,91), width=max(1,round(s/450)))
        line_y = s//2
        edge.line((left,line_y,left+width,line_y),fill=(113,98,76),width=max(1,round(s/500)))
        r = max(3,round(s*.009))
        edge.polygon(((s//2-r,line_y),(s//2,line_y-r),(s//2+r,line_y),(s//2,line_y+r)),fill=(214,184,121))
        return canvas

    def _wobble(self, *, control: bool) -> Image.Image:
        # Build at least 900px before reducing previews.  Fine anisotropic
        # elements otherwise alias to a different stimulus at small dimensions.
        n = max(900, self.size)
        yy, xx = np.mgrid[:n,:n].astype(np.float32)
        x, y = xx-(n-1)/2, yy-(n-1)/2
        scale = n/900
        length = self.parameters["element_length"] * scale
        short = length/self.parameters["aspect_ratio"]
        angle = self.parameters["surround_angle"]

        def texture(degrees):
            rad = math.radians(degrees)
            u = x*math.cos(rad) + y*math.sin(rad)
            v = -x*math.sin(rad) + y*math.cos(rad)
            return ((np.floor(u/length) + np.floor(v/short)).astype(np.int32) % 2).astype(bool)

        surround = texture(angle)
        centre = surround if control else texture(angle+90)
        radius = self.parameters["centre_radius"] * n
        centre_mask = x*x+y*y <= radius*radius
        cells = np.where(centre_mask, centre, surround)
        # Achromatic elements avoid attributing the effect to coloured edges.
        values = np.where(cells, 229, 36).astype(np.uint8)
        pixels = np.repeat(values[:,:,None], 3, axis=2)
        texture_image = Image.fromarray(pixels)
        canvas = Image.new("RGB", (n,n), (9,13,23))
        mask = Image.new("L",(n,n))
        ImageDraw.Draw(mask).rounded_rectangle((n*.055,n*.055,n*.945,n*.945),radius=n*.025,fill=255)
        canvas.paste(texture_image,(0,0),mask)
        ImageDraw.Draw(canvas).rounded_rectangle((n*.055,n*.055,n*.945,n*.945),radius=n*.025,outline=(173,144,91),width=max(1,round(n/450)))
        # No disc outline or shadow: the boundary is produced solely by the
        # orientation change.  The matched control therefore has no disc cue.
        if n != self.size:
            canvas = canvas.resize((self.size,self.size),Image.Resampling.LANCZOS)
        return canvas
