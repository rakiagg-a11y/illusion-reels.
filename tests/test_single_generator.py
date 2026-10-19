import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import five_styles as d
import five_style_render as r
from single_generator import choose_brief


class IndependentGeneratorTests(unittest.TestCase):
    def test_each_runner_has_only_its_own_modes(self):
        root=Path(__file__).resolve().parents[1]
        from account_studio import ROUTES
        replacements={'motion_paradox':'hypnotorium','binocular_worlds':'spiralium_',
                      'reversible_depth':'opticpop'}
        for style in d.STYLES:
            with self.subTest(style=style):
                run=subprocess.run([sys.executable,str(root/'generators'/(style+'.py')),'--help'],
                                   cwd=root.parent,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                self.assertIn(replacements.get(style,style),run.stdout)
                for mode in ROUTES[replacements[style]] if style in replacements else d.MODES[style]:
                    self.assertIn(mode,run.stdout)
                other=next(s for s in d.STYLES if s!=style)
                invalid=subprocess.run([sys.executable,str(root/'generators'/(style+'.py')),
                    '--out','unused','--mode',d.MODES[other][0]],cwd=root.parent,capture_output=True,text=True)
                self.assertNotEqual(invalid.returncode,0)

    def test_selection_is_reproducible_and_reserved_previews_are_skipped(self):
        history=dict(entries=[])
        a=choose_brief('motion_paradox',42,history,mode='motion_form')
        self.assertEqual(a,choose_brief('motion_paradox',42,history,mode='motion_form'))
        key=d.structural_key(a['style'],a['mode'],a['parameters'])
        history['entries'].append(dict(key=key,quality='preview'))
        b=choose_brief('motion_paradox',42,history,mode='motion_form')
        self.assertNotEqual(a['id'],b['id'])

    def test_invalid_style_account_and_seed_do_not_reach_renderer(self):
        for kwargs in (dict(style='unknown',seed=1),dict(style='reversible_depth',seed=True),
                       dict(style='reversible_depth',seed=1,mode='afterimage'),
                       dict(style='reversible_depth',seed=1,account_id='../escape')):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                choose_brief(history=dict(entries=[]),**kwargs)

    def test_one_generator_renders_records_and_promotes_the_exact_brief(self):
        b=choose_brief('perception_lab',42,dict(entries=[]),mode='muller_lyer')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);history=root/'history.json'
            def fake_encode(renderer,target,fps,ffmpeg):
                Path(target).write_bytes(b'encoded-video-fixture'*100)
            with patch.object(r,'encode',side_effect=fake_encode):
                preview=r.render_one(b,root/'preview',history,True)
                self.assertEqual(len(preview['outputs']),1)
                changed=copy.deepcopy(b);changed['seed']+=1
                with self.assertRaisesRegex(ValueError,'identical reviewed brief'):
                    r.render_one(changed,root/'changed',history)
                self.assertFalse((root/'changed').exists())
                full=r.render_one(b,root/'full',history)
                self.assertEqual(full['quality'],'full')
                self.assertEqual(len(r.load_history(history)['entries']),2)
                with self.assertRaisesRegex(ValueError,'already rendered'):
                    r.render_one(b,root/'duplicate',history)

    def test_another_style_brief_is_rejected_by_fixed_entry_point(self):
        b=choose_brief('perception_lab',1,dict(entries=[]),mode='muller_lyer')
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'brief.json'
            source.write_text(json.dumps(b),encoding='utf-8')
            out=Path(temp)/'unused'
            run=subprocess.run([sys.executable,str(root/'generators'/'motion_paradox.py'),
                '--brief',str(source),'--out',str(out)],capture_output=True,text=True)
            self.assertNotEqual(run.returncode,0)
            self.assertIn('different generator',run.stderr)
            self.assertFalse(out.exists())


if __name__=='__main__':
    unittest.main()
