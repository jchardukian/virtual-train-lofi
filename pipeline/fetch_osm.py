#!/usr/bin/env python3
"""Download raw OpenStreetMap data for a bounding box via the OSM map API.

The API caps each call at 50k nodes, so the box is fetched in small tiles.
Data is (c) OpenStreetMap contributors, ODbL 1.0.

Usage: python3 pipeline/fetch_osm.py scenes/chicago_3d.json
"""
import json
import os
import pathlib
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = os.environ.get("FETCH_USER_AGENT", "TrainSceneBuilder/0.1 (OSM map API tile fetch)")


def main():
    scene = json.loads(pathlib.Path(sys.argv[1]).read_text())
    w, s, e, n = scene["osm"]["bbox"]
    dx, dy = scene["osm"].get("tile_deg", [0.006, 0.004])
    out = ROOT / scene["osm"]["raw_dir"]
    out.mkdir(parents=True, exist_ok=True)
    y, j = s, 0
    while y < n - 1e-9:
        x, i = w, 0
        while x < e - 1e-9:
            f = out / f"tile_{j}_{i}.osm"
            if not f.exists() or f.stat().st_size < 200:
                box = f"{x:.5f},{y:.5f},{min(x + dx, e):.5f},{min(y + dy, n):.5f}"
                url = f"https://api.openstreetmap.org/api/0.6/map?bbox={box}"
                for attempt in range(4):
                    try:
                        req = urllib.request.Request(url, headers={"User-Agent": UA})
                        f.write_bytes(urllib.request.urlopen(req, timeout=120).read())
                        break
                    except Exception as ex:  # noqa: BLE001
                        print("retry", box, ex)
                        time.sleep(10 * (attempt + 1))
                print(f.name, box, f.stat().st_size if f.exists() else "FAILED", flush=True)
                time.sleep(1.5)
            x += dx
            i += 1
        y += dy
        j += 1


if __name__ == "__main__":
    main()
