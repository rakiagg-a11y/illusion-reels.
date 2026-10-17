import copy
from collections import Counter
import itertools
import json
from pathlib import Path
import tempfile
import unittest
import batch_director as b
import concept_director as d
from scene_contract import OBJECT_SHAPES


class BatchTests(unittest.TestCase):
    def test_planning_is_deterministic_and_does_not_record_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            history=root/"history.json"
            a=b.plan(root/"a",history,seed=73,count=6)
            other=b.plan(root/"b",history,seed=73,count=6)
            self.assertEqual(a,other)
            self.assertFalse(history.exists())
            self.assertEqual(len(a["items"]),6)
            self.assertEqual(len({i["pair_key"] for i in a["items"]}),6)
            counts=Counter(s for i in a["items"] for s in i["pair_key"].split("|"))
            self.assertLessEqual(max(counts.values()),2)
            self.assertFalse(a["publishing_allowed"])
            for item in a["items"]:
                d.validate_brief(item["brief"])

    def test_record_only_selected_ids_and_repeated_record_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            history=root/"history.json"
            data=b.plan(root/"a",history,count=6)
            ids=[i["id"] for i in data["items"][:2]]
            self.assertEqual(b.record(root/"a/manifest.json",history,ids),2)
            old=history.read_bytes()
            self.assertEqual(b.record(root/"a/manifest.json",history,ids),0)
            self.assertEqual(old,history.read_bytes())
            entries=b.load_history(history)["entries"]
            self.assertEqual({e["id"] for e in entries},set(ids))
            self.assertTrue(all(e["status"]=="seen_in_local_review" for e in entries))

    def test_next_batch_excludes_seen_pair_even_with_changed_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            history=root/"history.json"
            a=b.plan(root/"a",history,seed=42,count=6)
            b.record(root/"a/manifest.json",history,[i["id"] for i in a["items"]])
            before=history.read_bytes()
            next_batch=b.plan(root/"b",history,seed=43,count=6)
            self.assertFalse({i["pair_key"] for i in a["items"]}&{i["pair_key"] for i in next_batch["items"]})
            self.assertEqual(before,history.read_bytes())

    def test_invalid_or_tampered_review_cannot_change_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            history=root/"history.json"
            data=b.plan(root/"a",history,count=4)
            selected=data["items"][0]["id"]
            for target in ("publishing","pair","caption","duplicate"):
                changed=copy.deepcopy(data)
                if target=="publishing":
                    changed["publishing_allowed"]=True
                elif target=="pair":
                    changed["items"][0]["pair_key"]="heart|heart"
                elif target=="caption":
                    changed["items"][0]["brief"]["caption"]["full_caption"]="tampered"
                else:
                    changed["items"].append(changed["items"][0])
                bad=root/"bad.json"
                bad.write_text(json.dumps(changed),encoding="utf-8")
                with self.assertRaises(ValueError):
                    b.record(bad,history,[selected])
                self.assertFalse(history.exists())
            with self.assertRaises(ValueError):
                b.record(root/"a/manifest.json",history,["unknown"])
            self.assertFalse(history.exists())

    def test_exhaustion_is_explicit_and_does_not_write_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            entries=[dict(id=str(k),novelty_key=str(k),pair_key="|".join(sorted(pair)))
                     for k,pair in enumerate(itertools.combinations(OBJECT_SHAPES,2))]
            history=root/"history.json"
            history.write_text(json.dumps(dict(schema_version=1,entries=entries)),encoding="utf-8")
            original=history.read_bytes()
            with self.assertRaises(ValueError):
                b.plan(root/"unavailable",history,count=4)
            self.assertFalse((root/"unavailable").exists())
            self.assertEqual(original,history.read_bytes())

    def test_existing_batch_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            b.plan(root/"a",root/"history.json",count=4)
            old=(root/"a/manifest.json").read_bytes()
            with self.assertRaises(ValueError):
                b.plan(root/"a",root/"history.json",seed=2,count=4)
            self.assertEqual(old,(root/"a/manifest.json").read_bytes())

    def test_ten_item_batch_stays_diverse(self):
        with tempfile.TemporaryDirectory() as tmp:
            data=b.plan(Path(tmp)/"batch",Path(tmp)/"history.json",count=10)
            counts=Counter(s for i in data["items"] for s in i["pair_key"].split("|"))
            self.assertEqual(len(data["items"]),10)
            self.assertEqual(set(counts),set(OBJECT_SHAPES))
            self.assertEqual(set(counts.values()),{2})

    def test_invalid_history_and_seed_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            history=root/"history.json"
            history.write_text('{"schema_version":true,"entries":[]}',encoding="utf-8")
            with self.assertRaises(ValueError):
                b.load_history(history)
            history.unlink()
            for seed in (True,-1,1000000):
                with self.assertRaises(ValueError):
                    b.plan(root/"out",history,seed=seed)
            self.assertFalse((root/"out").exists())


if __name__=="__main__":
    unittest.main()
