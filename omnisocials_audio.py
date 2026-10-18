"""Read-only OmniSocials native-audio checks and trending discovery."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from metricool_audio import matches, validate_request

SOURCE = "https://docs.omnisocials.com/api/audio"
BASE = "https://api.omnisocials.com/v1/audio/search"


class AudioAPIError(RuntimeError):
    def __init__(self,status=None):
        self.status = status
        super().__init__(f"OmniSocials audio read failed ({status or 'response/connection error'})")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise AudioAPIError(code)


class Client:
    def __init__(self,token):
        if not isinstance(token,str) or not token.strip():
            raise ValueError("configure OMNISOCIALS_API_KEY in the runtime environment")
        self._token = token
        self._open = build_opener(NoRedirect()).open

    def search(self,query=None,audio_type="music"):
        if audio_type not in ("music","original_sound"):
            raise ValueError("audio_type must be music or original_sound")
        params = dict(type=audio_type)
        if query is not None:
            if not isinstance(query,str) or not query.strip() or len(query)>200:
                raise ValueError("query must contain 1-200 characters, or be omitted for trending")
            params["q"] = query
        request = Request(BASE+"?"+urlencode(params),
            headers={"Authorization":"Bearer "+self._token,"Accept":"application/json"},method="GET")
        try:
            with self._open(request,timeout=30) as response:
                return json.load(response)
        except HTTPError as error:
            raise AudioAPIError(error.code) from None
        except (OSError,URLError,ValueError):
            raise AudioAPIError() from None


def initial_report():
    return dict(kind="opticpop_omnisocials_audio_preflight",version=1,publishing_allowed=False,
                checked_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),status="connection_required",
                audio=None,instagram_settings_preview=None,no_audio_fallback="hold",source=SOURCE,
                account_publish_permission="not_verified",
                note="Native audio metadata only. No download, upload, draft, scheduling or publishing.")


def rows(response,report):
    if not isinstance(response,dict) or not isinstance(response.get("data"),list):
        raise AudioAPIError()
    if response.get("needsFacebook") is True:
        report["status"] = "linked_facebook_connection_required"
        return None
    if response.get("error"):
        report["status"] = "catalog_access_not_verified"
        return None
    if response.get("needsFacebook") not in (None,False):
        raise AudioAPIError()
    return response["data"]


def metadata(item):
    if (not isinstance(item,dict) or not isinstance(item.get("audio_id"),str)
        or not re.fullmatch(r"\d{1,40}",item["audio_id"])
        or item.get("audio_type") not in ("music","original_sound")
        or not isinstance(item.get("title"),str)
        or type(item.get("duration_ms")) is not int or item["duration_ms"]<=0):
        raise AudioAPIError()
    # Preview/download URLs are temporary and are not part of the publishing identity.
    result = {k:item[k] for k in ("audio_id","audio_type","title","duration_ms")}
    for credit in ("artist","ig_username"):
        if isinstance(item.get(credit),str) and item[credit]:
            result[credit] = item[credit]
    return result


def failure(report,error):
    report["status"] = "connection_or_permissions_required" if error.status in (401,403) else "lookup_failed"
    report["http_status"] = error.status
    return report


def check(request,client=None,audio_type="music"):
    request = validate_request(request)
    if audio_type not in ("music","original_sound"):
        raise ValueError("audio_type must be music or original_sound")
    report = initial_report()
    report.update(request=request,catalog_type=audio_type)
    if client is None:
        return report
    try:
        found = rows(client.search(request["title"],audio_type),report)
        if found is None:
            return report
        candidates = {}
        for item in found:
            if not isinstance(item,dict):
                raise AudioAPIError()
            canonical = dict(title=item.get("title"),displayArtist=item.get("artist"),igUsername=item.get("ig_username"))
            if not matches(canonical,request):
                continue
            selected = metadata(item)
            if selected["audio_type"] != audio_type:
                raise AudioAPIError()
            key = selected["audio_id"]
            if request["audio_id"] is not None and key != request["audio_id"]:
                continue
            if key in candidates and candidates[key] != selected:
                raise AudioAPIError()
            candidates[key] = selected
        report["candidate_ids"] = sorted(candidates)
        if len(candidates)!=1:
            report["status"] = "no_exact_match_in_search" if not candidates else "ambiguous_need_audio_id"
            return report
        selected = next(iter(candidates.values()))
        if selected["duration_ms"] < request["seconds"]*1000:
            report["status"] = "audio_too_short"
            return report
        report.update(status="audio_found_for_review",audio=selected,
                      instagram_settings_preview=dict(audio_id=selected["audio_id"],audio_volume=100,video_volume=0))
        return report
    except AudioAPIError as error:
        return failure(report,error)


def trending(client=None,audio_type="music"):
    if audio_type not in ("music","original_sound"):
        raise ValueError("audio_type must be music or original_sound")
    report = initial_report()
    report.update(catalog_type=audio_type,items=[])
    if client is None:
        return report
    try:
        found = rows(client.search(audio_type=audio_type),report)
        if found is None:
            return report
        report["items"] = [metadata(item) for item in found]
        if any(item["audio_type"] != audio_type for item in report["items"]):
            raise AudioAPIError()
        report["status"] = "trending_catalog_results" if found else "empty_trending_results"
        return report
    except AudioAPIError as error:
        report["items"] = []
        return failure(report,error)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command",required=True)
    checker = commands.add_parser("check")
    checker.add_argument("request",type=Path)
    discover = commands.add_parser("trending")
    for command in (checker,discover):
        command.add_argument("--audio-type",choices=("music","original_sound"),default="music")
        command.add_argument("--check-live",action="store_true")
        command.add_argument("--out",type=Path,required=True)
    args = parser.parse_args()
    try:
        client = Client(os.environ["OMNISOCIALS_API_KEY"]) if args.check_live and os.environ.get("OMNISOCIALS_API_KEY") else None
        if args.command=="check":
            request = json.loads(args.request.read_text(encoding="utf-8-sig"))
            report = check(request,client,args.audio_type)
        else:
            report = trending(client,args.audio_type)
        if args.out.exists():
            raise ValueError("choose a new report path")
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(dict(status=report["status"],publishing_allowed=False)))
        return 0 if report["status"] in ("audio_found_for_review","trending_catalog_results") else 2
    except (ValueError,OSError) as error:
        parser.error(str(error))


if __name__=="__main__":
    raise SystemExit(main())
