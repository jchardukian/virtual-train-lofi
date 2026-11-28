#!/usr/bin/env python3
"""Download the CC0 Poly Haven assets the scene uses (sky HDRI, wall textures).

Usage: python3 pipeline/fetch_assets.py
"""
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEST = ROOT / "assets" / "polyhaven"
UA = {"User-Agent": "asset-fetch/0.1"}
# asset id -> (kind, resolution, maps)
ASSETS = {
    "kloofendal_48d_partly_cloudy_puresky": ("hdri", "4k", None),
    "brick_wall_001": ("tex", "2k", ["Diffuse"]),
    "red_brick_03": ("tex", "2k", ["Diffuse"]),
    "concrete_wall_008": ("tex", "2k", ["Diffuse"]),
    "concrete_tile_facade": ("tex", "2k", ["Diffuse"]),
    "asphalt_01": ("tex", "2k", ["Diffuse"]),
}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for aid, (kind, res, maps) in ASSETS.items():
        try:
            files = json.load(get(f"https://api.polyhaven.com/files/{aid}"))
        except Exception as e:  # noqa: BLE001
            print("skip", aid, e)
            continue
        if kind == "hdri":
            jobs = [(files["hdri"][res]["hdr"]["url"], DEST / f"{aid}.hdr")]
        else:
            jobs = [(files[m][res]["jpg"]["url"], DEST / f"{aid}_{m.lower()}.jpg") for m in maps if m in files]
        for url, path in jobs:
            if not path.exists():
                path.write_bytes(get(url).read())
            print(path.name, path.stat().st_size)


if __name__ == "__main__":
    main()
