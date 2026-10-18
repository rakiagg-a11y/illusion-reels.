import copy
import unittest
from unittest.mock import Mock, patch

import metricool_audio as audio


def request(audio_id="12345"):
    return dict(title="moths (over slowed)",artists=["Navjaxx","Staarz"],audio_id=audio_id,seconds=15)


def track():
    return dict(audioId="12345",audioType="music",title="moths - over slowed",
                displayArtist="Navjaxx, Staarz",durationMs=242000)


def client(*results):
    result = Mock(user_id="1",blog_id="2")
    result.get.side_effect = list(results)
    return result


class AudioPreflightTests(unittest.TestCase):
    def test_no_connection_and_disabled_autopublish_never_emit_audio_settings(self):
        self.assertEqual(audio.check(request())["status"],"connection_required")
        for props in ({"autopublishAllowed":False},{},{"autopublishAllowed":"true"}):
            source = client(props)
            result = audio.check(request(),source)
            self.assertEqual(result["status"],"autopublish_not_verified")
            self.assertIsNone(result["instagram_settings_preview"])
            self.assertEqual(source.get.call_count,1)

    def test_exact_variant_and_artist_are_required_without_title_fallback(self):
        for changed in (dict(title="moths"),dict(title="moths (slowed + reverb)"),
                        dict(audioId="999"),dict(displayArtist="another artist")):
            item=track()
            item.update(changed)
            source=client({"autopublishAllowed":True},item)
            result=audio.check(request(),source)
            self.assertEqual(result["status"],"audio_identity_mismatch")
            self.assertIsNone(result["instagram_settings_preview"])
            source.get.assert_called_with(audio.CATALOG+"/12345")

    def test_verified_result_remains_review_only_and_refers_to_native_audio(self):
        source=client({"autopublishAllowed":True},track())
        result=audio.check(request(),source)
        self.assertEqual(result["status"],"audio_verified_for_review")
        self.assertFalse(result["publishing_allowed"])
        self.assertEqual(result["no_audio_fallback"],"hold")
        settings=result["instagram_settings_preview"]
        self.assertEqual(settings["audioConfiguration"]["audioId"],"12345")
        self.assertEqual(settings["audioConfiguration"]["videoVolume"],0)
        self.assertTrue(settings["autoPublish"])

    def test_original_sound_uses_creator_credit_without_inventing_a_music_artist(self):
        wanted = request()
        wanted["artists"] = ["sound_creator"]
        item = track()
        del item["displayArtist"]
        item.update(audioType="original_sound",igUsername="sound_creator")
        result = audio.check(wanted,client({"autopublishAllowed":True},item))
        self.assertEqual(result["status"],"audio_verified_for_review")
        config = result["instagram_settings_preview"]["audioConfiguration"]
        self.assertEqual(config["igUsername"],"sound_creator")
        self.assertNotIn("displayArtist",config)

    def test_search_requires_complete_unambiguous_match_and_rechecks_exact_id(self):
        for items,cursor,status in (([],None,"audio_not_in_catalog"),
                                   ([track()],"next","search_incomplete_need_audio_id"),
                                   ([track(),dict(track(),audioId="67890")],None,"ambiguous_need_audio_id")):
            source=client({"autopublishAllowed":True},dict(music=items,originalSound=[],musicNextCursor=cursor))
            self.assertEqual(audio.check(request(None),source)["status"],status)
            self.assertEqual(source.get.call_count,2)
        source=client({"autopublishAllowed":True},dict(music=[track()],originalSound=[]),track())
        self.assertEqual(audio.check(request(None),source)["status"],"audio_verified_for_review")
        source.get.assert_called_with(audio.CATALOG+"/12345")

    def test_permissions_absence_errors_and_short_audio_hold_the_reel(self):
        for code,status in ((403,"connection_or_permissions_required"),(404,"audio_not_in_catalog"),(500,"lookup_failed")):
            source=client({"autopublishAllowed":True},audio.AudioAPIError(code))
            result=audio.check(request(),source)
            self.assertEqual(result["status"],status)
            self.assertIsNone(result["instagram_settings_preview"])
        source=client({"autopublishAllowed":True},dict(track(),durationMs=14999))
        self.assertEqual(audio.check(request(),source)["status"],"audio_too_short")

    def test_invalid_requests_cannot_make_network_calls(self):
        for field,value in (("audio_id","../../posts"),("artists",[]),("seconds",True),("title","")):
            changed=copy.deepcopy(request())
            changed[field]=value
            source=client()
            with self.assertRaises(ValueError):
                audio.check(changed,source)
            source.get.assert_not_called()

    def test_transport_only_allows_get_audio_endpoints_and_keeps_token_in_header(self):
        source=audio.Client("private-test-token","1","2")
        response=Mock()
        response.read.return_value=b'{"data":{"autopublishAllowed":true}}'
        opened=Mock()
        opened.__enter__=Mock(return_value=response)
        opened.__exit__=Mock(return_value=False)
        source._open=Mock(return_value=opened)
        self.assertEqual(source.get(audio.PROPERTIES),{"autopublishAllowed":True})
        sent=source._open.call_args.args[0]
        self.assertEqual(sent.get_method(),"GET")
        self.assertNotIn("private-test-token",sent.full_url)
        self.assertEqual(sent.get_header("X-mc-auth"),"private-test-token")
        for path in ("/v2/scheduler/posts",audio.CATALOG+"/../posts"):
            with self.assertRaises(ValueError):
                source.get(path)


if __name__=="__main__":
    unittest.main()
