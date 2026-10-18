import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock
import creative_director as cd
from render_brief import render_local


class DirectorTests(unittest.TestCase):
    def test_reproducible_and_diverse(self):
        ideas = cd.generate_ideas(42)
        self.assertEqual(ideas, cd.generate_ideas(42))
        self.assertEqual({i["render"]["obj"] for i in ideas}, set(cd.capabilities()))
        self.assertNotEqual(ideas, cd.generate_ideas(43))

    def test_capabilities_match_runtime(self):
        import pointcloud
        self.assertEqual(set(cd.capabilities()), set(pointcloud.OBJECTS) | set(cd.TEXT_OBJECTS))

    def test_feasibility_rejects_unsupported_specs(self):
        base = cd.generate_ideas()[0]
        for key, value in [("obj", "theatre masks"), ("style", "blender"),
                           ("seconds", 12), ("fps", 60), ("seed", True),
                           ("width", 1080.0), ("seed", -1)]:
            idea = copy.deepcopy(base)
            idea["render"][key] = value
            self.assertFalse(cd.evaluate(idea)["eligible"], (key, value))
        idea = copy.deepcopy(base)
        idea["render"]["camera"] = "orbit"
        self.assertFalse(cd.evaluate(idea)["eligible"])

    def test_text_constraints_and_mechanism(self):
        idea = next(i for i in cd.generate_ideas() if i["render"]["obj"] == "hidden word")
        for text in [None, "", " ", "שלום", "TOO LONG FOR THIS RENDERER", "A\nB"]:
            bad = copy.deepcopy(idea)
            bad["render"]["text"] = text
            self.assertFalse(cd.evaluate(bad)["eligible"])
        idea["mechanism"] = "motion aftereffect"
        self.assertFalse(cd.evaluate(idea)["eligible"])

    def test_recent_history_penalty_and_stable_ties(self):
        ideas = cd.generate_ideas()
        obj = ideas[0]["render"]["obj"]
        self.assertGreater(cd.evaluate(ideas[0])["total"], cd.evaluate(ideas[0], [obj])["total"])
        self.assertEqual(cd.rank(ideas), cd.rank(list(reversed(ideas))))

    def test_brief_roundtrip_and_adapter_arguments(self):
        brief = cd.production_brief(cd.rank(cd.generate_ideas())[0])
        brief = json.loads(json.dumps(brief))
        cd.validate_brief(brief)
        self.assertEqual(len(brief["caption"]["hashtags"]), 5)
        runner = Mock(return_value={"ok": True})
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "demo.mp4"
            self.assertEqual(render_local(brief, out, runner), {"ok": True})
            spec = brief["render"]
            runner.assert_called_once_with("pointspin", spec["seed"], str(out), "",
                                           obj=spec["obj"], text=spec["text"])
            out.touch()
            with self.assertRaises(ValueError):
                render_local(brief, out, runner)

    def test_tampered_brief_never_calls_renderer(self):
        brief = cd.production_brief(cd.rank(cd.generate_ideas())[0])
        runner = Mock()
        for key, value in [("publishing_allowed", True), ("schema_version", 2),
                           ("status", "approved")]:
            bad = copy.deepcopy(brief)
            bad[key] = value
            with self.assertRaises(ValueError):
                render_local(bad, "unused.mp4", runner)
        bad = copy.deepcopy(brief)
        bad["render"] = cd.render_spec("cube", 12)
        with self.assertRaises(ValueError):
            render_local(bad, "unused.mp4", runner)
        runner.assert_not_called()

    def test_all_rejected_and_bad_inputs(self):
        with self.assertRaises(ValueError):
            cd.production_brief(cd.rank([{}])[0])
        for value in [[], {}, [1]]:
            with self.assertRaises(ValueError):
                cd.rank(value)

    def test_cli_writes_only_local_planning_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(cd.ROOT / "creative_director.py"),
                                     "--mode", "catalogue", "--out", tmp], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual({p.name for p in Path(tmp).iterdir()},
                             {"ranking.json", "production_brief.json"})
            cd.validate_brief(json.loads((Path(tmp) / "production_brief.json").read_text(encoding="utf-8")))


    def test_actual_scene_geometry_and_preview_frame(self):
        import numpy as np
        import pointcloud as pc
        for obj in cd.capabilities():
            scene = pc.Scene(obj, 42, 15, "LOOK AGAIN" if obj in cd.TEXT_OBJECTS else None)
            self.assertEqual(scene.P.shape[1], 3)
            self.assertTrue(np.isfinite(scene.P).all(), obj)
            self.assertTrue(np.isfinite(scene.Cw).all(), obj)
            self.assertGreater(len(scene.P), 0)
        previous = pc.W, pc.H
        try:
            pc.W, pc.H = 270, 480
            scene = pc.Scene("hidden word", 42, 15, "FOUND ME")
            frame = scene.frame_crisp(0)
            self.assertEqual(frame.shape, (480, 270, 3))
            self.assertEqual(frame.dtype, np.uint8)
            self.assertGreater(frame.max(), 0)
        finally:
            pc.W, pc.H = previous

    def test_rejected_cli_clears_previous_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "production_brief.json").write_text("stale", encoding="utf-8")
            ideas = out / "ideas.json"
            ideas.write_text("[{}]", encoding="utf-8")
            result = subprocess.run([sys.executable, str(cd.ROOT / "creative_director.py"),
                                     "--ideas", str(ideas), "--out", tmp],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((out / "production_brief.json").exists())
            self.assertFalse(json.loads((out / "ranking.json").read_text())[0]["evaluation"]["eligible"])


if __name__ == "__main__":
    unittest.main()
