#!/usr/bin/env python3
"""Upload a long-form video to the owner's YouTube channel, private until a scheduled publish time.

  python3 pipeline/youtube_upload.py <video.mp4> <meta.json> [--thumbnail img.jpg] [--dry-run]

meta.json: {"title", "description", "tags": [...], "publish_at": ISO-8601 with offset, "expected_sha256"}

Reads YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN from the environment (never printed). Refuses unless:
the token resolves to the channel named in publish/limits.json, the file hash matches expected_sha256, the
description has the music credit and no mention of AI, and the publish time is in the future. Uses YouTube's
resumable upload; the video stays private and YouTube publishes it at publish_at. Prints the video id and URL.
"""
import argparse, datetime, hashlib, json, os, pathlib, sys, urllib.error, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://www.googleapis.com"


def access_token():
    d = urllib.parse.urlencode({"client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
                                "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request("https://oauth2.googleapis.com/token", data=d), timeout=30))["access_token"]


def call(method, url, tok, body=None, headers=None, data=None, want_headers=False):
    h = {"Authorization": "Bearer " + tok}
    h.update(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        h["Content-Type"] = "application/json; charset=UTF-8"
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=600)
    except urllib.error.HTTPError as e:
        sys.exit(f"YouTube API {method} {url.split('?')[0]} failed: {e.code} {e.read()[:500]!r}")
    return (r.headers, r.read()) if want_headers else json.loads(r.read() or b"{}")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def checks(video, meta, limits):
    bad = []
    if sha256(video) != meta.get("expected_sha256"):
        bad.append("video file does not match the approved build's hash")
    d = meta.get("description", "")
    if "Purrple Cat" not in d or "CC BY 4.0" not in d:
        bad.append("description lacks the music credit")
    if limits.get("channel_blurb") and limits["channel_blurb"] not in d:
        bad.append("description lacks the channel blurb")
    words = (d + " " + meta.get("title", "")).replace("-", " ").split()
    if "AI" in words:
        bad.append("title or description mentions AI (owner rule)")
    try:
        t = datetime.datetime.fromisoformat(meta["publish_at"])
        if t.tzinfo is None or t <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15):
            bad.append("publish_at must carry a UTC offset and be at least 15 minutes ahead")
    except Exception as e:
        bad.append(f"bad publish_at: {e}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("meta")
    ap.add_argument("--thumbnail")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    meta = json.loads(pathlib.Path(a.meta).read_text())
    limits = json.loads((ROOT / "publish/limits.json").read_text())
    want = limits["channel"]["youtube_channel_url"].rsplit("/", 1)[-1]
    bad = checks(a.video, meta, limits)
    tok = access_token()
    me = call("GET", f"{API}/youtube/v3/channels?part=id,snippet&mine=true", tok)
    ids = [i["id"] for i in me.get("items", [])]
    if ids != [want]:
        bad.append(f"signed-in channel {ids} is not the owner-named channel {want}")
    if bad:
        sys.exit("refused:\n- " + "\n- ".join(bad))
    publish_at = datetime.datetime.fromisoformat(meta["publish_at"]).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {"snippet": {"title": meta["title"], "description": meta["description"], "tags": meta.get("tags", []), "categoryId": "10"},
            "status": {"privacyStatus": "private", "publishAt": publish_at, "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": False, "license": "youtube", "embeddable": True}}
    if a.dry_run:
        print(json.dumps({"would_upload": a.video, "channel": want, "body": body}, indent=1))
        return
    size = os.path.getsize(a.video)
    hdrs, _ = call("POST", f"{API}/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status", tok, body=body,
                   headers={"X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)}, want_headers=True)
    loc = hdrs["Location"]
    with open(a.video, "rb") as f:
        data = f.read()
    v = call("PUT", loc, tok, data=data, headers={"Content-Type": "video/mp4", "Content-Length": str(size)})
    vid = v["id"]
    print(json.dumps({"video_id": vid, "url": f"https://youtu.be/{vid}", "privacy": v["status"]["privacyStatus"],
                      "publish_at": v["status"].get("publishAt"), "upload_status": v["status"].get("uploadStatus")}))
    if a.thumbnail:
        with open(a.thumbnail, "rb") as f:
            img = f.read()
        call("POST", f"{API}/upload/youtube/v3/thumbnails/set?videoId={vid}", tok, data=img, headers={"Content-Type": "image/jpeg"})
        print("thumbnail set")


if __name__ == "__main__":
    main()
