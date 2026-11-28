#!/usr/bin/env python3
"""Prepare one finished city for release: upload the 4K long-form to YouTube (private, scheduled) and put its
two Shorts in the delivery bucket, then print what the Shorts posts need (titles, descriptions, links, times).

  python3 pipeline/release_city.py <city> <YYYY-MM-DD>

Reads publish/meta/<city>.json: {"long": {"summary", "tags", "hashtags"}, "short_1": {"summary", "hashtags"},
"short_2": {...}, optional "name" (display name, default from the spec), "hashtag", "emoji" (Short 2's emoji)}.
Titles are always the owner's simple format: "<City> Chillhop 🚆", Shorts "<City> Chillhop 🚆 #lofi #<city> #shorts". The channel blurb, the 'not real footage' line and the
music credit (from data/music/used.json) are added here, in the owner's order. Times are fixed, America/Chicago:
long-form 11:00, Short 1 14:30, Short 2 20:30, so both Shorts can link to a video that is already public.
The Shorts posts themselves are created through Buffer by the agent with the printed payload.
"""
import datetime, hashlib, json, os, pathlib, secrets, subprocess, sys, urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
TZ = ZoneInfo("America/Chicago")
DELIVERY = "https://pub-a7aa0de9fe59416c8b4a6db9cefd6a22.r2.dev"
FOOTAGE = "Stylised illustrated artwork; not real footage."


def credit(titles, note):
    t = " and ".join(f'"{x}"' for x in titles)
    return f"Music: {t} by Purrple Cat (purrplecat.com), licensed under CC BY 4.0 (creativecommons.org/licenses/by/4.0/). {note}"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def cf(method, path, data=None, ctype=None):
    acct = json.load(urllib.request.urlopen(urllib.request.Request("https://api.cloudflare.com/client/v4/accounts",
                     headers={"Authorization": "Bearer dummy"}), timeout=60))["result"][0]["id"]
    h = {"Authorization": "Bearer dummy"}
    if ctype:
        h["Content-Type"] = ctype
    r = urllib.request.Request(f"https://api.cloudflare.com/client/v4/accounts/{acct}/r2/buckets/{path}", data=data, method=method, headers=h)
    return urllib.request.urlopen(r, timeout=600).status


def carded(src, short=False):
    """the uploaded copy carries the owner-approved 'Departing daily' card (pipeline/promo_card.py)"""
    import promo_card
    out = src.with_name(src.stem + ".card.mp4")
    promo_card.apply(src, out, short)
    return out


def upload_long(city, D, mp):
    master = D / f"{city}_illustrated_master.mp4"
    if not master.exists():
        subprocess.run(["pipeline/fetch_master.sh", city], cwd=ROOT, check=True, stdout=sys.stderr)
    meta = json.loads(mp.read_text())
    if sha(master) != meta["expected_sha256"]:
        sys.exit("master does not match its build hash")
    cm = carded(master)
    meta["expected_sha256"], meta["built_sha256"] = sha(cm), meta["expected_sha256"]
    mp.write_text(json.dumps(meta, indent=1, ensure_ascii=False) + "\n")
    out = subprocess.run([sys.executable, "pipeline/youtube_upload.py", str(cm), str(mp)], cwd=ROOT,
                         capture_output=True, text=True)
    cm.unlink()
    if out.returncode:
        sys.exit("long-form upload failed: " + out.stdout[-500:] + out.stderr[-500:])
    up = json.loads(out.stdout.strip().splitlines()[-1])
    master.unlink()
    return up


def main():
    city, day = sys.argv[1], datetime.date.fromisoformat(sys.argv[2])
    limits = json.loads((ROOT / "publish/limits.json").read_text())
    meta = json.loads((ROOT / f"publish/meta/{city}.json").read_text())
    music = json.loads((ROOT / "data/music/used.json").read_text())[city]["titles"]
    D = ROOT / f"output/cities/{city}/illustrated"
    sums = {pathlib.Path(l.split()[1]).name: l.split()[0] for l in (D / "SHA256SUMS").read_text().splitlines()}
    at = lambda h, m: datetime.datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)
    t_long, t_s1, t_s2 = at(11, 0), at(14, 30), at(20, 30)
    if t_long <= datetime.datetime.now(TZ) + datetime.timedelta(hours=1):
        sys.exit("release day is too soon")
    log = json.loads((ROOT / "publish/release_log.json").read_text())
    if any(e["city"] == city for e in log) and not (D / "RELEASE_STATE.json").exists():
        sys.exit(f"{city} already has release log entries; refusing to release twice")
    taken = {e.get("publish_at", e.get("due_at", ""))[:10] for e in log if e.get("item") == "long_form"}
    if day.isoformat() in taken:
        sys.exit(f"{day} already has a long-form")

    L = meta["long"]
    # titles: the owner's simple format (2026-11-24), e.g. "Chicago Chillhop 🚆" / "Chicago Chillhop 🚆 #lofi #chicago #shorts"
    spec = next(x for f in sorted((ROOT / "cities/specs").glob("batch*.json")) for x in json.loads(f.read_text()) if x["id"] == city)
    NAMES = {"washington_dc": "Washington DC", "portland_maine": "Portland Maine", "phoenix_sedona": "Sedona", "anchorage": "Anchorage"}
    name = meta.get("name") or NAMES.get(city) or spec["name"].split(",")[0].strip()
    tag = meta.get("hashtag") or "".join(ch for ch in name.lower() if ch.isalnum())
    L["title"] = f"{name} Chillhop 🚆"
    meta["short_1"]["title"] = f"{name} Chillhop 🚆 #lofi #{tag} #shorts"
    # owner 2026-11-25: Short 2 never repeats Short 1's title; it rotates simple lofi/train/window titles so we can see what works
    em = meta.get('emoji', '🌆')
    S2 = [f"{name} Lofi {em} #lofi #{tag} #shorts", f"Train Window: {name} {em} #lofi #{tag} #shorts",
          f"Lofi Train to {name} {em} #lofi #{tag} #shorts", f"{name} Window Seat {em} #lofi #{tag} #shorts",
          f"{name} by Train 🚆 #lofi #{tag} #shorts", f"Lofi Ride Through {name} {em} #lofi #{tag} #shorts"]
    n_rel = len({e["city"] for e in log if e.get("item") == "long_form"})
    meta["short_2"]["title"] = meta["short_2"].get("title_override") or S2[n_rel % len(S2)]
    long_meta = {"title": L["title"], "tags": L["tags"], "publish_at": t_long.isoformat(),
                 "expected_sha256": sums[f"{city}_illustrated_master.mp4"],
                 "description": "\n\n".join([limits["promotion"]["description_line"], L["summary"], limits["channel_blurb"],
                                             FOOTAGE + "\n" + credit(music, "Tracks were trimmed and cross-faded."), L["hashtags"]])}
    mp = ROOT / f"publish/meta/{city}_long.json"
    mp.write_text(json.dumps(long_meta, indent=1, ensure_ascii=False) + "\n")

    state = D / "RELEASE_STATE.json"            # resume here if a later step fails; never upload twice
    if state.exists():
        up = json.loads(state.read_text())
    else:
        up = upload_long(city, D, mp)
        state.write_text(json.dumps(up))
    link = f"https://youtu.be/{up['video_id']}"

    shorts = []
    for i, t in ((1, t_s1), (2, t_s2)):
        S = meta[f"short_{i}"]
        f = D / f"{city}_illustrated_vertical_{i}.mp4"
        if sha(f) != sums[f.name]:
            sys.exit(f"{f.name} does not match its approved hash")
        fc = carded(f, short=True)
        want = sha(fc)
        key = f"{secrets.token_hex(12)}/{city}_short_{i}.mp4"
        cf("PUT", f"lofitrain-delivery/objects/{key}", fc.read_bytes(), "video/mp4")
        fc.unlink()
        url = f"{DELIVERY}/{key}"
        got = hashlib.sha256(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"}), timeout=300).read()).hexdigest()
        if got != want:
            sys.exit(f"public copy of {f.name} does not match")
        # credit only the songs that play in this Short: song A runs to about its length minus the 4 s cross-fade
        start = 2.0 if i == 1 else float((D / "SHORT2_START").read_text()) if (D / "SHORT2_START").exists() else 100.0
        dur_a = json.loads((ROOT / "data/music/used.json").read_text())[city].get("durations_s", [999])[0]
        cr = credit(music[:1] if start + 25 <= dur_a - 4 else music, "Trimmed.")
        text = "\n\n".join([limits["promotion"]["description_line"], S["summary"] + f"\n▶ Watch the full ride: {link}", limits["channel_blurb"],
                            FOOTAGE + "\n" + cr, S["hashtags"]])
        if "AI" in (text + " " + S["title"]).replace("-", " ").split():
            sys.exit("Short text mentions AI")
        shorts.append({"item": f"short_{i}", "title": S["title"], "text": text, "url": url, "due_at": t.isoformat(),
                       "media_sha256": want, "built_sha256": sums[f.name]})
    print(json.dumps({"city": city, "long_form": {**up, "publish_at": t_long.isoformat(),
                                                   "media_sha256": long_meta["expected_sha256"]}, "shorts": shorts},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
