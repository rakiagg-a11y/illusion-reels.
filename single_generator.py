"""Shared local runner for five independently selectable generator entry points."""
import argparse
import json
from pathlib import Path
import random
import secrets

import five_styles as d
from five_style_render import load_history, render_one


def choose_brief(style, seed, history, mode=None, account_id=None, handle=None):
    if not isinstance(style, str) or style not in d.STYLES:
        raise ValueError("unknown generator style")
    if type(seed) is not int or not 0 <= seed < 1_000_000:
        raise ValueError("seed must be in 0-999999")
    if mode is not None and mode not in d.MODES[style]:
        raise ValueError("mode does not belong to this generator")
    account = next(a for a in d.default_accounts()["accounts"] if a["style"] == style)
    if account_id is not None:
        account["id"] = account_id
    if handle is not None:
        account["handle"] = handle
    d.validate_account(account)
    # Pending previews are reserved for exact-brief promotion via --brief.
    seen = {entry["key"] for entry in history["entries"]}
    rng = random.Random(seed)
    pools = []
    primary = d.PRIMARY_MODES.get(style)
    if mode is None and primary and any(d.structural_key(style, primary, p) not in seen
                                        for p in d.parameters_for(primary)):
        mode = primary
    for name in ((mode,) if mode else d.MODES[style]):
        parameters = d.parameters_for(name)
        used = sum(d.structural_key(style, name, p) in seen for p in parameters)
        eligible = [p for p in parameters if d.structural_key(style, name, p) not in seen]
        rng.shuffle(eligible)
        eligible.sort(key=lambda p: -d.evaluate(name, p)["total"])
        if eligible:
            pools.append((used, name, eligible))
    if not pools:
        raise ValueError("this generator's structural catalogue is exhausted; add geometry rather than recycle colors")
    rng.shuffle(pools)
    pools.sort(key=lambda pool: pool[0])
    _, name, parameters = pools[0]
    return d.make_brief(account, name, parameters[0], seed)


def main(style):
    if style not in d.STYLES:
        raise ValueError("unknown generator")
    profile = next(a for a in d.default_accounts()["accounts"] if a["style"] == style)
    ap = argparse.ArgumentParser(description=f"{d.GENERATORS[style]['name']} ({style}): one local video from this style only. Default page: {profile['handle'] or 'unassigned'}")
    ap.add_argument("--out", required=True, help="new output folder")
    ap.add_argument("--mode", choices=d.MODES[style])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--account", help="local account ID")
    ap.add_argument("--handle", help="watermark handle")
    ap.add_argument("--brief", help="exact prior brief for reviewed-preview promotion")
    ap.add_argument("--history", default=str(Path(__file__).resolve().parent/"local_demo"/"ready_generators_history.json"))
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()
    try:
        if a.brief:
            if any(v is not None for v in (a.mode, a.seed, a.account, a.handle)):
                ap.error("--brief cannot be combined with mode, seed, account or handle overrides")
            brief = d.validate_brief(json.loads(Path(a.brief).read_text(encoding="utf-8-sig")))
            if brief["style"] != style:
                ap.error("brief belongs to a different generator")
        else:
            brief = choose_brief(style, a.seed if a.seed is not None else secrets.randbelow(1_000_000),
                                 load_history(a.history), a.mode, a.account, a.handle)
        print(json.dumps(dict(generator=d.GENERATORS[style]["name"], generator_label=d.GENERATORS[style]["label"],
                              account=brief["account"], style=style, mode=brief["mode"],
                              concept=brief["id"], local_only=True), ensure_ascii=True), flush=True)
        print(json.dumps(render_one(brief, a.out, a.history, a.preview, a.ffmpeg), ensure_ascii=True))
    except (ValueError, OSError, RuntimeError) as error:
        ap.error(str(error))
