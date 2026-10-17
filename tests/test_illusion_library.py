import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np

import creative_library as batches
import illusion_library as lib
import illusion_lab as lab
from creative_director import validate_brief
from render_brief import render_local


def ideas():
    return {family:next(lib.candidates(family,42)) for family in lib.OPTIONS}


class IllusionLibraryTests(unittest.TestCase):
    def test_catalogue_is_finite_structurally_distinct_and_reproducible(self):
        for family in lib.OPTIONS:
            a = list(lib.candidates(family,42))
            self.assertEqual(a,list(lib.candidates(family,42)))
            self.assertGreater(len(a),10)
            self.assertEqual(len(a),len({i["novelty_key"] for i in a}))
            self.assertTrue(all(lib.evaluate(i)["eligible"] for i in a))
            for idea in a[:3]:
                score = lib.evaluate(idea)
                self.assertEqual(score["total"],sum(score["scores"][k]*v/5 for k,v in lib.WEIGHTS.items()))
        self.assertEqual(len(batches.candidate_pools(42)["paired_objects"]),45)

    def test_color_seed_speed_reversal_and_rotation_do_not_earn_novelty(self):
        for family,idea in ideas().items():
            scene = copy.deepcopy(idea["scene"])
            scene["parameters"]["cycles"] = 1 if scene["parameters"]["cycles"]!=1 else 2
            if family != "footsteps":
                scene["palette"] = "amber" if scene["palette"]!="amber" else "ice"
            if family == "penrose":
                scene["parameters"]["direction"] *= -1
                scene["parameters"]["rotation"] = 0
            changed = lib.idea_for(scene,1234)
            self.assertEqual(idea["novelty_key"],changed["novelty_key"])

    def test_invalid_parameters_and_publishing_flags_are_rejected(self):
        for family,idea in ideas().items():
            for value in (True,None,{},float("nan"),float("inf"),99999):
                scene = copy.deepcopy(idea["scene"])
                scene["parameters"]["cycles"] = value
                with self.assertRaises(ValueError):
                    lib.validate_scene(scene)
            scene = copy.deepcopy(idea["scene"])
            scene["parameters"]["script"] = "anything"
            with self.assertRaises(ValueError):
                lib.validate_scene(scene)
            brief = lib.production_brief(idea)
            for field,value in (("publishing_allowed",True),("schema_version",3.0),("status","approved")):
                changed = copy.deepcopy(brief)
                changed[field] = value
                with self.assertRaises(ValueError):
                    validate_brief(changed)

    def test_tampered_source_caption_or_render_never_reaches_generator(self):
        brief = lib.production_brief(ideas()["penrose"])
        runner = Mock()
        for target in ("source","caption","render"):
            changed = copy.deepcopy(brief)
            if target == "source":
                changed["idea"]["source"]["commit"] = "fake"
            elif target == "caption":
                changed["caption"]["full_caption"] = "fake"
            else:
                changed["render"]["scene"]["parameters"]["cycles"] = 99
            with self.assertRaises(ValueError):
                render_local(changed,"unused.mp4",runner)
        runner.assert_not_called()

    def test_adapter_preserves_scene_caption_and_explicit_encoder(self):
        brief = lib.production_brief(ideas()["penrose"])
        runner = Mock(return_value={"ok":True})
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/"clip.mp4"
            render_local(brief,out,runner,ffmpeg="encoder.exe")
            runner.assert_called_once_with("illusion_lab",brief["render"]["seed"],str(out),"",
                scene=brief["render"]["scene"],creative_caption=brief["caption"],ffmpeg="encoder.exe")

    def test_generate_routes_library_and_writes_matching_caption(self):
        import generate
        brief = lib.production_brief(ideas()["ebbinghaus"])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/"clip.mp4"
            with patch("illusion_lab.render",return_value={"style":"illusion_lab"}) as renderer:
                metadata = generate.run("illusion_lab",brief["render"]["seed"],str(out),"",
                    scene=brief["render"]["scene"],creative_caption=brief["caption"],ffmpeg="encoder.exe")
            self.assertEqual(metadata["full_caption"],brief["caption"]["full_caption"])
            self.assertEqual(json.loads(out.with_suffix(".json").read_text()),metadata)
            renderer.assert_called_once_with(brief["render"]["scene"],brief["render"]["seed"],str(out),15,"",ffmpeg="encoder.exe")
        self.assertEqual(generate.STYLES,["pointspin"])

    def test_ebbinghaus_targets_remain_equal_and_surroundings_do_not_collide(self):
        for idea in lib.candidates("ebbinghaus",42):
            p = idea["scene"]["parameters"]
            for side in ("small","large"):
                points = lab.outer_circles([0,0],p["target_radius"],p[side+"_radius"],p[side+"_count"],p["gap"],.7)
                np.testing.assert_allclose(np.linalg.norm(points,axis=1),p["target_radius"]+p[side+"_radius"]+p["gap"])
                distances = np.linalg.norm(points-np.roll(points,1,axis=0),axis=1)
                self.assertTrue((distances >= 2*p[side+"_radius"]).all())
        scene = ideas()["ebbinghaus"]["scene"]
        frame = lab.frame(scene,11.5,180,320)
        mask = (frame[:,:,0] > 220) & (frame[:,:,1] > 80) & (frame[:,:,1] < 180) & (frame[:,:,2] < 70)
        self.assertEqual(mask[:160].sum(),mask[160:].sum())

    def test_footsteps_share_constant_velocity_and_control_preserves_positions(self):
        p = ideas()["footsteps"]["scene"]["parameters"]
        positions = [np.array(lab.block_positions(p,t)) for t in (.1,.2,.3)]
        for frame in positions:
            np.testing.assert_allclose(frame[:,0],frame[0,0])
        np.testing.assert_allclose(positions[1]-positions[0],positions[2]-positions[1],atol=1e-14)
        self.assertEqual(lab.context_opacity(11.5),0)
        self.assertEqual(lab.context_opacity(0),1)
        self.assertEqual(lab.context_opacity(15),1)

    def test_penrose_face_order_and_all_family_loops(self):
        p = ideas()["penrose"]["scene"]["parameters"]
        faces = lab.penrose_faces(p,0)
        self.assertEqual((faces[0][0],faces[0][1]),(0,0))
        self.assertEqual([(i,part) for i,part,_ in faces[-2:]],[(0,1),(0,2)])
        self.assertEqual(len(faces),9*p["cubes"])
        for family,idea in ideas().items():
            a = lab.frame(idea["scene"],0,180,320)
            b = lab.frame(idea["scene"],15,180,320)
            c = lab.frame(idea["scene"],2.1,180,320)
            np.testing.assert_array_equal(a,b)
            self.assertFalse(np.array_equal(a,c),family)
            self.assertGreater(a.max(),200)


class MixedBatchTests(unittest.TestCase):
    def test_checked_in_demo_and_source_notices_are_consistent(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root/"samples/library_v1/manifest.json").read_text(encoding="utf-8"))
        batches.validate_manifest(manifest)
        self.assertEqual({i["family"] for i in manifest["items"]},set(batches.FAMILIES))
        sources = json.loads((root/"third_party/sources.json").read_text())["sources"]
        for source in lib.SOURCES.values():
            match = next(s for s in sources if s["repository"]==source["repository"])
            self.assertEqual(match["commit"],source["commit"])
            self.assertIn(source["path"],match["files"])
            self.assertIn("Permission is hereby granted",(root/match["license_file"]).read_text())

    def test_planning_balances_families_without_changing_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root/"history.json"
            a = batches.plan(root/"a",history,count=12)
            b = batches.plan(root/"b",history,count=12)
            self.assertEqual(a,b)
            self.assertFalse(history.exists())
            self.assertEqual({f:sum(i["family"]==f for i in a["items"]) for f in batches.FAMILIES},dict.fromkeys(batches.FAMILIES,3))
            self.assertEqual(len({i["novelty_key"] for i in a["items"]}),12)

    def test_render_records_successes_and_next_seed_excludes_seen_structures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root/"history.json"
            a = batches.plan(root/"a",history,count=4)
            batches.render_batch(root/"a/manifest.json",root/"videos",history,
                renderer=lambda brief,out:out.write_bytes(brief["idea"]["id"].encode()))
            old = history.read_bytes()
            b = batches.plan(root/"b",history,seed=43,count=12)
            self.assertEqual(history.read_bytes(),old)
            self.assertFalse({i["novelty_key"] for i in a["items"]}&{i["novelty_key"] for i in b["items"]})
            with self.assertRaises(ValueError):
                batches.render_batch(root/"a/manifest.json",root/"duplicate",history,renderer=Mock())
            self.assertFalse((root/"duplicate").exists())

    def test_preview_can_promote_once_without_counting_as_another_concept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root/"history.json"
            batches.plan(root/"a",history,count=4)
            batches.render_batch(root/"a/manifest.json",root/"preview",history,
                renderer=lambda brief,out:out.write_bytes((brief["idea"]["id"]+"preview").encode()))
            before = batches.load_history(history)
            changed = json.loads((root/"a/manifest.json").read_text())
            item = changed["items"][0]
            idea = item["brief"]["idea"]
            idea["scene"]["entities"][0]["orientation"][0] += 4
            idea["novelty_key"] = batches.pairs.novelty_key(idea)
            item["brief"] = batches.pairs.production_brief(dict(idea=idea,evaluation=batches.pairs.evaluate(idea)))
            # An unchanged ID/pair is insufficient to promote a modified scene.
            batches.validate_manifest(changed)
            (root/"modified.json").write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                batches.render_batch(root/"modified.json",root/"modified_full",history,quality="full",renderer=Mock())
            self.assertFalse((root/"modified_full").exists())
            batches.render_batch(root/"a/manifest.json",root/"full",history,quality="full",
                renderer=lambda brief,out:out.write_bytes((brief["idea"]["id"]+"full").encode()))
            after = batches.load_history(history)
            self.assertEqual(len(after["entries"]),4)
            self.assertTrue(all(e["mode"]=="full" for e in after["entries"]))
            self.assertEqual([e["preview"]["sha256"] for e in after["entries"]],[e["sha256"] for e in before["entries"]])
            with self.assertRaises(ValueError):
                batches.render_batch(root/"a/manifest.json",root/"again",history,quality="full",renderer=Mock())

    def test_failed_or_duplicate_encoding_does_not_record_failed_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root/"history.json"
            batches.plan(root/"a",history,count=4)
            with self.assertRaises(RuntimeError):
                batches.render_batch(root/"a/manifest.json",root/"failed",history,renderer=Mock(side_effect=RuntimeError("encoder failed")))
            self.assertFalse(history.exists())
            with self.assertRaises(ValueError):
                batches.render_batch(root/"a/manifest.json",root/"duplicate",history,renderer=lambda brief,out:out.write_bytes(b"same bytes"))
            self.assertEqual(len(batches.load_history(history)["entries"]),1)
            self.assertEqual(len(list((root/"duplicate").glob("*.mp4"))),1)
            self.assertFalse(history.with_name(history.name+".lock").exists())

    def test_invalid_manifest_is_rejected_before_any_renderer_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root/"history.json"
            manifest = batches.plan(root/"a",history,count=4)
            for mutation in ("duplicate","signature","family","publishing"):
                changed = copy.deepcopy(manifest)
                if mutation == "duplicate":
                    changed["items"][1] = copy.deepcopy(changed["items"][0])
                elif mutation == "publishing":
                    changed["publishing_allowed"] = True
                else:
                    changed["items"][0]["novelty_key" if mutation=="signature" else "family"] = "../escape"
                path = root/"tampered.json"
                path.write_text(json.dumps(changed))
                renderer = Mock()
                with self.assertRaises(ValueError):
                    batches.render_batch(path,root/"videos",history,renderer=renderer)
                renderer.assert_not_called()
                self.assertFalse(history.exists())

    def test_legacy_seen_pairs_are_respected_and_existing_plans_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root/"legacy.json"
            legacy.write_text(json.dumps(dict(schema_version=1,entries=[dict(id="x",novelty_key="x",pair_key="heart|crescent")])) )
            manifest = batches.plan(root/"a",root/"history.json",count=20,pair_history=legacy)
            forbidden = batches.signature("paired_objects",dict(shapes=["crescent","heart"]))
            self.assertNotIn(forbidden,{i["novelty_key"] for i in manifest["items"]})
            before = (root/"a/manifest.json").read_bytes()
            with self.assertRaises(ValueError):
                batches.plan(root/"a",root/"history.json")
            self.assertEqual(before,(root/"a/manifest.json").read_bytes())

    def test_history_lock_blocks_second_writer_and_exhaustion_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root/"history.json"
            with batches.history_lock(path):
                with self.assertRaises(ValueError):
                    with batches.history_lock(path):
                        self.fail("second writer entered")
            with patch("creative_library.candidate_pools",return_value=dict.fromkeys(batches.FAMILIES,[])):
                with self.assertRaisesRegex(ValueError,"exhausted"):
                    batches.plan(root/"a",path)
            self.assertFalse((root/"a").exists())

    def test_invalid_history_cannot_allow_a_repeat_or_create_a_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root/"history.json"
            batches.plan(root/"a",history,count=4)
            batches.render_batch(root/"a/manifest.json",root/"videos",history,
                renderer=lambda brief,out:out.write_bytes(brief["idea"]["id"].encode()))
            original = batches.load_history(history)
            for target in ("version","key","digest","duplicate"):
                changed = copy.deepcopy(original)
                if target=="version":
                    changed["version"] = True
                elif target=="key":
                    changed["entries"][0]["key"] = "fake"
                elif target=="digest":
                    changed["entries"][0]["brief_digest"] = "fake"
                else:
                    changed["entries"].append(copy.deepcopy(changed["entries"][0]))
                history.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    batches.plan(root/target,history)
                self.assertFalse((root/target).exists())


if __name__ == "__main__":
    unittest.main()
