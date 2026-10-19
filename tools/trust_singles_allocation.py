"""Re-fill trustyoureyes_ days 2-30 with single characters only (Rakia, 2026-10-19).

The pool has 30 characters, each in 6 variants (tilt 0/6/12 x 2 or 3 turns), so a
character returns about every five days with a different tilt or spin count; no
brief is used twice and nothing already rendered is reused. Day 1 and every other
account are left exactly as they are, and the render history is not touched.

    python3 tools/trust_singles_allocation.py ALLOCATION PLAN HISTORY OUT
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import trial_captions
import trial_production as T
from five_style_render import atomic_json, load_history
from trial_records import read_json

TRUST, MODE = "trustyoureyes_", "brainrot_spin"
GAP_DAYS = 4


def singles_only(plan, history, previous, seed=20261021):
    alloc = T.check_previous(plan, previous)
    slots = alloc["slots"]
    rows = sorted((r for r in plan["slots"] if r["account"] == TRUST and r["day"] >= 2),
                  key=lambda r: r["scheduled_at_utc"])
    used = {e["key"] for e in history["entries"]}
    used |= {T._key(TRUST, MODE, a["brief"]["parameters"]) for sid, a in slots.items()
             if a["account"] == TRUST and a["day"] == 1 and a.get("brief")}
    rng = random.Random(seed)
    variants = {}
    for p in T._catalogue(TRUST, MODE):
        if "partner" not in p and T._key(TRUST, MODE, p) not in used:
            variants.setdefault(p["character"], []).append(p)
    for v in variants.values():
        rng.shuffle(v)
    order = sorted(variants)
    rng.shuffle(order)
    last_day = {}
    for row in rows:
        # The character waiting longest that still has an unused variant and was not shown in the last GAP_DAYS days.
        ok = [c for c in order if variants[c] and row["day"]-last_day.get(c, -99) > GAP_DAYS]
        if not ok:
            ok = [c for c in order if variants[c]]
        if not ok:
            raise ValueError("ran out of single-character variants")
        c = min(ok, key=lambda c: (last_day.get(c, -99), order.index(c)))
        p = variants[c].pop()
        last_day[c] = row["day"]
        entry = slots[row["slot_id"]]
        entry["brief"] = T._brief(TRUST, MODE, p, T._seed(row["slot_id"]))
        entry["caption"] = trial_captions.caption(TRUST, MODE, p)
    alloc["filled"] = sum(bool(a.get("brief")) for a in slots.values())
    alloc["empty"] = len(slots)-alloc["filled"]
    return alloc


if __name__ == "__main__":
    alloc_path, plan_path, history_path, out = sys.argv[1:5]
    result = singles_only(read_json(plan_path), load_history(history_path), read_json(alloc_path))
    atomic_json(out, result)
    print(json.dumps(dict(filled=result["filled"], empty=result["empty"])))
