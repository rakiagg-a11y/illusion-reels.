import math
import unittest

import numpy as np

import bistable_spin as b
import five_styles as d
from single_generator import choose_brief


class BistableSpinTests(unittest.TestCase):
    def test_every_frame_also_fits_the_opposite_spin(self):
        # Depth-mirrored object, opposite spin and opposite tilt project to the same pixels,
        # so nothing in the image decides the direction.
        for shape in b.SHAPES:
            points, _, _ = b.geometry(np.random.default_rng(1), shape)
            for angle in (0., .7, 2.1):
                a = b.project(points, angle, 18)
                mirrored = b._rx(b._ry(points*[1, 1, -1], -math.degrees(angle)-30), -18)[:, :2]
                np.testing.assert_allclose(a, mirrored, atol=1e-9)

    def test_opticpop_defaults_to_bistable_spin_with_matching_hook(self):
        brief = choose_brief("reversible_depth", 7, dict(entries=[]))
        self.assertEqual(brief["mode"], "bistable_spin")
        self.assertEqual(brief["caption"]["hook"], d.SPIN_HOOKS[brief["parameters"]["shape"]])
        self.assertEqual(choose_brief("reversible_depth", 7, dict(entries=[]), "tilted_pair")["mode"], "tilted_pair")

    def test_exhausted_spin_catalogue_falls_back_to_other_modes(self):
        used = [dict(key=d.structural_key("reversible_depth", "bistable_spin", p))
                for p in d.parameters_for("bistable_spin")]
        self.assertEqual(choose_brief("reversible_depth", 7, dict(entries=used))["mode"], "tilted_pair")


if __name__ == "__main__":
    unittest.main()


class BrainrotSpinTests(unittest.TestCase):
    def test_brainrot_figures_also_fit_the_opposite_spin(self):
        import brainrot
        for character in brainrot.CHARACTERS:
            points, _, _ = brainrot.geometry(np.random.default_rng(1), character)
            a = b.project(points, .9, 14)
            mirrored = b._rx(b._ry(points*[1, 1, -1], -math.degrees(.9)-30), -14)[:, :2]
            np.testing.assert_allclose(a, mirrored, atol=1e-9)

    def test_trustyoureyes_defaults_to_brainrot_with_character_hook(self):
        brief = choose_brief("perception_lab", 3, dict(entries=[]))
        self.assertEqual(brief["mode"], "brainrot_spin")
        self.assertEqual(brief["caption"]["hook"], d.BRAINROT_HOOKS[brief["parameters"]["character"]])
