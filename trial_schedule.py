"""Metricool payloads for one trial day, and a record of what was scheduled.

  python3 trial_schedule.py payloads --queue DIR/queue.json --allocation allocation.json --base RAW_URL_PREFIX
  python3 trial_schedule.py record --queue DIR/queue.json --slot SLOT --network instagram --post-id ID [--audio ID --audio-title T]

Each video becomes two posts at the plan time: Instagram with the silent file
and a library sound attached, and Facebook + YouTube with our own music burned
into the _yt copy. Nothing here talks to Metricool.
"""
import argparse
import json
from pathlib import Path

import trial_captions
from five_style_render import atomic_json

BRANDS = {"opticpop": 7443198, "hypnotorium": 7498748, "spiralium_": 7498862, "trustyoureyes_": 7498890}
BRAINROT_AUDIO = "24360627876895620"  # "La polizia noooo 😭", Rakia's pick for brainrot from the 2nd reel on


def _common(row, url):
    return dict(autoPublish=True, draft=False, descendants=[], firstCommentText="", hasNotReadNotes=False,
                media=[url], mediaAltText=[], shortener=False, smartLinkData=dict(ids=[]), text=row["caption"],
                publicationDate=dict(dateTime=f"{row['local_date']}T{row['local_time']}:00", timezone="Asia/Jerusalem"))


def payloads(queue, allocation, base):
    out = []
    for row in queue["slots"]:
        p = allocation["slots"][row["slot_id"]]["brief"]["parameters"]
        name = Path(row["asset_path"]).name
        ig = _common(row, f"{base}/{name}")
        ig.update(providers=[dict(network="instagram")], instagramData=dict(
            type="REEL", showReelOnFeed=True,
            audioConfiguration=dict(audioId=BRAINROT_AUDIO if row["account"] == "trustyoureyes_" else "?",
                                    audioVolume=100, videoVolume=0)))
        title, tags = trial_captions.youtube(row["account"], row["style"], p)
        fy = _common(row, f"{base}/{Path(row['yt_asset_path']).name}")
        fy.update(providers=[dict(network="facebook"), dict(network="youtube")], facebookData=dict(type="REEL"),
                  youtubeData=dict(title=title, type="short", privacy="public", madeForKids=False,
                                   tags=tags, category="ENTERTAINMENT"))
        out.append(dict(slot_id=row["slot_id"], blogId=str(BRANDS[row["account"]]),
                        date=f"{row['local_date']}T{row['local_time']}:00", instagram=ig, facebook_youtube=fy))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("payloads", "record"))
    ap.add_argument("--queue", required=True)
    ap.add_argument("--base")
    ap.add_argument("--allocation")
    ap.add_argument("--slot")
    ap.add_argument("--network", choices=("instagram", "facebook_youtube"))
    ap.add_argument("--post-id")
    ap.add_argument("--audio")
    ap.add_argument("--audio-title")
    a = ap.parse_args()
    queue = json.loads(Path(a.queue).read_text(encoding="utf-8"))
    if a.command == "payloads":
        allocation = json.loads(Path(a.allocation).read_text(encoding="utf-8"))
        print(json.dumps(payloads(queue, allocation, a.base.rstrip("/")), ensure_ascii=False))
        return
    row = next(r for r in queue["slots"] if r["slot_id"] == a.slot)
    posts = row.setdefault("posts", {})
    posts[a.network] = dict(provider="metricool", provider_post_id=a.post_id, network_post_id=None,
                            scheduled_local=f"{row['local_date']}T{row['local_time']}",
                            actual_published_at_utc=None,
                            sound=dict(audio_id=a.audio, title=a.audio_title) if a.audio else
                            ("burned original music (music.py)" if a.network == "facebook_youtube" else None))
    atomic_json(a.queue, queue)


if __name__ == "__main__":
    main()
