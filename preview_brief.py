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
    import pointcloud as pc
    from PIL import Image, ImageDraw
    # Preview only. Restore globals so imported callers retain production dimensions.
    previous = pc.W, pc.H
    try:
        pc.W, pc.H = 270, 480
        scene = pc.Scene(r["obj"], r["seed"], r["seconds"], r["text"])
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet = Image.new("RGB", (270 * 3, 500))
        angles = [scene.phase, 0.0, scene.phase + math.pi]
        for k, angle in enumerate(angles):
            sheet.paste(Image.fromarray(scene.frame_crisp(angle, dot=1.1 * 270 / 1080)), (k * 270, 20))
        ImageDraw.Draw(sheet).text((6, 3), "Review: opening | alignment | half turn (not a timeline)", fill="white")
        sheet.save(out.with_suffix(".png"))
        with subprocess.Popen(
            [executable, "-n", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", "270x480", "-r", "10", "-i", "-", "-an", "-c:v", "libx264",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
            stdin=subprocess.PIPE
        ) as proc:
            try:
                for i in range(150):
                    angle = scene.phase + scene.direction * 2 * math.pi * (i / 10) / scene.period
                    proc.stdin.write(scene.frame_crisp(angle, dot=1.1 * 270 / 1080).tobytes())
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
