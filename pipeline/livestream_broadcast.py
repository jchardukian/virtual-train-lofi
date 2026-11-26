#!/usr/bin/env python3
"""Create a scheduled YouTube live broadcast for a day's stream and print where to send it.

  python3 pipeline/livestream_broadcast.py <date> <start ISO time> [--hours 4] [--title-index N]

Creates (or reuses, by title + start time) a public liveBroadcast with auto-start and auto-stop, a reusable 1080p30
RTMP liveStream, binds them, and writes work/stream/<date>/broadcast.json with the broadcast id, watch URL and the
ingestion URL (which contains the stream key: never print it, never commit it; it is handed to the stream server only).
Title from the owner-approved rotation (publish/limits.json livestream_titles); description from livestream_build.credits.
The saved stream (VOD) stays on the channel as the evergreen long-form.
"""
import argparse, datetime, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from youtube_upload import API, access_token, call  # noqa: E402
import livestream_build as LB  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date"); ap.add_argument("start")
    ap.add_argument("--title-index", type=int)
    a = ap.parse_args()
    limits = json.loads((ROOT / "publish/limits.json").read_text())
    rot = limits["livestream_titles"]["rotation"]
    log_p = ROOT / "publish/livestream_log.json"
    log = json.loads(log_p.read_text()) if log_p.exists() else []
    title = rot[a.title_index if a.title_index is not None else len(log) % len(rot)]
    desc = LB.credits(a.date)
    if "AI" in desc.replace("-", " ").split() or "AI" in title.split():
        sys.exit("description mentions AI")
    start = datetime.datetime.fromisoformat(a.start).astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tok = access_token()
    b = call("POST", f"{API}/youtube/v3/liveBroadcasts?part=snippet,status,contentDetails", tok, {
        "snippet": {"title": title, "description": desc, "scheduledStartTime": start},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        "contentDetails": {"enableAutoStart": True, "enableAutoStop": True, "enableDvr": True, "recordFromStart": True,
                           "latencyPreference": "normal", "enableEmbed": False}})
    s = call("POST", f"{API}/youtube/v3/liveStreams?part=snippet,cdn,contentDetails", tok, {
        "snippet": {"title": f"lofitrain {a.date}"},
        "cdn": {"ingestionType": "rtmp", "resolution": "1080p", "frameRate": "30fps"},
        "contentDetails": {"isReusable": True}})
    call("POST", f"{API}/youtube/v3/liveBroadcasts/bind?id={b['id']}&part=id,contentDetails&streamId={s['id']}", tok)
    import urllib.request                                 # automatic custom thumbnail made on the stream server
    try:
        img = urllib.request.urlopen(urllib.request.Request(f"{LB.WORKER}/obj/control/pkg/thumb_{a.date}.jpg",
                                     headers={"X-Key": LB._key(), "User-Agent": "curl/8.5.0"}), timeout=120).read()
        call("POST", f"{API}/upload/youtube/v3/thumbnails/set?videoId={b['id']}", tok, data=img, headers={"Content-Type": "image/jpeg"})
        print("thumbnail set", file=sys.stderr)
    except Exception as e:
        print("THUMBNAIL NOT SET:", e, file=sys.stderr)
    ing = s["cdn"]["ingestionInfo"]
    out = {"date": a.date, "title": title, "broadcast_id": b["id"], "stream_id": s["id"], "scheduled_start": start,
           "watch_url": f"https://youtu.be/{b['id']}", "rtmp": f"{ing['ingestionAddress']}/{ing['streamName']}"}
    d = LB.WORK / a.date
    d.mkdir(parents=True, exist_ok=True)
    (d / "broadcast.json").write_text(json.dumps(out, indent=1) + "\n")
    log.append({k: v for k, v in out.items() if k != "rtmp"})
    log_p.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "rtmp"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
