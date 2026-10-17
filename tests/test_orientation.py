import copy
import json
import math
from pathlib import Path
import unittest

import numpy as np

import concept_director as director
from relational_scene import Scene, orientation_matrix, rotate
from scene_contract import validate_scene


class OrientationTests(unittest.TestCase):
    def setUp(self):
        self.idea = director.generate_concepts()[0]

    def test_old_scenes_render_identically_with_missing_or_zero_orientation(self):
        legacy = copy.deepcopy(self.idea["scene"])
        for entity in legacy["entities"]:
            entity.pop("orientation")
        explicit = copy.deepcopy(legacy)
        for entity in explicit["entities"]:
            entity["orientation"] = [0, 0, 0]
        a, b = Scene(legacy, 3), Scene(explicit, 3)
        for angle in (0, .7, math.pi):
            expected = np.vstack([rotate(p, angle * t + phase) + rotate(c[None, :], angle)[0]
                                  for p, c, t, phase, _ in a.layers])
            np.testing.assert_array_equal(a.positions(angle), b.positions(angle))
            np.testing.assert_allclose(a.positions(angle), expected, atol=1e-14)
        old_idea = copy.deepcopy(self.idea)
        old_idea["scene"] = legacy
        zero_idea = copy.deepcopy(old_idea)
        zero_idea["scene"] = explicit
        self.assertEqual(director.novelty_key(old_idea), director.novelty_key(zero_idea))

    def test_known_axis_rotations_and_rigid_euler_order(self):
        np.testing.assert_allclose([0, 1, 0] @ orientation_matrix([90, 0, 0]), [0, 0, 1], atol=1e-14)
        np.testing.assert_allclose([0, 0, 1] @ orientation_matrix([0, 90, 0]), [1, 0, 0], atol=1e-14)
        np.testing.assert_allclose([1, 0, 0] @ orientation_matrix([0, 0, 90]), [0, 1, 0], atol=1e-14)
        base = orientation_matrix([-18, 9, -15])
        np.testing.assert_allclose(base @ base.T, np.eye(3), atol=1e-14)
        self.assertAlmostEqual(np.linalg.det(base), 1)
        sequential = np.array([.2, .4, .7])
        for angles in ([-18, 0, 0], [0, 9, 0], [0, 0, -15]):
            sequential = sequential @ orientation_matrix(angles)
        np.testing.assert_allclose([.2, .4, .7] @ base, sequential, atol=1e-14)

    def test_pair_has_distinct_tilted_axes_rigid_geometry_and_closed_loop(self):
        sc = Scene(self.idea["scene"], self.idea["seed"])
        axes = [np.array([0, 1, 0]) @ layer[-1] for layer in sc.layers]
        self.assertLess(abs(np.dot(*axes)), .95)
        legacy = copy.deepcopy(self.idea["scene"])
        for entity in legacy["entities"]:
            entity.pop("orientation")
        old = Scene(legacy, self.idea["seed"])
        self.assertGreater(np.max(abs(sc.positions(0)[:, :2] - old.positions(0)[:, :2])), .1)
        np.testing.assert_allclose(sc.positions(0), sc.positions(2 * math.pi), atol=1e-12)
        sizes = [len(layer[0]) for layer in sc.layers]
        for angle in np.linspace(0, 2 * math.pi, 9):
            offset = 0
            for size, (points, center, turns, phase, base) in zip(sizes, sc.layers):
                transformed = sc.positions(angle)[offset:offset + size]
                np.testing.assert_allclose(np.linalg.norm(transformed[1:100] - transformed[0], axis=1),
                                           np.linalg.norm(points[1:100] - points[0], axis=1), atol=1e-12)
                self.assertLess(np.linalg.norm(transformed, axis=1).max() * sc.scale, 1080 / 2)
                offset += size

    def test_invalid_or_unknown_orientation_fields_rejected(self):
        for value in (None, [0, 0], "18,0,0", [True, 0, 0], [0, float("nan"), 0],
                      [0, 0, float("inf")], [181, 0, 0]):
            spec = copy.deepcopy(self.idea["scene"])
            spec["entities"][0]["orientation"] = value
            with self.assertRaises(ValueError):
                validate_scene(spec)
        spec = copy.deepcopy(self.idea["scene"])
        spec["entities"][0]["orientaton"] = [0, 0, 0]
        with self.assertRaises(ValueError):
            validate_scene(spec)

    def test_orientation_is_part_of_signature_and_brief_validation(self):
        changed = copy.deepcopy(self.idea)
        changed["scene"]["entities"][0]["orientation"][0] += 10
        self.assertNotEqual(director.novelty_key(changed), self.idea["novelty_key"])
        self.assertFalse(director.evaluate(changed)["eligible"])
        brief = director.production_brief(director.rank([self.idea])[0])
        director.validate_brief(brief)
        brief["render"]["scene"]["entities"][0]["orientation"][2] += 10
        with self.assertRaises(ValueError):
            director.validate_brief(brief)

    def test_tilted_non_coplanar_arcs_cannot_claim_completion(self):
        idea = next(i for i in director.generate_concepts(42, "geometry")
                    if i["illusion"]["mechanism"] == "overlap_completion")
        idea["scene"]["entities"][0]["orientation"] = [20, 0, 0]
        idea["novelty_key"] = director.novelty_key(idea)
        self.assertFalse(director.evaluate(idea)["eligible"])

    def test_checked_in_tilted_pair_brief_is_renderable(self):
        path = Path(__file__).resolve().parents[1] / "samples/angled_pair/production_brief.json"
        brief = json.loads(path.read_text(encoding="utf-8"))
        director.validate_brief(brief)
        spec = brief["render"]["scene"]
        self.assertEqual([e["shape"] for e in spec["entities"]], ["butterfly", "hourglass"])
        self.assertTrue(all(any(e["orientation"]) for e in spec["entities"]))
        self.assertFalse(brief["publishing_allowed"])


if __name__ == "__main__":
    unittest.main()
