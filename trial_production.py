"""Month timing trial: give every plan slot its own video, then render a day.

  python3 trial_production.py allocate --plan plan.json --history H --out allocation.json
  python3 trial_production.py render --allocation allocation.json --day 1 --history H --out DIR [--accounts A ...]
  python3 trial_production.py capacity --plan plan.json --history H [--allocation allocation.json] [--extra-history F ...]
  python3 trial_production.py review --day-dir DIR --slot S --verdict approved --reviewer NAME --evidence PATH

allocate gives each slot one brief whose work is not in the history and not
used by any other slot of the month. A work is what the viewer sees (a shape
pair, a sphere build, a character or a pair of characters); a new view angle,
speed, seed or colour of the same work is not a new video, so it is never used
to fill a slot. For trustyoureyes_ a character appears as a single figure at
most once, and every pair at most once. Slots it cannot fill stay empty.
An earlier allocation is kept only if it was made for this plan (same slot ids,
accounts, styles, dates, times, time zone and networks); otherwise it is refused.

render renders a day's slots and adds the burned-music copy for YouTube and
Facebook. Each video gets a sidecar <slot>.render.json (checksum, brief digest,
history entries) before it is moved into place, so a later run can verify an
existing file against its brief and checksum and still merge its history if
an earlier run died. Everything is rendered and hashed on local disk, and a
file is kept in the day folder (which can be a network mount) only once it
reads back with the same checksum; the music copy is also checked (picture,
length, audio track) before it takes its final name. queue.json holds render
facts only; scheduling state lives in posts.json (trial_schedule.py)
and visual review in review.json, which a re-render never rewrites.

capacity reports, per account and style, how many works the catalogue has, how
many are already used by renders made before the trial, and how many slots the
month needs.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import time

import account_studio as studio
import five_styles as legacy
from five_style_render import atomic_json, history_lock, load_history
import trial_captions
from trial_records import read_json, sha256_file, update_json

TRUST = "trustyoureyes_"
IDENTITY = ("account", "mode", "day", "local_date", "local_time", "timezone", "scheduled_at_utc", "networks")


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


def _brief_digest(account, brief):
    return legacy.digest(brief) if account == TRUST else studio.digest(brief)


def _catalogue(account, mode):
    return legacy.parameters_for(mode) if account == TRUST else studio.parameters_for(mode)


def _identity(plan, row):
    return dict(account=row["account"], mode=row["style"], day=row["day"], local_date=row["local_date"],
                local_time=row["local_time"], timezone=plan["timezone"],
                scheduled_at_utc=row["scheduled_at_utc"], networks=list(row["networks"]))


def plan_fingerprint(plan):
    rows = {r["slot_id"]: _identity(plan, r) for r in plan["slots"]}
    blob = json.dumps(dict(start_date=plan["start_date"], slots=rows), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def check_previous(plan, previous):
    """A copy of an earlier allocation, or ValueError if it was made for another plan."""
    if previous.get("plan_fingerprint") not in (None, plan_fingerprint(plan)):
        raise ValueError("the allocation was made for a different plan")
    rows = {r["slot_id"]: _identity(plan, r) for r in plan["slots"]}
    if set(previous["slots"]) != set(rows):
        raise ValueError("the allocation's slot ids do not match the plan")
    for slot_id, want in rows.items():
        have = previous["slots"][slot_id]
        # Allocations from before version 2 did not store the UTC time, zone or networks.
        wrong = [k for k in IDENTITY if have.get(k, want[k]) != want[k]]
        wrong += [k for k in IDENTITY[:5] if k not in have]
        if wrong:
            raise ValueError(f"{slot_id}: allocation does not match the plan ({', '.join(wrong)})")
    return copy.deepcopy(previous)


def allocate(plan, history, previous=None):
    slots = check_previous(plan, previous)["slots"] if previous else {}
    used = {e["key"] for e in history["entries"]}
    rng = random.Random(plan["seed"])
    done_works = {}
    for a in slots.values():
        if a.get("brief"):
            used.add(_key(a["account"], a["mode"], a["brief"]["parameters"]))
            done_works.setdefault((a["account"], a["mode"]), []).append(_work(a["mode"], a["brief"]["parameters"]))
    groups = {}
    for row in plan["slots"]:
        entry = slots.setdefault(row["slot_id"], {})
        entry.update(_identity(plan, row))
        if not entry.get("brief"):
            groups.setdefault((row["account"], row["style"]), []).append(row)
    for (account, mode), rows in groups.items():
        rows.sort(key=lambda r: r["scheduled_at_utc"])
        # A work already rendered (before or during the month) is never used again.
        spent = {_work(mode, p) for p in _catalogue(account, mode) if _key(account, mode, p) in used}
        spent |= set(done_works.get((account, mode), []))
        if mode == "brainrot_spin":
            picks = _brainrot_order(rows, spent, rng)
        else:
            candidates = [p for p in _catalogue(account, mode) if _work(mode, p) not in spent]
            rng.shuffle(candidates)
            fresh = {}
            for p in candidates:
                fresh.setdefault(_work(mode, p), p)
            picks = list(fresh.values())
        for row, p in zip(rows, picks):
            entry = slots[row["slot_id"]]
            entry["brief"] = _brief(account, mode, p, _seed(row["slot_id"]))
            entry["caption"] = trial_captions.caption(account, mode, p)
            used.add(_key(account, mode, p))
    filled = sum(bool(a.get("brief")) for a in slots.values())
    return dict(kind="trial_allocation", version=2, plan_fingerprint=plan_fingerprint(plan),
                plan_start=plan["start_date"], timezone=plan["timezone"],
                slots=slots, filled=filled, empty=len(slots)-filled)


def _brainrot_order(rows, spent, rng):
    singles = {}
    duo_pool = []
    for p in legacy.parameters_for("brainrot_spin"):
        if _work("brainrot_spin", p) in spent:
            continue
        if "partner" in p:
            duo_pool.append(p)
        else:
            singles.setdefault(p["character"], []).append(p)
    single_pool = [rng.choice(v) for v in singles.values()]
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


def capacity(plan, history, allocation=None, extra=()):
    """Works per account and style, after removing everything rendered before the trial."""
    trial_dir = "/reels/trial/"
    before = {e["key"] for e in history["entries"] if trial_dir not in e["output"].replace("\\", "/")}
    for h in extra:
        before |= {e["key"] for e in h.get("entries", []) if "key" in e}
    need = {}
    for row in plan["slots"]:
        need[(row["account"], row["style"])] = need.get((row["account"], row["style"]), 0)+1
    report = []
    for (account, mode), slots in need.items():
        catalogue = _catalogue(account, mode)
        works = {_work(mode, p) for p in catalogue}
        spent = {_work(mode, p) for p in catalogue if _key(account, mode, p) in before}
        row = dict(account=account, style=mode, slots=slots, catalogue_briefs=len(catalogue), works=len(works),
                   works_rendered_before_trial=len(spent), works_available=len(works-spent),
                   spare=len(works-spent)-slots)
        if mode == "brainrot_spin":
            row["singles_available"] = sum(1 for w in works-spent if None in w)
            row["pairs_available"] = sum(1 for w in works-spent if None not in w)
        if allocation:
            mine = [a for a in allocation["slots"].values() if (a["account"], a["mode"]) == (account, mode)]
            assigned = [_work(mode, a["brief"]["parameters"]) for a in mine if a.get("brief")]
            row.update(assigned=len(assigned), assigned_distinct=len(set(assigned)),
                       assigned_rendered_before_trial=sum(w in spent for w in assigned),
                       empty_slots=len(mine)-len(assigned))
        report.append(row)
    return report


def _probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True)
    info = json.loads(out.stdout)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    audio = [s["codec_name"] for s in info["streams"] if s["codec_type"] == "audio"]
    num, den = map(int, video["r_frame_rate"].split("/"))
    return dict(width=video["width"], height=video["height"], fps=round(num/den, 3),
                seconds=round(float(info["format"]["duration"]), 3), audio=audio[0] if audio else None)


def _record_for(target, slot_id, entry, history):
    """The render record of an existing video, checked against this slot's brief and the file."""
    sidecar = target.with_name(slot_id+".render.json")
    key = _key(entry["account"], entry["mode"], entry["brief"]["parameters"])
    if sidecar.is_file():
        record = read_json(sidecar)
    else:
        # Videos made before sidecars existed are known from the shared history.
        found = [e for e in load_history(history)["entries"]
                 if e["quality"] == "full" and Path(e["output"]).resolve() == target.resolve()]
        if len(found) != 1:
            raise ValueError(f"{target.name} exists but no render record names it; move it aside and render again")
        record = dict(slot_id=slot_id, key=found[0]["key"], brief_digest=found[0]["brief_digest"],
                      sha256=found[0]["sha256"], history_entries=found)
        atomic_json(sidecar, record)
    if record["key"] != key or record["brief_digest"] != _brief_digest(entry["account"], entry["brief"]):
        raise ValueError(f"{target.name} was rendered from a different brief")
    if sha256_file(target) != record["sha256"]:
        raise ValueError(f"{target.name} changed after it was rendered")
    return record


def _scratch(slot_id):
    """A fresh local folder for one slot's work; leftovers of a run that died are discarded."""
    scratch = Path(tempfile.gettempdir())/"trial_render"/slot_id
    shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    return scratch


def _place(source, target, digest, tries=12):
    """Copy a finished local file to its final name and read it back.

    The day folder can be a network mount whose writes show up late, so files
    are rendered and hashed on local disk and only checked copies are kept."""
    partial = target.with_name(target.stem+".partial"+target.suffix)
    shutil.copyfile(source, partial)
    os.replace(partial, target)
    for _ in range(tries):
        if sha256_file(target) == digest:
            return
        time.sleep(5)
    raise ValueError(f"{target.name} does not read back as the rendered file")


def _render_new(slot_id, entry, history, day_dir, target):
    brief = entry["brief"]
    scratch = _scratch(slot_id)
    work, private = scratch/"render", scratch/"history.json"
    # Each worker renders against its own snapshot of the shared history (the
    # renderers hold the history lock for a whole render); render_day merges
    # the new entries and refuses a concept someone else recorded meanwhile.
    atomic_json(private, load_history(history))
    before = len(load_history(private)["entries"])
    if entry["account"] == TRUST:
        from five_style_render import render_one
        render_one(brief, work, private)
        video = work/(brief["account"]["id"]+"_"+brief["id"]+".mp4")
    else:
        studio.render_brief(brief, work, private)
        video = work/(brief["account"]+"_"+brief["id"]+".mp4")
    entries = load_history(private)["entries"][before:]
    for e in entries:
        e["output"] = str(target.resolve())
    record = dict(slot_id=slot_id, key=_key(entry["account"], entry["mode"], brief["parameters"]),
                  brief_digest=_brief_digest(entry["account"], brief), sha256=sha256_file(video),
                  rendered_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  history_entries=entries)
    # The record goes down before the video takes its final name.
    atomic_json(day_dir/f"{slot_id}.render.json", record)
    shutil.copyfile(video.with_suffix(".png"), day_dir/f"{slot_id}.png")
    atomic_json(day_dir/f"{slot_id}.json", brief)
    _place(video, target, record["sha256"])
    shutil.rmtree(scratch)
    return record


def _music_copy(slot_id, target, info, record, day_dir):
    """The YouTube/Facebook copy with our own music, checked before it takes its final name."""
    import music
    yt = day_dir/f"{slot_id}_yt.mp4"
    if yt.is_file() and record.get("yt_sha256") == sha256_file(yt):
        return yt, record["yt_sha256"]
    scratch = _scratch(slot_id)
    wav, local = scratch/"music.wav", scratch/"yt.mp4"
    music.track_for(_seed(slot_id), str(wav), info["seconds"])
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(target), "-i", str(wav), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(local)], check=True)
    got = _probe(local)
    if (got["width"], got["height"], got["fps"]) != (info["width"], info["height"], info["fps"]) \
            or abs(got["seconds"]-info["seconds"]) > .2 or got["audio"] != "aac":
        raise ValueError(f"{slot_id}: music copy failed its check ({got})")
    digest = sha256_file(local)
    _place(local, yt, digest)
    shutil.rmtree(scratch)
    record["yt_sha256"] = digest
    atomic_json(day_dir/f"{slot_id}.render.json", record)
    return yt, digest


def _render_slot(job):
    slot_id, entry, history, day_dir = job
    day_dir = Path(day_dir)
    target = day_dir/f"{slot_id}.mp4"
    brief = entry["brief"]
    if target.is_file():
        record = _record_for(target, slot_id, entry, history)
        if not (day_dir/f"{slot_id}.json").is_file():
            atomic_json(day_dir/f"{slot_id}.json", brief)
    else:
        record = _render_new(slot_id, entry, history, day_dir, target)
    info = _probe(target)
    yt, yt_sha = _music_copy(slot_id, target, info, record, day_dir)
    yt_info = _probe(yt)
    checks = dict(size=(info["width"], info["height"]) == (1080, 1920), fps=info["fps"] == 30,
                  duration=abs(info["seconds"]-brief["render"]["seconds"]) < .2,
                  instagram_file_silent=info["audio"] is None,
                  music_copy_has_audio=yt_info["audio"] == "aac",
                  music_copy_duration=abs(yt_info["seconds"]-info["seconds"]) <= .2)
    return dict(slot_id=slot_id, **{k: entry[k] for k in IDENTITY if k in entry}, style=entry["mode"],
                content_id=brief["id"], parameters=brief["parameters"],
                brief_path=str(day_dir/f"{slot_id}.json"), brief_digest=record["brief_digest"],
                asset_path=str(target), sha256=record["sha256"], yt_asset_path=str(yt), yt_sha256=yt_sha,
                width=info["width"], height=info["height"], fps=info["fps"], seconds=info["seconds"],
                qa=dict(automatic=checks, passed=all(checks.values())),
                caption=entry["caption"], caption_template_digest=trial_captions.template_digest())


def merge_history(history, entries, wait=1800):
    """Add a slot's entries to the shared history; refuse a concept another render recorded meanwhile."""
    deadline = time.monotonic()+wait
    while True:
        try:
            with history_lock(history):
                shared = load_history(history)
                have = {(e["key"], e["quality"]): e for e in shared["entries"]}
                new = []
                for e in entries:
                    other = have.get((e["key"], e["quality"]))
                    if other is None:
                        new.append(e)
                    elif (other["sha256"], other["output"]) != (e["sha256"], e["output"]):
                        raise ValueError(f"{Path(e['output']).name}: the same concept was recorded by another render "
                                         f"({other['output']})")
                if new:
                    shared["entries"] += new
                    atomic_json(history, shared)
                return len(new)
        except ValueError as e:
            # The renderers hold the lock for a whole render; wait for it.
            if not str(e).startswith("history is locked") or time.monotonic() > deadline:
                raise
            time.sleep(5)


def _merge_recorded(history, day_dir, slot_id):
    """Merge a slot's sidecar into the history when its video is in place, even after a later failure."""
    sidecar, target = day_dir/f"{slot_id}.render.json", day_dir/f"{slot_id}.mp4"
    if sidecar.is_file() and target.is_file():
        record = read_json(sidecar)
        if sha256_file(target) == record["sha256"]:
            merge_history(history, record["history_entries"])


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          cwd=Path(__file__).resolve().parent).stdout.strip()


def render_day(allocation, day, history, out, workers=4, accounts=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    commit, dirty = _git("rev-parse", "HEAD"), bool(_git("status", "--porcelain", "--untracked-files=no"))
    # Production can be split by account; each side renders only its own slots.
    day_slots = [sid for sid, a in allocation["slots"].items()
                 if a["day"] == day and (accounts is None or a["account"] in accounts)]
    jobs = [(sid, allocation["slots"][sid], str(history), str(out)) for sid in day_slots
            if allocation["slots"][sid].get("brief")]
    # The slowest generator first, so the pool finishes together.
    jobs.sort(key=lambda j: j[1]["mode"] != "tilted_pair")
    rows, failed = [], []

    def finished(slot_id, result=None, error=None):
        try:
            _merge_recorded(Path(history), out, slot_id)
        except Exception as e:
            error = error or e
        if error is None:
            rows.append(result)
        else:
            failed.append(dict(slot_id=slot_id, error=f"{type(error).__name__}: {error}"))

    if workers:
        with ProcessPoolExecutor(workers) as pool:
            futures = {pool.submit(_render_slot, j): j[0] for j in jobs}
            for f in as_completed(futures):
                error = f.exception()
                finished(futures[f], None if error else f.result(), error)
    else:
        for j in jobs:
            try:
                finished(j[0], _render_slot(j))
            except Exception as e:
                finished(j[0], error=e)
    for r in rows:
        r.update(generator_commit=commit, generator_tree_dirty=dirty)
    rows.sort(key=lambda r: (r["local_time"], r["account"], r["slot_id"]))
    queue = dict(kind="trial_day_queue", version=2, day=day, plan_fingerprint=allocation.get("plan_fingerprint"),
                 accounts=sorted(accounts) if accounts else None,
                 local_date=allocation["slots"][day_slots[0]]["local_date"] if day_slots else None,
                 slots=rows, failed=sorted(failed, key=lambda f: f["slot_id"]),
                 missing=[sid for sid in day_slots if not allocation["slots"][sid].get("brief")])
    atomic_json(out/"queue.json", queue)
    return queue


def review(day_dir, slot_id, verdict, reviewer, evidence, note=""):
    """Record a visual review of one exact file (by checksum) in review.json."""
    day_dir = Path(day_dir)
    row = next((r for r in read_json(day_dir/"queue.json")["slots"] if r["slot_id"] == slot_id), None)
    if row is None:
        raise ValueError(f"{slot_id} is not in this day's queue")
    if sha256_file(row["asset_path"]) != row["sha256"] or sha256_file(row["yt_asset_path"]) != row["yt_sha256"]:
        raise ValueError(f"{slot_id}: files changed since the queue was written")
    result = dict(verdict=verdict, sha256=row["sha256"], yt_sha256=row["yt_sha256"], reviewer=reviewer,
                  evidence=evidence, note=note,
                  reviewed_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    update_json(day_dir/"review.json", lambda reviews: reviews.__setitem__(slot_id, result), {})
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("allocate", "render", "capacity", "review"))
    ap.add_argument("--plan")
    ap.add_argument("--allocation")
    ap.add_argument("--history")
    ap.add_argument("--extra-history", nargs="*", default=[])
    ap.add_argument("--out")
    ap.add_argument("--day", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--accounts", nargs="+", help="render only these accounts' slots")
    ap.add_argument("--day-dir")
    ap.add_argument("--slot", nargs="+")
    ap.add_argument("--verdict", choices=("approved", "rejected"))
    ap.add_argument("--reviewer")
    ap.add_argument("--evidence")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    if a.command == "review":
        for slot_id in a.slot:
            review(a.day_dir, slot_id, a.verdict, a.reviewer, a.evidence, a.note)
        print(json.dumps(dict(reviewed=a.slot, verdict=a.verdict)))
        return
    if a.command == "capacity":
        plan = read_json(a.plan)
        allocation = read_json(a.allocation) if a.allocation else None
        if allocation:
            check_previous(plan, allocation)
        extra = [read_json(f) for f in a.extra_history]
        print(json.dumps(capacity(plan, load_history(a.history), allocation, extra), indent=1))
        return
    if a.command == "allocate":
        plan = read_json(a.plan)
        previous = read_json(a.out) if Path(a.out).is_file() else None
        result = allocate(plan, load_history(a.history), previous)
        atomic_json(a.out, result)
        print(json.dumps(dict(filled=result["filled"], empty=result["empty"])))
        return
    queue = render_day(read_json(a.allocation), a.day, a.history, a.out, a.workers, a.accounts)
    print(json.dumps(dict(rendered=len(queue["slots"]),
                          failed_checks=[r["slot_id"] for r in queue["slots"] if not r["qa"]["passed"]],
                          failed=queue["failed"], missing=queue["missing"])))
    if queue["failed"] or queue["missing"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
