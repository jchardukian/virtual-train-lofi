#!/usr/bin/env python3
"""From a city spec to generated art, cut pieces and a composer settings file.

  python3 pipeline/city_from_spec.py <spec.json> --generate      # 6 image calls, logged to a ledger, refuses past the cap
  python3 pipeline/city_from_spec.py <spec.json> --cut           # key out the green, split sheets into pieces
  python3 pipeline/city_from_spec.py <spec.json> --config        # write cities/illustrated/<id>.json

spec: {"id", "name", "next", "mood" (season/time/weather/light, one sentence), "weather" (snow|leaves|petals|rain|none),
       "opening", "sky", "skyline", "ground_band", "near", "landmarks": [6], "local": [7, the last one a tree], "music": [2 titles]}
All six images are generated as one matched set: the same mood sentence opens every prompt, so light, season and
palette agree across layers.
"""
import argparse, json, pathlib, subprocess, sys
import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
ART = ROOT / "work/cities_v3"
LEDGER = ROOT / "data/illustrated/batch50_generation_ledger.json"
CAP = 60.0
STYLE = ("Use the attached illustration ONLY as the art-style reference: match exactly its anime-inspired hand-painted look, "
         "clean linework, soft cel shading and rich detail. Do not copy its composition, buildings, season or lighting. ")
KEY = (" Everything that is not part of the described artwork must be a single flat solid pure chroma green colour (#00FF00) "
       "with clean sharp edges against it: no ground plane, no cast shadows on the green, no sky, no readable text or lettering "
       "anywhere, no watermark, no border.")
PLAIN = " No readable text or lettering anywhere, no watermark, no border, no train window frame."
ELEV = ("Draw it as a flat side-on elevation, as seen from the window of a train passing by, like the background art of a "
        "side-scrolling animation: no perspective convergence, verticals perfectly vertical. ")
ROW = ("standing side by side in one row with a clear wide green gap between each, every one complete from its base to its top, "
       "all bases aligned on one level line near the bottom edge of the canvas")


def prompts(sp):
    m = sp["mood"].rstrip(".") + ". All lighting, colours, season and weather must match this exactly. "
    lm = ", ".join(f"{i + 1}) {x}" for i, x in enumerate(sp["landmarks"]))
    lo = ", ".join(f"{i + 1}) {x}" for i, x in enumerate(sp["local"]))
    return {
        "opening": (False, f"{sp['name']}: {m}A wide illustrated view seen from a train window: {sp['opening']} The scene fills the whole canvas edge to edge."),
        "sky": (False, f"{sp['name']}: {m}A very wide sky only, filling the entire canvas edge to edge: {sp['sky']} No land, no buildings, no mountains."),
        "landmarks": (True, f"{ELEV}{sp['name']}: {m}A sprite sheet of six separate landmarks {ROW}: {lm}."),
        "local": (True, f"{ELEV}{sp['name']}: {m}A sprite sheet of seven separate local elements {ROW}: {lo}."),
        "far": (True, f"{ELEV}{sp['name']}: {m}Two separate full-width horizontal landscape strips stacked one above the other, each running "
                      f"continuously from the left edge to the right edge, separated by a band of flat green: STRIP 1 (top): {sp['skyline']} "
                      f"STRIP 2 (bottom): {sp['ground_band']}"),
        "near": (True, f"{ELEV}{sp['name']}: {m}A single full-width horizontal strip running from the left edge to the right edge, in the lower "
                       f"part of the canvas: right beside the train, {sp['near']}, all in the foreground."),
    }


def spent():
    """Total so far across the shared ledger and every per-city ledger (each city writes only its own file)."""
    calls = json.loads(LEDGER.read_text())["calls"] if LEDGER.exists() else []
    seen = {(c["city"], c["name"]) for c in calls}
    for f in ART.glob("*/ledger.json"):
        for c in json.loads(f.read_text()):
            if (c["city"], c["name"]) not in seen:
                calls.append(c)
    return sum(c["est_cost_usd"] for c in calls), calls


def generate(sp):
    d = ART / sp["id"]
    d.mkdir(parents=True, exist_ok=True)
    todo = [(k, v) for k, v in prompts(sp).items() if not (d / f"{k}.png").exists()]
    total, calls = spent()
    if total + 0.19 * len(todo) > CAP:
        sys.exit(f"refused: {len(todo)} calls would pass the {CAP} USD cap (spent {total:.2f})")
    procs = []
    for k, (keyed, p) in todo:
        full = STYLE + p + (KEY if keyed else PLAIN)
        procs.append((k, full, subprocess.Popen(
            ["curl", "-sS", "https://api.openai.com/v1/images/edits", "-H", "Authorization: Bearer dummy", "-F", "model=gpt-image-2",
             "-F", f"image=@{ROOT / 'work/illus/scene.png'}", "-F", "size=1536x1024", "-F", "quality=high",
             "--form-string", f"prompt={full}", "-o", str(d / f"{k}.json")])))
    import base64
    for k, full, pr in procs:
        pr.wait()
        try:
            r = json.loads((d / f"{k}.json").read_text())
        except Exception as e:
            print(sp["id"], k, "FAILED", e); continue
        if "data" not in r:
            print(sp["id"], k, "FAILED", str(r)[:200]); continue
        (d / f"{k}.png").write_bytes(base64.b64decode(r["data"][0]["b64_json"]))
        u = r["usage"]; dd = u["input_tokens_details"]
        cost = round(u["output_tokens"] * 30e-6 + dd["image_tokens"] * 8e-6 + dd["text_tokens"] * 5e-6, 4)
        calls.append({"city": sp["id"], "name": k, "model": "gpt-image-2", "quality": "high", "prompt": full, "usage": u, "est_cost_usd": cost})
        (d / f"{k}.json").unlink()
    mine = [c for c in calls if c["city"] == sp["id"]]
    (d / "ledger.json").write_text(json.dumps(mine, indent=1) + "\n")       # per city: no shared file, no write races
    print(sp["id"], "generated", len(todo), "spent so far", round(spent()[0], 2))


def autosplit(d):
    """Split pieces the cutter merged (two objects touching across a thin gap)."""
    for f in sorted((d / "sprites").glob("l*_*.png")):
        im = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)
        if im is None:
            continue
        a = im[..., 3] > 128
        col = a.sum(0)
        w, h = im.shape[1], im.shape[0]
        if w < 1.25 * h or w < 260:
            continue
        lo, hi = int(w * 0.25), int(w * 0.75)
        c = lo + int(np.argmin(col[lo:hi]))
        if col[c] > 0.12 * h:
            continue
        for tag, part in (("a", im[:, :c]), ("b", im[:, c:])):
            pa = part[..., 3] > 128
            if pa.sum() < 500:
                continue
            ys, xs = np.where(pa.any(1))[0], np.where(pa.any(0))[0]
            cv2.imwrite(str(f.with_name(f.stem + tag + ".png")), part[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1])
        f.rename(f.with_suffix(".merged"))


def sky_key(path):
    """Some strips come back with painted sky behind them instead of the key colour. Flood-fill from the top
    edge with a floating colour tolerance (follows the sky gradient) and make that region transparent."""
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    a = im[..., 3]
    rows = np.where((a > 128).mean(1) > 0.8)[0]          # first nearly fully opaque row: painted sky starts here
    if not len(rows) or rows[0] > 0.3 * a.shape[0]:
        return False
    y0 = int(rows[0]) + 1
    rgb = np.ascontiguousarray(im[..., :3])
    h, w = a.shape
    mask = np.zeros((h + 2, w + 2), np.uint8)
    for x in range(0, w, max(1, w // 24)):
        if mask[y0 + 1, x + 1] == 0:
            cv2.floodFill(rgb.copy(), mask, (x, y0), (0, 0, 0), (7, 7, 7), (7, 7, 7), 4 | cv2.FLOODFILL_MASK_ONLY | (255 << 8))
    mask[1:y0 + 1] = 255                                    # rows above the start are key colour or edge spill
    sky = mask[1:-1, 1:-1] > 0
    if sky.mean() < 0.05:
        return False
    sky = cv2.morphologyEx(sky.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    soft = cv2.GaussianBlur(sky.astype(np.float32), (0, 0), 1.5)
    im[..., 3] = (a.astype(np.float32) * (1 - soft)).astype(np.uint8)
    rows = np.where((im[..., 3] > 128).mean(1) > 0.05)[0]
    if len(rows):
        im = im[max(0, rows[0] - 2):]
    cv2.imwrite(str(path), im)
    return True


def trim_flat_top(path):
    """A strip whose top is painted, featureless sky (gradients the flood fill could not follow): find the first
    row with real detail (edges) and fade the strip in from just above it."""
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    a = im[..., 3]
    h = a.shape[0]
    if (a[: max(3, h // 10)] > 128).mean() < 0.9:
        return False
    g = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2GRAY).astype(np.float32)
    e = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3))
    row = cv2.blur(e, (31, 9)).mean(1)
    thr = 0.45 * np.median(row[h // 3:])
    detail = np.where(row > thr)[0]
    y = int(detail[0]) if len(detail) else 0
    if y < 0.08 * h:
        return False
    y = max(0, y - 10)
    ramp = np.clip((np.arange(h) - y) / 14.0, 0, 1)[:, None]
    im[..., 3] = (a.astype(np.float32) * ramp).astype(np.uint8)
    cv2.imwrite(str(path), im[max(0, y - 2):])
    return True


def trim_near_backdrop(path):
    """Trackside strips sometimes come back with a little distant town or skyline painted above the foreground.
    Keep only the solid foreground band (rows that are almost fully covered) plus a short soft margin."""
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    cov = (im[..., 3] > 128).mean(1)
    solid = np.where(cov > 0.9)[0]
    if not len(solid):
        return False
    h = im.shape[0]
    y = max(0, int(solid[0] - 0.12 * (h - solid[0])))
    if y < 0.15 * h:
        return False
    ramp = np.clip((np.arange(h) - y) / 20.0, 0, 1)[:, None]
    im[..., 3] = (im[..., 3].astype(np.float32) * ramp).astype(np.uint8)
    cv2.imwrite(str(path), im[y:])
    return True


def drop_specks(path, min_frac=0.004):
    """Remove small disconnected islands left in a strip's alpha (bits of keyed sky, stray clouds)."""
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    a = (im[..., 3] > 64).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(a, 8)
    if n <= 2:
        return False
    keep = np.zeros(n, bool)
    keep[1:] = st[1:, cv2.CC_STAT_AREA] >= min_frac * a.size
    # also drop anything that floats free in the upper half (sky remnants): real scenery touches the strip's base
    h = a.shape[0]
    for i in range(1, n):
        if st[i, cv2.CC_STAT_TOP] + st[i, cv2.CC_STAT_HEIGHT] < 0.6 * h:
            keep[i] = False
    mask = keep[lab]
    if mask.sum() == a.sum():
        return False
    im[..., 3] = np.where(mask, im[..., 3], 0).astype(np.uint8)
    cv2.imwrite(str(path), im)
    return True


def cut(sp):
    d = ART / sp["id"]
    subprocess.run([sys.executable, str(ROOT / "pipeline/illustrated_cut.py"), str(d), "--sheets", "landmarks", "local", "--strips", "far", "near"],
                   check=True, stdout=subprocess.DEVNULL)
    autosplit(d)
    for f in sorted((d / "sprites").glob("far_*.png")) + [d / "sprites/near_0.png"]:
        if f.exists() and sky_key(f):
            print(sp["id"], "keyed painted sky out of", f.name)
        if f.exists() and trim_flat_top(f):
            print(sp["id"], "trimmed flat painted sky from", f.name)
    for f in sorted((d / "sprites").glob("far_*.png")):
        if drop_specks(f):
            print(sp["id"], "removed stray specks from", f.name)
    n0 = d / "sprites/near_0.png"
    if n0.exists() and trim_near_backdrop(n0):
        print(sp["id"], "trimmed distant scenery off the trackside strip")


def dense_top(path):
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    rows = np.where((im[..., 3] > 128).mean(1) > 0.4)[0]
    return im.shape[0], (rows[0] if len(rows) else 0), im


def config(sp):
    d = ART / sp["id"]; s = d / "sprites"
    rel = lambda p: str(p.relative_to(ROOT))
    pieces = lambda pre: sorted(p for p in s.glob(f"{pre}_*.png") if not p.name.endswith(".merged"))
    L, O = pieces("landmarks"), pieces("local")
    far = sorted(s.glob("far_*.png")); near = s / "near_0.png"
    if len(far) < 2 or not near.exists() or len(L) < 3 or len(O) < 3:
        sys.exit(f"{sp['id']}: too few pieces (landmarks {len(L)}, local {len(O)}, far {len(far)})")
    bh, bt, bim = dense_top(far[1])
    band_scale, band_base = 0.95, 905
    band_top = band_base - (bh - bt) * band_scale
    bottom = bim[-30:][bim[-30:, :, 3] > 128][:, :3].astype(np.float32)
    gc = bottom.mean(0) if len(bottom) else np.array([90, 140, 100.])
    nh, nt, _ = dense_top(near)
    nscale = 0.85
    nbase = int(890 - nt * nscale + nh * nscale - 1080)

    def sized(p, target):
        im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        h, w = im.shape[:2]
        tall = h / max(w, 1) > 2.2
        return float(np.clip((target * (1.2 if tall else 1.0)) / h, 0.55, 1.7))

    mid_base = int(band_top + (bh - bt) * band_scale * 0.62)   # bases sit well behind the band, not on open water
    secs = []
    for k in range(5):
        items = []
        for p in L[k::5][:2]:
            items.append({"src": rel(p), "scale": sized(p, 470), "base": mid_base})
        for p in O[k::5][:2]:
            items.append({"src": rel(p), "scale": sized(p, 300), "base": mid_base + 25})
        order = [items[i] for i in (2, 0, 3, 1) if i < len(items)] + items[4:]
        secs.append({"name": f"part {k + 1}", "mid": order or items,
                     "band": {"src": rel(far[1]), "scale": band_scale, "base": band_base, "offset": 300 + 700 * k, "feather_top": 35}})
    tree = max(O, key=lambda p: (lambda im: im.shape[0] / im.shape[1])(cv2.imread(str(p), cv2.IMREAD_UNCHANGED)))
    cfg = {"city": sp["name"], "next": sp.get("next", "coming soon"), "version": 3, "season": sp["mood"],
           "sky": rel(d / "sky.png"), "sky_top": 0.25, "opening": {"src": rel(d / "opening.png"), "hold": 6, "fade": 3},
           "weather": sp.get("weather") if sp.get("weather") not in (None, "none") else None,
           "ground_src": {"colour": [[float(x) for x in gc * 1.02], [float(x) for x in gc * 0.85]]},
           "near": {"src": rel(near), "scale": nscale, "base": nbase},
           "treewall_cfg": {"src": rel(tree), "crop": [0, 4000, 0, 1.0]},
           "backdrop": [{"src": rel(far[0]), "scale": 1.5, "tile": True, "speed": 5, "haze": 0.15, "base": int(band_top + 60), "alpha": 1.0}],
           "sections": secs}
    (ROOT / "cities/illustrated" / f"{sp['id']}.json").write_text(json.dumps(cfg, indent=1))
    print(sp["id"], "config written; pieces", len(L), len(O))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--cut", action="store_true")
    ap.add_argument("--config", action="store_true")
    a = ap.parse_args()
    specs = json.loads(pathlib.Path(a.spec).read_text())
    for sp in (specs if isinstance(specs, list) else [specs]):
        if a.generate:
            generate(sp)
        if a.cut:
            cut(sp)
        if a.config:
            config(sp)


if __name__ == "__main__":
    main()
