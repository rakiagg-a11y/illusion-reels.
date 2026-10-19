import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import account_studio as a
import account_depth_flip as depth
from bistable_spin import _rx, _ry


ROOT = Path(__file__).resolve().parents[1]


class AccountRoutingTests(unittest.TestCase):
    def test_replacement_and_addition_are_exact(self):
        self.assertEqual(a.ROUTES['hypnotorium'], ('color_echo', 'face_flash'))
        self.assertEqual(a.ROUTES['spiralium_'], ('mirror_flip', 'still_wobble'))
        self.assertEqual(a.ROUTES['opticpop'], ('bistable_spin', 'tilted_pair', 'depth_flip'))
        self.assertNotIn('trustyoureyes_', a.ROUTES)
        for account, mode in [('hypnotorium','motion_form'), ('spiralium_','helix'),
                              ('trustyoureyes_','brainrot_spin')]:
            with self.assertRaises(ValueError):
                a.plan(account, mode=mode)

    def test_monthly_capacity_and_structural_deduplication(self):
        for account in a.ROUTES:
            briefs = a.plan(account, 186)['briefs']
            keys = [a.structural_key(b['mode'], b['parameters']) for b in briefs]
            self.assertEqual(len(set(keys)), 186)
            if account != 'opticpop':
                self.assertEqual([sum(b['mode']==m for b in briefs) for m in a.ROUTES[account]], [93,93])
            self.assertTrue(all(b['publishing_allowed'] is False for b in briefs))
        b = a.plan('hypnotorium',1)['briefs'][0]
        key = a.structural_key(b['mode'],b['parameters'])
        next_brief = a.plan('hypnotorium',1,used=[key])['briefs'][0]
        self.assertEqual(next_brief['mode'], 'face_flash')
        self.assertEqual(key, a.structural_key(b['mode'],dict(b['parameters'])))

    def test_contract_rejects_tampering_before_side_effects(self):
        b = a.plan('hypnotorium',1)['briefs'][0]
        for field, value in [('account','trustyoureyes_'), ('seed',True), ('local_only',False),
                             ('publishing_allowed',True), ('version',True), ('render',{})]:
            bad = copy.deepcopy(b); bad[field] = value
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp)/'no'; history=Path(tmp)/'history.json'
                with self.assertRaises(ValueError):
                    a.render_brief(bad,out,history)
                self.assertFalse(out.exists())
                self.assertFalse(history.exists())
        for seed in [True,-1,1_000_000,'3']:
            with self.assertRaises(ValueError):
                a.plan('hypnotorium',seed=seed)

    def test_historical_shortcuts_and_new_account_shortcuts_match(self):
        for old, new, account in [('motion_paradox','hypnotorium','hypnotorium'),
                                  ('binocular_worlds','spiralium','spiralium_'),
                                  ('reversible_depth','opticpop','opticpop')]:
            outputs=[]
            for script in (old,new):
                run=subprocess.run([sys.executable,str(ROOT/'generators'/(script+'.py')),'--help'],
                    cwd=ROOT.parent,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertIn(account,run.stdout)
                for mode in a.ROUTES[account]:
                    self.assertIn(mode,run.stdout)
                outputs.append(run.stdout.split('options:')[-1])
            self.assertEqual(outputs[0],outputs[1])

    def test_exact_promotion_history_and_failed_encode_do_not_record_success(self):
        b=a.plan('hypnotorium',1)['briefs'][0]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); history=root/'history.json'
            def fake(renderer,target,fps,ffmpeg):
                Path(target).write_bytes(b'video-fixture'*200)
            with patch.object(a,'encode_with_phase_boundary',side_effect=fake):
                a.render_brief(b,root/'preview',history,True)
                other=a.make_brief(b['account'],b['mode'],b['parameters'], b['seed']+1)
                with self.assertRaisesRegex(ValueError,'identical reviewed brief'):
                    a.render_brief(other,root/'wrong',history)
                a.render_brief(b,root/'full',history)
                with self.assertRaisesRegex(ValueError,'already rendered'):
                    a.render_brief(b,root/'again',history)
            next_b=a.plan('hypnotorium',1,used=[e['key'] for e in a.load_history(history)['entries']])['briefs'][0]
            before=history.read_bytes()
            with patch.object(a,'encode_with_phase_boundary',side_effect=RuntimeError('encoder failed')):
                with self.assertRaises(RuntimeError):
                    a.render_brief(next_b,root/'failed',history)
            self.assertEqual(history.read_bytes(),before)
            self.assertFalse(Path(str(history)+'.lock').exists())

    def test_opticpop_old_brief_and_default_history_remain_compatible(self):
        from single_generator import choose_brief
        b=choose_brief('reversible_depth',42,dict(entries=[]))
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'old.json'; source.write_text(json.dumps(b),encoding='utf-8')
            with patch.object(sys,'argv',['opticpop','--brief',str(source),'--out',str(Path(tmp)/'out')]), \
                 patch.object(a,'render_legacy',return_value={}) as old_render:
                a.main('opticpop')
            old_render.assert_called_once()
            self.assertEqual(old_render.call_args.args[0],b)
            self.assertEqual(Path(old_render.call_args.args[2]).name,'ready_generators_history.json')

    def test_catalogue_cannot_be_mutated_by_a_caller(self):
        old=a.parameters_for('tilted_pair')[0]
        candidate=a.parameters_for('tilted_pair')[0]
        candidate['subjects'][0]='invalid'
        self.assertEqual(a.parameters_for('tilted_pair')[0],old)
        brief=a.make_brief('opticpop','tilted_pair',old,42)
        old['subjects'][0]='invalid'
        a.validate_brief(brief)


class DepthFlipTests(unittest.TestCase):
    def test_new_geometry_is_ambiguous_without_a_coded_reversal(self):
        for p in (depth.parameters_for()[0],depth.parameters_for()[-1]):
            points, colors=depth.geometry(p)
            for angle in [0,.8,2.1]:
                expected=depth.project(points,angle,p['tilt'])
                reflected=_rx(_ry(points*[1,1,-1],-math.degrees(angle)),-p['tilt'])[:,:2]
                np.testing.assert_allclose(expected,reflected,atol=1e-9)
            self.assertEqual(colors.shape,points.shape)
            self.assertTrue(np.isfinite(points).all())

    def test_existing_opticpop_renderer_is_reused_exactly(self):
        from five_style_render import Renderer as OldRenderer
        for mode in ['bistable_spin','tilted_pair']:
            brief=a.make_brief('opticpop',mode,a.parameters_for(mode)[0],42)
            new=a.Renderer(brief,180,320)
            old=OldRenderer(brief['legacy_brief'],180,320)
            self.assertEqual(new.frame(2).tobytes(),old.frame(2).tobytes())


if __name__=='__main__':
    unittest.main()
