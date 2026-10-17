import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import numpy as np
import concept_director as d
import creative_director as legacy
import pointcloud as pc
from relational_scene import Scene
from render_brief import render_local
from scene_contract import validate_scene


class ConceptTests(unittest.TestCase):
    def setUp(self):
        self.ideas = d.generate_concepts(42, "emotion")
        self.rows = d.rank(self.ideas)
        self.brief = d.production_brief(self.rows[0])

    def test_composition_and_reproducibility(self):
        self.assertEqual(self.ideas, d.generate_concepts(42, "emotion"))
        self.assertNotEqual(self.ideas, d.generate_concepts(43, "emotion"))
        ready = [i for i in self.ideas if i["scene"]]
        self.assertEqual(len({d.novelty_key(i) for i in ready}), len(ready))
        self.assertGreaterEqual(len({i["illusion"]["mechanism"] for i in ready}), 2)
        self.assertTrue(any(len(i["scene"]["entities"]) > 1 for i in ready))
        self.assertTrue(all(d.evaluate(i)["eligible"] for i in ready))

    def test_theme_changes_scene_grammar(self):
        emotion = d.generate_concepts(42, "emotion")
        identity = d.generate_concepts(42, "identity")
        self.assertNotEqual(emotion[0]["scene"], identity[0]["scene"])
        self.assertEqual(d.generate_concepts(42, "רגש"), emotion)

    def test_development_proposals_are_retained_but_not_briefed(self):
        backlog = [r for r in self.rows if r["evaluation"]["status"] == "needs_extension"]
        self.assertEqual(len(backlog), 2)
        for row in backlog:
            self.assertTrue(row["evaluation"]["missing_capabilities"])
            with self.assertRaises(ValueError):
                d.production_brief(row)

    def test_color_and_copy_are_not_new_concepts(self):
        idea = copy.deepcopy(self.ideas[0])
        old = d.novelty_key(idea)
        idea["scene"]["entities"][0]["color"] = "cyan"
        idea["hook"] = "Look again"
        self.assertEqual(old, d.novelty_key(idea))
        self.assertGreater(d.evaluate(idea)["total"], d.evaluate(idea, [old])["total"])

    def test_claimed_mechanism_and_signature_must_match_geometry(self):
        for mutation in ("mechanism", "novelty"):
            idea = copy.deepcopy(self.ideas[0])
            if mutation == "mechanism":
                idea["illusion"]["mechanism"] = "negative_space_face"
            else:
                idea["novelty_key"] = "fake"
            self.assertFalse(d.evaluate(idea)["eligible"])

    def test_scene_contract_rejects_resource_and_numeric_errors(self):
        original = self.ideas[0]["scene"]
        for field, value in [("turns", True), ("turns", 99), ("scale", float("nan")),
                             ("phase", float("inf")), ("center", [0, 0, 8]),
                             ("shape", "third_face"), ("expression", "angry"),
                             ("color", "opaque_black")]:
            spec = copy.deepcopy(original)
            spec["entities"][0][field] = value
            with self.assertRaises(ValueError, msg=field):
                validate_scene(spec)
        for count in (0, 1, 4):
            spec = copy.deepcopy(original)
            spec["entities"] = spec["entities"][:1] * count
            with self.assertRaises(ValueError):
                validate_scene(spec)

    def test_completion_requires_complementary_geometry(self):
        idea = copy.deepcopy(next(i for i in self.ideas if i["scene"] and
                                  i["illusion"]["mechanism"] == "overlap_completion"))
        idea["scene"]["entities"][1]["phase"] = 90
        idea["novelty_key"] = d.novelty_key(idea)
        self.assertFalse(d.evaluate(idea)["eligible"])

    def test_ranking_stable_and_history_penalized(self):
        self.assertEqual(self.rows, d.rank(list(reversed(self.ideas))))
        best = self.rows[0]["idea"]
        self.assertLess(d.evaluate(best, [best["novelty_key"]])["total"],
                        d.evaluate(best)["total"])

    def test_all_generated_scenes_build_and_loop_geometrically(self):
        for idea in self.ideas:
            if not idea["scene"]:
                continue
            sc = Scene(idea["scene"], idea["seed"])
            self.assertTrue(np.isfinite(sc.P).all())
            self.assertEqual(sc.P.shape, sc.Cw.shape)
            np.testing.assert_allclose(sc.positions(0), sc.positions(4 * math.pi), atol=1e-12)
            maxnorm = np.linalg.norm(sc.positions(math.pi / 3), axis=1).max()
            self.assertLess(maxnorm * sc.scale, pc.W / 2)

    def test_frame_has_both_colors_and_changes_during_turn(self):
        previous = pc.W, pc.H
        try:
            pc.W, pc.H = 180, 320
            sc = Scene(self.ideas[0]["scene"], self.ideas[0]["seed"])
            a = sc.frame_crisp(0, dot=1.1 * pc.W / 1080)
            b = sc.frame_crisp(math.pi / 2, dot=1.1 * pc.W / 1080)
            self.assertEqual(a.shape, (320, 180, 3))
            self.assertGreater(int(a[:, :, 0].max()), 100)
            self.assertGreater(int(a[:, :, 2].max()), 100)
            self.assertFalse(np.array_equal(a, b))
        finally:
            pc.W, pc.H = previous

    def test_brief_roundtrip_and_generator_adapter(self):
        brief = json.loads(json.dumps(self.brief))
        self.assertEqual(legacy.validate_brief(brief), brief["render"])
        runner = Mock(return_value={"ok": True})
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "test.mp4"
            render_local(brief, out, runner)
            runner.assert_called_once_with("opticpop", brief["render"]["seed"], str(out), "",
                                           scene=brief["render"]["scene"], creative_caption=brief["caption"])

    def test_tampering_cannot_reach_generator(self):
        runner = Mock()
        for target in ("render", "caption", "publishing", "schema"):
            brief = copy.deepcopy(self.brief)
            if target == "render":
                brief["render"]["scene"]["entities"][0]["turns"] = -2
            elif target == "caption":
                brief["caption"]["full_caption"] = "unrelated claim"
            elif target == "publishing":
                brief["publishing_allowed"] = True
            else:
                brief["schema_version"] = 2.0
            with self.assertRaises(ValueError):
                render_local(brief, "unused.mp4", runner)
        runner.assert_not_called()

    def test_generate_routes_scene_and_uses_exact_brief_caption(self):
        import generate
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "test.mp4"
            with patch("relational_scene.render", return_value={"style": "opticpop"}) as renderer:
                meta = generate.run("opticpop", self.brief["render"]["seed"], str(out), "",
                                    scene=self.brief["render"]["scene"], creative_caption=self.brief["caption"])
            self.assertEqual(meta["full_caption"], self.brief["caption"]["full_caption"])
            self.assertEqual(json.loads(out.with_suffix(".json").read_text(encoding="utf-8")), meta)
            renderer.assert_called_once()

    def test_model_proposal_import_derives_only_missing_signatures(self):
        ideas = copy.deepcopy(self.ideas)
        for idea in ideas:
            idea.pop("novelty_key")
        normalized = d.normalize_proposals(ideas)
        self.assertEqual(normalized, self.ideas)
        self.assertNotIn("novelty_key", ideas[0])
        normalized[0]["novelty_key"] = "mismatch"
        self.assertFalse(d.evaluate(d.normalize_proposals(normalized)[0])["eligible"])

    def test_auto_style_remains_existing_pointspin(self):
        import generate
        self.assertEqual(generate.STYLES, ["pointspin"])
        self.assertNotIn("opticpop", generate.STYLES)

    def test_default_cli_concepts_and_selection(self):
        with tempfile.TemporaryDirectory() as temp:
            args = [sys.executable, str(legacy.ROOT / "creative_director.py"),
                    "--theme", "emotion", "--out", temp, "--select", self.ideas[0]["id"]]
            result = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            brief = json.loads((Path(temp) / "production_brief.json").read_text(encoding="utf-8"))
            self.assertEqual(brief["schema_version"], 2)
            self.assertEqual(brief["idea"]["id"], self.ideas[0]["id"])
            legacy.validate_brief(brief)


if __name__ == "__main__":
    unittest.main()
