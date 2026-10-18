"""Read-only, brand-specific Instagram audio preflight. Never uploads or schedules."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://app.metricool.com/api"
CATALOG = "/v2/scheduler/catalogs/instagram/audio"
PROPERTIES = "/v2/scheduler/posts/instagram-properties"
HELP = "https://help.metricool.com/how-to-add-audio-to-your-instagram-reels-from-metricool-2o2ks"


class AudioAPIError(RuntimeError):
    def __init__(self, status=None):
        self.status = status
        super().__init__(f"Metricool read failed ({status or 'connection/response error'})")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward the API credential to a redirected host.
        raise AudioAPIError(code)


class Client:
    def __init__(self, token, user_id, blog_id):
        if not token or any(not str(value).isdigit() for value in (user_id,blog_id)):
            raise ValueError("configure METRICOOL_TOKEN, METRICOOL_USER_ID and METRICOOL_BLOG_ID")
        self._token = token
        self.user_id, self.blog_id = str(user_id),str(blog_id)
        self._open = build_opener(NoRedirect()).open

    def get(self, path, **params):
        if path != PROPERTIES and path != CATALOG and not re.fullmatch(CATALOG+r"/\d+",path):
            raise ValueError("only read-only audio endpoints are supported")
        query = urlencode(dict(userId=self.user_id,blogId=self.blog_id,**params))
        request = Request(BASE+path+"?"+query,headers={"X-Mc-Auth":self._token,"Accept":"application/json"},method="GET")
        try:
            with self._open(request,timeout=30) as response:
                result = json.load(response)
            if not isinstance(result,dict) or "data" not in result:
                raise AudioAPIError()
            return result["data"]
        except HTTPError as error:
            raise AudioAPIError(error.code) from None
        except (URLError,OSError,ValueError):
            raise AudioAPIError() from None


def normalized(text):
    return re.sub(r"[^a-z0-9]","",text.casefold())


def validate_request(request):
    if not isinstance(request,dict) or set(request)!={"title","artists","audio_id","seconds"}:
        raise ValueError("audio request needs title, artists, audio_id and seconds")
    if not isinstance(request["title"],str) or not normalized(request["title"]) or len(request["title"])>200:
        raise ValueError("provide the exact song/version title")
    if (not isinstance(request["artists"],list) or not request["artists"]
        or any(not isinstance(a,str) or not normalized(a) or len(a)>100 for a in request["artists"])):
        raise ValueError("provide at least one expected artist")
    audio_id = request["audio_id"]
    if audio_id is not None and (not isinstance(audio_id,str) or not re.fullmatch(r"\d{1,40}",audio_id)):
        raise ValueError("audio_id must be the exact numeric Instagram audio ID, or null for search")
    if type(request["seconds"]) is not int or not 3 <= request["seconds"] <= 90:
        raise ValueError("seconds must be an integer in 3-90")
    return request


def matches(item, request):
    if not isinstance(item,dict) or not isinstance(item.get("title"),str):
        return False
    artists = item.get("displayArtist") or item.get("igUsername","")
    return (isinstance(artists,str) and normalized(item["title"])==normalized(request["title"])
            and all(normalized(a) in normalized(artists) for a in request["artists"]))


def check(request, client=None):
    request = validate_request(request)
    report = dict(kind="opticpop_audio_preflight",version=1,publishing_allowed=False,
                  checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),request=request,
                  status="connection_required",audio=None,instagram_settings_preview=None,
                  no_audio_fallback="hold",source=HELP,
                  note="Catalog access is not evidence that a song is currently trending. No post is created.")
    if client is None:
        return report
    report["brand_id"],report["user_id"] = client.blog_id,client.user_id
    phase = "properties"
    try:
        properties = client.get(PROPERTIES)
        if not isinstance(properties,dict) or properties.get("autopublishAllowed") is not True:
            report["status"] = "autopublish_not_verified"
            return report
        audio_id = request["audio_id"]
        if audio_id is None:
            phase = "search"
            page = client.get(CATALOG,searchQuery=request["title"],limit=50)
            if not isinstance(page,dict) or any(not isinstance(page.get(k),list) for k in ("music","originalSound")):
                raise AudioAPIError()
            candidates = {str(i.get("audioId")):i for i in page["music"]+page["originalSound"] if matches(i,request)}
            report["candidate_ids"] = sorted(candidates)
            # A truncated search cannot establish uniqueness or absence.
            if page.get("musicNextCursor") or page.get("originalSoundNextCursor"):
                report["status"] = "search_incomplete_need_audio_id"
                return report
            if len(candidates)!=1:
                report["status"] = "audio_not_in_catalog" if not candidates else "ambiguous_need_audio_id"
                return report
            audio_id = next(iter(candidates))
            if not re.fullmatch(r"\d{1,40}",audio_id):
                raise AudioAPIError()
        # Do not pass the API's optional title fallback: it may substitute another audio ID.
        phase = "audio"
        item = client.get(CATALOG+"/"+audio_id)
        if not isinstance(item,dict) or item.get("audioId")!=audio_id or not matches(item,request):
            report["status"] = "audio_identity_mismatch"
            return report
        if item.get("audioType") not in ("music","original_sound") or type(item.get("durationMs")) is not int:
            raise AudioAPIError()
        if item["durationMs"] < request["seconds"]*1000:
            report["status"] = "audio_too_short"
            return report
        audio = {k:item[k] for k in ("audioId","audioType","title","durationMs")}
        for credit in ("displayArtist","igUsername"):
            if isinstance(item.get(credit),str) and item[credit]:
                audio[credit] = item[credit]
        report.update(status="audio_verified_for_review",audio=audio,
                      instagram_settings_preview=dict(type="REEL",autoPublish=True,showReelOnFeed=True,
                          audioConfiguration=dict(**audio,audioVolume=100,videoVolume=0)))
        return report
    except AudioAPIError as error:
        report["status"] = ("connection_or_permissions_required" if error.status in (401,403)
                            else "audio_not_in_catalog" if error.status==404 and phase=="audio" else "lookup_failed")
        report["http_status"] = error.status
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--check-live",action="store_true",help="authenticated GET requests only; credentials come from environment")
    args = parser.parse_args()
    try:
        request = validate_request(json.loads(args.request.read_text(encoding="utf-8-sig")))
        client = None
        if args.check_live and all(os.environ.get(k) for k in ("METRICOOL_TOKEN","METRICOOL_USER_ID","METRICOOL_BLOG_ID")):
            client = Client(os.environ["METRICOOL_TOKEN"],os.environ["METRICOOL_USER_ID"],os.environ["METRICOOL_BLOG_ID"])
        report = check(request,client)
        if args.out.exists():
            raise ValueError("choose a new report path")
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(dict(status=report["status"],publishing_allowed=False)))
        return 0 if report["status"]=="audio_verified_for_review" else 2
    except (ValueError,OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
