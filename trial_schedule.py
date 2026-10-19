"""Metricool posts for one trial day, and a durable record of what was scheduled.

  python3 trial_schedule.py payloads --day-dir DIR --allocation allocation.json --base RAW_URL_PREFIX --host-repo CLONE
  python3 trial_schedule.py sound --day-dir DIR --slot S [S ...] --audio-id ID --title T --artist A --source approved_list --check TEXT
  python3 trial_schedule.py record --day-dir DIR --slot S --network instagram --post-id ID [--replace]
  python3 trial_schedule.py fail --day-dir DIR --slot S --network youtube --error TEXT
  python3 trial_schedule.py live --day-dir DIR --slot S --network instagram --published ISO --network-post-id ID --url URL
  python3 trial_schedule.py observed --day-dir DIR --slot S --network instagram --age 72

Every video goes to Instagram, Facebook and YouTube as three separate posts, so
each network has its own post id and state and a failed one can be retried
alone. payloads prints only the posts that are ready and not scheduled yet; a
post is ready when its video passed the automatic checks and a visual review of
this exact file (by checksum), the hosted copy is the same file, the slot still
matches the allocation (account, style, brief, date, time, networks), the
caption is the one the approved template gives for this brief, and, for
Instagram, a checked library sound that is not on the blocklist is recorded for
the slot. Everything else is listed under blocked, with the reasons.

The publishing record is posts.json next to the day's queue. A render never
writes it, a post id once recorded is kept (record refuses to overwrite it
without --replace, and keeps the old one in the attempts), and payloads skips
every network that already has one. Nothing here talks to Metricool.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

import trial_captions
from trial_records import read_json, sha256_file, update_json

BRANDS = {"opticpop": 7443198, "hypnotorium": 7498748, "spiralium_": 7498862, "trustyoureyes_": 7498890}
BRAINROT_AUDIO = "24360627876895620"  # "La polizia noooo 😭", Rakia's pick for brainrot from the 2nd reel on
NETWORKS = ("instagram", "facebook", "youtube")
APPROVAL = "/mnt/project-files/experiment/timing-2026-10/caption_approval.json"
BLOCKLIST = "/mnt/project-files/production/sound_blocklist.json"
DONE = ("scheduled", "live")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _common(row, url):
    return dict(autoPublish=True, draft=False, descendants=[], firstCommentText="", hasNotReadNotes=False,
                media=[url], mediaAltText=[], shortener=False, smartLinkData=dict(ids=[]), text=row["caption"],
                publicationDate=dict(dateTime=f"{row['local_date']}T{row['local_time']}:00", timezone=row["timezone"]))


def _blob(repo, commit, path):
    """Git blob id of a hosted file, or None when the commit does not have it."""
    out = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{commit}:{path}"], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def _hash_object(path):
    return subprocess.run(["git", "hash-object", str(path)], capture_output=True, text=True, check=True).stdout.strip()


def _sound_problems(sound, blocklist):
    if not sound:
        return ["no checked Instagram sound recorded for this slot"]
    problems = []
    if not re.fullmatch(r"\d{6,}", str(sound.get("audio_id", ""))):
        problems.append(f"Instagram sound id {sound.get('audio_id')!r} is not a Metricool audio id")
    blocked = blocklist.get("blocked", [])
    if any(str(b.get("audioId")) == str(sound.get("audio_id")) or
           b.get("title", "").casefold() == str(sound.get("title", "")).casefold() for b in blocked):
        problems.append(f"sound {sound.get('title')!r} is on the blocklist")
    if not sound.get("check"):
        problems.append("the sound record does not say how its availability was checked")
    return problems


def _slot_problems(slot_id, row, entry, review, approval, plan_fingerprint):
    """Reasons a slot's video may not be posted on any network."""
    if row is None:
        return ["video not rendered (not in queue.json)"]
    problems = []
    if plan_fingerprint and row.get("plan_fingerprint", plan_fingerprint) != plan_fingerprint:
        problems.append("the queue was rendered for a different plan")
    for k in ("account", "local_date", "local_time", "timezone", "scheduled_at_utc", "networks"):
        if row.get(k) != entry.get(k):
            problems.append(f"{k} differs from the allocation ({row.get(k)!r} vs {entry.get(k)!r})")
    brief = entry.get("brief") or {}
    if (row.get("style"), row.get("content_id"), row.get("parameters")) != \
            (entry.get("mode"), brief.get("id"), brief.get("parameters")):
        problems.append("the video was rendered from a different brief than the allocation's")
    local = datetime.fromisoformat(entry["scheduled_at_utc"]).astimezone(ZoneInfo(entry["timezone"]))
    if (local.strftime("%Y-%m-%d"), local.strftime("%H:%M")) != (entry["local_date"], entry["local_time"]):
        problems.append("the local date and time do not match the UTC time")
    if not row["qa"]["passed"]:
        failed = [k for k, ok in row["qa"]["automatic"].items() if not ok]
        problems.append(f"automatic QA failed: {', '.join(failed)}")
    for path, digest in ((row["asset_path"], row["sha256"]), (row["yt_asset_path"], row["yt_sha256"])):
        if not Path(path).is_file() or sha256_file(path) != digest:
            problems.append(f"{Path(path).name} is missing or changed since rendering")
    if not review or review.get("verdict") != "approved":
        problems.append("no visual approval" if not review else f"visual review: {review.get('verdict')}")
    elif (review.get("sha256"), review.get("yt_sha256")) != (row["sha256"], row["yt_sha256"]):
        problems.append("the visual approval is for a different file")
    expected = trial_captions.caption(row["account"], entry["mode"], brief.get("parameters"))
    if row["caption"] != expected or entry.get("caption") != expected:
        problems.append("caption is not the approved template's text for this brief")
    digest = trial_captions.template_digest()
    if approval.get("template_digest") != digest or row.get("caption_template_digest") != digest:
        problems.append("caption templates differ from the approved version")
    return problems


def payloads(day_dir, allocation, base, host_repo, approval, blocklist):
    day_dir = Path(day_dir)
    queue = read_json(day_dir/"queue.json")
    reviews = read_json(day_dir/"review.json", {})
    sounds = read_json(day_dir/"sounds.json", {})
    posts = read_json(day_dir/"posts.json", {})
    commit = next((part for part in base.split("/") if re.fullmatch(r"[0-9a-f]{40}", part)), None)
    rows = {r["slot_id"]: r for r in queue["slots"]}
    # A queue rendered for some accounts only is checked against those accounts' slots.
    day_slots = sorted(sid for sid, a in allocation["slots"].items() if a["day"] == queue["day"] and
                       (not queue.get("accounts") or a["account"] in queue["accounts"]))
    ready, blocked = [], []
    for slot_id in day_slots:
        entry, row = allocation["slots"][slot_id], rows.get(slot_id)
        common = _slot_problems(slot_id, row, entry, reviews.get(slot_id), approval, allocation.get("plan_fingerprint"))
        for network in entry["networks"]:
            if posts.get(slot_id, {}).get(network, {}).get("status") in DONE:
                continue
            problems = list(common)
            if row is not None:
                asset = Path(row["asset_path"] if network == "instagram" else row["yt_asset_path"])
                if commit is None:
                    problems.append("the hosting URL does not name a commit")
                elif not problems and _blob(host_repo, commit, asset.name) != _hash_object(asset):
                    problems.append(f"the hosted {asset.name} at {commit[:7]} is not this file")
            if network == "instagram":
                problems += _sound_problems(sounds.get(slot_id), blocklist)
            if problems:
                blocked.append(dict(slot_id=slot_id, network=network, reasons=problems))
                continue
            post = _common(row, f"{base}/{asset.name}")
            if network == "instagram":
                sound = sounds[slot_id]
                post.update(providers=[dict(network="instagram")], instagramData=dict(
                    type="REEL", showReelOnFeed=True,
                    audioConfiguration=dict(audioId=str(sound["audio_id"]), audioVolume=100, videoVolume=0)))
            elif network == "facebook":
                post.update(providers=[dict(network="facebook")], facebookData=dict(type="REEL"))
            else:
                title, tags = trial_captions.youtube(row["account"], row["style"], row["parameters"])
                post.update(providers=[dict(network="youtube")], youtubeData=dict(
                    title=title, type="short", privacy="public", madeForKids=False, tags=tags, category="ENTERTAINMENT"))
            ready.append(dict(slot_id=slot_id, network=network, blogId=str(BRANDS[row["account"]]),
                              asset_sha256=row["sha256"] if network == "instagram" else row["yt_sha256"],
                              post=post))
    return dict(day=queue["day"], ready=ready, blocked=blocked)


def set_sound(day_dir, slot_ids, sound, blocklist):
    problems = _sound_problems(sound, blocklist)
    if problems:
        raise ValueError("; ".join(problems))
    sound = dict(sound, recorded_at_utc=_now())
    update_json(Path(day_dir)/"sounds.json", lambda sounds: sounds.update({s: sound for s in slot_ids}), {})


def _post_record(posts, slot_id, network):
    return posts.setdefault(slot_id, {}).setdefault(network, dict(status="pending", attempts=[]))


def record(day_dir, slot_id, network, post_id, replace=False, **facts):
    def change(posts):
        p = _post_record(posts, slot_id, network)
        if p.get("provider_post_id") and not replace:
            raise ValueError(f"{slot_id} {network} already has post {p['provider_post_id']}; use --replace on purpose")
        p["attempts"].append(dict(at_utc=_now(), result="scheduled", provider_post_id=post_id,
                                  replaced=p.get("provider_post_id")))
        p.update(facts, status="scheduled", provider="metricool", provider_post_id=post_id)
        p.setdefault("actual_published_at_utc", None)
        p.setdefault("network_post_id", None)
        p.setdefault("url", None)
        p.setdefault("observed_ages", [])
    update_json(Path(day_dir)/"posts.json", change, {})


def fail(day_dir, slot_id, network, error):
    def change(posts):
        p = _post_record(posts, slot_id, network)
        if p["status"] in DONE:
            raise ValueError(f"{slot_id} {network} is already {p['status']}")
        p["attempts"].append(dict(at_utc=_now(), result="failed", error=error))
        p["status"] = "failed"
    update_json(Path(day_dir)/"posts.json", change, {})


def live(day_dir, slot_id, network, published, network_post_id, url):
    # Only a permalink or public URL proves that a post went live.
    if not url:
        raise ValueError("a post counts as live only with its public URL")
    def change(posts):
        p = posts[slot_id][network]
        p.update(status="live", actual_published_at_utc=published, network_post_id=network_post_id, url=url)
    update_json(Path(day_dir)/"posts.json", change, {})


def observed(day_dir, slot_id, network, age):
    update_json(Path(day_dir)/"posts.json",
                lambda posts: posts[slot_id][network]["observed_ages"].append(age), {})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("payloads", "sound", "record", "fail", "live", "observed"))
    ap.add_argument("--day-dir", required=True)
    ap.add_argument("--allocation")
    ap.add_argument("--base")
    ap.add_argument("--host-repo")
    ap.add_argument("--approval", default=APPROVAL)
    ap.add_argument("--blocklist", default=BLOCKLIST)
    ap.add_argument("--slot", nargs="+")
    ap.add_argument("--network", choices=NETWORKS)
    ap.add_argument("--post-id")
    ap.add_argument("--replace", action="store_true")
    ap.add_argument("--audio-id")
    ap.add_argument("--title")
    ap.add_argument("--artist")
    ap.add_argument("--source", choices=("approved_list", "rakia_brainrot"))
    ap.add_argument("--check")
    ap.add_argument("--error")
    ap.add_argument("--published")
    ap.add_argument("--network-post-id")
    ap.add_argument("--url")
    ap.add_argument("--age", type=int)
    a = ap.parse_args()
    blocklist = read_json(a.blocklist, {})
    if a.command == "payloads":
        out = payloads(a.day_dir, read_json(a.allocation), a.base.rstrip("/"), a.host_repo,
                       read_json(a.approval, {}), blocklist)
        print(json.dumps(out, ensure_ascii=False))
    elif a.command == "sound":
        set_sound(a.day_dir, a.slot, dict(audio_id=a.audio_id, title=a.title, artist=a.artist,
                                          source=a.source, check=a.check), blocklist)
    elif a.command == "record":
        posts_sound = read_json(Path(a.day_dir)/"sounds.json", {}).get(a.slot[0]) if a.network == "instagram" else \
            "burned original music (music.py)"
        record(a.day_dir, a.slot[0], a.network, a.post_id, a.replace, sound=posts_sound)
    elif a.command == "fail":
        fail(a.day_dir, a.slot[0], a.network, a.error)
    elif a.command == "live":
        live(a.day_dir, a.slot[0], a.network, a.published, a.network_post_id, a.url)
    else:
        observed(a.day_dir, a.slot[0], a.network, a.age)


if __name__ == "__main__":
    main()
