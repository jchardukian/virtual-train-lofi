#!/usr/bin/env python3
"""Fast path: build a full shot from sparse keyframes by depth reprojection.

blender_scene.py --keys renders a sharp, world-only frame with its depth every N frames
(N = 30 means one per second) and writes the camera pose of every frame. Each in-between
frame is then synthesised from its two neighbouring keyframes: their depth is splatted
into the new view, colour is pulled back through that depth, the two are blended by
time and visibility, and the static carriage interior is laid on top. The geometry of
the motion is exact (it is the real 3D scene depth); what is approximated is anything
that changes between keyframes other than the camera: moving cars and boats, water
ripples and view-dependent reflections.

Usage:
  python3 pipeline/fast_shot.py work/fast/<shot> --step 30 --out out.mp4 [--frames a-b] [--png-dir d]
"""
import argparse
import json
import math
import pathlib
import subprocess
import sys
import time

import cv2
import numpy as np
import OpenEXR
from numba import njit, prange

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))


def read_depth(p):
    z = next(iter(OpenEXR.File(str(p)).channels().values())).pixels
    return np.ascontiguousarray(z[..., 0] if z.ndim == 3 else z, dtype=np.float32)


@njit(cache=True)
def splat(depth, T, fx, cx, cy, zbuf):
    """Forward-project one keyframe's depth into the target view (z-buffer, 2x2 footprint)."""
    H, W = depth.shape
    for v in range(H):
        for u in range(W):
            d = depth[v, u]
            x = (u - cx) / fx * d
            y = -(v - cy) / fx * d
            z = -d
            X = T[0, 0] * x + T[0, 1] * y + T[0, 2] * z + T[0, 3]
            Y = T[1, 0] * x + T[1, 1] * y + T[1, 2] * z + T[1, 3]
            Z = T[2, 0] * x + T[2, 1] * y + T[2, 2] * z + T[2, 3]
            if Z > -0.5:
                continue
            dt = -Z
            ut = X / dt * fx + cx
            vt = -Y / dt * fx + cy
            u0 = int(math.floor(ut))
            v0 = int(math.floor(vt))
            for dv in range(2):
                vv = v0 + dv
                if vv < 0 or vv >= H:
                    continue
                for du in range(2):
                    uu = u0 + du
                    if 0 <= uu < W and dt < zbuf[vv, uu]:
                        zbuf[vv, uu] = dt


@njit(parallel=True, cache=True)
def pull(zbuf, T, fx, cx, cy, src_depth, mapx, mapy, vis):
    """For every target pixel: where it sits in a keyframe, and whether that keyframe really sees it."""
    H, W = zbuf.shape
    for v in prange(H):
        for u in range(W):
            d = zbuf[v, u]
            vis[v, u] = 0.0
            mapx[v, u] = -1.0
            mapy[v, u] = -1.0
            if d > 1e8:
                continue
            x = (u - cx) / fx * d
            y = -(v - cy) / fx * d
            z = -d
            X = T[0, 0] * x + T[0, 1] * y + T[0, 2] * z + T[0, 3]
            Y = T[1, 0] * x + T[1, 1] * y + T[1, 2] * z + T[1, 3]
            Z = T[2, 0] * x + T[2, 1] * y + T[2, 2] * z + T[2, 3]
            if Z > -0.5:
                continue
            ds = -Z
            us = X / ds * fx + cx
            vs = -Y / ds * fx + cy
            if us < 0 or vs < 0 or us > W - 1 or vs > H - 1:
                continue
            mapx[v, u] = us
            mapy[v, u] = vs
            # the keyframe sees this point if any of the four surrounding depth samples agrees with it
            ui = int(us)
            vi = int(vs)
            if src_depth[int(vs + 0.5), int(us + 0.5)] < 0:      # anti-aliased silhouette pixel: colour is a mix
                continue
            tol = 0.04 * ds + 0.25
            ok = False
            for dv in range(2):
                for du in range(2):
                    a = min(vi + dv, H - 1)
                    b = min(ui + du, W - 1)
                    if abs(src_depth[a, b] - ds) < tol:
                        ok = True
            if ok:
                # fade a keyframe out towards its own image border, so the place where it stops
                # contributing is a gradient rather than a visible seam
                e = min(min(us, W - 1 - us), min(vs, H - 1 - vs)) / 96.0
                vis[v, u] = min(1.0, max(0.02, e))


@njit(parallel=True, cache=True)
def blend(c0, c1, v0, v1, a, out, hole):
    H, W = v0.shape
    for v in prange(H):
        for u in range(W):
            w0 = (1.0 - a) * v0[v, u]
            w1 = a * v1[v, u]
            s = w0 + w1
            if s <= 0:
                hole[v, u] = 255
                out[v, u, 0] = 0
                out[v, u, 1] = 0
                out[v, u, 2] = 0
            else:
                hole[v, u] = 0
                for k in range(3):
                    out[v, u, k] = np.uint8((w0 * c0[v, u, k] + w1 * c1[v, u, k]) / s + 0.5)


def fill_holes(img, hole):
    """Push-pull fill for the few pixels neither keyframe sees."""
    if not hole.any():
        return img
    w = (hole == 0).astype(np.float32)
    c = img.astype(np.float32) * w[..., None]
    cs, ws = [c], [w]
    for _ in range(7):
        c, w = cv2.pyrDown(c), cv2.pyrDown(w)
        cs.append(c)
        ws.append(w)
    fill = cs[-1] / np.maximum(ws[-1], 1e-4)[..., None]
    for c, w in zip(cs[-2::-1], ws[-2::-1]):
        up = cv2.resize(fill, (c.shape[1], c.shape[0]), interpolation=cv2.INTER_LINEAR)
        k = np.clip(w * 4, 0, 1)[..., None]
        fill = (c / np.maximum(w, 1e-4)[..., None]) * k + up * (1 - k)
    out = img.copy()
    m = hole > 0
    out[m] = np.clip(fill[m], 0, 255).astype(np.uint8)
    return out


class Shot:
    def __init__(self, d, step):
        self.d = pathlib.Path(d)
        P = json.loads((self.d / "poses.json").read_text())
        self.P = P
        self.W, self.H, self.n, self.fps = P["width"], P["height"], P["frames"], P["fps"]
        self.fx = self.W / 2 / math.tan(math.radians(P["hfov_deg"]) / 2)
        self.cx = (self.W - 1) / 2
        self.cy = (self.H - 1) / 2 + P["shift_y"] * self.W
        self.M = np.array(P["cam_to_world"], dtype=np.float64)
        self.step = step
        self.cache = {}

    def key(self, k):
        if k not in self.cache:
            if len(self.cache) >= 3:
                self.cache.pop(min(self.cache))
            z = read_depth(self.d / f"z_{k:04d}.exr")
            # A background pixel touching a nearer object carries some of that object's colour (anti-aliasing)
            # but the background's depth; reprojected, it leaves a ghost outline where the object used to be.
            # Mark those (depth -1) so colour is never pulled from them. Foreground pixels are kept, so thin
            # things such as railings survive.
            lo = cv2.erode(z, np.ones((3, 3), np.uint8))
            zc = z.copy()
            zc[(z - lo) > 0.08 * lo + 0.3] = -1.0
            self.cache[k] = (cv2.imread(str(self.d / f"k_{k:04d}.png")), z, zc)
        return self.cache[k]

    def frame(self, f):
        k0 = (f // self.step) * self.step
        k1 = k0 + self.step                     # keys run to frame n inclusive, one past the last output frame
        c0, z0, e0 = self.key(k0)
        if f == k0:
            return c0, 0
        c1, z1, e1 = self.key(k1)
        Mt_inv = np.linalg.inv(self.M[f])
        zbuf = np.full((self.H, self.W), np.inf, dtype=np.float32)
        splat(z0, Mt_inv @ self.M[k0], self.fx, self.cx, self.cy, zbuf)
        splat(z1, Mt_inv @ self.M[k1], self.fx, self.cx, self.cy, zbuf)
        outs = []
        for k, c, z in ((k0, c0, e0), (k1, c1, e1)):
            mx = np.empty((self.H, self.W), np.float32)
            my = np.empty_like(mx)
            vis = np.empty_like(mx)
            pull(zbuf, np.linalg.inv(self.M[k]) @ self.M[f], self.fx, self.cx, self.cy, z, mx, my, vis)
            outs.append((cv2.remap(c, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE), vis))
        out = np.empty((self.H, self.W, 3), np.uint8)
        hole = np.empty((self.H, self.W), np.uint8)
        blend(outs[0][0], outs[1][0], outs[0][1], outs[1][1], (f - k0) / (k1 - k0), out, hole)
        return fill_holes(out, hole), int((hole > 0).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--step", type=int, default=30)
    ap.add_argument("--frames")
    ap.add_argument("--out")
    ap.add_argument("--png-dir")
    ap.add_argument("--carriage", help="RGBA still of the carriage interior to lay over every frame")
    ap.add_argument("--style", default="illustrated")
    ap.add_argument("--preset", default="slow")
    a = ap.parse_args()
    sh = Shot(a.dir, a.step)
    f0, f1 = (int(x) for x in a.frames.split("-")) if a.frames else (0, sh.n - 1)
    car = None
    if a.carriage:
        rgba = cv2.imread(a.carriage, cv2.IMREAD_UNCHANGED).astype(np.float32)
        al = rgba[..., 3:] / 255.0
        car = (rgba[..., :3] * al, 1.0 - al)          # Blender PNGs are straight alpha
    ff = None
    if a.out:
        from stylize import STYLES
        ff = subprocess.Popen(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{sh.W}x{sh.H}",
             "-r", str(sh.fps), "-i", "-", "-filter_complex", f"[0:v]{STYLES[a.style]},format=yuv420p[v]", "-map", "[v]",
             "-c:v", "libx264", "-preset", a.preset, "-crf", "17", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(sh.fps),
             "-g", str(sh.fps * 2), "-movflags", "+faststart", "-color_primaries", "bt709", "-color_trc", "bt709",
             "-colorspace", "bt709", a.out], stdin=subprocess.PIPE)
    t0, holes = time.time(), []
    for f in range(f0, f1 + 1):
        img, h = sh.frame(f)
        holes.append(h)
        if car is not None:
            img = np.clip(img.astype(np.float32) * car[1] + car[0], 0, 255).astype(np.uint8)
        if a.png_dir:
            cv2.imwrite(f"{a.png_dir}/s_{f:04d}.png", img)
        if ff:
            ff.stdin.write(img.tobytes())
    if ff:
        ff.stdin.close()
        ff.wait()
    n = f1 - f0 + 1
    rep = {"frames": n, "seconds": round(time.time() - t0, 1), "s_per_frame": round((time.time() - t0) / n, 3),
           "hole_px_mean": float(np.mean(holes)), "hole_px_max": int(max(holes)), "step": a.step}
    print(json.dumps(rep))
    if a.out:
        pathlib.Path(a.out).with_suffix(".fast.json").write_text(json.dumps(rep, indent=1) + "\n")


if __name__ == "__main__":
    main()
