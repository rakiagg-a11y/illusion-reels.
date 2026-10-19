"""Render one local example per new style and a self-contained review gallery."""
import argparse
import html
import json
from pathlib import Path

import account_studio as studio


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="new folder")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--preview", action="store_true", help="360x640 instead of 1080x1920")
    a = ap.parse_args()
    output = Path(a.out)
    if output.exists():
        ap.error("choose a new folder")
    output.mkdir(parents=True)
    cards, records = [], []
    for index, (account, mode) in enumerate([
            ("hypnotorium", "color_echo"), ("hypnotorium", "face_flash"),
            ("spiralium_", "mirror_flip"), ("spiralium_", "still_wobble"),
            ("opticpop", "depth_flip")]):
        parameters = studio.parameters_for(mode)[2]
        if mode == "still_wobble":
            parameters = dict(element_length=30, aspect_ratio=5, surround_angle=0, centre_radius=.25)
        if mode == "depth_flip":
            parameters = dict(ribs=11, rings=7, opening=290, tilt=24)
        brief = studio.make_brief(account, mode, parameters, 420+index)
        result = studio.render_brief(brief, output/mode, output/"demo_history.json", a.preview, a.ffmpeg)
        renderer = studio.Renderer(brief, 360, 640)
        if hasattr(renderer.stimulus, "control_frame"):
            try:
                control = renderer.stimulus.control_frame(2)
            except TypeError:
                control = renderer.stimulus.control_frame()
            control.save(output/mode/"control.png")
        if mode == "color_echo":
            renderer.frame(20).save(output/mode/"gray_test.png")
        reference = brief["reference"]
        records.append(dict(brief=brief, manifest=result))
        cards.append(f'''<article><h2>{brief['generator']} · @{account}</h2>
          <video controls playsinline preload="metadata" poster="{mode}/{result['poster']}">
            <source src="{mode}/{result['video']}" type="video/mp4"></video>
          <p>{html.escape(brief['mechanism']['mechanism'])}</p>
          <p>מקור השראה: <a href="{reference['url']}">{reference['reel']}</a> ·
          {reference['likes_display']} לייקים + {reference['comments_display']} תגובות. שיתופים אינם זמינים.</p>
          <p><a href="{mode}/{result['brief']}">תדריך הפקה JSON</a></p></article>''')
    studio.atomic_json(output/"review_manifest.json", dict(
        kind="account_style_review", local_only=True, publishing_allowed=False,
        status="pending_user_visual_review", examples=records))
    (output/"review.html").write_text('''<!doctype html><html lang="he" dir="rtl"><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1"><title>חמשת הסגנונות — בדיקת איכות</title>
    <style>body{font:17px Arial;background:#090d18;color:#edf1fa;margin:36px;line-height:1.6}
    main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:24px}
    article{background:#151d2d;padding:20px;border-radius:18px}video{width:100%;max-height:660px;background:black}
    a{color:#93caff}h2{font-size:21px}p{font-size:15px}</style>
    <h1>השיוך החדש — חמישה סרטוני בדיקה</h1>
    <p>Hypnotorium: ColorEcho + FaceFlash · Spiralium: MirrorFlip + StillWobble · OpticPop: תוספת DepthFlip.</p>
    <p>הסרטונים מקוריים ונוצרו בקוד. MirrorFlip הוא אנלוג דמות־רקע של Rubin, ו־StillWobble הוא אנלוג Ouchi;
    הם אינם העתק של ציור המראה או צילום הכמהין. FaceFlash משתמש באיורים מקוריים; עוצמת האפקט עדיין דורשת בדיקה אנושית.
    ב־ColorEcho יש להתמקד בסימון במשך 18 שניות ולהמשיך להביט בשלב האפור. אף סרטון אינו מאושר לפרסום אוטומטי.</p>
    <main>'''+"\n".join(cards)+"</main></html>", encoding="utf-8")
    print(str((output/"review.html").resolve()), flush=True)


if __name__ == "__main__":
    main()
