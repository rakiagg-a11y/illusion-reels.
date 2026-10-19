"""What the month trial needs to check now, and a store for what was observed.

  python3 trial_observe.py due --reels /mnt/project-files/reels/trial
  python3 trial_observe.py add --store snapshots.jsonl --row '{...}'

due reads each day's queue.json and posts.json and lists scheduled posts that
should be live but are not verified yet, and live posts whose 24, 72 or 168
hour observation window is open now (age within 3 hours of the target).
add appends one observation. Instagram rows use the fields trial_metrics.py
reads; Facebook and YouTube rows are kept apart, with their own ids and metric
names, so views are never mixed with Instagram reach.
A metric that was not returned is stored as null, never as 0.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from trial_records import read_json

TZ = ZoneInfo("Asia/Jerusalem")
AGES = (24, 72, 168)
INSTAGRAM = ("slot_id", "instagram_media_id", "actual_published_at_utc", "observed_at_utc", "metrics_as_of_utc",
             "reach", "views", "likes", "comments", "shares", "saves")


def _scheduled(row):
    local = datetime.fromisoformat(f"{row['local_date']}T{row['local_time']}").replace(tzinfo=TZ)
    return local.astimezone(timezone.utc)


def due(reels, now):
    out = dict(unverified=[], observe=[])
    for queue_file in sorted(Path(reels).glob("*/queue.json")):
        posts = read_json(queue_file.with_name("posts.json"), {})
        for row in read_json(queue_file)["slots"]:
            when = _scheduled(row)
            for network, post in posts.get(row["slot_id"], {}).items():
                if post.get("status") not in ("scheduled", "live"):
                    continue
                published = post.get("actual_published_at_utc")
                if not published and now >= when+timedelta(minutes=30):
                    out["unverified"].append(dict(slot_id=row["slot_id"], account=row["account"], network=network,
                                                  provider_post_id=post.get("provider_post_id"),
                                                  scheduled_utc=when.isoformat(), day_dir=str(queue_file.parent)))
                if published:
                    age = (now-datetime.fromisoformat(published)).total_seconds()/3600
                    for target in AGES:
                        if abs(age-target) <= 3 and target not in post.get("observed_ages", []):
                            out["observe"].append(dict(slot_id=row["slot_id"], account=row["account"], network=network,
                                                       target_age=target, age=round(age, 2),
                                                       network_post_id=post.get("network_post_id"),
                                                       day_dir=str(queue_file.parent)))
    return out


def add(store, row):
    if row.get("network") == "instagram":
        missing = [k for k in INSTAGRAM if k not in row]
        if missing:
            raise ValueError(f"instagram observation is missing {missing}")
    for value in row.values():
        if isinstance(value, (int, float)) and value < 0:
            raise ValueError("counters cannot be negative")
    with open(store, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False)+"\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("due", "add"))
    ap.add_argument("--reels", default="/mnt/project-files/reels/trial")
    ap.add_argument("--store", default="/mnt/project-files/experiment/timing-2026-10/snapshots.jsonl")
    ap.add_argument("--row")
    ap.add_argument("--now", help="ISO time, default now")
    a = ap.parse_args()
    if a.command == "due":
        now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc)
        print(json.dumps(due(a.reels, now), indent=1))
    else:
        add(a.store, json.loads(a.row))


if __name__ == "__main__":
    main()
