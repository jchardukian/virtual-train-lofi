#!/usr/bin/env python3
"""Similarity gate: is a candidate city different enough from recent releases?

  python3 pipeline/similarity_gate.py <candidate.json> [--against a.json b.json ...] [--video cand.mp4 --videos a.mp4 ...]

Two checks, both reported, neither a numeric guarantee:
1. Asset overlap: which source images the candidate shares with each earlier city, split into
   ground/foreground (river, lawn, tree line, embankment, strips: these must not be shared) and
   backdrop (sky, window frame: shared by design).
2. Picture similarity: perceptual hashes of the opening 10 s and five evenly spaced frames, compared
   frame for frame with each earlier video. Close hashes flag a look-alike for a human to check.
Writes a contact sheet (candidate row on top, earlier cities below) for the human review.
Exit 1 if any rule is broken: shared ground/foreground strip, or opening frames that hash as near-identical.
"""
import argparse, json, pathlib, subprocess, sys
import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
BY_DESIGN = {"work/illus/frame.png", "work/chi/sky.png"}
FOREGROUND_HINTS = ("strip_", "strips_", "mountains_1", "embank", "lawn", "river")


def sources(cfg):
    out = set()
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("src", "treewall") and isinstance(v, str):
                    out.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(cfg)
    # the composer falls back to the shared embankment and lawn when a city gives no trackside or ground of its own
    if "near" not in cfg or "ground_src" not in cfg:
        out.add("work/chi/sprites/strip_3.png")
    if any(s.get("ground") == "river" for s in cfg.get("sections", [])):
        out.add("work/illus/scene.png#water")
    return out


def dhash(img, n=16):
    g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (n + 1, n), interpolation=cv2.INTER_AREA)
    return (g[:, 1:] > g[:, :-1]).flatten()


def frames(video, times):
    out = []
    for t in times:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf", "scale=480:270",
                              "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
        out.append(np.frombuffer(raw, np.uint8).reshape(270, 480, 3) if len(raw) == 270 * 480 * 3 else np.zeros((270, 480, 3), np.uint8))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("candidate")
    ap.add_argument("--against", nargs="*", default=[])
    ap.add_argument("--video")
    ap.add_argument("--videos", nargs="*", default=[])
    ap.add_argument("--sheet", default="similarity_sheet.jpg")
    a = ap.parse_args()
    cand = sources(json.loads(pathlib.Path(a.candidate).read_text()))
    fails, report = [], {"asset_overlap": {}, "frame_similarity": {}}
    for other in a.against:
        shared = cand & sources(json.loads(pathlib.Path(other).read_text()))
        fg = sorted(s for s in shared - BY_DESIGN if any(h in s for h in FOREGROUND_HINTS))
        report["asset_overlap"][pathlib.Path(other).stem] = {"shared": sorted(shared), "shared_ground_or_foreground": fg}
        if fg:
            fails.append(f"shares ground/foreground art with {pathlib.Path(other).stem}: {fg}")
    if a.video:
        times = [3, 8, 60, 120, 180, 240, 290]
        cf = frames(a.video, times)
        rows = [np.hstack(cf)]
        for v in a.videos:
            of = frames(v, times)
            rows.append(np.hstack(of))
            d = [int((dhash(x) != dhash(y)).sum()) for x, y in zip(cf, of)]   # 0 identical .. 256 unrelated
            report["frame_similarity"][pathlib.Path(v).stem] = {"hash_distance_per_frame": d, "times_s": times}
            if min(d[:2]) < 40:
                fails.append(f"opening looks near-identical to {pathlib.Path(v).stem} (hash distance {min(d[:2])})")
        cv2.imwrite(a.sheet, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
        report["contact_sheet"] = a.sheet
    report["pass"] = not fails
    report["fails"] = fails
    print(json.dumps(report, indent=1))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
