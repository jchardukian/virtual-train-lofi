#!/usr/bin/env python3
"""Seamless train-window loop from a few still layer renders (2.5D parallax).

Input: orthographic depth-layer strips from `blender_scene.py --layers`.
Each strip scrolls at the speed its depth implies, wraps exactly once per
loop, and is composited with sky, a mirrored rippling river, passing
track-side posts and a carriage window frame. Every motion is periodic in
the loop length, so the last frame flows into the first.

Usage: python3 pipeline/parallax_loop.py scenes/chicago_loop_v1.json [--seconds 60] [--out output/x.mp4]
"""
import argparse
import json
import math
import pathlib
import subprocess
import time

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H = 1920, 1080
FONT_B = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FONT_R = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"


def sky_from_hdri(path, hfov_deg=80.0, az_frac=0.62, top_deg=52.0):
    hdr = cv2.imread(str(path), cv2.IMREAD_ANYDEPTH | cv2.IMREAD_COLOR)
    h, w = hdr.shape[:2]
    cw = int(w * hfov_deg / 360)
    x0 = int(w * az_frac) % w
    cols = np.arange(x0, x0 + cw) % w
    r0, r1 = int(h / 2 - h * top_deg / 180), int(h / 2 + h * 3 / 180)
    crop = hdr[r0:r1][:, cols]
    img = crop * 0.55
    img = img / (1.0 + img)
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    return cv2.resize((img * 255).astype(np.uint8), (W, H), interpolation=cv2.INTER_CUBIC)


def window_frame():
    """Carriage window surround drawn once: dark trim, rubber gasket, sill with a soft highlight."""
    a = np.zeros((H, W), np.float32)
    col = np.zeros((H, W, 3), np.float32)
    x0, x1, y0, y1, r = 70, W - 70, 46, H - 118, 54
    mask = np.zeros((H, W), np.uint8)
    cv2.rectangle(mask, (x0 + r, y0), (x1 - r, y1), 255, -1)
    cv2.rectangle(mask, (x0, y0 + r), (x1, y1 - r), 255, -1)
    for cx, cy in ((x0 + r, y0 + r), (x1 - r, y0 + r), (x0 + r, y1 - r), (x1 - r, y1 - r)):
        cv2.circle(mask, (cx, cy), r, 255, -1)
    opening = cv2.GaussianBlur(mask, (0, 0), 1.2).astype(np.float32) / 255
    a[:] = 1 - opening
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    base = np.array([34, 33, 31], np.float32) / 255            # BGR, warm dark grey panel
    col[:] = base * (0.75 + 0.5 * yy)[..., None]
    gasket = cv2.dilate(mask, np.ones((25, 25), np.uint8)) > 0
    col[gasket & (mask == 0)] = np.array([10, 10, 10], np.float32) / 255
    lip = cv2.dilate(mask, np.ones((37, 37), np.uint8)) > 0
    col[lip & ~gasket] = np.array([70, 68, 64], np.float32) / 255
    sill = slice(y1 + 22, y1 + 34)
    col[sill, x0 - 10:x1 + 10] = np.array([120, 116, 108], np.float32) / 255
    col[y1 + 34:y1 + 60, x0 - 10:x1 + 10] = np.array([52, 50, 47], np.float32) / 255
    # soft shadow the frame casts onto the glass edge
    shade = 1 - 0.35 * (cv2.GaussianBlur(255 - mask, (0, 0), 26).astype(np.float32) / 255)
    return (col * 255), a[..., None], shade[..., None]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--out")
    ap.add_argument("--frames", type=int, help="render only the first N frames (preview)")
    a = ap.parse_args()
    S = json.loads(pathlib.Path(a.scene).read_text())
    L, P = S["layers"], S.get("loop", {})
    ld = ROOT / L["out_dir"]
    meta = json.loads((ld / "layers.json").read_text())
    fps = S["render"]["fps"]
    T = a.seconds or P.get("seconds", 60.0)
    N = int(round(T * fps))
    span = meta["x1"] - meta["x0"]
    v_world = span / T
    yh, eye = P.get("horizon_y", 560), meta["eye_z"]
    haze_col = np.array(P.get("haze_bgr", [214, 190, 168]), np.float32)

    layers = []
    for sl, haze in zip(reversed(meta["slabs"]), P.get("haze", [0.42, 0.20, 0.04])):   # far -> near
        img = cv2.imread(str(ld / sl["file"]), cv2.IMREAD_UNCHANGED).astype(np.float32)
        rgb, al = img[..., :3], img[..., 3:4] / 255
        rgb = rgb * (1 - haze) + haze_col * haze
        rh = (sl["z_max"] - eye) * sl["px_per_m"]              # strip row of the horizon
        top = int(round(rh - yh))
        rows = slice(max(0, top), min(img.shape[0], top + H))
        y_on_screen = max(0, -top)
        pre = np.concatenate([rgb * al, al], axis=2)[rows]      # premultiplied
        pre = np.concatenate([pre, pre[:, :W + 2]], axis=1)     # wrap margin
        layers.append({"pre": pre, "w": img.shape[1], "y": y_on_screen, "ppm": sl["px_per_m"]})

    sky = sky_from_hdri(ROOT / S["render"]["hdri"]).astype(np.float32)
    fcol, falpha, fshade = window_frame()
    ground = np.array(P.get("ground_bgr", [150, 152, 150]), np.float32) * (1 - 0.15) + haze_col * 0.15
    near_ppm = layers[-1]["ppm"]
    yw = int(yh + (eye + 4.0) * near_ppm)                       # water line under the near bank
    water_h = H - yw
    tint = np.array(P.get("water_bgr", [52, 74, 38]), np.float32)
    rr = np.arange(water_h, dtype=np.float32)[:, None]
    depth_fade = (0.62 - 0.30 * rr / water_h)                   # reflection weakens toward the viewer
    xs = np.tile(np.arange(W, dtype=np.float32), (water_h, 1))
    src_rows = np.clip(yw - 1 - rr * P.get("reflect_stretch", 0.9), 0, H - 1).astype(np.float32) * np.ones((1, W), np.float32)
    rng = np.random.default_rng(5)
    streak = cv2.GaussianBlur(rng.random((water_h, 4096)).astype(np.float32), (0, 0), sigmaX=22, sigmaY=1.2)
    streak = (streak - streak.mean()) / (streak.std() + 1e-6)
    streak = np.concatenate([streak, streak[:, :W]], axis=1)
    post_gap_m, post_depth = P.get("post_gap_m", 60.0), P.get("post_depth_m", 7.0)
    post_ppm = L["focal_px"] / post_depth

    out = pathlib.Path(a.out) if a.out else ROOT / "output" / f"{S['id']}.mp4"
    out.parent.mkdir(exist_ok=True)
    o = S.get("overlay", {})
    vf = ("curves=r='0/0 0.5/0.52 1/1':b='0/0 0.5/0.49 1/0.98',eq=contrast=1.08:saturation=1.22,"
          f"drawbox=x=96:y=90:w=600:h=112:color=black@0.34:t=fill,"
          f"drawtext=fontfile={FONT_B}:text='{o.get('title', '').upper().replace(',', chr(92) + ',')}':fontsize=44:fontcolor=white@0.96:x=124:y=106,"
          f"drawtext=fontfile={FONT_R}:text='Next destination\\: {o.get('next', '').replace(',', chr(92) + ',')}':fontsize=28:fontcolor=white@0.9:x=124:y=160,"
          "format=yuv420p")
    n_out = a.frames or N
    enc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
         "-r", str(fps), "-i", "-", "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
         "-g", str(fps * 2), "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(n_out):
        t = f / fps
        ph = 2 * math.pi * t / T
        frame = sky.copy()
        frame[yh - 6:] = ground          # land behind the buildings: no sky below the horizon
        bob = 1.6 * math.sin(3 * ph) + 0.8 * math.sin(7 * ph + 1.0)   # integer cycles per loop
        for ly in layers:
            off = (v_world * ly["ppm"] * t) % ly["w"]
            xi, fx = int(off), off - int(off)
            seg = ly["pre"][:, xi:xi + W + 1]
            seg = seg[:, :-1] * (1 - fx) + seg[:, 1:] * fx          # sub-pixel scroll: no stair-step judder
            y0 = ly["y"]
            hh = min(seg.shape[0], H - y0)
            frame[y0:y0 + hh] = frame[y0:y0 + hh] * (1 - seg[:hh, :, 3:4]) + seg[:hh, :, :3]
        if abs(bob) > 0.01:
            frame = cv2.warpAffine(frame, np.float32([[1, 0, 0], [0, 1, bob]]), (W, H), flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_REPLICATE)
        # river: mirrored scene with travelling ripples, tinted Chicago-river green
        amp = 0.6 + 2.6 * rr / water_h
        mx = xs + amp * np.sin(rr * 0.55 + 9 * ph) + 0.6 * amp * np.sin(rr * 0.21 - 5 * ph + xs * 0.01)
        refl = cv2.remap(frame, mx, src_rows, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        so = (v_world * near_ppm * 1.6 * t) % 4096
        sp = streak[:, int(so):int(so) + W][..., None]
        water = refl * depth_fade[..., None] + tint * (1 - depth_fade[..., None]) + sp * 5.0
        frame[yw:] = water
        # track-side posts streaking past the glass
        gap_px = post_gap_m * post_ppm
        x_post = (W + 200) - ((v_world * post_ppm * t) % gap_px)
        if -260 < x_post < W + 260:
            blur = v_world * post_ppm / fps * 0.5
            xx = np.arange(W, dtype=np.float32)
            bar = np.clip(1 - np.abs(xx - x_post) / (blur / 2 + 26), 0, 1) * 0.5
            frame *= (1 - bar)[None, :, None]
            frame += (np.array([28, 30, 32], np.float32) * bar[None, :, None])
        frame = frame * fshade
        frame = frame * (1 - falpha) + fcol * falpha
        enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    print(json.dumps({"file": str(out), "frames": n_out, "loop_seconds": T, "train_speed_kmh": round(v_world * 3.6, 1),
                      "composite_s": round(time.time() - t0, 1), "bytes": out.stat().st_size}))


if __name__ == "__main__":
    main()
