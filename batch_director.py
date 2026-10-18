"""Plan and review local OpticPop batches. No publishing, scheduling or network access."""
import argparse
from collections import Counter
import datetime
import json
import math
import os
from pathlib import Path
import tempfile
import concept_director as director
from scene_contract import OBJECT_SHAPES

SCHEMA = 1
SHAPE_LABELS = dict(heart="לב", star="כוכב", crescent="סהר", butterfly="פרפר", ring="טבעת",
                    leaf="עלה", diamond="יהלום", lightning="ברק", flower="פרח", hourglass="שעון חול")


def pair_key(idea):
    return "|".join(sorted(e["shape"] for e in idea["scene"]["entities"]))


def load_history(path):
    path = Path(path)
    if not path.exists():
        return dict(schema_version=SCHEMA, entries=[])
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != SCHEMA or not isinstance(data.get("entries"), list)):
        raise ValueError("unsupported history format")
    for item in data["entries"]:
        if not isinstance(item, dict) or any(not isinstance(item.get(k), str) for k in ("id", "novelty_key", "pair_key")):
            raise ValueError("invalid history entry")
        shapes = item["pair_key"].split("|")
        if len(shapes) != 2 or any(s not in OBJECT_SHAPES for s in shapes):
            raise ValueError("history pair must contain two supported object shapes")
    return data


def select_batch(rows, count, history):
    if type(count) is not int or not 1 <= count <= 10:
        raise ValueError("batch count must be 1-10")
    used_pairs = {e["pair_key"] for e in history["entries"]}
    seen_shapes = Counter(s for e in history["entries"] for s in e["pair_key"].split("|"))
    candidates, considered = [], set()
    for row in rows:
        if not row["evaluation"]["eligible"]:
            continue
        idea = row["idea"]
        entities = idea["scene"]["entities"]
        if len(entities) != 2 or any(e["shape"] not in OBJECT_SHAPES for e in entities):
            continue
        key = pair_key(idea)
        if key in used_pairs or key in considered:
            continue
        considered.add(key)
        candidates.append(row)
    # Select a set of distinct pairs while limiting repeated shapes within the batch.
    # Backtracking prevents an early greedy choice from making a feasible batch impossible.
    cap = max(2, math.ceil(count * 2 / len(OBJECT_SHAPES)))
    def choose(pool, chosen, counts):
        if len(chosen) == count:
            return chosen
        if len(pool) < count - len(chosen):
            return None
        ordered = sorted(pool, key=lambda r: (
            sum(seen_shapes[e["shape"]] + counts[e["shape"]] for e in r["idea"]["scene"]["entities"]),
            -r["evaluation"]["total"], r["idea"]["id"]))
        for pos, row in enumerate(ordered):
            shapes = [e["shape"] for e in row["idea"]["scene"]["entities"]]
            extra = Counter(shapes)
            if any(counts[s] + n > cap for s, n in extra.items()):
                continue
            result = choose(ordered[pos+1:], chosen+[row], counts+extra)
            if result is not None:
                return result
        return None
    result = choose(candidates, [], Counter())
    if result is None:
        raise ValueError("not enough unseen pairs for a diverse batch; lower count or review the history")
    return result


def plan(out, history_path, seed=42, count=6):
    if type(seed) is not int or not 0 <= seed < 1_000_000:
        raise ValueError("seed must be an integer in 0-999999")
    history = load_history(history_path)
    recent = [e["novelty_key"] for e in history["entries"]]
    # Several deterministic pools offer enough unseen combinations without touching history.
    ideas = [idea for offset in range(3)
             for idea in director.generate_concepts((seed+offset) % 1_000_000, "paired_objects", 40)]
    rows = director.rank(ideas[:100], recent)
    selected = select_batch(rows, count, history)
    out = Path(out)
    if out.exists():
        raise ValueError("choose a new batch output folder")
    out.mkdir(parents=True)
    briefs_dir = out / "briefs"
    briefs_dir.mkdir()
    items = []
    for row in selected:
        brief = director.production_brief(row)
        director.validate_brief(brief)
        idea = brief["idea"]
        (briefs_dir / (idea["id"]+".json")).write_text(
            json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        items.append(dict(id=idea["id"], pair_key=pair_key(idea), brief=brief))
    manifest = dict(schema_version=SCHEMA, status="local_review", publishing_allowed=False,
                    seed=seed, items=items,
                    note="Planning does not record history. Use record after reviewing selected concepts.")
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "ranking.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# OpticPop — אצווה לבדיקה מקומית", "",
             "לא בוצעו תזמון או פרסום. יצירת האצווה אינה משנה את ההיסטוריה.", "",
             "| מזהה | רעיון | זוג צורות | ציון |", "|---|---|---|---|"]
    for item in items:
        b = item["brief"]
        labels=" + ".join(SHAPE_LABELS[s] for s in item["pair_key"].split("|"))
        lines.append(f"| {item['id']} | {b['idea']['title']} | {labels} | {b['evaluation']['total']} |")
    lines.extend(["", "אפשר להפיק תצוגה לכל בריף באמצעות preview_brief.py. רושמים להיסטוריה רק מזהים שנבחרו לאחר בדיקה."])
    (out / "review.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
    return manifest


def record(manifest_path, history_path, ids):
    if not ids or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("supply at least one reviewed concept ID")
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8-sig"))
    if (not isinstance(data, dict) or type(data.get("schema_version")) is not int
            or data["schema_version"] != SCHEMA or data.get("publishing_allowed") is not False
            or data.get("status") != "local_review" or not isinstance(data.get("items"), list)):
        raise ValueError("unsupported local review manifest")
    available = {}
    for item in data["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("brief"), dict):
            raise ValueError("invalid manifest item")
        brief = item["brief"]
        director.validate_brief(brief)
        if item.get("id") != brief["idea"]["id"] or item.get("pair_key") != pair_key(brief["idea"]):
            raise ValueError("manifest identity differs from the validated brief")
        if item["id"] in available:
            raise ValueError("duplicate concept ID in manifest")
        available[item["id"]] = brief["idea"]
    if set(ids) - available.keys():
        raise ValueError("one or more IDs are not in this batch")
    history = load_history(history_path)
    existing = {e["novelty_key"] for e in history["entries"]}
    added = 0
    for key in sorted(set(ids)):
        idea = available[key]
        if idea["novelty_key"] in existing:
            continue
        history["entries"].append(dict(
            id=key, novelty_key=idea["novelty_key"], pair_key=pair_key(idea),
            status="seen_in_local_review",
            recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        existing.add(idea["novelty_key"])
        added += 1
    target = Path(history_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent,
                                         prefix=target.name+".", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(history, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return added


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="action", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--history", type=Path, default=Path("local_demo/history.json"))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--count", type=int, default=6)
    r = sub.add_parser("record")
    r.add_argument("manifest", type=Path)
    r.add_argument("--history", type=Path, default=Path("local_demo/history.json"))
    r.add_argument("--ids", nargs="+", required=True)
    args = ap.parse_args()
    try:
        if args.action == "plan":
            if not 0 <= args.seed < 1_000_000:
                raise ValueError("seed must be in 0-999999")
            result = plan(args.out, args.history, args.seed, args.count)
            print(json.dumps(dict(concepts=len(result["items"]), manifest=str(args.out/"manifest.json"),
                                  publishing_allowed=False)))
        else:
            print(json.dumps(dict(recorded=record(args.manifest,args.history,args.ids), publishing_allowed=False)))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        ap.error(str(exc))


if __name__ == "__main__":
    main()
