"""Five account identities, deterministic concepts and local-only production briefs.

This is a procedural director, not a trained model. It never contacts a publisher.
See FIVE_STYLES.md for research coverage and perceptual validation limits.
"""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random

STYLES = ("reversible_depth", "hidden_stereogram", "binocular_worlds",
          "motion_paradox", "perception_lab")
GENERATORS = {
    "reversible_depth": dict(name="AngleSpin", label="סיבוב בזוויות"),
    "hidden_stereogram": dict(name="HiddenShape", label="צורות חבויות בסטריאוגרמה"),
    "binocular_worlds": dict(name="StereoTwin", label="עומק בשתי תמונות"),
    "motion_paradox": dict(name="MotionShift", label="אשליות תנועה"),
    "perception_lab": dict(name="PerceptionLab", label="צבע, גודל ותפיסה"),
}
SUBJECTS = ("heart", "star", "crescent", "butterfly", "ring", "leaf",
            "diamond", "lightning", "flower", "hourglass")
# The tilted pairs also use shapes added for the month trial.
PAIR_SUBJECTS = SUBJECTS+("drop",)
MODES = {
    "reversible_depth": ("bistable_spin", "tilted_pair"),
    "hidden_stereogram": ("hidden_relief",),
    "binocular_worlds": ("orbital_rings", "helix", "constellation"),
    "motion_paradox": ("motion_form", "infinite_regress", "footsteps"),
    "perception_lab": ("brainrot_spin", "munker_white", "muller_lyer", "afterimage", "troxler", "cafe_wall"),
}
# The generator a page runs when no --mode is given (Rakia, 2026-10-18: opticpop
# should produce shapes that can be seen spinning either way).
PRIMARY_MODES = {"reversible_depth": "bistable_spin",
                 # Rakia, 2026-10-19: trustyoureyes_ becomes a brainrot particle-spin page.
                 "perception_lab": "brainrot_spin"}
SPIN_HOOKS = {
    "planet_wedge": "Which way is the planet spinning?",
    "necker_cube": "Which way is the cube turning?",
    "arrow_disc": "Which way is the arrow turning?",
    "crossed_arrows": "Left or right: which way do the arrows spin?",
    "chevron_band": "Which way are the arrows travelling?",
    "twin_masks": "Which way are the masks turning?",
    "arrow_globe": "Which way is the globe spinning?",
}
PALETTES = ("coral_blue", "mint_violet", "amber_cyan")
REFERENCES = {
    "reversible_depth": "https://www.instagram.com/biologistmichael/reel/DeNPeIkyeLx/",
    "hidden_stereogram": "https://www.instagram.com/biologistmichael/p/Dec9MipPEKe/",
    "binocular_worlds": "https://www.instagram.com/biologistmichael/reel/DeLpuvouR5f/",
    "motion_paradox": "https://www.instagram.com/biologistmichael/reel/DdE0kwoOo9h/",
    "perception_lab": "https://www.instagram.com/biologistmichael/p/DU2P5ERDg-3/",
}
COPY = {
    "brainrot_spin": ("Reverse the spin with your mind", "Blink, then look again. Can you make it switch direction?",
                      "Orthographic projection; additive transparent particles; no occlusion or depth shading."),
    "bistable_spin": ("Which way is it spinning?", "Blink, then look again. Can you make it switch direction?",
                      "Orthographic projection; additive transparent particles; no occlusion or depth shading."),
    "tilted_pair": ("Which object is in front?", "Follow one object through the overlap.",
                    "Orthographic projection; additive surfaces; fixed, distinct tilted axes."),
    "hidden_relief": ("There is a shape inside the pattern.", "Look through the pattern. Keep your phone still.",
                      "Repeated horizontal correspondences encode relief; no visible outline."),
    "orbital_rings": ("Two views. One floating world.", "Relax your eyes through the screen to merge the center views.",
                      "Parallel eye cameras; bounded off-axis disparity; identical scene time."),
    "helix": ("Can you see the spiral in depth?", "Relax your eyes through the screen to merge the center views.",
              "Parallel eye cameras; bounded off-axis disparity; identical scene time."),
    "constellation": ("A galaxy between the two images.", "Relax your eyes through the screen to merge the center views.",
                      "Parallel eye cameras; bounded off-axis disparity; identical scene time."),
    "motion_form": ("The shape lives in the movement.", "Watch it move, then pause. Can you find the shape?",
                    "Equal noise distributions inside and outside; opposite coherent motion."),
    "infinite_regress": ("Are the patches moving diagonally?", "Keep looking at the center dot.",
                         "Patch centers travel vertically; internal carriers drift horizontally."),
    "footsteps": ("Do these blocks move at the same speed?", "Watch as the stripes fade.",
                  "Both blocks share exactly one trajectory; contrast context changes."),
    "munker_white": ("These bars have exactly the same color.", "Watch the surrounding stripes disappear.",
                     "Target RGB stays constant; only the surrounding grating fades."),
    "muller_lyer": ("Which line is longer?", "Watch the arrowheads disappear.",
                   "Both shafts have exactly equal endpoints and length."),
    "afterimage": ("Keep looking at the center dot.", "Stay on the dot when the color turns gray.",
                   "Long fixed chromatic adaptor; achromatic test; continuous fixation point."),
    "troxler": ("Can the colors fade from your view?", "Keep a relaxed, steady gaze on the center dot.",
                "Peripheral low contrast patches remain physically unchanged for the whole clip."),
    "cafe_wall": ("Are the horizontal lines parallel?", "Watch the tiles fade to check the straight lines.",
                  "Every mortar line is horizontal; alternating rows have offset tiles."),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=True).encode()).hexdigest()


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{label}: expected {sorted(keys)}")


def default_accounts():
    # Local content routing only; a handle is not a connected publishing account.
    return dict(version=1, accounts=[
        dict(id="opticpop", handle="@opticpop", style="reversible_depth"),
        dict(id="unassigned_hidden_shape", handle="", style="hidden_stereogram"),
        dict(id="spiralium_", handle="@spiralium_", style="binocular_worlds"),
        dict(id="hypnotorium", handle="@hypnotorium", style="motion_paradox"),
        dict(id="trustyoureyes_", handle="@trustyoureyes_", style="perception_lab"),
    ])


def validate_accounts(value):
    exact(value, ("version", "accounts"), "accounts")
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("unsupported account config")
    rows = value["accounts"]
    if not isinstance(rows, list) or len(rows) != 5:
        raise ValueError("exactly five account profiles are required")
    ids, styles, handles = set(), set(), set()
    for row in rows:
        exact(row, ("id", "handle", "style"), "account")
        if (not isinstance(row["id"], str) or not row["id"] or len(row["id"]) > 50
                or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_" for c in row["id"])):
            raise ValueError("account id must use lowercase letters, digits or underscore")
        if not isinstance(row["handle"], str) or (row["handle"] and
            (not row["handle"].startswith("@") or len(row["handle"]) > 31 or
             any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_." for c in row["handle"][1:].lower())
             or len(row["handle"]) == 1)):
            raise ValueError("invalid handle")
        if not isinstance(row["style"], str) or row["style"] not in STYLES:
            raise ValueError("unknown account style")
        if row["id"] in ids or row["style"] in styles or (row["handle"] and row["handle"].lower() in handles):
            raise ValueError("accounts, handles and styles must be unique")
        ids.add(row["id"]); styles.add(row["style"])
        if row["handle"]:
            handles.add(row["handle"].lower())
    return value


def validate_account(row):
    # Validate one profile using five synthetic, noncolliding siblings.
    if not isinstance(row, dict) or not isinstance(row.get("style"), str) or row["style"] not in STYLES:
        raise ValueError("invalid account style")
    siblings = [dict(id=f"validation_{i}", handle="", style=s) for i, s in enumerate(STYLES) if s != row["style"]]
    for sibling in siblings:
        if sibling["id"] == row.get("id"):
            sibling["id"] += "_sibling"
    validate_accounts(dict(version=1, accounts=[row]+siblings))
    return row


def parameters_for(mode):
    if mode == "brainrot_spin":
        from brainrot import CHARACTERS, TILTS
        from brainrot import PAIRS, DUO_TILT, DUO_TURNS
        return [dict(character=c, tilt=tilt, turns=turns)
                for c, tilt, turns in itertools.product(CHARACTERS, TILTS, (2, 3))]+[
                dict(character=a, partner=b, tilt=DUO_TILT, turns=DUO_TURNS) for a, b in PAIRS]
    if mode == "bistable_spin":
        from bistable_spin import SHAPES, TILTS
        return [dict(shape=shape, tilt=tilt, turns=turns)
                for shape, tilt, turns in itertools.product(SHAPES, TILTS, (2, 3))]
    if mode == "tilted_pair":
        return [dict(subjects=list(p), layout=layout, tilt=tilt, turns=turns)
                for p in itertools.combinations(PAIR_SUBJECTS, 2)
                for layout, tilt, turns in itertools.product(("orbit", "coaxial"), (0, 1, 2), (1, -1))]
    if mode == "hidden_relief":
        return [dict(subject=s, relief=relief, repeat=repeat) for s, relief, repeat in
                itertools.product(SUBJECTS, (0.10, 0.15), (0.13, 0.16))]
    if mode in MODES["binocular_worlds"]:
        return [dict(complexity=n, eye_separation=e, view="parallel")
                for n, e in itertools.product((3, 4, 5, 6), (0.08, 0.12))]
    if mode == "motion_form":
        return [dict(subject=s, direction=d, dot_size=z)
                for s, d, z in itertools.product(SUBJECTS, (-1, 1), (2, 3, 4))]
    if mode == "infinite_regress":
        return [dict(columns=n, carrier=d, cycles=c)
                for n, d, c in itertools.product((3, 4, 5), (-1, 1), (1, 2))]
    if mode == "footsteps":
        return [dict(stripes=n, axis=a, cycles=c)
                for n, a, c in itertools.product((12, 16, 20), ("horizontal", "vertical"), (1, 2))]
    if mode == "munker_white":
        return [dict(stripes=n, target=v) for n, v in itertools.product((18, 24, 30), (100, 128, 156))]
    if mode == "muller_lyer":
        return [dict(wing_angle=a, wing_length=l) for a, l in itertools.product((25, 35, 45), (0.12, 0.17))]
    if mode == "afterimage":
        return [dict(subject=s, segments=n) for s, n in itertools.product(SUBJECTS, (3, 5, 7))]
    if mode == "troxler":
        return [dict(patches=n, contrast=c) for n, c in itertools.product((8, 12, 16), (0.15, 0.23))]
    if mode == "cafe_wall":
        return [dict(columns=n, offset=o) for n, o in itertools.product((5, 7, 9), (0.35, 0.5, 0.65))]
    raise ValueError("unsupported mode")


def structural_key(style, mode, parameters):
    # A new seed, palette, caption or account is not a new concept.
    return digest(dict(style=style, mode=mode, parameters=parameters))


def validate_brief(b):
    exact(b, ("kind", "version", "id", "account", "style", "mode", "seed", "palette", "parameters",
              "render", "caption", "evaluation", "reference", "local_only"), "brief")
    if b["kind"] != "five_style_production_brief" or type(b["version"]) is not int or b["version"] != 1 or b["local_only"] is not True:
        raise ValueError("brief must be version 1 and local_only=true")
    style, mode, p = b["style"], b["mode"], b["parameters"]
    if not isinstance(style, str) or style not in STYLES or not isinstance(mode, str) or mode not in MODES[style]:
        raise ValueError("mode does not belong to style")
    if not isinstance(p, dict) or p not in parameters_for(mode):
        raise ValueError("unsupported or unsafe parameters")
    # Equality alone accepts booleans as numbers; require canonical JSON types too.
    if not any(digest(p) == digest(candidate) for candidate in parameters_for(mode)):
        raise ValueError("incorrect parameter types")
    if b["palette"] not in PALETTES or type(b["seed"]) is not int or not 0 <= b["seed"] < 1_000_000:
        raise ValueError("invalid palette or seed")
    exact(b["account"], ("id", "handle", "style"), "brief account")
    # Reuse full account string validation without weakening the five-profile requirement.
    if b["account"]["style"] != style:
        raise ValueError("account cannot render another account's style")
    validate_account(b["account"])
    if b["render"] != dict(width=1080, height=1920, fps=30, seconds=24 if mode in ("afterimage", "troxler") else 15):
        raise ValueError("invalid production render settings")
    if digest(b["render"]) != digest(dict(width=1080, height=1920, fps=30, seconds=24 if mode in ("afterimage", "troxler") else 15)):
        raise ValueError("invalid render types")
    if b["caption"] != caption(mode, p):
        raise ValueError("caption must retain the viewing instruction and factual control")
    if b["evaluation"] != evaluate(mode, p):
        raise ValueError("invalid evaluation")
    if b["reference"] != REFERENCES[style]:
        raise ValueError("invalid mechanism reference")
    if b["id"] != structural_key(style, mode, p)[:16]:
        raise ValueError("brief identity mismatch")
    return b


def caption(mode, parameters=None):
    hook, instruction, control = COPY[mode]
    if mode == "bistable_spin" and parameters:
        hook = SPIN_HOOKS[parameters["shape"]]
    if mode == "brainrot_spin" and parameters:
        from brainrot import hook as brainrot_hook
        hook = brainrot_hook(parameters["character"], parameters.get("partner"))
    return dict(hook=hook, instruction=instruction, physical_control=control,
        full_caption=f"{hook}\n\n{instruction}\n\n#opticalillusion #perception #generativeart",
        perception_claim="May be perceived differently by different viewers; human review required.")


def evaluate(mode, parameters=None):
    # Transparent engineering rubric. This is not a prediction of views or virality.
    viewing = 12 if mode in ("hidden_relief", "orbital_rings", "helix", "constellation") else 18
    if mode in ("afterimage", "troxler"):
        viewing = 10
    reasons = ["Existing Python geometry or bounded procedural renderer; no external assets.",
               COPY[mode][2], "Perceptual strength remains subject to human review."]
    p = parameters or {}
    if mode == "motion_form" and p.get("dot_size") == 2:
        viewing -= 2
        reasons.append("Fine noise is more vulnerable to platform compression.")
    if mode in MODES["binocular_worlds"] and p.get("complexity", 0) > 4:
        viewing -= 2
        reasons.append("Dense structure can make binocular fusion harder.")
    if mode == "hidden_relief" and p.get("relief") == .10:
        viewing -= 1
        reasons.append("Shallower disparity offers a subtler depth cue.")
    return dict(feasibility=25, mechanism_control=25, viewing_accessibility=viewing,
                variation=15, originality=10, total=75+viewing,
                status="renderable_needs_human_review", blender_required=False,
                rubric="25 feasibility + 25 physical control + 20 accessibility + 15 variation + 15 originality",
                reasons=reasons,
                limitation="Original procedural analogue; no copied reference artwork; no audience-performance prediction.")


def make_brief(account, mode, parameters, seed):
    style = account["style"]
    b = dict(kind="five_style_production_brief", version=1,
        id=structural_key(style, mode, parameters)[:16], account=copy.deepcopy(account),
        style=style, mode=mode, seed=seed, palette=PALETTES[seed % 3],
        parameters=copy.deepcopy(parameters),
        render=dict(width=1080, height=1920, fps=30, seconds=24 if mode in ("afterimage", "troxler") else 15),
        caption=caption(mode, parameters), evaluation=evaluate(mode, parameters), reference=REFERENCES[style], local_only=True)
    return validate_brief(b)


def plan(accounts, seed=42, per_account=3, used=()):
    validate_accounts(accounts)
    if type(seed) is not int or not 0 <= seed < 1_000_000 or type(per_account) is not int or not 1 <= per_account <= 100:
        raise ValueError("seed 0-999999; per_account 1-100")
    seen, briefs = set(used), []
    for i, account in enumerate(accounts["accounts"]):
        pools = []
        for j, mode in enumerate(MODES[account["style"]]):
            rows = parameters_for(mode)
            random.Random(seed+i*100+j).shuffle(rows)
            rows.sort(key=lambda p: -evaluate(mode, p)["total"])
            pools.append((mode, rows))
        # Round-robin modes first. Rank within a mode, so a fixation mode isn't starved forever.
        count = 0
        for row_index in range(max(len(rows) for _, rows in pools)):
            for mode, rows in pools:
                if row_index >= len(rows) or count == per_account:
                    continue
                p = rows[row_index]
                key = structural_key(account["style"], mode, p)
                if key in seen:
                    continue
                briefs.append(make_brief(account, mode, p, (seed+i*101+count) % 1_000_000))
                seen.add(key); count += 1
            if count == per_account:
                break
        if count != per_account:
            raise ValueError(f"structural catalogue exhausted for {account['id']}; add geometry rather than recycle colors")
    return dict(kind="five_style_plan", version=1, local_only=True, seed=seed,
                account_count=5, selection="mode coverage then deterministic variation; evaluation stored per brief",
                briefs=briefs)


def ranking(accounts, seed=42, used=()):
    validate_accounts(accounts)
    used = set(used)
    groups = []
    for a in accounts["accounts"]:
        rows = []
        for mode in MODES[a["style"]]:
            for p in parameters_for(mode):
                key = structural_key(a["style"], mode, p)
                rows.append(dict(id=key[:16], mode=mode, parameters=p,
                    evaluation=evaluate(mode, p), eligible=key not in used))
        random.Random(seed).shuffle(rows)
        rows.sort(key=lambda row: (not row["eligible"], -row["evaluation"]["total"]))
        groups.append(dict(account=a, candidate_count=len(rows), eligible_count=sum(r["eligible"] for r in rows),
                           ranked_candidates=rows))
    return dict(kind="five_style_candidate_ranking", version=1, accounts=groups,
                interpretation="Engineering heuristics, not learned scores or predicted performance. Plans reserve mode coverage before ranking within each mode.")


def main():
    ap = argparse.ArgumentParser(description="Five distinct account styles; local files only")
    commands = ap.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init"); p.add_argument("--out", required=True)
    p = commands.add_parser("plan"); p.add_argument("--accounts", required=True)
    p.add_argument("--seed", type=int, default=42); p.add_argument("--per-account", type=int, default=3)
    p.add_argument("--history"); p.add_argument("--out", required=True)
    p = commands.add_parser("render"); p.add_argument("--plan", required=True)
    p.add_argument("--out", required=True); p.add_argument("--history", required=True)
    p.add_argument("--preview", action="store_true"); p.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()
    if a.command == "render":
        from five_style_render import render_plan
        print(json.dumps(render_plan(a.plan, a.out, a.history, a.preview, a.ffmpeg), ensure_ascii=True))
        return
    target = Path(a.out)
    if target.exists():
        ap.error("choose a new output file")
    value = default_accounts()
    if a.command == "plan":
        used = []
        if a.history:
            from five_style_render import load_history
            used = [e["key"] for e in load_history(a.history)["entries"] if e["quality"] == "full"]
        config = json.loads(Path(a.accounts).read_text(encoding="utf-8-sig"))
        value = plan(config, a.seed, a.per_account, used)
        rank_target = target.with_name(target.stem+"_ranking.json")
        if rank_target.exists():
            ap.error("ranking output already exists")
        rank_target.parent.mkdir(parents=True, exist_ok=True)
        rank_target.write_text(json.dumps(ranking(config, a.seed, used), ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(str(target.resolve()))


if __name__ == "__main__":
    main()
