#!/usr/bin/env python3
"""Close deep, narrow gaps between houses in a strip of buildings, where open sky would otherwise show below the
distant scenery. Each gap is filled with wall cloned from the house beside it (same rows), so the street reads
as one continuous terrace. A backup is kept as <sprite>.bak.png.

  python3 pipeline/fill_notches.py <sprite.png> [--depth 30] [--max-width 160] [--span 140] [--dry]
"""
import argparse, shutil
import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sprite")
    ap.add_argument("--depth", type=int, default=30, help="how far below both neighbours' roofs a gap must reach")
    ap.add_argument("--max-width", type=int, default=160)
    ap.add_argument("--span", type=int, default=140, help="how far to look left and right for the neighbouring roofs")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sp = cv2.imread(a.sprite, cv2.IMREAD_UNCHANGED)
    al = sp[..., 3]
    h, w = al.shape
    top = np.array([(np.where(al[:, x] > 128)[0][:1].tolist() or [h])[0] for x in range(w)])
    level = np.full(w, h)
    for x in range(w):
        lft, rgt = top[max(0, x - a.span):x], top[x + 1:x + 1 + a.span]
        if len(lft) and len(rgt):
            level[x] = max(lft.min(), rgt.min())
    notch = top - level > a.depth
    runs, x = [], 0
    while x < w:
        if notch[x]:
            x1 = x
            while x1 < w and notch[x1]:
                x1 += 1
            if x1 - x <= a.max_width:
                runs.append((x, x1))
            x = x1
        else:
            x += 1
    total = 0
    for x0, x1 in runs:
        lvl = int(level[x0:x1].max())
        wd = x1 - x0
        for dx in range(wd, wd + 220):                    # nearest stretch of wall on the left that is solid over these rows
            if x0 - dx >= 0 and (al[lvl:int(top[x0:x1].max()) + 2, x0 - dx:x1 - dx] > 128).mean() > 0.97:
                break
        else:
            print(f"  gap {x0}-{x1}: no solid wall to clone from, left as is")
            continue
        print(f"  gap {x0}-{x1} (rows {lvl}-{int(top[x0:x1].max())}) filled from {dx} px left")
        if a.dry:
            continue
        for x in range(x0, x1):
            rows = np.arange(lvl, top[x] + 3)
            sp[rows, x] = sp[rows, x - dx]
            total += len(rows)
    if total and not a.dry:
        shutil.copy(a.sprite, a.sprite[:-4] + ".bak.png")
        cv2.imwrite(a.sprite, sp)
        print(f"  {total} px filled")


if __name__ == "__main__":
    main()
