import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import five_styles as d
import five_style_render as r


def brief(mode, seed=42):
    style = next(style for style, modes in d.MODES.items() if mode in modes)
    account = next(a for a in d.default_accounts()["accounts"] if a["style"] == style)
    return d.make_brief(account, mode, d.parameters_for(mode)[0], seed)


class FiveStyleContractTests(unittest.TestCase):
    def test_five_accounts_are_a_bijection_of_five_styles(self):
        config = d.default_accounts()
        self.assertEqual(len(d.STYLES), 5)
        self.assertEqual(set(a["style"] for a in d.validate_accounts(config)["accounts"]), set(d.STYLES))
        config["accounts"][1]["style"] = config["accounts"][0]["style"]
        with self.assertRaises(ValueError):
            d.validate_accounts(config)

    def test_custom_account_ids_can_be_reordered(self):
        account = dict(id="opticpop", handle="@newpage", style="perception_lab")
        self.assertEqual(d.make_brief(account, "troxler", d.parameters_for("troxler")[0], 1)["account"], account)

    def test_plan_is_deterministic_and_mode_diverse(self):
        a = d.plan(d.default_accounts(), 52, 5)
        self.assertEqual(a, d.plan(d.default_accounts(), 52, 5))
        self.assertEqual(len(a["briefs"]), 25)
        for style in d.STYLES:
            self.assertEqual({b["mode"] for b in a["briefs"] if b["style"] == style}, set(d.MODES[style]))
        self.assertEqual(len({b["id"] for b in a["briefs"]}), 25)

    def test_history_avoids_structural_repeats_across_accounts(self):
        a = d.plan(d.default_accounts(), 42, 3)
        keys = [d.structural_key(b["style"], b["mode"], b["parameters"]) for b in a["briefs"]]
        b = d.plan(d.default_accounts(), 42, 3, keys)
        self.assertFalse(set(x["id"] for x in a["briefs"]) & set(x["id"] for x in b["briefs"]))

    def test_seed_palette_and_copy_do_not_create_novelty(self):
        b = brief("motion_form")
        old = b["id"]
        b["seed"] += 1
        b["palette"] = "amber_cyan"
        self.assertEqual(d.validate_brief(b)["id"], old)

    def test_untrusted_brief_cannot_change_style_or_render_contract(self):
        for mutation in (lambda b: b.update(local_only=False),
                         lambda b: b.update(mode="afterimage"),
                         lambda b: b["render"].update(seconds=900),
                         lambda b: b["parameters"].update(direction=True),
                         lambda b: b.update(code="import os"),
                         lambda b: b["account"].update(style="perception_lab")):
            b = brief("motion_form")
            mutation(b)
            with self.assertRaises(ValueError):
                d.validate_brief(b)

    def test_exact_history_promotion_and_preflight(self):
        plan = d.plan(d.default_accounts(), 42, 1)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, history = root/"plan.json", root/"history.json"
            source.write_text(json.dumps(plan), encoding="utf-8")
            b = plan["briefs"][0]
            entry = dict(key=d.structural_key(b["style"], b["mode"], b["parameters"]),
                         brief_digest=d.digest(b), quality="preview", sha256="a"*64, output="preview.mp4")
            r.atomic_json(history, dict(kind="five_style_history", version=1, entries=[entry]))
            b["seed"] += 1
            source.write_text(json.dumps(plan), encoding="utf-8")
            with patch.object(r, "encode") as encoder:
                with self.assertRaisesRegex(ValueError, "identical reviewed brief"):
                    r.render_plan(source, root/"out", history)
                encoder.assert_not_called()
            self.assertFalse((root/"out").exists())

    def test_lock_excludes_concurrent_render(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"history.json"
            with r.history_lock(path):
                with self.assertRaisesRegex(ValueError, "locked"):
                    with r.history_lock(path):
                        pass
            self.assertFalse(Path(str(path)+".lock").exists())


class PerceptualInvariantTests(unittest.TestCase):
    def test_normalized_particle_brightness_survives_resolution_change(self):
        from PIL import Image
        rng = np.random.default_rng(18)
        points = rng.uniform(-.35, .35, (2000, 2))
        colors = np.tile([.8, .1, .2], (len(points), 1))
        small = np.asarray(r.splat(points, colors, 180, 2., 1.))
        big = np.asarray(r.splat(points, colors, 540, 2., 3.).resize((180,180), Image.Resampling.LANCZOS))
        self.assertLess(abs(float(big.mean())-float(small.mean()))/small.mean(), .15)

    def test_stereo_zero_plane_disparity_and_near_far_sign(self):
        pts = np.array([[.1, .2, 0], [.1, .2, -.8], [.1, .2, .8]])
        left, right = r.stereo_project(pts, -.06), r.stereo_project(pts, .06)
        disparity = left[:, 0]-right[:, 0]
        self.assertAlmostEqual(disparity[0], 0)
        self.assertGreater(disparity[1], 0)
        self.assertLess(disparity[2], 0)
        np.testing.assert_allclose(left[:, 1], right[:, 1])

    def test_infinite_regress_patch_centers_never_move_horizontally(self):
        p = brief("infinite_regress")["parameters"]
        a, b = np.array(r.gabor_centers(p, 0)), np.array(r.gabor_centers(p, 3.75))
        np.testing.assert_array_equal(a[:, 2], b[:, 2])
        self.assertGreater(np.max(abs(a[:, 3]-b[:, 3])), .05)

    def test_muller_lyer_targets_keep_equal_lengths_during_control(self):
        renderer = r.Renderer(brief("muller_lyer"), 360, 640)
        for t in (0, 11):
            arr = np.asarray(renderer.frame(t))
            red = (arr[:, :, 0] > 180) & (arr[:, :, 1] < 100) & (arr[:, :, 2] < 120)
            ys = np.where(red.sum(axis=1) > 150)[0]
            top = red[ys[0]:ys[len(ys)//2]+1].any(axis=0)
            bottom = red[ys[len(ys)//2]:ys[-1]+1].any(axis=0)
            np.testing.assert_array_equal(top, bottom)

    def test_ranking_prioritizes_compression_resistant_noise(self):
        a, b = copy.deepcopy(brief("motion_form")["parameters"]), copy.deepcopy(brief("motion_form")["parameters"])
        a["dot_size"], b["dot_size"] = 2, 4
        self.assertLess(d.evaluate("motion_form", a)["total"], d.evaluate("motion_form", b)["total"])

    def test_motion_form_is_recoverable_from_temporal_correspondence(self):
        renderer = r.Renderer(brief("motion_form"), 360, 640)
        a = renderer.motion_noise(0)
        dt = renderer.seconds/renderer.cells
        b = renderer.motion_noise(dt)
        mask = renderer.motion_mask
        # Erode by one pixel to exclude aperture-boundary replacements.
        from scipy.ndimage import binary_erosion
        inside, outside = binary_erosion(mask, iterations=2), binary_erosion(~mask, iterations=2)
        shift = renderer.p["direction"]
        self.assertGreater(np.mean(b[inside] == np.roll(a, shift, axis=0)[inside]), .98)
        self.assertGreater(np.mean(b[outside] == np.roll(a, -shift, axis=0)[outside]), .98)
        self.assertLess(abs(float(a[inside].mean())-float(a[outside].mean())), .08)
        self.assertGreater(np.mean(b[inside] != np.roll(a, -shift, axis=0)[inside]), .35)

    def test_autostereogram_encodes_flat_plane_with_expected_period(self):
        from more_illusions import autostereogram
        rng = np.random.default_rng(1)
        tex = rng.integers(0, 256, (40, 32, 3), dtype=np.uint8)
        for depth, separation in ((0., 32), (1., 26)):
            pattern = autostereogram(np.full((40, 180), depth), tex, 32, 6)
            np.testing.assert_array_equal(pattern[:, 45:120], pattern[:, 45+separation:120+separation])

    def test_afterimage_test_is_achromatic_without_colored_shape(self):
        renderer = r.Renderer(brief("afterimage"), 360, 640)
        arr = np.asarray(renderer.cache["test"])
        np.testing.assert_array_equal(arr[:, :, 0], arr[:, :, 1])
        self.assertEqual(np.unique(arr).tolist(), [140])
        self.assertFalse(np.array_equal(renderer.frame(17), renderer.frame(19)))

    def test_troxler_is_physically_static_not_an_animated_fade(self):
        renderer = r.Renderer(brief("troxler"), 360, 640)
        np.testing.assert_array_equal(np.asarray(renderer.frame(0)), np.asarray(renderer.frame(20)))

    def test_all_supported_modes_render_and_loop_as_specified(self):
        for modes in d.MODES.values():
            for mode in modes:
                with self.subTest(mode=mode):
                    renderer = r.Renderer(brief(mode), 360, 640)
                    frame = np.asarray(renderer.frame(0))
                    self.assertEqual(frame.shape, (640, 360, 3))
                    self.assertEqual(frame.dtype, np.uint8)
                    self.assertGreater(frame.std(), 10)
                    np.testing.assert_array_equal(frame, np.asarray(renderer.frame(renderer.seconds)))

    def test_camera_axes_are_distinct_and_fixed_in_pair_spec(self):
        from relational_scene import orientation_matrix
        p = brief("tilted_pair")["parameters"]
        a, b = r.pair_spec(p)["entities"]
        axis_a = np.array([0., 1., 0.]) @ orientation_matrix(a["orientation"])
        axis_b = np.array([0., 1., 0.]) @ orientation_matrix(b["orientation"])
        self.assertGreater(np.degrees(np.arccos(np.clip(axis_a @ axis_b, -1, 1))), 20)


if __name__ == "__main__":
    unittest.main()
