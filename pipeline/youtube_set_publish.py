#!/usr/bin/env python3
"""Change the scheduled publish time of a private, scheduled YouTube video on the owner's channel.

  python3 pipeline/youtube_set_publish.py <video_id> <publish_at ISO-8601 with offset>

Keeps every other status field as it is (read first, then written back). Refuses a time in the past.
"""
import datetime, sys, urllib.parse
sys.path.insert(0, __import__("os").path.dirname(__file__))
from youtube_upload import API, access_token, call

vid, when = sys.argv[1], sys.argv[2]
t = datetime.datetime.fromisoformat(when)
if t <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30):
    sys.exit("publish time must be at least 30 minutes ahead")
tok = access_token()
items = call("GET", f"{API}/youtube/v3/videos?part=status&id={vid}", tok)["items"]
if not items:
    sys.exit("video not found on this channel")
st = items[0]["status"]
if st.get("privacyStatus") != "private":
    sys.exit("video is not private; refusing to reschedule")
st = {k: v for k, v in st.items() if k in ("privacyStatus", "embeddable", "license", "publicStatsViewable",
                                          "selfDeclaredMadeForKids", "containsSyntheticMedia")}
st["publishAt"] = t.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
r = call("PUT", f"{API}/youtube/v3/videos?part=status", tok, body={"id": vid, "status": st})
print({"video_id": vid, "publish_at": r["status"].get("publishAt"), "privacy": r["status"]["privacyStatus"],
       "synthetic": r["status"].get("containsSyntheticMedia")})
