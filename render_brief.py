"""Explicit local render adapter. No scheduling, uploads, or publishing."""
import argparse
import json
from pathlib import Path
from creative_director import validate_brief


def render_local(brief, out, runner=None):
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
    return runner(spec["style"], spec["seed"], str(out), "",
                  obj=spec["obj"], text=spec["text"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    try:
        print(json.dumps(render_local(json.loads(a.brief.read_text(encoding="utf-8")), a.out),
                         ensure_ascii=False, indent=2))
    except (ValueError, OSError, RuntimeError) as exc:
        ap.error(str(exc))
