"""Close empty bands between a city's layers (see gap_probe.py): first lower the scenery band (and the
landmarks standing on it) until no bare ground shows above the trackside strip, then lower the distant
backdrop until no sky shows between it and the band."""
import json, sys, numpy as np, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import illustrated_city as ic
FR = (1500, 4500, 7500)
def measure(cfg):
    cfg = json.loads(json.dumps(cfg)); cfg.pop("opening", None); cfg["weather"] = "none"
    C = ic.City(cfg); C.grade = lambda im: im; C.sky[:] = (255, 0, 255)
    rgb, a, p = C.lawn; C.lawn = (np.zeros_like(rgb) + np.array([255, 255, 0], np.float32), a, p)
    C.frame = C.frame * 0; C.fa = C.fa * 0
    sg = gg = 0
    for f in FR:
        im = C.render(f)[:, 300:1620].astype(int)
        mf = ((abs(im[..., 0] - 255) + im[..., 1] + abs(im[..., 2] - 255)) < 90).mean(1)
        cf = ((abs(im[..., 0] - 255) + abs(im[..., 1] - 255) + im[..., 2]) < 90).mean(1)
        solid = np.where(mf < 0.1)[0]; r1 = solid[0] if len(solid) else 1080
        sg = max(sg, int((mf[r1:] > 0.15).sum())); gg = max(gg, int((cf > 0.15).sum()))
    return sg, gg
for cid in [a for a in sys.argv[1:] if not a.startswith('--')]:
    p = f"cities/illustrated/{cid}.json"; cfg = json.load(open(p))
    sg, gg = measure(cfg); log = [(sg, gg)]
    moved_band = moved_back = 0
    for _ in range(4 if '--band' in sys.argv else 0):
        if gg <= 3 or moved_band >= 160: break
        d = min(gg + 8, 160 - moved_band); moved_band += d
        for s in cfg["sections"]:
            if s.get("band"): s["band"]["base"] += d
            for m in s.get("mid", []): m["base"] += d
        sg, gg = measure(cfg); log.append((sg, gg))
    for _ in range(5):
        if sg <= 3 or moved_back >= 260: break
        d = min(sg + 10, 260 - moved_back); moved_back += d
        for b in cfg.get("backdrop", []): b["base"] += d
        for s in cfg["sections"]:
            for f in s.get("far", []): f["base"] = f.get("base", 712) + d
        sg, gg = measure(cfg); log.append((sg, gg))
    json.dump(cfg, open(p, "w"), indent=1)
    print(f"{cid:16s} band +{moved_band:3d} backdrop +{moved_back:3d}  (sky rows, ground rows): {log}", flush=True)
