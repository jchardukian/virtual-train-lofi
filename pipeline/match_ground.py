"""Set a city's plain ground field to run from the colour at the bottom of its distant backdrop down to its
original lower colour, so no flat stripe of a different colour shows between the backdrop and the band."""
import cv2, json, sys, numpy as np
for c in sys.argv[1:]:
    p = f"cities/illustrated/{c}.json"; cfg = json.load(open(p))
    im = cv2.imread(cfg["backdrop"][0]["src"], -1)
    a = im[..., 3] > 200
    rows = np.where(a.mean(1) > 0.8)[0]
    band = im[rows[-30]:rows[-1] + 1][..., :3][a[rows[-30]:rows[-1] + 1]]
    top = band.reshape(-1, 3).mean(0)
    old = cfg["ground_src"]["colour"]
    cfg["ground_src"]["colour"] = [top.tolist(), old[1]]
    json.dump(cfg, open(p, "w"), indent=1)
    print(c, [int(v) for v in top], "->", [int(v) for v in old[1]])
