#!/usr/bin/env python3
"""Owner 2026-11-25: one picture per city, no street row, no close-ups, ~40-50% sky.
  python3 pipeline/single_layer.py <city> [...]   rewrites cities/illustrated/<city>.json in place (old config kept as .two_layer.json)
The single layer is the skyline art (or, for cities listed in USE_ROW, the street-row art), scaled so its dense part
fills ~55% of the window and its bottom sits just below the window sill; it scrolls at the skyline speed."""
import json, pathlib, shutil, sys
import cv2, numpy as np
ROOT = pathlib.Path(__file__).resolve().parent.parent
USE_ROW = {"portland_maine", "reykjavik", "santorini"}
OVERRIDE = {c: f"work/cities_v3/{c}/sprites/skyline2.png" for c in ("amsterdam", "pittsburgh", "hallstatt")}
WIN_TOP, SILL, LAND = 40, 1040, 0.55
def dense_extent(path):
    a = cv2.imread(str(ROOT / path), cv2.IMREAD_UNCHANGED)
    al = a[..., 3] if a.shape[2] == 4 else np.full(a.shape[:2], 255, np.uint8)
    cov = (al > 128).mean(1)
    rows = np.where(cov > 0.35)[0]
    solid = np.where(cov > 0.6)[0]
    return int(rows[0]) if len(rows) else 0, int(solid[-1]) + 1 if len(solid) else a.shape[0], a.shape[0]
for c in sys.argv[1:]:
    p = ROOT / f"cities/illustrated/{c}.json"
    bak = p.with_suffix(".two_layer.json")
    if not bak.exists():
        shutil.copy(p, bak)
    d = json.loads(bak.read_text())
    bands = [s["band"]["src"] for s in d["sections"] if s.get("band")]
    bd = d.get("backdrop") or [f for s_ in d["sections"] for f in s_.get("far", [])][:1]
    src = bands[0] if (c in USE_ROW and bands) or not bd else bd[0]["src"]
    src = OVERRIDE.get(c, src)
    top, bot, h = dense_extent(src)
    scale = LAND * (SILL - WIN_TOP) / max(1, bot - top)
    base = SILL + 30 + int(round((h - bot) * scale))          # art bottom just below the sill
    layer = {"src": src, "scale": round(scale, 3), "tile": True, "speed": 5, "haze": 0.0, "base": base, "alpha": 1.0, "feather_bottom": 0}
    d["backdrop"] = [layer]
    for s in d["sections"]:
        s.pop("band", None); s["far"] = []; s["mid"] = []; s["ground"] = "lawn"
    if d.get("weather") in ("leaves", "petals", "fireflies"):
        d["weather"] = "none"          # owner 2026-11-25: nothing falls from the sky except rain and snow
    d["single_layer"] = True; d["street_speed"] = 5; d["gaps_ok"] = "single layer"
    for k in ("near", "mid_front", "hide_backdrop_edge", "no_fill_down"):
        d.pop(k, None)
    p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    print(c, "row" if src in bands else "skyline", "scale", layer["scale"], "base", base)
