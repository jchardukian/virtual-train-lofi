#!/usr/bin/env python3
"""Key the chroma green out of generated sheets and split them into pieces.

  python3 pipeline/illustrated_cut.py <dir> [--sheets a b] [--strips c d] [--whole e]

<dir>/<name>.png in, <dir>/sprites/<name>_<i>.png out (strips: one file per horizontal band; whole: one file).
"""
import argparse, json, pathlib
import cv2
import numpy as np


def key(path):
    im = cv2.imread(str(path)).astype(np.float32)
    g = im[..., 1] - np.maximum(im[..., 0], im[..., 2])
    a = 1 - np.clip((g - 35) / 60, 0, 1)
    a = cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8)), (0, 0), 0.8)
    im[..., 1] = np.where(a < 0.999, np.minimum(im[..., 1], np.maximum(im[..., 0], im[..., 2]) * 1.04), im[..., 1])   # de-spill
    return np.dstack([im, a * 255]).astype(np.uint8)


def runs(mask, gap):
    idx = np.where(mask)[0]
    out, s, p = [], idx[0], idx[0]
    for i in idx[1:]:
        if i - p > gap:
            out.append((s, p)); s = i
        p = i
    out.append((s, p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--sheets", nargs="*", default=[])
    ap.add_argument("--strips", nargs="*", default=[])
    ap.add_argument("--whole", nargs="*", default=[])
    a = ap.parse_args()
    d = pathlib.Path(a.dir); out = d / "sprites"; out.mkdir(exist_ok=True)
    inv = {}
    for sheet in a.sheets:
        rgba = key(d / f"{sheet}.png"); m = rgba[..., 3] > 128
        inv[sheet] = []
        for i, (x0, x1) in enumerate(r for r in runs(m.any(0), 3) if r[1] - r[0] > 25):
            ys = np.where(m[:, x0:x1 + 1].any(1))[0]
            s = rgba[max(0, ys[0] - 3):ys[-1] + 2, max(0, x0 - 3):x1 + 4]
            cv2.imwrite(str(out / f"{sheet}_{i}.png"), s); inv[sheet].append([int(s.shape[1]), int(s.shape[0])])
    for sheet in a.strips:
        rgba = key(d / f"{sheet}.png"); m = rgba[..., 3] > 128
        inv[sheet] = []
        for i, (y0, y1) in enumerate(r for r in runs(m.mean(1) > 0.05, 6) if r[1] - r[0] > 30):
            t = max(0, y0 - 90)
            while t < y0 and not m[t].any():
                t += 1
            s = rgba[t:y1 + 1]
            cv2.imwrite(str(out / f"{sheet}_{i}.png"), s); inv[sheet].append([int(s.shape[1]), int(s.shape[0])])
    for sheet in a.whole:
        rgba = key(d / f"{sheet}.png"); m = rgba[..., 3] > 128; ys = np.where(m.any(1))[0]
        s = rgba[max(0, ys[0] - 2):ys[-1] + 1]
        cv2.imwrite(str(out / f"{sheet}.png"), s); inv[sheet] = [int(s.shape[1]), int(s.shape[0])]
    (out / "inventory.json").write_text(json.dumps(inv, indent=1))
    print(json.dumps(inv))
    cells = []
    for f in sorted(out.glob("*_*.png")):
        v = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)
        if v.shape[1] > 1000:
            continue
        h = 180; w = max(1, int(v.shape[1] * h / v.shape[0])); r = cv2.resize(v, (w, h)); al = r[..., 3:] / 255.0
        c = (r[..., :3] * al + np.array([255, 0, 255]) * (1 - al)).astype(np.uint8)
        cv2.putText(c, f.stem, (2, 12), 0, 0.38, (0, 0, 0), 1); cells.append(c)
    if cells:
        half = (len(cells) + 1) // 2
        r1, r2 = np.hstack(cells[:half]), np.hstack(cells[half:]) if cells[half:] else np.zeros((180, 10, 3), np.uint8)
        w = max(r1.shape[1], r2.shape[1])
        pad = lambda r: np.hstack([r, np.full((180, w - r.shape[1], 3), 255, np.uint8)])
        cv2.imwrite(str(out / "sheet.jpg"), np.vstack([pad(r1), pad(r2)]))


if __name__ == "__main__":
    main()
