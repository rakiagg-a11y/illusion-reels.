"""Month timing trial: give every plan slot its own video, then render a day.

  python3 trial_production.py allocate --plan plan.json --history H --out allocation.json
  python3 trial_production.py render --allocation allocation.json --day 1 --history H --out DIR

allocate gives each slot one brief that is not in the history or elsewhere in
the month. Within a style it first uses every distinct work (a shape pair, a
sphere build, a character or a pair of characters) once, and only then a
second view of the same work. For trustyoureyes_ a character appears as a
single figure at most once, and every pair at most once. Slots it cannot fill
yet stay empty; running allocate again keeps every existing assignment.

render renders a day's slots, adds the burned-music copy for YouTube and
Facebook, and writes that day's queue (checksums, format checks, captions).
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile

import account_studio as studio
import five_styles as legacy
from five_style_render import atomic_json
import trial_captions

TRUST = "trustyoureyes_"


def _seed(slot_id):
    return int(hashlib.sha256(slot_id.encode()).hexdigest(), 16) % 1_000_000


def _key(account, mode, p):
    if account == TRUST:
        return legacy.structural_key("perception_lab", mode, p)
    return studio.structural_key(mode, p)


def _work(mode, p):
    """What makes two videos the same piece of work, ignoring view and speed."""
    if mode == "brainrot_spin":
        return frozenset((p["character"], p.get("partner")))
    if mode == "tilted_pair":
        return tuple(p["subjects"]), p["layout"]
    if mode == "depth_flip":
        return p["ribs"], p["rings"], p["opening"]
    return json.dumps(p, sort_keys=True)


def _brief(account, mode, p, seed):
    if account == TRUST:
        profile = next(a for a in legacy.default_accounts()["accounts"] if a["id"] == account)
        return legacy.make_brief(profile, mode, p, seed)
    return studio.make_brief(account, mode, p, seed)


def _catalogue(account, mode):
    return legacy.parameters_for(mode) if account == TRUST else studio.parameters_for(mode)


def allocate(plan, history, previous=None):
    used = {e["key"] for e in history["entries"]}
    rng = random.Random(plan["seed"])
    slots = previous["slots"] if previous else {}
    done_works = {}
    for a in slots.values():
        if a.get("brief"):
            used.add(_key(a["account"], a["mode"], a["brief"]["parameters"]))
            done_works.setdefault((a["account"], a["mode"]), []).append(_work(a["mode"], a["brief"]["parameters"]))
    groups = {}
    for row in plan["slots"]:
        if row["slot_id"] not in slots or not slots[row["slot_id"]].get("brief"):
            groups.setdefault((row["account"], row["style"]), []).append(row)
    for (account, mode), rows in groups.items():
        rows.sort(key=lambda r: r["scheduled_at_utc"])
        # Works already posted (or already in this month) are used last, if ever.
        spent = {_work(mode, p) for p in _catalogue(account, mode) if _key(account, mode, p) in used}
        spent |= set(done_works.get((account, mode), []))
        if mode == "brainrot_spin":
            picks = _brainrot_order(rows, used, spent, rng)
        else:
            fresh, seconds = {}, []
            candidates = [p for p in _catalogue(account, mode) if _key(account, mode, p) not in used]
            rng.shuffle(candidates)
            for p in candidates:
                w = _work(mode, p)
                (seconds.append(p) if w in fresh or w in spent else fresh.setdefault(w, p))
            picks = list(fresh.values())+seconds
        for row, p in zip(rows, picks+[None]*len(rows)):
            entry = dict(account=row["account"], mode=mode, local_date=row["local_date"],
                         local_time=row["local_time"], day=row["day"])
            if p is not None:
                entry["brief"] = _brief(account, mode, p, _seed(row["slot_id"]))
                entry["caption"] = trial_captions.caption(account, mode, p)
                used.add(_key(account, mode, p))
            slots[row["slot_id"]] = entry
    filled = sum(bool(a.get("brief")) for a in slots.values())
    return dict(kind="trial_allocation", version=1, plan_start=plan["start_date"],
                slots=slots, filled=filled, empty=len(slots)-filled)


def _brainrot_order(rows, used, spent, rng):
    import brainrot
    singles = {}
    for p in legacy.parameters_for("brainrot_spin"):
        if "partner" not in p and _key(TRUST, "brainrot_spin", p) not in used:
            singles.setdefault(p["character"], []).append(p)
    single_pool = [rng.choice(v) for c, v in singles.items() if frozenset((c, None)) not in spent]
    duo_pool = [p for p in legacy.parameters_for("brainrot_spin")
                if "partner" in p and _work("brainrot_spin", p) not in spent and _key(TRUST, "brainrot_spin", p) not in used]
    rng.shuffle(single_pool)
    rng.shuffle(duo_pool)
    # One single figure a day (at a random one of that day's slots) while
    # singles last; pairs fill the other slots.
    days = {}
    for row in rows:
        days.setdefault(row["day"], []).append(row["slot_id"])
    solo = {rng.choice(ids) for ids in days.values()}
    picks, by_day = [], {}
    for row in rows:
        if not single_pool and not duo_pool:
            break
        want_single = single_pool and (row["slot_id"] in solo or not duo_pool)
        pool = single_pool if want_single else duo_pool
        today = by_day.setdefault(row["day"], set())
        # Avoid showing the same character twice on one day when there is a choice.
        j = next((k for k, p in enumerate(pool) if not ({p["character"], p.get("partner")} & today)), 0)
        p = pool.pop(j)
        today |= {p["character"], p.get("partner")}
        picks.append(p)
    return picks


def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    info = json.loads(out.stdout)
    s = info["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return dict(width=s["width"], height=s["height"], fps=round(num/den, 3), seconds=round(float(info["format"]["duration"]), 3))


def _render_slot(job):
    slot_id, entry, history, day_dir = job
    import music
    day_dir = Path(day_dir)
    target, yt = day_dir/f"{slot_id}.mp4", day_dir/f"{slot_id}_yt.mp4"
    brief = entry["brief"]
    new_entries = []
    if not target.is_file():
        work = Path(tempfile.mkdtemp(prefix=slot_id+"_", dir=day_dir))
        shutil.rmtree(work)
        # The history lock is held for a whole render, so each worker checks and
        # records against its own copy; render_day merges the new entries after.
        private = day_dir/f".history_{slot_id}.json"
        shutil.copyfile(history, private)
        before = len(json.loads(private.read_text(encoding="utf-8"))["entries"])
        if entry["account"] == TRUST:
            from five_style_render import render_one
            render_one(brief, work, private)
            video = work/(brief["account"]["id"]+"_"+brief["id"]+".mp4")
        else:
            studio.render_brief(brief, work, private)
            video = work/(brief["account"]+"_"+brief["id"]+".mp4")
        new_entries = json.loads(private.read_text(encoding="utf-8"))["entries"][before:]
        private.unlink()
        shutil.move(str(video.with_suffix(".png")), day_dir/f"{slot_id}.png")
        shutil.move(str(video.with_suffix(".json")), day_dir/f"{slot_id}.json")
        shutil.move(str(video), target)
        shutil.rmtree(work)
        for e in new_entries:
            e["output"] = str(target.resolve())
    info = _probe(target)
    if not yt.is_file():
        wav = day_dir/f"{slot_id}.wav"
        music.track_for(_seed(slot_id), str(wav), info["seconds"])
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(target), "-i", str(wav), "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", str(yt)], check=True)
        wav.unlink()
    checks = dict(size=(info["width"], info["height"]) == (1080, 1920), fps=info["fps"] == 30,
                  duration=abs(info["seconds"]-brief["render"]["seconds"]) < .2)
    return dict(slot_id=slot_id, account=entry["account"], style=entry["mode"], content_id=brief["id"],
                parameters=brief["parameters"],
                asset_path=str(target), sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                yt_asset_path=str(yt), yt_sha256=hashlib.sha256(yt.read_bytes()).hexdigest(),
                **info, qa=dict(automatic=checks, passed=all(checks.values()), visual="pending"),
                local_date=entry["local_date"], local_time=entry["local_time"], caption=entry["caption"],
                history_entries=new_entries)


def render_day(allocation, day, history, out, workers=4):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                            cwd=Path(__file__).resolve().parent).stdout.strip()
    jobs = [(sid, a, str(history), str(out)) for sid, a in allocation["slots"].items()
            if a["day"] == day and a.get("brief")]
    # The slowest generator first, so the pool finishes together.
    jobs.sort(key=lambda j: j[1]["mode"] != "tilted_pair")
    with ProcessPoolExecutor(workers) as pool:
        rows = list(pool.map(_render_slot, jobs))
    from five_style_render import history_lock, load_history
    with history_lock(history):
        shared = load_history(history)
        seen = {(e["key"], e["quality"]) for e in shared["entries"]}
        for r in rows:
            shared["entries"] += [e for e in r.pop("history_entries") if (e["key"], e["quality"]) not in seen]
        atomic_json(history, shared)
    for r in rows:
        r["generator_commit"] = commit
    rows.sort(key=lambda r: (r["local_time"], r["account"]))
    queue = dict(kind="trial_day_queue", version=1, day=day, slots=rows,
                 missing=[sid for sid, a in allocation["slots"].items() if a["day"] == day and not a.get("brief")])
    atomic_json(out/"queue.json", queue)
    return queue


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("allocate", "render"))
    ap.add_argument("--plan")
    ap.add_argument("--allocation")
    ap.add_argument("--history", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--day", type=int)
    a = ap.parse_args()
    from five_style_render import load_history
    if a.command == "allocate":
        plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
        previous = json.loads(Path(a.out).read_text(encoding="utf-8")) if Path(a.out).is_file() else None
        result = allocate(plan, load_history(a.history), previous)
        atomic_json(a.out, result)
        print(json.dumps(dict(filled=result["filled"], empty=result["empty"])))
    else:
        allocation = json.loads(Path(a.allocation).read_text(encoding="utf-8"))
        queue = render_day(allocation, a.day, a.history, a.out)
        print(json.dumps(dict(rendered=len(queue["slots"]), failed_checks=[r["slot_id"] for r in queue["slots"] if not r["qa"]["passed"]],
                              missing=queue["missing"])))


if __name__ == "__main__":
    main()
