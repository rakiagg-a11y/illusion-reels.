import unittest
from unittest.mock import Mock
from urllib.parse import parse_qs,urlsplit

import omnisocials_audio as omni


def request(audio_id=None):
    return dict(title="moths (over slowed)",artists=["Navjaxx","Staarz"],audio_id=audio_id,seconds=15)


def track(**changes):
    return dict(dict(audio_id="12345",audio_type="music",title="moths - over slowed",
                     artist="Navjaxx, Staarz",duration_ms=242000,preview_url="https://example.com/temporary"),**changes)


class OmniAudioTests(unittest.TestCase):
    def test_no_connection_and_facebook_requirement_cannot_emit_audio_settings(self):
        self.assertEqual(omni.check(request())["status"],"connection_required")
        source=Mock()
        source.search.return_value=dict(data=[],needsFacebook=True,error="connect Facebook")
        result=omni.check(request(),source)
        self.assertEqual(result["status"],"linked_facebook_connection_required")
        self.assertIsNone(result["instagram_settings_preview"])

    def test_exact_version_is_native_metadata_only_and_does_not_authorize_publication(self):
        source=Mock()
        source.search.return_value=dict(data=[track()],error=None,needsFacebook=False)
        result=omni.check(request(),source)
        self.assertEqual(result["status"],"audio_found_for_review")
        self.assertEqual(result["instagram_settings_preview"],dict(audio_id="12345",audio_volume=100,video_volume=0))
        self.assertNotIn("preview_url",result["audio"])
        self.assertFalse(result["publishing_allowed"])
        self.assertEqual(result["account_publish_permission"],"not_verified")

    def test_wrong_version_artist_or_requested_id_never_substitutes_another_sound(self):
        source=Mock()
        for item in (track(title="moths"),track(artist="another artist"),track(audio_id="999")):
            source.search.return_value=dict(data=[item])
            result=omni.check(request("12345"),source)
            self.assertEqual(result["status"],"no_exact_match_in_search")
            self.assertIsNone(result["instagram_settings_preview"])

    def test_ambiguous_and_conflicting_audio_ids_are_held(self):
        source=Mock()
        source.search.return_value=dict(data=[track(),track(audio_id="67890")])
        self.assertEqual(omni.check(request(),source)["status"],"ambiguous_need_audio_id")
        self.assertEqual(omni.check(request("67890"),source)["audio"]["audio_id"],"67890")
        source.search.return_value=dict(data=[track(),track(duration_ms=200000)])
        self.assertEqual(omni.check(request(),source)["status"],"lookup_failed")

    def test_too_short_invalid_duration_and_catalog_errors_are_held(self):
        source=Mock()
        for item,status in ((track(duration_ms=14000),"audio_too_short"),(track(duration_ms=True),"lookup_failed")):
            source.search.return_value=dict(data=[item])
            self.assertEqual(omni.check(request(),source)["status"],status)
        source.search.return_value=dict(data=[],error="expired connection")
        self.assertEqual(omni.check(request(),source)["status"],"catalog_access_not_verified")
        source.search.side_effect=omni.AudioAPIError(403)
        self.assertEqual(omni.check(request(),source)["status"],"connection_or_permissions_required")

    def test_trending_omits_query_and_does_not_claim_song_search_is_trending_evidence(self):
        source=Mock()
        source.search.return_value=dict(data=[track()])
        result=omni.trending(source)
        source.search.assert_called_once_with(audio_type="music")
        self.assertEqual(result["status"],"trending_catalog_results")
        self.assertEqual(result["items"][0]["audio_id"],"12345")
        self.assertNotIn("preview_url",result["items"][0])

    def test_original_sound_keeps_creator_identity(self):
        wanted=request("12345")
        wanted["artists"]=["creator"]
        source=Mock()
        source.search.return_value=dict(data=[track(audio_type="original_sound",artist=None,ig_username="creator")])
        result=omni.check(wanted,source,"original_sound")
        self.assertEqual(result["status"],"audio_found_for_review")
        self.assertEqual(result["audio"]["ig_username"],"creator")

    def test_transport_is_get_only_omits_q_for_trending_and_never_redirects_credentials(self):
        source=omni.Client("private-test-key")
        response=Mock()
        response.read.return_value=b'{"data":[],"error":null}'
        opened=Mock()
        opened.__enter__=Mock(return_value=response)
        opened.__exit__=Mock(return_value=False)
        source._open=Mock(return_value=opened)
        source.search()
        sent=source._open.call_args.args[0]
        self.assertEqual(sent.get_method(),"GET")
        self.assertNotIn("q",parse_qs(urlsplit(sent.full_url).query))
        self.assertNotIn("private-test-key",sent.full_url)
        self.assertEqual(sent.get_header("Authorization"),"Bearer private-test-key")
        with self.assertRaises(omni.AudioAPIError):
            omni.NoRedirect().redirect_request(sent,None,302,"",{},"https://another.example.com")

    def test_invalid_request_cannot_query_the_service(self):
        source=Mock()
        wanted=request()
        wanted["seconds"]=True
        with self.assertRaises(ValueError):
            omni.check(wanted,source)
        source.search.assert_not_called()


if __name__=="__main__":
    unittest.main()
