"""Diverse local batches across existing paired objects and licensed illusion ports.

Plans do not reserve concepts. Rendering takes an exclusive history lock and
rechecks all signatures before encoding. Only successful local outputs are recorded.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import random
import uuid

import concept_director as pairs
import illusion_library as library
from creative_director import validate_brief

FAMILIES = ("paired_objects",) + tuple(library.OPTIONS)
HISTORY_KIND = "opticpop_library_history"
MANIFEST_KIND = "opticpop_library_batch"


def identity(brief):
    spec = validate_brief(brief)
    if spec["style"] == "illusion_lab":
        family = spec["scene"]["family"]
        structure = {k:v for k,v in spec["scene"]["parameters"].items()
                     if k not in ("cycles","direction","rotation")}
    elif spec["style"] == "opticpop" and brief["idea"]["theme"] == "paired_objects":
        entities = spec["scene"]["entities"]
        if len(entities) != 2 or any(e["shape"] not in pairs.OBJECT_SHAPES for e in entities):
            raise ValueError("mixed batches support exactly two non-face objects")
        family = "paired_objects"
        # Stricter than the old novelty key: a reviewed shape pair is not new after tilt/color changes.
        structure = dict(shapes=sorted(e["shape"] for e in entities))
    else:
        raise ValueError("unsupported mixed-batch brief")
    return family, structure, signature(family,structure)


def signature(family, structure):
    return library.digest(dict(family=family,structure=structure))


def load_history(path):
    path = Path(path)
    if not path.exists():
        return dict(kind=HISTORY_KIND,version=1,entries=[])
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    library.exact(data,("kind","version","entries"),"history")
    if data["kind"] != HISTORY_KIND or type(data["version"]) is not int or data["version"] != 1 or not isinstance(data["entries"],list):
        raise ValueError("invalid library history")
    keys = set()
    for item in data["entries"]:
        library.exact(item,("family","structure","key","brief_id","brief_digest","mode","sha256","output","preview"),"history entry")
        family, structure = item["family"],item["structure"]
        if not isinstance(family,str) or family not in FAMILIES or not isinstance(structure,dict):
            raise ValueError("invalid history family or structure")
        if family == "paired_objects":
            shapes = structure.get("shapes")
            if (set(structure) != {"shapes"} or not isinstance(shapes,list) or len(shapes)!=2
                or any(s not in pairs.OBJECT_SHAPES for s in shapes) or shapes != sorted(shapes)):
                raise ValueError("invalid historical shape pair")
        else:
            p = {k:values[0] for k,values in library.OPTIONS[family].items()}
            expected = set(p) - {"cycles","direction","rotation"}
            if set(structure) != expected:
                raise ValueError("invalid historical parameters")
            p.update(structure)
            library.validate_scene(dict(version=1,family=family,parameters=p,
                palette="classic" if family=="footsteps" else "neon"))
        if item["key"] != signature(family,structure) or item["key"] in keys:
            raise ValueError("invalid or duplicate history signature")
        keys.add(item["key"])
        if any(not isinstance(item[k],str) or not item[k] for k in ("brief_id","output","mode","sha256")):
            raise ValueError("invalid history metadata")
        if item["mode"] not in ("preview","full") or len(item["sha256"])!=64 or any(c not in "0123456789abcdef" for c in item["sha256"]):
            raise ValueError("invalid history render mode or checksum")
        if not isinstance(item["brief_digest"],str) or len(item["brief_digest"])!=64 or any(c not in "0123456789abcdef" for c in item["brief_digest"]):
            raise ValueError("invalid historical brief digest")
        if item["preview"] is not None:
            library.exact(item["preview"],("sha256","output"),"preview provenance")
            if (item["mode"] != "full" or not isinstance(item["preview"]["output"],str)
                or not isinstance(item["preview"]["sha256"],str) or len(item["preview"]["sha256"])!=64
                or any(c not in "0123456789abcdef" for c in item["preview"]["sha256"])):
                raise ValueError("invalid preview provenance")
    return data


def seen_keys(history, pair_history=None):
    keys = {item["key"] for item in history["entries"]}
    if pair_history is not None and Path(pair_history).exists():
        from batch_director import load_history as old_history
        for item in old_history(pair_history)["entries"]:
            keys.add(signature("paired_objects",dict(shapes=sorted(item["pair_key"].split("|")))))
    return keys


def candidate_pools(seed):
    if type(seed) is not int or not 0 <= seed < 1_000_000:
        raise ValueError("seed must be an integer in 0-999999")
    pool = {}
    for offset,family in enumerate(FAMILIES):
        # Reuse the existing pair grammar across all 45 pairs, beyond the CLI's 40-item limit.
        candidates = (pairs._generate_pairs(seed,45)
                      if family=="paired_objects" else list(library.candidates(family,(seed+offset)%1_000_000)))
        random.Random(seed+offset).shuffle(candidates)
        pool[family] = candidates
    return pool


def plan(out, history_path, seed=42, count=12, pair_history=None):
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError("count must be an integer in 1-100")
    out = Path(out)
    if out.exists():
        raise ValueError("choose a new plan folder")
    history = load_history(history_path)
    used = seen_keys(history,pair_history)
    pools = candidate_pools(seed)
    items = []
    family_counts = Counter()
    while len(items) < count:
        added = False
        # A depleted family yields its slot to another; old variants are never recycled.
        for family in sorted(FAMILIES,key=lambda f:(family_counts[f],FAMILIES.index(f))):
            while pools[family]:
                idea = pools[family].pop()
                if family == "paired_objects":
                    brief = pairs.production_brief(dict(idea=idea,evaluation=pairs.evaluate(idea)))
                else:
                    brief = library.production_brief(idea)
                _,_,key = identity(brief)
                if key in used:
                    continue
                used.add(key)
                items.append(dict(id=idea["id"],family=family,novelty_key=key,brief=brief))
                family_counts[family] += 1
                added = True
                break
            if len(items) == count:
                break
        if not added:
            raise ValueError("catalogue exhausted for this history; add a new geometry family or lower count")
    manifest = dict(kind=MANIFEST_KIND,version=1,publishing_allowed=False,seed=seed,items=items)
    validate_manifest(manifest)
    out.mkdir(parents=True)
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"briefs").mkdir()
    rows = ["# אצווה מקומית לבדיקה", "", "אין פרסום או תזמון. התכנון אינו משנה היסטוריה.", "",
            "| מס׳ | משפחה | רעיון | ציון |", "|---|---|---|---|"]
    for index,item in enumerate(items,1):
        brief = item["brief"]
        (out/"briefs"/f"{index:03d}.json").write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding="utf-8")
        rows.append(f"| {index} | {item['family']} | {brief['idea']['title']} | {brief['evaluation']['total']} |")
    rows.extend(["", "השוואת החזרות מתעלמת מצבע, seed ושינוי מהירות בלבד. בזוגות אובייקטים נבדק זוג הצורות עצמו.",
                 "הרינדור בודק שוב היסטוריה ונועל אותה, ורושם רק קבצים שהופקו בהצלחה.",
                 "אין הבטחה למקוריות עולמית או לכך שכל צופה יראה את אותה אשליה."])
    (out/"review_he.md").write_text("\n".join(rows)+"\n",encoding="utf-8")
    return manifest


def validate_manifest(manifest):
    library.exact(manifest,("kind","version","publishing_allowed","seed","items"),"manifest")
    if manifest["kind"] != MANIFEST_KIND or type(manifest["version"]) is not int or manifest["version"] != 1 or manifest["publishing_allowed"] is not False:
        raise ValueError("only local library batches are accepted")
    if type(manifest["seed"]) is not int or not 0 <= manifest["seed"] < 1_000_000:
        raise ValueError("invalid manifest seed")
    if not isinstance(manifest["items"],list) or not 1 <= len(manifest["items"]) <= 100:
        raise ValueError("manifest needs 1-100 items")
    seen = set()
    for item in manifest["items"]:
        library.exact(item,("id","family","novelty_key","brief"),"batch item")
        family,_,key = identity(item["brief"])
        if item["family"] != family or item["novelty_key"] != key or item["id"] != item["brief"]["idea"]["id"] or key in seen:
            raise ValueError("batch item differs from brief or duplicates another concept")
        seen.add(key)
    return manifest


@contextmanager
def history_lock(path):
    path = Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    lock = path.with_name(path.name+".lock")
    try:
        fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        raise ValueError("history is locked by another render; wait for it to finish") from None
    try:
        with os.fdopen(fd,"w") as file:
            file.write(str(os.getpid()))
        yield
    finally:
        lock.unlink(missing_ok=True)


def save_history(path, data):
    path = Path(path)
    temp = path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    try:
        with temp.open("x",encoding="utf-8") as file:
            json.dump(data,file,ensure_ascii=False,indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp,path)
    finally:
        temp.unlink(missing_ok=True)


def file_hash(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda:file.read(1024*1024),b""):
            result.update(chunk)
    return result.hexdigest()


def render_batch(manifest_path, out, history_path, quality="preview", ffmpeg="ffmpeg", pair_history=None, renderer=None):
    manifest = validate_manifest(json.loads(Path(manifest_path).read_text(encoding="utf-8-sig")))
    if quality not in ("preview","full"):
        raise ValueError("quality must be preview or full")
    out = Path(out)
    if out.exists():
        raise ValueError("choose a new render folder; successful partial results remain in history")
    with history_lock(history_path):
        history = load_history(history_path)
        used = seen_keys(history,pair_history)
        previous = {entry["key"]:entry for entry in history["entries"]}
        for item in manifest["items"]:
            old = previous.get(item["novelty_key"])
            promotion = (old is not None and old["mode"] == "preview" and quality == "full"
                         and old["brief_digest"] == library.digest(item["brief"]))
            if item["novelty_key"] in used and not promotion:
                raise ValueError("plan contains a previously rendered/reviewed concept; create a new plan")
        out.mkdir(parents=True)
        report = dict(publishing_allowed=False,quality=quality,items=[])
        for item in manifest["items"]:
            brief = item["brief"]
            # Never use user-supplied titles, IDs or paths as filenames.
            video = out / (item["family"]+"_"+item["novelty_key"][:12]+".mp4")
            if renderer is not None:
                renderer(brief,video)
            elif quality == "preview":
                from preview_brief import preview
                preview(brief,video,ffmpeg)
            else:
                from render_brief import render_local
                render_local(brief,video,ffmpeg=ffmpeg)
            if not video.is_file() or video.stat().st_size == 0:
                raise ValueError("renderer did not produce a nonempty video; not recorded")
            checksum = file_hash(video)
            hashes = {entry["sha256"] for entry in history["entries"]}
            hashes.update(entry["preview"]["sha256"] for entry in history["entries"] if entry["preview"] is not None)
            if checksum in hashes:
                video.unlink()
                for suffix in (".json",".png"):
                    video.with_suffix(suffix).unlink(missing_ok=True)
                raise ValueError("encoded output duplicates an earlier file; not recorded")
            family,structure,key = identity(brief)
            entry = dict(family=family,structure=structure,key=key,brief_id=item["id"],brief_digest=library.digest(brief),
                         mode=quality,sha256=checksum,output=str(video.resolve()),preview=None)
            old = previous.get(key)
            if old is not None:
                entry["preview"] = dict(sha256=old["sha256"],output=old["output"])
                history["entries"][history["entries"].index(old)] = entry
            else:
                history["entries"].append(entry)
            save_history(history_path,history)
            video.with_suffix(".brief.json").write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding="utf-8")
            report["items"].append(entry)
            (out/"render_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
            print(f"LOCAL {len(report['items'])}/{len(manifest['items'])}: {family}",flush=True)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command",required=True)
    planner = commands.add_parser("plan")
    planner.add_argument("--seed",type=int,default=42)
    planner.add_argument("--count",type=int,default=12)
    renderer = commands.add_parser("render")
    renderer.add_argument("manifest",type=Path)
    renderer.add_argument("--quality",choices=("preview","full"),default="preview")
    renderer.add_argument("--ffmpeg",default="ffmpeg")
    for command in (planner,renderer):
        command.add_argument("--out",type=Path,required=True)
        command.add_argument("--history",type=Path,default=Path("local_demo/library_history.json"))
        command.add_argument("--pair-history",type=Path,default=Path("local_demo/history.json"))
    args = parser.parse_args()
    try:
        if args.command == "plan":
            result = plan(args.out,args.history,args.seed,args.count,args.pair_history)
            print(json.dumps(dict(planned=len(result["items"]),families=dict(Counter(i["family"] for i in result["items"])),publishing_allowed=False)))
        else:
            render_batch(args.manifest,args.out,args.history,args.quality,args.ffmpeg,args.pair_history)
    except (ValueError,OSError,RuntimeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
