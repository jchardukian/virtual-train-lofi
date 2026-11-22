#!/usr/bin/env python3
"""Reusable city-to-city handoff: a trackside "NEXT STOP: <CITY>" sign, a tunnel, and the exit into the next city.

  python3 pipeline/tunnel.py --a cityA_clean.mp4 --a-carriage carA.png --b cityB_clean.mp4 --b-carriage carB.png \\
      --city "Tokyo" --out handoff.mp4 [--seconds 8]

Works on finished (styled, text-free) city videos, so it costs seconds, not a render. The tunnel is drawn only
inside the window opening (taken from each city's carriage image), so the carriage interior, camera height and
framing never change. Timeline for the default 8 s:
  0.0-3.0  the last seconds of city A; the sign crosses the window, forward edge first
  3.0-3.6  the portal sweeps across the window in the direction scenery travels
  3.6-5.4  tunnel wall, cable trays and lamps streaming past; the cut from A to B happens here, in the dark
  5.4-6.0  the exit sweeps across, with a short over-bright moment as the eye adapts
  6.0-8.0  the first seconds of city B
The clip is video only: the compilation that uses it lays one continuous soundtrack over everything.
"""
import argparse
import pathlib
import subprocess

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def read_frames(path, start, n):
    raw = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-i", str(path), "-frames:v", str(n),
                          "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout)


def window_mask(carriage_png):
    """1 where the world shows through the window, 0 on the carriage interior (soft at the edge)."""
    a = cv2.imread(str(carriage_png), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255.0
    return 1.0 - a


def sign_sprite(city):
    """A station-style board on two posts, drawn once; returns BGR and alpha."""
    text1, text2 = "NEXT STOP", city.upper()
    f1, f2 = ImageFont.truetype(FONT, 54), ImageFont.truetype(FONT, 104)
    w2 = int(f2.getlength(text2))
    bw, bh = max(760, w2 + 140), 260
    img = Image.new("RGBA", (bw + 40, bh + 330), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for x in (70, bw - 50):                                    # posts
        d.rectangle([x, bh, x + 20, bh + 330], fill=(52, 56, 64, 255))
    d.rounded_rectangle([20, 10, bw + 20, bh + 10], radius=22, fill=(240, 238, 230, 255))
    d.rounded_rectangle([32, 22, bw + 8, bh - 2], radius=14, fill=(24, 58, 92, 255))
    d.text(((bw + 40 - f1.getlength(text1)) / 2, 44), text1, font=f1, fill=(236, 200, 110, 255))
    d.text(((bw + 40 - w2) / 2, 110), text2, font=f2, fill=(248, 246, 240, 255))
    a = np.array(img)
    return a[..., 2::-1].astype(np.float32), a[..., 3].astype(np.float32) / 255.0


def tunnel_strip(seed=7):
    """One long, horizontally tiling strip of tunnel wall as it looks at speed (already motion-blurred)."""
    rng = np.random.default_rng(seed)
    L = 7200                                                    # one lamp spacing; tiles seamlessly
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    base = 20 + 16 * (1 - np.abs(y - 0.42) * 1.6).clip(0, 1)    # a little lighter at lamp height
    wall = np.repeat(base, L, axis=1)
    wall += cv2.GaussianBlur(rng.normal(0, 5, (H // 8, L // 8)).astype(np.float32), (0, 0), 3, 0.6).repeat(8, 0).repeat(8, 1)[:H, :L]
    for x in range(0, L, 900):                                  # panel joints
        wall[:, x:x + 10] *= 0.55
    for yy, th, k in ((0.20, 16, 0.5), (0.235, 8, 0.6), (0.71, 22, 0.45), (0.76, 6, 1.5)):   # cable trays, kerb line
        wall[int(yy * H):int(yy * H) + th] *= k
    lamp = np.zeros((H, L), np.float32)                         # one lamp per tile, with its pool of light on the wall
    cv2.ellipse(lamp, (L // 2, int(0.16 * H)), (130, 16), 0, 0, 360, 255, -1)
    glow = cv2.GaussianBlur(lamp, (0, 0), 260, sigmaY=190) * 7.0 + cv2.GaussianBlur(lamp, (0, 0), 30) * 1.2
    wall = wall + glow.clip(0, 235)
    rgb = np.stack([wall * 0.80, wall * 0.93, wall * 1.06], -1)  # BGR: warm sodium tint
    rgb = cv2.blur(np.concatenate([rgb[:, -80:], rgb, rgb[:, :80]], 1), (71, 1))[:, 80:-80]   # motion blur along travel; tiles
    return rgb.clip(0, 255)


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--a-carriage", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--b-carriage", required=True)
    ap.add_argument("--city", required=True, help="name of the city being entered")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seconds", type=float, default=8.0)
    ap.add_argument("--b-start", type=float, default=0.0)
    ap.add_argument("--direction", choices=["rtl", "ltr"], default="rtl", help="which way scenery travels across the window")
    a = ap.parse_args()
    n = int(round(a.seconds * FPS))
    k = a.seconds / 8.0
    t_sign, t_in0, t_in1, t_out0, t_out1 = 0.2 * k, 3.0 * k, 3.6 * k, 5.4 * k, 6.0 * k
    t_cut = (t_in1 + t_out0) / 2
    n_a = int(round(t_cut * FPS))
    A = read_frames(a.a, duration(a.a) - n_a / FPS, n_a)
    B = read_frames(a.b, a.b_start + 0.0, n - n_a + 0)
    # B is shown from the cut onward, so the frame at the cut is B's frame 0 and it reaches full view already moving
    mA, mB = window_mask(a.a_carriage), window_mask(a.b_carriage)
    spr, spa = sign_sprite(a.city)
    strip = tunnel_strip()
    L = strip.shape[1]
    xs = np.arange(W, dtype=np.float32)[None, :]
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                           "-g", str(FPS * 2), "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    rtl = a.direction == "rtl"
    for i in range(n):
        t = i / FPS
        src = A[min(i, len(A) - 1)] if t < t_cut else B[min(i - n_a, len(B) - 1)]
        mask = mA if t < t_cut else mB
        img = src.astype(np.float32)
        # --- the sign: a board about 12 m from the track, crossing in ~2.6 s and growing slightly as it nears
        u = (t - t_sign) / (2.6 * k)
        if 0 <= u <= 1 and t < t_cut:
            sc = 0.85 + 0.25 * u
            s_rgb = cv2.resize(spr, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
            s_a = cv2.resize(spa, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
            sh, sw = s_a.shape
            x = (W + 40) - u * (W + sw + 80) if rtl else -sw - 40 + u * (W + sw + 80)
            x0, y0 = int(x), int(H * 0.80) - sh
            xa, xb, ya, yb = max(0, x0), min(W, x0 + sw), max(0, y0), min(H, y0 + sh)
            if xb > xa and yb > ya:
                al = (s_a[ya - y0:yb - y0, xa - x0:xb - x0] * mask[ya:yb, xa:xb])[..., None]
                img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - al) + s_rgb[ya - y0:yb - y0, xa - x0:xb - x0] * al
        # --- how much of the window the tunnel covers: the portal edge sweeps across, then sweeps off again
        if t < t_in0 or t >= t_out1:
            cover = None
        else:
            soft = 70.0
            if t < t_in1:
                p = (t - t_in0) / (t_in1 - t_in0)                        # 0..1, the portal's leading edge crossing
                edge = (W + soft) - p * (W + 2 * soft) if rtl else -soft + p * (W + 2 * soft)
                cover = smooth((xs - edge) / soft + 0.5) if rtl else smooth((edge - xs) / soft + 0.5)
            elif t < t_out0:
                cover = np.ones((1, W), np.float32)
            else:
                p = (t - t_out0) / (t_out1 - t_out0)
                edge = (W + soft) - p * (W + 2 * soft) if rtl else -soft + p * (W + 2 * soft)
                cover = 1 - smooth((xs - edge) / soft + 0.5) if rtl else 1 - smooth((edge - xs) / soft + 0.5)
        if cover is not None:
            off = int((t * 2300.0) % L)                                  # a wall 2.5 m away at train speed
            off = off if rtl else L - 1 - off
            idx = (np.arange(W) + off) % L
            tun = strip[:, idx]
            m = (cover * mask)[..., None]
            img = img * (1 - m) + tun * m
            # the cabin dims a little while the window is dark
            img *= 1 - 0.22 * float(cover.mean()) * (1 - mask[..., None])
        # --- stepping out into daylight: a brief over-bright moment in the window
        if t_out0 <= t < t_out1 + 0.9 * k:
            fl = 0.55 * (1 - smooth((t - t_out0) / (t_out1 + 0.9 * k - t_out0)))
            m = (mask if cover is None else mask * (1 - cover))[..., None]
            img = img + (255 - img) * fl * m
        ff.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close()
    ff.wait()
    print(f"{a.out}: {n / FPS:.2f} s, cut at {t_cut:.2f} s")


if __name__ == "__main__":
    main()
