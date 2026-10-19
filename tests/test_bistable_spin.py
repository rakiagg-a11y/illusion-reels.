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
            points, _ = brainrot.geometry(np.random.default_rng(1), character, total=4000)
            a = b.project(points, .9, 14)
            mirrored = b._rx(b._ry(points*[1, 1, -1], -math.degrees(.9)-30), -14)[:, :2]
            np.testing.assert_allclose(a, mirrored, atol=1e-9)

    def test_duos_add_each_pair_once_after_the_original_grid(self):
        import itertools
        import brainrot
        rows = d.parameters_for("brainrot_spin")
        singles = [dict(character=c, tilt=t, turns=n)
                   for c, t, n in itertools.product(brainrot.CHARACTERS, brainrot.TILTS, (2, 3))]
        self.assertEqual(rows[:len(singles)], singles)
        duos = rows[len(singles):]
        n = len(brainrot.CHARACTERS)
        self.assertEqual(len(duos), n*(n-1)//2)
        self.assertEqual(len({frozenset((r["character"], r["partner"])) for r in duos}), len(duos))

    def test_duo_figures_stay_between_the_text_and_the_bottom_overlay(self):
        from five_style_render import Renderer
        account = next(a for a in d.default_accounts()["accounts"] if a["id"] == "trustyoureyes_")
        brief = d.make_brief(account, "brainrot_spin", d.parameters_for("brainrot_spin")[-1], 3)
        self.assertEqual(brief["caption"]["hook"], "Are they spinning the same way?")
        renderer = Renderer(brief, 540, 960)
        for t in (0., 2.5, 5.):
            pixels = np.asarray(renderer.frame(t)).max(2)
            # Same band as a single figure: below the instruction lines, above the bottom overlay.
            self.assertGreater(pixels[round(960*.26):round(960*.63)].max(), 40)
            self.assertLessEqual(pixels[round(960*.23):round(960*.25)].max(), 30)
            self.assertLessEqual(pixels[round(960*.65):round(960*.77)].max(), 30)

    def test_trustyoureyes_defaults_to_brainrot_with_character_hook(self):
        brief = choose_brief("perception_lab", 3, dict(entries=[]))
        self.assertEqual(brief["mode"], "brainrot_spin")
        self.assertEqual(brief["caption"]["hook"], __import__("brainrot").hook(brief["parameters"]["character"], brief["parameters"].get("partner")))
