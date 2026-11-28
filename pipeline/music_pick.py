#!/usr/bin/env python3
"""Pick two unused, licensed tracks for a city and download them.

  python3 pipeline/music_pick.py <city_id> <keyword> [<keyword> ...]

Only tracks in data/music/purrplecat_manifest.json (CC BY 4.0) are eligible. Tracks already used by any city
(data/music/used.json) are skipped, so no two cities share a track. Tracks whose title matches a keyword are
tried first, then the rest in a fixed shuffled order. Each candidate is downloaded and probed; the pair must
cover at least 310 s after cross-fading. Prints the two file paths and records them as used.
"""
import json, pathlib, random, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
USED = ROOT / "data/music/used.json"
DIR = ROOT / "work/music_lib"


def duration(f):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def fetch(t):
    DIR.mkdir(parents=True, exist_ok=True)
    f = DIR / ("".join(c if c.isalnum() else "_" for c in t["title"]) + ".mp3")
    if not f.exists() or duration(f) < 30:
        subprocess.run(["curl", "-sS", "--fail", "-L", "-o", str(f), t["mp3_url"]], capture_output=True)
    return f if f.exists() and duration(f) >= 60 else None


def main():
    city, keys = sys.argv[1], [k.lower() for k in sys.argv[2:]]
    used = json.loads(USED.read_text()) if USED.exists() else {}
    if city in used:
        print("\n".join(used[city]["files"])); return
    taken = {t for v in used.values() for t in v["titles"]}
    tracks = [t for t in json.loads((ROOT / "data/music/purrplecat_manifest.json").read_text())["tracks"]
              if t.get("license") == "CC BY 4.0" and t["title"] not in taken]
    rnd = random.Random(city)
    rnd.shuffle(tracks)
    tracks.sort(key=lambda t: -sum(k in t["title"].lower() or k in t.get("album", "").lower() for k in keys))
    got = []
    for t in tracks:
        f = fetch(t)
        if not f:
            continue
        got.append((t, f, duration(f)))
        if len(got) >= 2 and sum(d for _, _, d in got[:2]) - 4 >= 310:
            break
        if len(got) >= 2:                           # pair too short: keep the longer one and try again
            got.sort(key=lambda g: -g[2]); got = got[:1]
    if len(got) < 2:
        sys.exit("no pair long enough")
    got = got[:2]
    used[city] = {"titles": [t["title"] for t, _, _ in got], "albums": [t.get("album") for t, _, _ in got],
                  "files": [str(f.relative_to(ROOT)) for _, f, _ in got], "durations_s": [round(d, 1) for _, _, d in got], "licence": "CC BY 4.0"}
    USED.write_text(json.dumps(used, indent=1) + "\n")
    print("\n".join(used[city]["files"]))


if __name__ == "__main__":
    main()
