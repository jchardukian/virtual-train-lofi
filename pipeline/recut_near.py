"""Re-cut a city's trackside (near) strip from its source sheet: keep only source rows y0..y1, key the green,
feather the top so it melts into the scene, and set its scale/base so it fills the bottom of the window.
usage: recut_near.py city y0 y1 [target_height_px] [base]"""
import cv2, json, numpy as np, sys
c, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
target = int(sys.argv[4]) if len(sys.argv) > 4 else 230
base = int(sys.argv[5]) if len(sys.argv) > 5 else -5
im = cv2.imread(f"work/cities_v3/{c}/near.png")[y0:y1]
h = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
g = (h[..., 0] > 40) & (h[..., 0] < 85) & (h[..., 1] > 120) & (h[..., 2] > 100)
a = cv2.GaussianBlur(np.where(g, 0, 255).astype(np.uint8), (3, 3), 0)
for i in range(20):
    a[i] = (a[i] * (i / 20)).astype(np.uint8)
out = np.dstack([im, a])
rows = np.where(a.max(1) > 0)[0]
out = out[:rows[-1] + 1]
cv2.imwrite(f"work/cities_v3/{c}/sprites/near_0.png", out)
p = f"cities/illustrated/{c}.json"
cfg = json.load(open(p))
cfg["near"]["scale"] = round(target / out.shape[0], 3)
cfg["near"]["base"] = base
json.dump(cfg, open(p, "w"), indent=1)
print(c, out.shape, cfg["near"])
