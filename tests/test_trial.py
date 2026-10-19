import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import account_studio as studio
import brainrot
import five_style_render
from five_style_render import atomic_json, load_history
import trial_captions
import trial_production as T
import trial_schedule as S
from trial_records import read_json

STYLES = {"opticpop": ("depth_flip", "tilted_pair"), "hypnotorium": ("color_echo", "face_flash"),
          "spiralium_": ("mirror_flip", "still_wobble"), "trustyoureyes_": ("brainrot_spin",)}


def plan(days=30, start="2026-10-20", per_account=6):
    slots = []
    for day in range(1, days+1):
        date = f"2026-10-{19+day:02d}" if day <= 12 else f"2026-11-{day-12:02d}"
        for account, styles in STYLES.items():
            for s in range(1, per_account+1):
                hour = (s*4) % 24
                slots.append(dict(slot_id=f"t-{start}-{account}-d{day:02d}-s{s}", account=account,
                                  style=styles[(s-1) % len(styles)], day=day, local_date=date,
                                  local_time=f"{hour:02d}:30", scheduled_at_utc=f"{date}T{hour:02d}:30:00+00:00",
                                  networks=["instagram", "facebook", "youtube"]))
    return dict(start_date=start, timezone="UTC", seed=7, slots=slots)


def empty():
    return dict(kind="five_style_history", version=1, entries=[])


class AllocationTests(unittest.TestCase):
    def test_a_month_uses_a_different_work_in_every_slot(self):
        result = T.allocate(plan(), empty())
        self.assertEqual((result["filled"], result["empty"]), (720, 0))
        works = {}
        for a in result["slots"].values():
            works.setdefault((a["account"], a["mode"]), []).append(T._work(a["mode"], a["brief"]["parameters"]))
        for group, w in works.items():
            self.assertEqual(len(w), len(set(w)), group)

    def test_works_rendered_before_are_not_used_and_a_new_angle_is_not_a_new_work(self):
        p = dict(ribs=9, rings=7, opening=250, tilt=12)
        history = dict(empty(), entries=[dict(key=T._key("opticpop", "depth_flip", p), brief_digest="0"*64,
                                              quality="full", sha256="0"*64, output="/old/x.mp4")])
        result = T.allocate(plan(days=2), history)
        used = [a["brief"]["parameters"] for a in result["slots"].values() if a["mode"] == "depth_flip"]
        self.assertFalse([u for u in used if (u["ribs"], u["rings"], u["opening"]) == (9, 7, 250)])

    def test_capacity_covers_the_month_with_spare_works(self):
        report = {r["style"]: r for r in T.capacity(plan(), empty())}
        for style, r in report.items():
            self.assertGreaterEqual(r["spare"], 0, style)
        self.assertGreaterEqual(report["brainrot_spin"]["works_available"], 180+len(brainrot.CHARACTERS))

    def test_one_single_figure_a_day_and_no_character_twice(self):
        result = T.allocate(plan(), empty())
        days = {}
        for a in result["slots"].values():
            if a["mode"] == "brainrot_spin":
                days.setdefault(a["day"], []).append(a["brief"]["parameters"])
        singles = [c["character"] for d in days.values() for c in d if "partner" not in c]
        self.assertEqual(len(singles), len(set(singles)))
        for d in days.values():
            self.assertEqual(sum("partner" not in c for c in d), 1)

    def test_an_allocation_for_another_plan_is_refused_and_left_unchanged(self):
        first = T.allocate(plan(days=2), empty())
        kept = copy.deepcopy(first)
        with self.assertRaises(ValueError):
            T.allocate(plan(days=2, start="2026-10-21"), empty(), first)
        moved = plan(days=2)
        moved["slots"][0]["local_time"] = "23:59"
        with self.assertRaises(ValueError):
            T.allocate(moved, empty(), first)
        self.assertEqual(first, kept)
        again = T.allocate(plan(days=2), empty(), first)
        self.assertEqual({k: v["brief"] for k, v in again["slots"].items()},
                         {k: v["brief"] for k, v in first["slots"].items()})
        self.assertEqual(again["slots"][next(iter(again["slots"]))]["networks"], ["instagram", "facebook", "youtube"])

    def test_an_old_allocation_without_utc_or_networks_is_checked_slot_by_slot(self):
        first = T.allocate(plan(days=1), empty())
        old = copy.deepcopy(first)
        old.pop("plan_fingerprint")
        for a in old["slots"].values():
            for k in ("timezone", "scheduled_at_utc", "networks"):
                a.pop(k)
        self.assertEqual(T.allocate(plan(days=1), empty(), old)["filled"], first["filled"])


def fake_render(brief, output, history_path, *rest, **kw):
    """Stands in for both renderers: a black video, poster, brief and history entry."""
    output = Path(output)
    output.mkdir(parents=True)
    account = brief["account"]["id"] if isinstance(brief["account"], dict) else brief["account"]
    target = output/f"{account}_{brief['id']}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                    f"color=black:s=1080x1920:r=30:d={brief['render']['seconds']}", "-c:v", "libx264",
                    "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(target)], check=True)
    target.with_suffix(".png").write_bytes(b"png")
    atomic_json(target.with_suffix(".json"), brief)
    history = load_history(history_path)
    mode, p = brief["mode"], brief["parameters"]
    history["entries"].append(dict(key=T._key(account, mode, p), brief_digest=T._brief_digest(account, brief),
                                   quality="full", sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                                   output=str(target.resolve())))
    atomic_json(history_path, history)


def day_allocation():
    """Day 1 of a small plan: two quick studio slots."""
    small = plan(days=1, per_account=2)
    small["slots"] = [s for s in small["slots"] if s["account"] in ("hypnotorium", "spiralium_")][:2]
    return T.allocate(small, empty())


class RenderDayTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.out = self.dir/"day"
        self.allocation = day_allocation()
        self.calls = mock.patch.object(studio, "render_brief", side_effect=fake_render)
        self.render = self.calls.start()
        self.addCleanup(self.calls.stop)

    def run_day(self, history):
        return T.render_day(self.allocation, 1, history, self.out, workers=0)

    def test_starts_from_a_missing_history_and_does_not_render_twice(self):
        history = self.dir/"new"/"history.json"
        queue = self.run_day(history)
        self.assertEqual((len(queue["slots"]), queue["failed"]), (2, []))
        self.assertEqual(len(load_history(history)["entries"]), 2)
        for row in queue["slots"]:
            self.assertTrue(row["qa"]["passed"], row["qa"])
            self.assertEqual(row["caption_template_digest"], trial_captions.template_digest())
        again = self.run_day(history)
        self.assertEqual(self.render.call_count, 2)
        self.assertEqual(len(load_history(history)["entries"]), 2)
        self.assertEqual([r["sha256"] for r in again["slots"]], [r["sha256"] for r in queue["slots"]])

    def test_reads_a_history_saved_with_a_byte_order_mark(self):
        history = self.dir/"bom.json"
        history.write_bytes(b"\xef\xbb\xbf"+json.dumps(empty()).encode())
        self.assertEqual(self.run_day(history)["failed"], [])

    def test_a_changed_video_is_refused_not_reused(self):
        history = self.dir/"h.json"
        queue = self.run_day(history)
        with open(queue["slots"][0]["asset_path"], "ab") as f:
            f.write(b"x")
        again = self.run_day(history)
        self.assertEqual([f["slot_id"] for f in again["failed"]], [queue["slots"][0]["slot_id"]])
        self.assertIn("changed after it was rendered", again["failed"][0]["error"])

    def test_a_failed_music_copy_keeps_the_history_and_leaves_no_partial_file(self):
        history = self.dir/"h.json"
        with mock.patch("music.track_for", side_effect=RuntimeError("no music")):
            queue = self.run_day(history)
        self.assertEqual(len(queue["failed"]), 2)
        self.assertEqual(len(load_history(history)["entries"]), 2)
        self.assertFalse(list(self.out.glob("*_yt*.mp4")))
        queue = self.run_day(history)
        self.assertEqual((len(queue["slots"]), queue["failed"]), (2, []))
        self.assertEqual(self.render.call_count, 2)
        self.assertEqual(len(load_history(history)["entries"]), 2)

    def test_a_concept_recorded_meanwhile_by_another_render_is_a_failure(self):
        history = self.dir/"h.json"
        slot_id, entry = next(iter(self.allocation["slots"].items()))
        key = T._key(entry["account"], entry["mode"], entry["brief"]["parameters"])

        def other_render_first(*args, **kw):
            fake_render(*args, **kw)
            atomic_json(history, dict(empty(), entries=[dict(key=key, brief_digest="1"*64, quality="full",
                                                             sha256="2"*64, output="/elsewhere/v.mp4")]))
        self.render.side_effect = other_render_first
        queue = self.run_day(history)
        self.assertIn(slot_id, [f["slot_id"] for f in queue["failed"]])


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.day = self.dir/"day"
        self.allocation = day_allocation()
        with mock.patch.object(studio, "render_brief", side_effect=fake_render):
            self.queue = T.render_day(self.allocation, 1, self.dir/"h.json", self.day, workers=0)
        self.slots = [r["slot_id"] for r in self.queue["slots"]]
        self.repo = self.dir/"host"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        for f in self.day.glob("*.mp4"):
            (self.repo/f.name).write_bytes(f.read_bytes())
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "host"],
                       check=True)
        commit = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.base = f"https://raw.example/{commit}"
        self.approval = dict(template_digest=trial_captions.template_digest())
        self.blocklist = dict(blocked=[dict(audioId="741258222164035", title="Little Dark Age - MGMT")])

    def payloads(self):
        return S.payloads(self.day, self.allocation, self.base, self.repo, self.approval, self.blocklist)

    def approve(self, *slots):
        for s in slots or self.slots:
            T.review(self.day, s, "approved", "test", "sheet.png")

    def sound(self, *slots):
        S.set_sound(self.day, list(slots or self.slots), dict(audio_id="1652488768210767", title="Outro", artist="M83",
                                                              source="approved_list", check="Metricool music match"),
                    self.blocklist)

    def reasons(self, out, slot, network):
        return next(b["reasons"] for b in out["blocked"] if (b["slot_id"], b["network"]) == (slot, network))

    def test_nothing_is_ready_without_a_visual_approval(self):
        out = self.payloads()
        self.assertEqual(out["ready"], [])
        self.assertIn("no visual approval", self.reasons(out, self.slots[0], "facebook"))

    def test_instagram_waits_for_a_checked_sound_while_facebook_and_youtube_go(self):
        self.approve()
        out = self.payloads()
        self.assertEqual({(r["slot_id"], r["network"]) for r in out["ready"]},
                         {(s, n) for s in self.slots for n in ("facebook", "youtube")})
        self.assertIn("no checked Instagram sound recorded for this slot", self.reasons(out, self.slots[0], "instagram"))
        self.sound()
        ready = {(r["slot_id"], r["network"]): r for r in self.payloads()["ready"]}
        ig = ready[(self.slots[0], "instagram")]["post"]
        self.assertEqual(ig["instagramData"]["audioConfiguration"]["audioId"], "1652488768210767")
        self.assertTrue(ig["media"][0].endswith(self.slots[0]+".mp4"))
        self.assertTrue(ready[(self.slots[0], "youtube")]["post"]["media"][0].endswith("_yt.mp4"))

    def test_placeholder_or_blocked_sounds_are_refused(self):
        for sound in (dict(audio_id="?", title="x", check="c"),
                      dict(audio_id="741258222164035", title="Little Dark Age - MGMT", check="c"),
                      dict(audio_id="123456789", title="little dark age - mgmt", check="c"),
                      dict(audio_id="123456789", title="Fine", check="")):
            with self.assertRaises(ValueError):
                S.set_sound(self.day, self.slots, sound, self.blocklist)

    def test_failed_qa_changed_file_or_other_caption_blocks_the_slot(self):
        self.approve()
        self.sound()
        queue = read_json(self.day/"queue.json")
        queue["slots"][0]["qa"]["automatic"]["fps"] = False
        queue["slots"][0]["qa"]["passed"] = False
        queue["slots"][1]["caption"] += " extra"
        atomic_json(self.day/"queue.json", queue)
        out = self.payloads()
        self.assertEqual(out["ready"], [])
        self.assertIn("automatic QA failed: fps", self.reasons(out, self.slots[0], "youtube"))
        self.assertIn("caption is not the approved template's text for this brief",
                      self.reasons(out, self.slots[1], "youtube"))
        self.approval = dict(template_digest="0"*64)
        self.assertIn("caption templates differ from the approved version",
                      self.reasons(self.payloads(), self.slots[0], "facebook"))

    def test_an_approval_of_another_file_does_not_count(self):
        self.approve()
        reviews = read_json(self.day/"review.json")
        reviews[self.slots[0]]["sha256"] = "0"*64
        atomic_json(self.day/"review.json", reviews)
        self.assertIn("the visual approval is for a different file",
                      self.reasons(self.payloads(), self.slots[0], "facebook"))

    def test_a_scheduled_post_is_not_offered_again_or_overwritten(self):
        self.approve()
        self.sound()
        slot = self.slots[0]
        S.record(self.day, slot, "instagram", "111")
        S.fail(self.day, slot, "youtube", "upload error")
        ready = {(r["slot_id"], r["network"]) for r in self.payloads()["ready"]}
        self.assertNotIn((slot, "instagram"), ready)
        self.assertIn((slot, "youtube"), ready)
        with self.assertRaises(ValueError):
            S.record(self.day, slot, "instagram", "222")
        with self.assertRaises(ValueError):
            S.fail(self.day, slot, "instagram", "late error")
        S.record(self.day, slot, "instagram", "222", replace=True)
        post = read_json(self.day/"posts.json")[slot]["instagram"]
        self.assertEqual(post["provider_post_id"], "222")
        self.assertEqual(post["attempts"][-1]["replaced"], "111")
        with mock.patch.object(studio, "render_brief", side_effect=fake_render):
            T.render_day(self.allocation, 1, self.dir/"h.json", self.day, workers=0)
        self.assertEqual(read_json(self.day/"posts.json")[slot]["instagram"]["provider_post_id"], "222")

    def test_a_hosted_copy_that_is_not_this_file_blocks_the_post(self):
        self.approve()
        self.sound()
        name = self.slots[0]+".mp4"
        (self.repo/name).write_bytes(b"other")
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "x"],
                       check=True)
        commit = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        self.base = f"https://raw.example/{commit}"
        self.assertIn(f"the hosted {name} at {commit[:7]} is not this file",
                      self.reasons(self.payloads(), self.slots[0], "instagram"))

    def test_live_needs_a_public_url(self):
        self.approve()
        S.record(self.day, self.slots[0], "facebook", "9")
        with self.assertRaises(ValueError):
            S.live(self.day, self.slots[0], "facebook", "2026-10-20T00:00:00+00:00", "x", "")


if __name__ == "__main__":
    unittest.main()
