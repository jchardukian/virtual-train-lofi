#!/usr/bin/env python3
"""Swap a scheduled (not yet public) city for its rebuilt version, keeping the same publish times.

  python3 pipeline/replace_release.py <city>

1. uploads the rebuilt 4K long-form with the same title, description, tags and publish time, private + scheduled;
2. deletes the old upload, but only if it is still private (never touches a public video);
3. puts the rebuilt Shorts in the delivery bucket under new random names and removes the old copies;
4. prints what the two Buffer posts need (new video link, new Short URLs, text with the new link) and writes
   publish/release_log.json. The agent then edits the two Buffer posts with that payload.
"""
import datetime, hashlib, json, pathlib, secrets, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from youtube_upload import API, access_token, call  # noqa: E402
from release_city import DELIVERY, cf, sha, carded  # noqa: E402


def main():
    city = sys.argv[1]
    D = ROOT / f"output/cities/{city}/illustrated"
    sums = {pathlib.Path(l.split()[1]).name: l.split()[0] for l in (D / "SHA256SUMS").read_text().splitlines()}
    log_p = ROOT / "publish/release_log.json"
    log = json.loads(log_p.read_text())
    L = next(e for e in log if e["city"] == city and e["item"] == "long_form" and not e.get("replaced_by"))
    shorts = [next(e for e in log if e["city"] == city and e["item"] == f"short_{i}" and not e.get("replaced_by")) for i in (1, 2)]
    if datetime.datetime.fromisoformat(L["publish_at"]) <= datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30):
        sys.exit("the long-form publishes within 30 minutes or already has; not replacing")
    tok = access_token()
    old = call("GET", f"{API}/youtube/v3/videos?part=snippet,status&id={L['youtube_video_id']}", tok)["items"]
    if not old or old[0]["status"]["privacyStatus"] != "private":
        sys.exit("old upload is missing or no longer private; not replacing")
    sn = old[0]["snippet"]
    promo = json.loads((ROOT / "publish/limits.json").read_text())["promotion"]["description_line"]
    desc = sn["description"] if sn["description"].startswith(promo) else promo + "\n\n" + sn["description"]
    meta = {"title": sn["title"], "description": desc, "tags": sn.get("tags", []), "publish_at": L["publish_at"],
            "expected_sha256": sums[f"{city}_illustrated_master.mp4"]}
    mp = ROOT / f"publish/meta/{city}_long.json"
    mp.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
    master = D / f"{city}_illustrated_master.mp4"
    if master.exists() and sha(master) != meta["expected_sha256"]:
        master.unlink()                                   # left over from an earlier attempt (older build): fetch the current one
    if not master.exists():
        subprocess.run(["pipeline/fetch_master.sh", city], cwd=ROOT, check=True, stdout=sys.stderr)
    if sha(master) != meta["expected_sha256"]:
        sys.exit("master does not match its build hash")
    cm = carded(master)                                   # owner-approved 'Departing daily' card on the uploaded copy
    meta["expected_sha256"], meta["built_sha256"] = sha(cm), meta["expected_sha256"]
    mp.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
    out = subprocess.run([sys.executable, "pipeline/youtube_upload.py", str(cm), str(mp)], cwd=ROOT, capture_output=True, text=True)
    cm.unlink()
    if out.returncode:
        sys.exit("upload failed: " + out.stdout[-400:] + out.stderr[-400:])
    up = json.loads(out.stdout.strip().splitlines()[-1])
    master.unlink()
    call("DELETE", f"{API}/youtube/v3/videos?id={L['youtube_video_id']}", tok)
    new_link = f"https://youtu.be/{up['video_id']}"
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    L["replaced_by"] = up["video_id"]; L["status"] = f"deleted {now}: replaced by the rebuilt version"
    log.append({**{k: v for k, v in L.items() if k not in ("replaced_by", "status")}, "youtube_video_id": up["video_id"],
                "url": new_link, "media_sha256": meta["expected_sha256"], "built_sha256": meta["built_sha256"], "replaces": L["youtube_video_id"]})
    res = {"city": city, "long_form": {"old": L["youtube_video_id"], "new": up["video_id"], "url": new_link}, "shorts": []}
    for i, S in zip((1, 2), shorts):
        f = D / f"{city}_illustrated_vertical_{i}.mp4"
        if sha(f) != sums[f.name]:
            sys.exit(f"{f.name} does not match its build hash")
        fc = carded(f, short=True)
        want = sha(fc)
        # write over the file the scheduled Buffer post already points at, so the post never loses its video
        # (Buffer edits can wait for approval; the caption link is updated when they go through)
        key = S["delivery_url"].split(".r2.dev/")[1] if S.get("delivery_url") else f"{secrets.token_hex(12)}/{city}_short_{i}.mp4"
        cf("PUT", f"lofitrain-delivery/objects/{key}", fc.read_bytes(), "video/mp4")
        fc.unlink()
        url = f"{DELIVERY}/{key}"
        got = hashlib.sha256(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"}), timeout=300).read()).hexdigest()
        if got != want:
            sys.exit(f"public copy of {f.name} does not match")
        S["delivery_url"], S["media_sha256"], S["links_to"] = url, want, new_link
        S["note"] = f"media replaced {now} with the rebuilt version"
        res["shorts"].append({"item": f"short_{i}", "buffer_post_id": S["buffer_post_id"], "url": url, "old_link": L["url"], "new_link": new_link})
    log_p.write_text(json.dumps(log, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
