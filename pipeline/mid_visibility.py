"""List landmarks that only peek over the scenery band (their bottom hidden, top showing), which reads as a
roof or animal floating in the air. --fix removes those showing less than MINFRAC of their height."""
import cv2, json, sys, glob, numpy as np
MINFRAC = 0.6
fix = "--fix" in sys.argv
cities = [a for a in sys.argv[1:] if not a.startswith("--")]
def band_top(b):
    a = cv2.imread(b["src"], -1)[..., 3]; s = b.get("scale", 1)
    rows = np.where((a > 128).mean(1) > 0.6)[0]; t = rows[0] if len(rows) else 0
    return b.get("base", 850) - (a.shape[0] - t) * s + b.get("feather_top", 90) * 0.5
def main():
  for cid in cities:
      p = f"cities/illustrated/{cid}.json"; cfg = json.load(open(p)); out = []
      for s in cfg["sections"]:
          if not s.get("band"): continue
          bt = band_top(s["band"]); keep = []
          for m in s.get("mid", []):
              h = cv2.imread(m["src"], -1).shape[0] * m.get("scale", 1)
              frac = (bt - (m["base"] - h)) / h
              if frac < MINFRAC: out.append(f"{m['src'].split('/')[-1][:-4]}:{frac:.2f}")
              else: keep.append(m)
          if fix: s["mid"] = keep
      if fix: json.dump(cfg, open(p, "w"), indent=1)
      print(f"{cid:16s} {' '.join(out)}")

if __name__ == '__main__':
    main()
