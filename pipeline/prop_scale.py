#!/usr/bin/env python3
"""Give small street objects (phone boxes, post boxes, lamps, stalls, vehicles, animals) a believable size.

  python3 pipeline/prop_scale.py [city ...] [--apply] [--sheet out.jpg]

Every cut-out was scaled to house height when the cities were laid out, so a post box could stand as tall
as a three-storey terrace. This identifies each passing object against its city's own list of objects
(a local CLIP model, free, on this machine), looks up a real-world height for small things, and shrinks
any that are drawn far too big. Houses, shops, trees and landmarks keep their size; nothing is enlarged.
Scale: 30 px per metre at 1080p, which puts a 10 m terraced house at its current ~300 px.
"""
import argparse, json, pathlib, re
import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
PX_PER_M = 30.0
MIN_PX = 54                     # very small things stay big enough to read at a glance
# (pattern, height in metres); first match wins; None = keep its size
HEIGHTS = [
    (r"incline railway car|funicular", 4.5), (r"merlion", 8.6),
    (r"house|\bbar\b|bridge|mountain|bandstand|hotel|over the harbour|monastery|church|temple|tower|mill|shop|restaurant|diner|cafe|patio", None),
    (r"grand fountain|forsyth|point fountain|pineapple fountain|lizard fountain", 7.0),
    (r"post box|mailbox|letter box", 1.7), (r"phone box|telephone box", 2.6),
    (r"street lamp|gas lamp|lamp post|\blamp\b|lantern-lit|lantern$", 4.5), (r"bench", 1.0),
    (r"double-decker|\bbus\b", 4.4), (r"\btram\b|streetcar|trolley|people-mover|cable car(?! over)", 3.6),
    (r"passenger train car|train car", 4.2), (r"covered wagon", 3.0), (r"horse-drawn carriage", 2.7),
    (r"black cab|\bcab\b|taxi|tuk-tuk|trishaw|vintage car|\bcar\b|snowmobile|jeep", 1.8),
    (r"dog sled", 1.3), (r"\bsled\b|toboggan", 1.0), (r"snowman", 1.8),
    (r"stall|\bstand\b|kiosk|cart\b|hawker|grill|souk", 3.0), (r"beach umbrella|umbrella", 2.6), (r"beach hut", 3.0),
    (r"camel", 2.2), (r"moose", 2.1), (r"bison", 1.8), (r"husky|\bdog\b", 0.9), (r"penguin", 0.7),
    (r"falcon", 1.6), (r"roadrunner", 1.0), (r"bald eagle", 2.2), (r"swan", 1.0),
    (r"stack of firewood|wood pile|firewood", 1.6), (r"kayak rack", 2.0), (r"spirit house", 2.0),
    (r"ice-fishing hut", 2.6), (r"porch swing|rocking chairs", 3.0),
    (r"beehive sculpture", 2.2), (r"steam clock", 5.5), (r"fountain", 5.0), (r"shuttlecock", 5.5),
    (r"fist sculpture", 6.0), (r"spoon-and-cherry", 9.0), (r"golden spike", 5.0),
    (r"ocotillo", 4.0), (r"prickly pear|barrel cact", 1.5), (r"sunflower|coneflower|orchid cluster|protea bush|sagebrush", 1.6),
    (r"papel picado", 3.5), (r"flower box|flower stall", 3.0), (r"bicycle|vespa|scooter", 1.2),
]


# reviewed by eye on the contact sheet (2026-11-23): cut-outs that are really whole scenes, landmarks or merged
# with a tree keep their size; the model missed London's phone box
SKIP = {("marrakech", "landmarks_2.png"), ("nashville", "local_2.png"), ("atlanta", "local_3.png"), ("barcelona", "landmarks_2.png"),
        ("singapore", "landmarks_0.png"), ("pittsburgh", "landmarks_1.png"), ("hallstatt", "landmarks_3.png"), ("san_antonio", "local_5.png")}
FORCE = {("london", "local_2.png"): "a red telephone box"}


def target_height(name):
    n = name.lower()
    for pat, m in HEIGHTS:
        if re.search(pat, n):
            return None if m is None else max(MIN_PX, m * PX_PER_M)
    return None


_clip = None


def clip():
    global _clip
    if _clip is None:
        import open_clip, torch
        m, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
        _clip = (m.eval(), pre, open_clip.get_tokenizer("ViT-B-32"), torch)
    return _clip


def identify(paths, names):
    from PIL import Image
    m, pre, tok, torch = clip()
    ims = []
    for p in paths:
        im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        a = im[..., 3:] / 255.0
        rgb = (im[..., :3] * a + 255 * (1 - a)).astype(np.uint8)[..., ::-1]      # on white, as a picture of the object
        ims.append(pre(Image.fromarray(rgb)))
    with torch.no_grad():
        fi = m.encode_image(torch.stack(ims)); ft = m.encode_text(tok([f"an illustration of {n}" for n in names]))
        fi = fi / fi.norm(dim=-1, keepdim=True); ft = ft / ft.norm(dim=-1, keepdim=True)
        p = (100 * fi @ ft.T).softmax(-1).numpy()
    return [(names[int(r.argmax())], float(r.max())) for r in p]


def city_plan(c, spec):
    cfg_p = ROOT / f"cities/illustrated/{c}.json"
    cfg = json.loads(cfg_p.read_text())
    names = spec["local"] + spec["landmarks"]
    mids = [(k, i, m) for k, sc in enumerate(cfg["sections"]) for i, m in enumerate(sc.get("mid", []))]
    if not mids:
        return cfg_p, cfg, []
    ids = identify([ROOT / m["src"] for _, _, m in mids], names)
    plan = []
    for (k, i, m), (name, conf) in zip(mids, ids):
        key = (c, m["src"].split("/")[-1])
        if key in SKIP:
            continue
        if key in FORCE:
            name, conf = FORCE[key], 1.0
        h = cv2.imread(str(ROOT / m["src"]), cv2.IMREAD_UNCHANGED).shape[0]
        now = h * m.get("scale", 1.0)
        tgt = target_height(name)
        if tgt and now > tgt * 1.3 and conf > 0.35:
            plan.append({"section": k, "index": i, "src": m["src"], "name": name, "conf": round(conf, 2),
                         "now_px": int(now), "new_px": int(tgt), "new_scale": round(tgt / h, 4)})
    return cfg_p, cfg, plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cities", nargs="*")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--sheet")
    a = ap.parse_args()
    specs = {s["id"]: s for f in sorted((ROOT / "cities/specs").glob("batch*.json")) for s in json.loads(f.read_text())}
    cities = a.cities or (ROOT / "work/cities_v3/all50.txt").read_text().split()
    tiles = []
    for c in cities:
        cfg_p, cfg, plan = city_plan(c, specs[c])
        for p in plan:
            print(f"{c:16s} {p['src'].split('/')[-1]:18s} {p['name'][:40]:40s} {p['conf']:.2f}  {p['now_px']}px -> {p['new_px']}px")
            if a.sheet:
                im = cv2.imread(str(ROOT / p["src"]), cv2.IMREAD_UNCHANGED)
                al = im[..., 3:] / 255.0
                v = (im[..., :3] * al + 255 * (1 - al)).astype(np.uint8)
                v = cv2.resize(v, (int(v.shape[1] * 150 / v.shape[0]), 150))[:, :220]
                t = np.full((190, 230, 3), 255, np.uint8); t[:150, :v.shape[1]] = v
                cv2.putText(t, f"{c[:12]}: {p['name'][:22]}", (2, 168), 0, 0.36, (0, 0, 0), 1)
                cv2.putText(t, f"{p['now_px']} -> {p['new_px']}px  ({p['conf']})", (2, 184), 0, 0.36, (0, 0, 160), 1)
                tiles.append(t)
            if a.apply:
                cfg["sections"][p["section"]]["mid"][p["index"]]["scale"] = p["new_scale"]
        if a.apply and plan:
            cfg_p.write_text(json.dumps(cfg, indent=1) + "\n")
    if a.sheet and tiles:
        while len(tiles) % 8:
            tiles.append(np.full((190, 230, 3), 255, np.uint8))
        cv2.imwrite(a.sheet, np.vstack([np.hstack(tiles[i:i + 8]) for i in range(0, len(tiles), 8)]))


if __name__ == "__main__":
    main()
