#!/usr/bin/env python3
"""Append a released city to publish/release_log.json.
  python3 pipeline/log_release.py <release_city output.json> <buffer id short 1> <buffer id short 2>"""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
r = json.loads(pathlib.Path(sys.argv[1]).read_text())
AUTH = "owner, in the agent session: 'You can schedule cities when they're done. I want 1 city per day (one long form and two shorts)'"
L = r["long_form"]
log = json.loads((ROOT / "publish/release_log.json").read_text())
log.append({"city": r["city"], "item": "long_form", "route": "YouTube Data API (pipeline/release_city.py)",
            "youtube_video_id": L["video_id"], "url": L["url"], "resolution": "3840x2160", "privacy": "private until publishAt",
            "publish_at": L["publish_at"], "media_sha256": L["media_sha256"], "authorised": AUTH, "preflight": "passed"})
for s, bid in zip(r["shorts"], sys.argv[2:4]):
    log.append({"city": r["city"], "item": s["item"], "buffer_post_id": bid, "channel": "Lofi Train POV (UCLjE-J4o5HSXz1cCokDdZbQ)",
                "due_at": s["due_at"], "status": "scheduled", "media_sha256": s["media_sha256"], "delivery_url": s["url"],
                "links_to": L["url"], "authorised": AUTH, "preflight": "passed"})
(ROOT / "publish/release_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n")
(ROOT / f"output/cities/{r['city']}/illustrated/RELEASE_STATE.json").unlink(missing_ok=True)
print(r["city"], "logged")
