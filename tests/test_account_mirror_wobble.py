import json
import unittest

import numpy as np
from PIL import ImageOps

import account_mirror_wobble as effects


class MirrorWobbleTests(unittest.TestCase):
    def test_catalogues_are_json_safe_and_structural(self):
        for mode in effects.MODES:
            catalogue = effects.parameters_for(mode)
            signatures = {json.dumps(p, sort_keys=True) for p in catalogue}
            self.assertGreaterEqual(len(signatures),100)
            self.assertEqual(len(catalogue),len(signatures))
            self.assertTrue(all("seed" not in p and "palette" not in p for p in catalogue))
            # Sample each structural axis independently rather than counting
            # unique labels as proof of genuine image variation.
            base = catalogue[0]
            original = effects.Stimulus(mode,base,1,180).frame(0).tobytes()
            for key in base:
                variant = next(p for p in catalogue if p[key] != base[key]
                               and all(p[k] == base[k] for k in base if k != key))
                changed = effects.Stimulus(mode,variant,1,180).frame(0).tobytes()
                self.assertNotEqual(original,changed,(mode,key))

    def test_mirror_is_exact_reflection_of_same_ambiguous_artwork(self):
        stimulus = effects.Stimulus("mirror_flip",effects.parameters_for("mirror_flip")[0],7,450)
        image = stimulus.frame(7)
        source = image.crop(stimulus.source_box)
        reflected = image.crop(stimulus.reflection_box)
        self.assertEqual(ImageOps.flip(source).tobytes(),reflected.tobytes())
        data = np.array(source)
        # The bilateral figure uses shared boundaries: foreground is mirrored
        # left-to-right, with light side faces and a dark central vase.
        centre_column = data[:,data.shape[1]//2]
        self.assertLess(centre_column[len(centre_column)//2,0],50)
        self.assertGreater(data[data.shape[0]//2,10,0],200)
        self.assertEqual(image.mode,"RGB")
        self.assertEqual(image.size,(450,450))

    def test_still_wobble_is_bitwise_static_and_seed_does_not_fake_variants(self):
        parameters = effects.parameters_for("still_wobble")[31]
        a = effects.Stimulus("still_wobble",parameters,7,360)
        reference = a.frame(0).tobytes()
        for time in (0.03,1.7,7.5,14.99):
            self.assertEqual(reference,a.frame(time).tobytes())
        self.assertEqual(reference,effects.Stimulus("still_wobble",parameters,999,360).frame(0).tobytes())
        # Callers cannot accidentally mutate the cached stimulus for later frames.
        changed = a.frame(0)
        changed.putpixel((0,0),(255,0,0))
        self.assertEqual(reference,a.frame(1).tobytes())

    def test_matched_ouchi_control_removes_centre_orientation_change(self):
        parameters = dict(element_length=30,aspect_ratio=5,surround_angle=0,centre_radius=0.25)
        a = effects.Stimulus("still_wobble",parameters,1,900)
        self.assertEqual(a.centre_orientation,(a.surround_orientation+90)%180)
        illusion, control = np.array(a.frame(0)),np.array(a.control_frame())
        yy,xx = np.mgrid[:900,:900]
        centre = (xx-449.5)**2+(yy-449.5)**2 <= 225**2
        self.assertTrue(np.array_equal(illusion[~centre],control[~centre]))
        self.assertGreater(np.count_nonzero(np.any(illusion[centre] != control[centre],axis=1)),1000)
        # No brightness, scale, position or border changes accompany the control.
        x,y = xx-449.5,yy-449.5
        expected = ((np.floor(x/30)+np.floor(y/6)).astype(int)%2).astype(bool)
        expected = np.where(expected,229,36)
        self.assertTrue(np.array_equal(control[100:800,100:800,0],expected[100:800,100:800]))

    def test_invalid_inputs_fail_early(self):
        for mode,parameters,seed,size in (
            ("fake",{},1,300),
            ("mirror_flip",{},1,300),
            ("mirror_flip",effects.parameters_for("mirror_flip")[0],True,300),
            ("still_wobble",effects.parameters_for("still_wobble")[0],1,True),
        ):
            with self.subTest(mode=mode,seed=seed,size=size),self.assertRaises(ValueError):
                effects.Stimulus(mode,parameters,seed,size)
        for mode in effects.MODES:
            stimulus = effects.Stimulus(mode,effects.parameters_for(mode)[0],1,180)
            with self.assertRaises(ValueError):
                stimulus.frame(float("nan"))
            description = effects.describe(mode,stimulus.parameters)
            self.assertFalse(description["physical_motion"])
            self.assertIn("Human review required",description["perceptual_qa"])


if __name__ == "__main__":
    unittest.main()
