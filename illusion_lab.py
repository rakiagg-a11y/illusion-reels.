"""Python/Pillow ports of three MIT-licensed illusion algorithms.

Ebbinghaus placement: Copyright (c) 2018 Dominique Makowski (Pyllusion).
Footsteps shared motion: Copyright (c) 2021 Enes (sorceress).
Penrose coordinates/face ordering: Copyright (c) 2019 Albert Lobo.
Full upstream notices and pinned sources: third_party/ and THIRD_PARTY.md.
No upstream UI code is executed or installed.
"""
from functools import lru_cache
import math
import shutil
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from illusion_library import COPY, SOURCES, validate_scene

PALETTES = {"neon": ((255,110,35),(45,115,255)),
            "ice": ((255,150,45),(40,225,245)),
            "amber": ((255,120,35),(185,105,255))}


def context_opacity(seconds):
    """Smooth reveal at 10-13s, with the full context restored before loop end."""
    t = seconds % 15
    fade = max(0., min(1., (t-10)/.75, (13-t)/.75))
    return 1 - fade * fade * (3 - 2 * fade)


def outer_circles(center, target_radius, outer_radius, count, gap, angle=0):
    """Adapted from Pyllusion._ebbinghaus_parameters_outercircles (MIT)."""
    distance = target_radius + outer_radius + gap
    angles = np.linspace(0, 2*math.pi, count, endpoint=False) + angle
    return np.asarray(center) + np.c_[np.cos(angles),np.sin(angles)] * distance


def block_positions(parameters, seconds):
    """One shared displacement for every bar, preserving the footsteps control."""
    p = parameters
    phase = (seconds / 15 * p["cycles"]) % 1
    progress = 1 - abs(2*phase - 1)
    width = p["bar_width"] / p["stripes"]
    x = .06 + (1 - .12 - width) * progress
    height = min(.17, .5 / p["lanes"])
    return [(x, (i+.5)/p["lanes"] - height/2, width, height) for i in range(p["lanes"])]


def penrose_positions(parameters, seconds):
    """Port of calculateCubesCoords/updateCubesPositions; order closes the depth cycle."""
    p = parameters
    n, mid = p["cubes"], (p["cubes"]-1)//2
    a, b, c = np.array([0.,1.]), np.array([1.,1.]), np.array([.5,1-math.sqrt(3)/2])
    phase = (seconds / 15 * p["cycles"] * p["direction"]) % 1
    result = []
    for start, end, indexes in ((a,b,range(mid,n)), (b,c,range(n)),
                                (c,a,range(n)), (a,b,range(mid))):
        result.extend(start + (end-start) * ((i+phase)/n) for i in indexes)
    return np.array(result)


def penrose_faces(parameters, seconds):
    """Port of drawCubePart1/2 and drawTriangle, including the split first cube."""
    centers = penrose_positions(parameters, seconds)
    edge = parameters["fill"] / parameters["cubes"]
    half, height = edge/2, edge*math.sqrt(3)/2
    parts = [np.array([[0,0],[half,-height],[edge,0],[half,height]]),
             np.array([[0,0],[-edge,0],[-half,-height],[half,-height]]),
             np.array([[0,0],[half,height],[-half,height],[-edge,0]])]
    order = [(0,0)] + [(i,part) for i in range(1,len(centers)) for part in range(3)] + [(0,1),(0,2)]
    origin = np.array([.5, 1-math.sqrt(3)/6])
    angle = math.radians(parameters["rotation"])
    rotation = np.array([[math.cos(angle),math.sin(angle)],[-math.sin(angle),math.cos(angle)]])
    return [(i,part,(centers[i]+parts[part]-origin) @ rotation) for i,part in order]


@lru_cache(maxsize=12)
def font(size):
    for name in ("C:/Windows/Fonts/arial.ttf","DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name,size)
        except OSError:
            pass
    return ImageFont.load_default()


def circle(draw, center, radius, color):
    x,y = center
    draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color)


def frame(scene, seconds, width=1080, height=1920, handle=""):
    validate_scene(scene)
    # 2x antialiasing keeps the same geometry in previews and production.
    w,h = width*2,height*2
    image = Image.new("RGB",(w,h),"black")
    draw = ImageDraw.Draw(image)
    p, family = scene["parameters"],scene["family"]
    opacity = context_opacity(seconds)
    if family == "ebbinghaus":
        target, surround = PALETTES[scene["palette"]]
        orbit = 2*math.pi*(seconds % 15)/15*p["cycles"]
        for index, side in enumerate(("small","large")):
            center = (w*.5, h*(.30 if index==0 else .70))
            radius = p[side+"_radius"]*w
            points = outer_circles(center,p["target_radius"]*w,radius,p[side+"_count"],p["gap"]*w,
                                   orbit+index*math.pi)
            for xy in points:
                circle(draw,xy,radius,tuple(round(c*opacity) for c in surround))
            circle(draw,center,p["target_radius"]*w,target)
        control = "Both orange circles keep exactly the same size."
    elif family == "footsteps":
        side = round(w*.84)
        panel = Image.new("RGB",(side,side),(128,128,128))
        pd = ImageDraw.Draw(panel)
        for i in range(p["stripes"]):
            value = round(128 + ((255 if i%2 else 0)-128)*opacity)
            pd.rectangle((round(i*side/p["stripes"]),0,round((i+1)*side/p["stripes"]),side),fill=(value,)*3)
        for i,(x,y,bw,bh) in enumerate(block_positions(p,seconds)):
            pd.rectangle((round(x*side),round(y*side),round((x+bw)*side),round((y+bh)*side)),
                         fill=(255,235,30) if i%2==0 else (8,15,85))
        if p["axis"] == "vertical":
            panel = panel.transpose(Image.Transpose.ROTATE_90)
        image.paste(panel,((w-side)//2,(h-side)//2))
        control = "Same position. Same speed. Watch the stripes fade."
    else:
        primary, secondary = PALETTES[scene["palette"]]
        shades = (secondary,tuple(round(c*.78) for c in primary),primary)
        scale = .44*w / (1/math.sqrt(3)+p["fill"]/p["cubes"]*1.33)
        for _, part, vertices in penrose_faces(p,seconds):
            points = [(w/2+x*scale,h/2+y*scale) for x,y in vertices]
            draw.polygon(points,fill=shades[part],outline=(10,20,40),width=max(1,round(w*.0015)))
        control = "Follow the crossing: which face is in front?"
    draw = ImageDraw.Draw(image)
    def centered(text,y,size,color):
        f = font(size)
        box = draw.textbbox((0,0),text,font=f)
        draw.text(((w-(box[2]-box[0]))/2,y),text,font=f,fill=color)
    centered(COPY[family][1],h*.08,round(w*.034),(240,240,240))
    # The control is factual and does not promise that every viewer perceives the effect.
    # The largest lower Ebbinghaus ring reaches 91% of portrait height.
    centered(control,h*(.925 if family=="ebbinghaus" else .89),round(w*.026),(170,180,195))
    if handle:
        centered(handle,h*(.96 if family=="ebbinghaus" else .94),round(w*.025),(115,125,140))
    return np.asarray(image.resize((width,height),Image.Resampling.LANCZOS))


def render(scene, seed, out, seconds=15, handle="", ffmpeg="ffmpeg", width=1080, height=1920, fps=30):
    validate_scene(scene)
    executable = shutil.which(ffmpeg)
    if executable is None:
        raise ValueError("FFmpeg is required")
    with subprocess.Popen([executable,"-n","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
            "-s",f"{width}x{height}","-r",str(fps),"-i","-","-f","lavfi","-i","anullsrc=r=44100:cl=stereo",
            "-shortest","-c:v","libx264","-crf","19","-pix_fmt","yuv420p","-c:a","aac",
            "-movflags","+faststart",str(out)],stdin=subprocess.PIPE) as proc:
        try:
            for index in range(int(seconds*fps)):
                proc.stdin.write(frame(scene,index/fps,width,height,handle).tobytes())
        finally:
            proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("illusion lab encoding failed")
    return dict(style="illusion_lab",subject=scene["family"],seed=seed,scene=scene,
                source=SOURCES[scene["family"]],width=width,height=height,fps=fps,seconds=seconds)
