#!/usr/bin/env python3
"""Put back wall that the green-screen cut removed by mistake from a strip of buildings.

  python3 pipeline/fill_key_holes.py <sprite.png> <source.png> [--min-area 300] [--dry]

The strip is located in its source painting; any transparent patch enclosed inside the buildings (below the
first solid pixel of its column and above the last) of at least --min-area pixels is given back its painted
pixels from the source, except where the source itself is green screen. A backup is kept as <sprite>.bak.png.
"""
import argparse, shutil
import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sprite")
    ap.add_argument("source")
    ap.add_argument("--min-area", type=int, default=300)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sp = cv2.imread(a.sprite, cv2.IMREAD_UNCHANGED)
    src = cv2.imread(a.source)
    alpha = sp[..., 3]
    # where does the strip sit in its source? match on the visible pixels only
    res = cv2.matchTemplate(src, sp[..., :3], cv2.TM_SQDIFF, mask=cv2.merge([(alpha > 250).astype(np.uint8)] * 3))
    _, _, (x0, y0), _ = cv2.minMaxLoc(res)
    h, w = alpha.shape
    patch = src[y0:y0 + h, x0:x0 + w]
    err = np.abs(patch.astype(int) - sp[..., :3].astype(int))[alpha > 250].mean()
    if err > 6:
        raise SystemExit(f"could not locate the strip in its source (mean error {err:.1f})")
    inside = np.zeros_like(alpha, bool)
    for x in range(w):
        col = np.where(alpha[:, x] > 128)[0]
        if len(col):
            inside[col[0]:col[-1], x] = alpha[col[0]:col[-1], x] < 128
    b, g, r = (patch[..., i].astype(int) for i in range(3))
    screen = (g > r + 30) & (g > b + 30)
    n, lab, st, _ = cv2.connectedComponentsWithStats((inside & ~screen).astype(np.uint8))
    fill = np.zeros_like(alpha, bool)
    for i in range(1, n):
        if st[i][4] >= a.min_area:
            fill |= lab == i
            print("  fill", [int(v) for v in st[i][:5]])
    if a.dry or not fill.any():
        return
    fill = cv2.dilate(fill.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0       # cover the soft edge of the cut too
    shutil.copy(a.sprite, a.sprite[:-4] + ".bak.png")
    sp[fill, :3] = patch[fill]
    sp[fill, 3] = np.maximum(sp[fill, 3], 255)
    cv2.imwrite(a.sprite, sp)
    print(f"  {int(fill.sum())} px restored at source offset ({x0}, {y0}), match error {err:.1f}")


if __name__ == "__main__":
    main()
