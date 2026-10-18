"""Render a small local review MP4 using the existing pointcloud.Scene."""
import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path
from creative_director import validate_brief


def preview(brief, out, ffmpeg="ffmpeg"):
    r = validate_brief(brief)
    out = Path(out)
    if out.suffix.lower() != ".mp4" or out.exists() or out.with_suffix(".png").exists():
        raise ValueError("choose a new .mp4 path (including unused .png companion)")
    executable = shutil.which(ffmpeg)
    if executable is None:
        raise ValueError("ffmpeg is required for video preview")
    if r["style"] == "illusion_lab":
        from illusion_lab import frame, render
        from PIL import Image, ImageDraw
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGB", (360*4,664))
        for i,t in enumerate((0,3.75,7.5,11.5)):
            sheet.paste(Image.fromarray(frame(r["scene"],t,360,640)),(i*360,24))
            ImageDraw.Draw(sheet).text((i*360+8,5),f"{t}s",fill="white")
        sheet.save(out.with_suffix(".png"))
        render(r["scene"],r["seed"],out,ffmpeg=executable,width=360,height=640,fps=10)
        return out
    import pointcloud as pc
    from PIL import Image, ImageDraw
    # Preview only. Restore globals so imported callers retain production dimensions.
    previous = pc.W, pc.H
    try:
        relational = r["style"] == "opticpop"
        pc.W, pc.H = (360, 640) if relational else (270, 480)
        if relational:
            from relational_scene import Scene
            scene = Scene(r["scene"], r["seed"], r["seconds"])
        else:
            scene = pc.Scene(r["obj"], r["seed"], r["seconds"], r["text"])
        out.parent.mkdir(parents=True, exist_ok=True)
        angles = [k * math.pi / 2 for k in range(5)] if relational else [scene.phase, 0.0, scene.phase + math.pi]
        sheet = Image.new("RGB", (pc.W * len(angles), pc.H + 24))
        for k, angle in enumerate(angles):
            sheet.paste(Image.fromarray(scene.frame_crisp(angle, dot=1.1 * pc.W / 1080)), (k * pc.W, 24))
        draw = ImageDraw.Draw(sheet)
        if relational:
            for k in range(5):
                draw.text((k * pc.W + 8, 5), f"{k * scene.period / 4:.3f}s", fill="white")
        else:
            draw.text((6, 3), "Opening | alignment | half turn (not a timeline)", fill="white")
        sheet.save(out.with_suffix(".png"))
        with subprocess.Popen(
            [executable, "-n", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{pc.W}x{pc.H}", "-r", "10", "-i", "-", "-an", "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
            stdin=subprocess.PIPE
        ) as proc:
            try:
                for i in range(150):
                    angle = scene.phase + scene.direction * 2 * math.pi * (i / 10) / scene.period
                    proc.stdin.write(scene.frame_crisp(angle, dot=1.1 * pc.W / 1080).tobytes())
            finally:
                proc.stdin.close()
            if proc.wait() != 0:
                raise RuntimeError("ffmpeg preview encoding failed")
        return out
    finally:
        pc.W, pc.H = previous


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()
    try:
        print(preview(json.loads(a.brief.read_text(encoding="utf-8")), a.out, a.ffmpeg))
    except (ValueError, OSError, RuntimeError) as exc:
        ap.error(str(exc))
