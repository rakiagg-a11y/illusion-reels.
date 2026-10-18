"""Every generator keeps its on-video text below the Reels/Shorts top bar.

Instagram Reels and YouTube Shorts cover roughly the top 14% of a 9:16 frame
with the account bar, so nothing may be drawn there in any mode.
"""
import unittest

import numpy as np

import five_styles as d
import five_style_render as r

TOP_UI = .14


def brief(mode):
    style = next(style for style, modes in d.MODES.items() if mode in modes)
    account = next(a for a in d.default_accounts()["accounts"] if a["style"] == style)
    return d.make_brief(account, mode, d.parameters_for(mode)[0], 42)


class SafeZoneTests(unittest.TestCase):
    def test_nothing_is_drawn_under_the_top_platform_bar(self):
        for style, modes in d.MODES.items():
            for mode in modes:
                with self.subTest(mode=mode):
                    renderer = r.Renderer(brief(mode), 360, 640)
                    for t in (0., renderer.seconds*.5, renderer.seconds-.1):
                        frame = np.asarray(renderer.frame(t)).astype(int)
                        band = frame[:round(640*TOP_UI)]
                        background = frame[0, 0]
                        self.assertEqual(np.abs(band-background).max(), 0,
                                         f"{mode} draws inside the top {TOP_UI:.0%} at t={t}")

    def test_hook_starts_just_below_the_top_bar(self):
        renderer = r.Renderer(brief("munker_white"), 360, 640)
        frame = np.asarray(renderer.frame(0.)).astype(int)
        rows = np.where(np.abs(frame-frame[0, 0]).max(axis=(1, 2)) > 0)[0]
        self.assertLess(rows[0]/640, .20)


if __name__ == "__main__":
    unittest.main()
