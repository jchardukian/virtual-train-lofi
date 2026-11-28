"""Find cities where sky shows through between the distant layers and the band in front of them: the
distant layer's bottom edge must sit behind the band's solid top. --fix lowers the backdrop to cover the gap."""
import cv2, json, sys, numpy as np, glob
fix = "--fix" in sys.argv
def solid_top(src, scale, base, feather):
    a = cv2.imread(src, -1)[..., 3]
    h = a.shape[0]
    rows = np.where((a > 128).mean(1) > 0.9)[0]          # rows that are opaque nearly all the way across
    t = rows[0] if len(rows) else 0
    return base - (h - t) * scale + feather
for p in sorted(glob.glob("cities/illustrated/*.json")):
    c = json.load(open(p))
    if c.get("version") != 3 or not c.get("backdrop"):
        continue
    tops = [solid_top(s["band"]["src"], s["band"].get("scale", 1), s["band"].get("base", 850), s["band"].get("feather_top", 90))
            for s in c["sections"] if s.get("band")]
    need = max(tops) + 25
    b = c["backdrop"][0]
    gap = need - b["base"]
    if gap > 0:
        print(f"{p.split('/')[-1][:-5]:16s} backdrop bottom {b['base']} band solid from {int(max(tops))} -> gap {int(gap)}")
        if fix:
            b["base"] = int(need); json.dump(c, open(p, "w"), indent=1)
