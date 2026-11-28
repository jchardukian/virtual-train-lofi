#!/usr/bin/env python3
"""Automated quality checks for a rendered segment.

Checks that can be measured are measured here; checks that need eyes
(landmarks, geography, beauty) are listed in docs/QC_CHECKLIST.md and
supported by the contact sheet this script writes.

Usage: python3 pipeline/qc.py output/chicago_green_line_preview.mp4 [--sheet-every 2]
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

import cv2
import numpy as np


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=codec_name,width,height,r_frame_rate,pix_fmt,nb_frames:format=duration,size,bit_rate",
         "-of", "json", str(path)], capture_output=True, text=True, check=True)
    j = json.loads(r.stdout)
    s, f = j["streams"][0], j["format"]
    n, d = s["r_frame_rate"].split("/")
    return {"codec": s["codec_name"], "width": s["width"], "height": s["height"],
            "fps": round(int(n) / int(d), 3), "pix_fmt": s["pix_fmt"],
            "duration_s": round(float(f["duration"]), 2), "bytes": int(f["size"]),
            "mbps": round(int(f["bit_rate"]) / 1e6, 2)}


def detect(path, fade_s):
    """Black and frozen intervals, ignoring the intentional fades."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-an", "-vf",
         "blackdetect=d=0.2:pix_th=0.08,freezedetect=n=0.002:d=0.5", "-f", "null", "-"],
        capture_output=True, text=True)
    black = [(float(a), float(b)) for a, b in
             re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)]
    freeze = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", r.stderr)]
    return black, freeze


def motion(path, max_seconds=None):
    """Frame-to-frame global motion via sparse optical flow + partial affine.

    Returns per-frame dx, dy (px at 1080p scale) and rotation (deg).
    Jitter = what remains after removing a 1 s moving average, i.e. the
    shake a viewer feels as opposed to the steady flow of scenery.
    """
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    scale_to = 480
    prev, rows = None, []
    limit = int(max_seconds * fps) if max_seconds else None
    while True:
        ok, frame = cap.read()
        if not ok or (limit and len(rows) >= limit):
            break
        h, w = frame.shape[:2]
        k = scale_to / h
        g = cv2.cvtColor(cv2.resize(frame, (int(w * k), scale_to), interpolation=cv2.INTER_AREA),
                         cv2.COLOR_BGR2GRAY)
        if prev is not None:
            p0 = cv2.goodFeaturesToTrack(prev, 400, 0.01, 8)
            dx = dy = rot = 0.0
            if p0 is not None and len(p0) >= 12:
                p1, stt, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None)
                good = stt.ravel() == 1
                if good.sum() >= 12:
                    m, _ = cv2.estimateAffinePartial2D(p0[good], p1[good], method=cv2.RANSAC)
                    if m is not None:
                        dx, dy = m[0, 2] / k * 1080 / h, m[1, 2] / k * 1080 / h
                        rot = float(np.degrees(np.arctan2(m[1, 0], m[0, 0])))
            rows.append((dx, dy, rot))
        prev = g
    cap.release()
    a = np.array(rows) if rows else np.zeros((1, 3))
    win = max(3, int(fps) | 1)
    kern = np.ones(win) / win
    resid = a - np.stack([np.convolve(np.pad(a[:, i], win // 2, mode="edge"), kern, mode="valid")
                          for i in range(3)], axis=1)
    return {
        "frames_analysed": len(rows),
        "mean_flow_px_per_frame": [round(float(a[:, 0].mean()), 2), round(float(a[:, 1].mean()), 2)],
        "jitter_rms_px": [round(float(resid[:, 0].std()), 2), round(float(resid[:, 1].std()), 2)],
        "jitter_p99_px": round(float(np.percentile(np.hypot(resid[:, 0], resid[:, 1]), 99)), 2),
        "rotation_jitter_rms_deg": round(float(resid[:, 2].std()), 3),
        "max_frame_jump_px": round(float(np.abs(np.diff(a[:, :2], axis=0)).max()) if len(a) > 1 else 0, 2),
    }


def contact_sheet(path, out, every, duration):
    rows = max(1, -(-int(duration / every + 1) // 4))
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(path), "-vf",
         f"fps=1/{every},scale=640:-2,drawtext=text='%{{pts\\:hms}}':fontcolor=white:fontsize=22:"
         f"box=1:boxcolor=black@0.6:x=8:y=8,tile=4x{rows}:padding=4", "-frames:v", "1", "-q:v", "3",
         str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--sheet-every", type=float, default=2.0)
    ap.add_argument("--fade", type=float, default=1.5)
    ap.add_argument("--motion-seconds", type=float, default=None)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--no-jitter", action="store_true", help="edited output containing cuts or crossfades: the camera-jitter metric only means something on a continuous shot, where it is checked separately")
    ap.add_argument("--no-spec", action="store_true", help="skip output-spec assertions (for source files)")
    a = ap.parse_args()
    path = pathlib.Path(a.video)

    p = probe(path)
    black, freeze = detect(path, a.fade)
    inner_black = [b for b in black if b[0] > a.fade + 0.2 and b[1] < p["duration_s"] - a.fade - 0.2]
    m = motion(path, a.motion_seconds)
    sheet = path.with_suffix(".contact.jpg")
    contact_sheet(path, sheet, a.sheet_every, p["duration_s"])

    checks = {
        "h264": p["codec"] == "h264",
        f"{a.width}x{a.height}": (p["width"], p["height"]) == (a.width, a.height),
        "fps>=30": p["fps"] >= 30,
        "yuv420p": p["pix_fmt"] == "yuv420p",
        "no_black_frames_mid_clip": not inner_black,
        "no_frozen_frames": not freeze,
        "jitter_rms<1.5px": max(m["jitter_rms_px"]) < 1.5,
        "rotation_jitter<0.05deg": m["rotation_jitter_rms_deg"] < 0.05,
    }
    if a.no_jitter:
        checks = {k: v for k, v in checks.items() if not k.startswith(("jitter", "rotation"))}
    if a.no_spec:
        checks = {k: v for k, v in checks.items() if k.startswith(("no_", "jitter", "rotation"))}
    report = {"file": str(path), "probe": p, "black_intervals": black, "freeze_starts": freeze,
              "motion": m, "checks": checks, "pass": all(checks.values()),
              "contact_sheet": str(sheet)}
    path.with_suffix(".qc.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
