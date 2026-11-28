"""Render a few frames of a city with the sky painted magenta and the ground plane cyan, then report rows
below the first solid scenery where either still shows through: an empty band between layers."""
import json, sys, numpy as np, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import illustrated_city as ic
def probe(cid, frames=(1500, 3600, 5400, 7200, 8600)):
    cfg = json.load(open(f"cities/illustrated/{cid}.json"))
    cfg.pop("opening", None); cfg["weather"] = "none"
    C = ic.City(cfg)
    C.no_grade = True; C.grade = lambda im: im
    C.sky[:] = (255, 0, 255)
    rgb, a, p = C.lawn; C.lawn = (np.zeros_like(rgb) + np.array([255, 255, 0], np.float32), a, p)
    C.frame = C.frame * 0; C.fa = C.fa * 0
    worst = []
    for f in frames:
        im = C.render(f)[:, 300:1620].astype(int)
        mag = (abs(im[..., 0] - 255) + im[..., 1] + abs(im[..., 2] - 255)) < 60
        cya = (abs(im[..., 0] - 255) + abs(im[..., 1] - 255) + im[..., 2]) < 60
        mf, cf = mag.mean(1), cya.mean(1)
        solid = np.where(mf < 0.1)[0]
        r1 = solid[0] if len(solid) else 1080
        skygap = int((mf[r1:] > 0.25).sum())
        ground = int((cf > 0.25).sum())
        worst.append((f, skygap, ground))
    return worst
if __name__ == "__main__":
    for c in sys.argv[1:]:
        w = probe(c)
        print(f"{c:16s} sky-gap rows {max(x[1] for x in w):4d}   bare-ground rows {max(x[2] for x in w):4d}   {w}", flush=True)
