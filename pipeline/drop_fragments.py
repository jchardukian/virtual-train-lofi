"""Drop low, wide props (stalls, carts, boats, animals, vehicles, umbrellas...) that stand mostly hidden behind
the scenery band: with only their top showing they read as an awning or an animal floating in the air."""
import cv2, json, re, sys
KEY = re.compile(r"stall|stand|cart|boat|barge|abra|dhow|gondola|ferry|kayak|canoe|bumboat|longtail|trajinera|taxi|"
                 r"horse|camel|moose|bison|dog|husky|penguin|falcon|flamingo|roadrunner|eagle|swan|"
                 r"car\b|bus|cab\b|tram|streetcar|trolley|tuk|trishaw|wagon|sled|snowmobile|toboggan|plane|carriage|"
                 r"umbrella|awning|bench|rack|grill|stack|pile|table|bike|bicycle|scooter|kiosk|hut|tent|patio|lift", re.I)
sys.path.insert(0, "pipeline")
from mid_visibility import band_top
spec = {c["id"]: c for i in range(1, 6) for c in json.load(open(f"cities/specs/batch{i}.json"))}
for cid in open("work/cities_v3/all50.txt").read().split():
    p = f"cities/illustrated/{cid}.json"; cfg = json.load(open(p)); gone = []
    for s in cfg["sections"]:
        if not s.get("band"): continue
        bt = band_top(s["band"]); keep = []
        for m in s.get("mid", []):
            name = m["src"].split("/")[-1][:-4]
            kind, idx = name.split("_")[0], int(re.match(r"\d+", name.split("_")[1]).group())
            desc = spec[cid][kind][idx] if idx < len(spec[cid][kind]) else ""
            h = cv2.imread(m["src"], -1).shape[0] * m.get("scale", 1)
            frac = (bt - (m["base"] - h)) / h
            if frac < 0.75 and KEY.search(desc): gone.append(f"{name}({desc[:28]},{frac:.2f})")
            else: keep.append(m)
        s["mid"] = keep
    json.dump(cfg, open(p, "w"), indent=1)
    if gone: print(f"{cid:15s}", "; ".join(gone))
