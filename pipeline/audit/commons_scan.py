#!/usr/bin/env python3
"""Metadata-only scan of Wikimedia Commons for train-view videos of a city.

Commons' file host blocks the build machine, so nothing here is downloaded or
viewed: every hit is an UNVIEWED CANDIDATE. Output: data/audit/commons_candidates.json
"""
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
UA = "TrainFootageAudit/0.1 (metadata-only catalogue scan)"
CITIES = {"Tokyo": ["Tokyo", "Yamanote", "Shinjuku", "Shibuya"], "Barcelona": ["Barcelona"], "London": ["London"],
          "New York": ["New York", "NYC", "Manhattan", "Brooklyn"], "Paris": ["Paris"], "Istanbul": ["Istanbul"],
          "Hong Kong": ["Hong Kong"], "Bangkok": ["Bangkok"], "Sydney": ["Sydney"], "Rio de Janeiro": ["Rio de Janeiro"],
          "Chicago": ["Chicago", "CTA"]}
RIDE = re.compile(r"cab|ride|führerstand|fuhrerstand|window|view from|front view|rear view|pov|journey|trip|driver|前面展望|車窓|leaving|arriv|line|metro|tram|subway|train|rail", re.I)
FREE = ("CC BY", "CC0", "Public domain", "CC BY-SA", "PDM")


def api(**kw):
    kw.update(format="json")
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(kw)
    for i in range(5):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40))
        except Exception:  # noqa: BLE001
            time.sleep(6 * (i + 1))
    return {}


def main():
    out = {}
    for city, names in CITIES.items():
        seen, hits = set(), []
        for q in ("cab ride", "train ride view", "metro tram ride", "view from train"):
            d = api(action="query", generator="search", gsrsearch=f"filetype:video {names[0]} {q}", gsrnamespace=6,
                    gsrlimit=50, prop="imageinfo", iiprop="size|extmetadata|url",
                    iiextmetadatafilter="LicenseShortName|Artist")
            for p in d.get("query", {}).get("pages", {}).values():
                t = p["title"]
                if t in seen or "imageinfo" not in p:
                    continue
                seen.add(t)
                ii = p["imageinfo"][0]
                lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
                if not any(n.lower() in t.lower() for n in names) or not RIDE.search(t):
                    continue
                hits.append({"title": t, "width": ii.get("width"), "height": ii.get("height"),
                             "duration_s": round(ii.get("duration") or 0, 1), "license": lic,
                             "free_commercial": lic.startswith(FREE) and "NC" not in lic and "ND" not in lic,
                             "page": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_"))})
            time.sleep(3)
        out[city] = sorted(hits, key=lambda h: -h["duration_s"])
        ok = [h for h in hits if h["free_commercial"] and (h["width"] or 0) >= 1920 and (h["height"] or 0) >= 1080 and h["width"] > h["height"]]
        print(f"{city}: {len(hits)} title matches, {len(ok)} landscape 1080p+ free-licence, {sum(h['duration_s'] for h in ok) / 60:.1f} min", flush=True)
    (ROOT / "data" / "audit" / "commons_candidates.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
