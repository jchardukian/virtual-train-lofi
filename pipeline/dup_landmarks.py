#!/usr/bin/env python3
"""Flag close-up landmarks that also appear in the city's skyline art (the same landmark twice in one ride).

  python3 pipeline/dup_landmarks.py [city ...] [--sheet out.jpg]

Each close-up landmark cut-out is compared (local CLIP model, free) with windows of the skyline/backdrop art at
several sizes; a window that looks like the same thing (high image similarity) is reported with a side-by-side
tile for checking by eye.
"""
import argparse, json, pathlib
import cv2, numpy as np
ROOT = pathlib.Path(__file__).resolve().parent.parent
import sys; sys.path.insert(0, str(ROOT / "pipeline"))
from prop_scale import clip  # noqa: E402


def on_white(im):
    if im.shape[2] == 4:
        a = im[..., 3:] / 255.0
        return (im[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    return im


def emb(ims):
    from PIL import Image
    m, pre, tok, torch = clip()
    with torch.no_grad():
        x = m.encode_image(torch.stack([pre(Image.fromarray(i[..., ::-1])) for i in ims]))
    return (x / x.norm(dim=-1, keepdim=True)).numpy()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cities", nargs="*"); ap.add_argument("--sheet"); ap.add_argument("--min", type=float, default=0.86)
    a = ap.parse_args()
    cities = a.cities or (ROOT / "work/cities_v3/all50.txt").read_text().split()
    tiles = []
    for c in cities:
        cfg = json.loads((ROOT / f"cities/illustrated/{c}.json").read_text())
        backs = {L["src"] for L in cfg.get("backdrop", [])} | {L["src"] for s in cfg["sections"] for L in s.get("far", [])}
        mids = [m["src"] for s in cfg["sections"] for m in s.get("mid", []) if "landmarks_" in m["src"]]
        if not mids or not backs:
            continue
        wins, boxes = [], []
        for b in backs:
            im = on_white(cv2.imread(str(ROOT / b), cv2.IMREAD_UNCHANGED))
            H, W = im.shape[:2]
            for h in (int(H * 0.45), int(H * 0.7), H):
                for w in (int(h * 0.6), h, int(h * 1.6)):
                    for y in range(0, max(1, H - h + 1), max(1, h // 3)):
                        for x in range(0, max(1, W - w + 1), max(1, w // 3)):
                            wins.append(im[y:y + h, x:x + w]); boxes.append((b, x, y, w, h))
        E = emb(wins)
        M = emb([on_white(cv2.imread(str(ROOT / m), cv2.IMREAD_UNCHANGED)) for m in mids])
        S = M @ E.T
        for i, m in enumerate(mids):
            j = int(S[i].argmax())
            if S[i, j] >= a.min:
                print(f"{c:15s} {m.split('/')[-1]:17s} {S[i, j]:.3f}  {boxes[j][0].split('/')[-1]} at {boxes[j][1:]}")
                if a.sheet:
                    t1 = cv2.resize(on_white(cv2.imread(str(ROOT / m), cv2.IMREAD_UNCHANGED)), (180, 180)); t2 = cv2.resize(wins[j], (180, 180))
                    t = np.hstack([t1, t2]); cv2.putText(t, f"{c[:14]} {S[i, j]:.2f}", (4, 14), 0, 0.45, (0, 0, 255), 1); tiles.append(t)
    if a.sheet and tiles:
        while len(tiles) % 4: tiles.append(np.full_like(tiles[0], 255))
        cv2.imwrite(a.sheet, np.vstack([np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]))


if __name__ == "__main__":
    main()
