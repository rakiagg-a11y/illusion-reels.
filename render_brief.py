"""Explicit local render adapter. No scheduling, uploads, or publishing."""
import argparse
import json
from pathlib import Path
from creative_director import validate_brief


def render_local(brief, out, runner=None, ffmpeg=None):
    spec = validate_brief(brief)
    out = Path(out)
    if out.suffix.lower() != ".mp4":
        raise ValueError("local output must end in .mp4")
    if out.exists() or out.with_suffix(".json").exists():
        raise ValueError("output already exists; choose a new local path")
    if runner is None:
        from generate import run
        runner = run
    out.parent.mkdir(parents=True, exist_ok=True)
    # Fixed duration and dimensions were validated against generate.run.
    # Empty handle also avoids the Linux-only watermark font path on Windows.
    if spec["style"] in ("opticpop", "illusion_lab"):
        return runner(spec["style"], spec["seed"], str(out), "", scene=spec["scene"],
                      creative_caption=brief["caption"], **({"ffmpeg":ffmpeg} if ffmpeg is not None else {}))
    return runner(spec["style"], spec["seed"], str(out), "",
                  obj=spec["obj"], text=spec["text"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--ffmpeg", help="optional encoder path for opticpop/illusion_lab scenes")
    a = ap.parse_args()
    try:
        print(json.dumps(render_local(json.loads(a.brief.read_text(encoding="utf-8")), a.out, ffmpeg=a.ffmpeg),
                         ensure_ascii=False, indent=2))
    except (ValueError, OSError, RuntimeError) as exc:
        ap.error(str(exc))
