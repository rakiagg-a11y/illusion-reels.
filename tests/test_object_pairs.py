import copy
import math
import unittest
import numpy as np
import concept_director as d
import pointcloud as pc
from relational_scene import Scene, geometry, outline
from scene_contract import OBJECT_SHAPES, validate_scene


class ObjectPairTests(unittest.TestCase):
    def test_default_batch_is_twelve_renderable_nonface_pairs(self):
        ideas=d.generate_concepts()
        self.assertEqual(len(ideas),12)
        self.assertEqual(ideas,d.generate_concepts(42,"אובייקטים"))
        self.assertEqual(len({i["novelty_key"] for i in ideas}),12)
        found=set()
        for idea in ideas:
            entities=idea["scene"]["entities"]
            self.assertEqual(len(entities),2)
            self.assertTrue(all(e["shape"] in OBJECT_SHAPES and e["expression"] is None for e in entities))
            self.assertTrue(d.evaluate(idea)["eligible"])
            self.assertEqual(idea["illusion"]["mechanism"],"transparent_depth_ambiguity")
            found.update(e["shape"] for e in entities)
        self.assertEqual(found,set(OBJECT_SHAPES))

    def test_pair_mode_scales_to_requested_count_and_preserves_reference_motion(self):
        for count in (4,12,40):
            ideas=d.generate_concepts(52,"paired_objects",count)
            self.assertEqual(len(ideas),count)
            self.assertEqual(len({i["novelty_key"] for i in ideas}),count)
        for idea in d.generate_concepts()[:10]:
            a,b=idea["scene"]["entities"]
            self.assertEqual((a["turns"],b["turns"]),(1,1))
            self.assertEqual(idea["scene"]["layout"],"orbit")

    def test_all_new_geometry_is_finite_nonflat_and_reproducible(self):
        for shape in OBJECT_SHAPES:
            p,w=geometry(np.random.default_rng(3),shape)
            p2,w2=geometry(np.random.default_rng(3),shape)
            np.testing.assert_array_equal(p,p2)
            np.testing.assert_array_equal(w,w2)
            self.assertTrue(np.isfinite(p).all(),shape)
            self.assertEqual(len(p),len(w))
            self.assertGreater(np.ptp(p[:,2]),.1,shape)
            self.assertLess(len(p),20000)
            self.assertGreater(w.min(),0)
        with self.assertRaises(ValueError):
            outline("unimplemented_leaf")

    def test_new_shapes_reject_facial_expression(self):
        spec=copy.deepcopy(d.generate_concepts()[0]["scene"])
        spec["entities"][0]["expression"]="smile"
        with self.assertRaises(ValueError):
            validate_scene(spec)

    def test_frames_are_distinct_and_pair_loop_closes(self):
        previous=pc.W,pc.H
        try:
            pc.W,pc.H=180,320
            images=[]
            for idea in d.generate_concepts()[:3]:
                sc=Scene(idea["scene"],idea["seed"])
                np.testing.assert_allclose(sc.positions(0),sc.positions(4*math.pi),atol=1e-12)
                a=sc.frame_crisp(0,dot=1.1*pc.W/1080)
                b=sc.frame_crisp(math.pi/2,dot=1.1*pc.W/1080)
                self.assertEqual(a.shape,(320,180,3))
                self.assertFalse(np.array_equal(a,b))
                self.assertGreater(a.max(),100)
                images.append(a)
            self.assertFalse(np.array_equal(images[0],images[1]))
        finally:
            pc.W,pc.H=previous

    def test_same_rate_pair_is_preferred_in_pair_theme(self):
        idea=d.generate_concepts()[0]
        opposing=copy.deepcopy(idea)
        opposing["scene"]["entities"][1]["turns"]=-1
        opposing["novelty_key"]=d.novelty_key(opposing)
        self.assertGreater(d.evaluate(idea)["total"],d.evaluate(opposing)["total"])


if __name__=="__main__":
    unittest.main()
