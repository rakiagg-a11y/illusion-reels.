import hashlib
import json
import unittest

import numpy as np
from PIL import ImageOps

import account_color_face as effects


class ColorFaceControls(unittest.TestCase):
    def test_catalogues_are_structural_unique_and_bounded(self):
        for mode in effects.MODES:
            pool = effects.parameters_for(mode)
            encoded = [json.dumps(p, sort_keys=True) for p in pool]
            self.assertEqual(len(pool), 120)
            self.assertEqual(len(set(encoded)), len(pool))
            self.assertFalse(any("seed" in p or "palette" in p for p in pool))
        # Families change actual artwork, not just catalogue labels.
        for mode in effects.MODES:
            pool = effects.parameters_for(mode)
            hashes = [hashlib.sha256(effects.Stimulus(mode, p, 4, 160).frame(0).tobytes()).hexdigest()
                      for p in pool]
            self.assertEqual(len(set(hashes)), len(hashes))

    def test_afterimage_has_static_adapter_and_achromatic_aligned_test(self):
        for scene in ("terrace", "mountain", "botanical"):
            p = next(p for p in effects.parameters_for("color_echo") if p["scene"] == scene)
            stimulus = effects.Stimulus("color_echo", p, 7, 240)
            adapter = stimulus.frame(0)
            self.assertEqual(adapter.tobytes(), stimulus.frame(17.999).tobytes())
            test = stimulus.frame(18)
            self.assertEqual(test.tobytes(), stimulus.frame(23.99).tobytes())
            a = np.asarray(test)
            self.assertTrue(np.array_equal(a[:, :, 0], a[:, :, 1]))
            self.assertTrue(np.array_equal(a[:, :, 1], a[:, :, 2]))
            # A pixelwise transform proves spatial alignment throughout the image,
            # including the fixation mark; no edge can shift at the transition.
            self.assertEqual(ImageOps.grayscale(adapter).tobytes(), test.convert("L").tobytes())
            self.assertFalse(np.array_equal(np.asarray(adapter)[:, :, 0], np.asarray(adapter)[:, :, 1]))
            self.assertGreater(np.std(a[:, :, 0]), 25)
            self.assertEqual(stimulus.control_frame(0).tobytes(), test.tobytes())
            self.assertEqual(stimulus.control_frame(18).tobytes(), test.tobytes())

    def test_faces_are_static_per_interval_with_fixed_eyes_and_no_blank_strobe(self):
        p = effects.parameters_for("face_flash")[42]
        stimulus = effects.Stimulus("face_flash", p, 17, 240)
        eyes = stimulus.eye_positions
        self.assertEqual(len(eyes), 4)
        self.assertEqual(len({y for _, y in eyes}), 1)
        means = []
        for i in range(48):
            first, last = stimulus.frame(i*.25), stimulus.frame(i*.25+.249)
            self.assertEqual(first.tobytes(), last.tobytes())
            self.assertEqual(stimulus.eye_positions, eyes)
            means.append(float(np.asarray(first).mean()))
            # The pupils stay dark at exactly the same fixed anchors.
            for x, y in eyes:
                self.assertLess(np.asarray(first)[y, x].mean(), 65)
        # Ordinary changes in the face area introduce some mean variation;
        # there are no near-black/white blank flashes between identities.
        self.assertLess(max(means)-min(means), 10)
        self.assertNotEqual(stimulus.frame(0).tobytes(), stimulus.frame(.25).tobytes())
        self.assertNotEqual(stimulus.identity_at(0), stimulus.identity_at(.25))
        self.assertNotEqual(*stimulus.identity_at(0))
        self.assertEqual(stimulus.control_frame(0).tobytes(), stimulus.frame(0).tobytes())
        self.assertNotEqual(stimulus.control_frame(.25).tobytes(), stimulus.frame(.25).tobytes())
        self.assertEqual(stimulus.control_frame(.5).tobytes(), stimulus.frame(.25).tobytes())
        # Returning a portrait cannot let a caller mutate the renderer's asset.
        original = stimulus.portrait(2).tobytes()
        changed = stimulus.portrait(2)
        changed.paste((255, 0, 255), (0, 0, changed.width, changed.height))
        self.assertEqual(stimulus.portrait(2).tobytes(), original)

    def test_determinism_input_validation_and_metadata(self):
        for mode in effects.MODES:
            p = effects.parameters_for(mode)[5]
            a, b = (effects.Stimulus(mode, p, 93, 180) for _ in range(2))
            self.assertEqual(a.frame(1).tobytes(), b.frame(1).tobytes())
            self.assertIn("physical_control", effects.describe(mode, p))
            for t in (-1, float("nan"), float("inf")):
                with self.assertRaises(ValueError):
                    a.frame(t)
        for args in (("fake", {}, 1, 180), ("face_flash", {}, 1, 180),
                     ("face_flash", effects.parameters_for("face_flash")[0], True, 180),
                     ("face_flash", effects.parameters_for("face_flash")[0], 1, 80)):
            with self.assertRaises(ValueError):
                effects.Stimulus(*args)


if __name__ == "__main__":
    unittest.main()
