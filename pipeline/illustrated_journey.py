#!/usr/bin/env python3
"""Illustrated side-window journey: depth bands of painted artwork scrolling behind a fixed train window.

  python3 pipeline/illustrated_journey.py out.mp4 [--frames a-b] [--jobs 3] [--still f ...]

Chicago route (300 s, five 60 s sections): riverfront, Loop, lakefront, neighbourhoods, city edge.
Artwork: work/illus (first plate and its cut-outs in work/kit) and work/chi/sprites (generated sheets).
Every landmark appears once. Strips that repeat (tree lines, grass, water) are joined with a
blended seam, never mirrored. Video only; music is added afterwards.
"""
import argparse, json, math, pathlib, subprocess, sys, time
import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
ILL, KIT, CHI = ROOT / "work/illus", ROOT / "work/kit", ROOT / "work/chi/sprites"
W, H, FPS, SEC = 1920, 1080, 30, 300
MID, BAND, BRIDGE, NEAR = 46.0, 58.0, 78.0, 175.0          # px/s of each depth band
SECT = 60.0


def rgba(path, scale=1.0, flip=False):
    im = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if scale != 1.0:
        im = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4 if scale > 1 else cv2.INTER_AREA)
    if flip:
        im = im[:, ::-1]
    im = im.astype(np.float32)
    a = im[..., 3:] / 255.0
    return np.ascontiguousarray(im[..., :3] * a), np.ascontiguousarray(a)       # premultiplied


def tint(layer, colour, k):
    rgb, a = layer
    return rgb * (1 - k) + np.array(colour, np.float32) * a * k, a


def loop(layer, ov=140):
    """make a strip repeat without a visible seam: its end is blended into its start (no mirroring)"""
    rgb, a = layer
    w = rgb.shape[1]
    r = np.linspace(0, 1, ov, dtype=np.float32)[None, :, None]
    out_rgb, out_a = rgb[:, :w - ov].copy(), a[:, :w - ov].copy()
    out_rgb[:, :ov] = rgb[:, w - ov:] * (1 - r) + rgb[:, :ov] * r
    out_a[:, :ov] = a[:, w - ov:] * (1 - r) + a[:, :ov] * r
    reps = math.ceil((W * 2) / out_rgb.shape[1]) + 1
    return np.tile(out_rgb, (1, reps, 1)), np.tile(out_a, (1, reps, 1)), out_rgb.shape[1]


def over(img, rgb, a, x, y, k=1.0):
    h, w = a.shape[:2]
    xa, xb, ya, yb = max(0, x), min(W, x + w), max(0, y), min(H, y + h)
    if xb <= xa or yb <= ya or k <= 0:
        return
    A = a[ya - y:yb - y, xa - x:xb - x] * k
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - A) + rgb[ya - y:yb - y, xa - x:xb - x] * k


def strip(img, lp, off, base_y, k=1.0):
    rgb, a, period = lp
    o = int(off) % period
    over(img, rgb[:, o:o + W], a[:, o:o + W], 0, base_y - rgb.shape[0], k)


def weight(t, k, fade=3.0):
    """how much section k's own layers show at time t (cross-fades centred on the section boundaries)"""
    a, b = k * SECT, (k + 1) * SECT
    up = 1.0 if k == 0 else np.clip((t - (a - fade)) / (2 * fade), 0, 1)
    dn = 1.0 if k == 4 else np.clip(((b + fade) - t) / (2 * fade), 0, 1)
    return float(min(up, dn))


class Journey:
    def __init__(self):
        S = cv2.imread(str(ILL / "scene.png"))
        # sky: one wide painted sky, drifting slowly
        sky = cv2.resize(cv2.imread(str(ROOT / "work/chi/sky.png")), None, fx=1.9, fy=1.9, interpolation=cv2.INTER_CUBIC)
        self.sky = sky[560:560 + 760].astype(np.float32)
        # far skyline (hazy)
        self.skyline_big = tint(rgba(CHI / "skyline.png", 1.65), (196, 208, 250), 0.38)
        self.skyline_mid = tint(rgba(CHI / "skyline.png", 1.4, flip=True), (200, 212, 250), 0.55)
        # water: a boat-free patch of the first plate, looped
        wt = cv2.resize(S[775:1010, 505:775], (1300, 420), interpolation=cv2.INTER_LANCZOS4)
        self.river = loop((wt.astype(np.float32), np.ones(wt.shape[:2] + (1,), np.float32)), 200)
        lk = cv2.resize(S[775:900, 505:775], (1300, 190), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        lk = lk * 0.72 + np.array([190, 150, 110], np.float32) * 0.28                       # the lake is bluer than the river
        self.lake = loop((lk, np.ones(lk.shape[:2] + (1,), np.float32)), 200)
        # scenery strips
        self.trees = loop(rgba(CHI / "strip_0.png", 1.0))
        self.fences = loop(rgba(CHI / "strip_1.png", 1.45))
        self.prairie = loop(rgba(CHI / "strip_2.png", 1.35))
        self.prairie_far = loop(tint(rgba(CHI / "strip_2.png", 0.7, flip=True), (196, 208, 250), 0.5))
        emb = rgba(CHI / "strip_3.png", 1.7)
        self.near = loop((cv2.blur(emb[0], (11, 1)), cv2.blur(emb[1], (11, 1))[..., None]))
        g = cv2.imread(str(CHI / "strip_3.png"), cv2.IMREAD_UNCHANGED)[70:135, :, :3]
        lawn = cv2.resize(g, (1536, 420), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        self.lawn = loop((lawn, np.ones(lawn.shape[:2] + (1,), np.float32)), 200)
        # a close stand of trees that sweeps past the window at each change of scenery
        tw = cv2.imread(str(CHI / "strip_0.png"), cv2.IMREAD_UNCHANGED)[:175, 20:470]
        tw = cv2.resize(tw, None, fx=5.2, fy=5.2, interpolation=cv2.INTER_CUBIC).astype(np.float32)
        ramp = np.clip(np.minimum(np.arange(tw.shape[1]), tw.shape[1] - 1 - np.arange(tw.shape[1])) / 520.0, 0, 1).astype(np.float32)
        ramp = (ramp * ramp * (3 - 2 * ramp))[None, :, None]                          # the stand of trees tapers away at both ends
        ta = cv2.blur(tw[..., 3:] / 255.0, (41, 9))[..., None] * ramp
        self.treewall = (cv2.blur(tw[..., :3] * (tw[..., 3:] / 255.0), (41, 9)) * 0.8 * ramp, ta)
        # landmarks and buildings: (layer, section, slot time within the journey, base y)
        self.mid = []
        def place(section, layers, base):
            n = len(layers)
            for i, L in enumerate(layers):
                self.mid.append((L, section, section * SECT + (i + 0.5) / n * SECT, base))
        place(0, [rgba(KIT / f"{n}.png", f) for n, f in (("glassL", 1.45), ("deco", 1.7), ("marina", 1.4), ("tower", 1.75), ("brick", 1.3))], 722)
        lo = [rgba(CHI / f"loop_{i}.png", 0.92) for i in (1, 4, 2, 0, 3, 5, 6)]              # Wrigley, 333 Wacker, Tribune, Willis, Board of Trade, brick block, L station
        place(1, lo, 722)
        wheel = cv2.imread(str(CHI / "lake_0.png"), cv2.IMREAD_UNCHANGED)
        col = (wheel[..., 3] > 128).sum(0)
        cut = int(wheel.shape[1] * 0.35 + np.argmin(col[int(wheel.shape[1] * 0.35):int(wheel.shape[1] * 0.65)]))
        cv2.imwrite(str(CHI / "lake_0a.png"), wheel[:, :cut]); cv2.imwrite(str(CHI / "lake_0b.png"), wheel[:, cut:])
        place(2, [rgba(CHI / f"lake_{n}.png", 1.55) for n in ("0a", "2", "0b", "1")], 775)   # Navy Pier wheel, Field Museum, Buckingham Fountain, Adler Planetarium
        self.lake_far = [(rgba(CHI / "lake_3.png", 0.85), 2 * SECT + 18, 668), (rgba(CHI / "lake_4.png", 0.8), 2 * SECT + 42, 690)]
        place(3, [rgba(CHI / f"hood_{i}.png", 1.12) for i in (0, 2, 4, 1, 3, 6, 5)], 775)
        place(4, [rgba(CHI / f"edge_{i}.png", 1.3) for i in (1, 0, 2, 3)], 775)
        self.bridge = [(rgba(KIT / "bridge.png", 1.5), 32.0, 805), (rgba(KIT / "house.png", 1.5), 30.3, 795), (rgba(KIT / "house.png", 1.5), 43.4, 795),
                       (rgba(KIT / "bridge.png", 1.5, flip=True), 94.0, 805), (rgba(KIT / "house.png", 1.5, flip=True), 82.6, 795), (rgba(KIT / "house.png", 1.5, flip=True), 95.7, 795)]
        # window frame
        fr = cv2.resize(cv2.imread(str(ILL / "frame.png")), (W, 1280), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        g = fr[..., 1] - np.maximum(fr[..., 0], fr[..., 2])
        fa = 1 - np.clip((g - 40) / 70, 0, 1)
        fa = cv2.GaussianBlur(cv2.erode(fa, np.ones((3, 3), np.uint8)), (0, 0), 1.0)
        fr[..., 1] = np.where(fa < 0.999, np.minimum(fr[..., 1], np.maximum(fr[..., 0], fr[..., 2]) * 1.05), fr[..., 1])
        self.frame, self.fa = fr[120:120 + H] * fa[120:120 + H, :, None], fa[120:120 + H, :, None]
        self.gy, self.gx = np.mgrid[0:420, 0:W].astype(np.float32)

    def water(self, lp, t, speed, h):
        rgb, _, period = lp
        o = int(300 + speed * t) % period
        r = rgb[:h, o:o + W]
        gx, gy = self.gx[:h], self.gy[:h]
        mx = (gx + 1.8 * np.sin(gy * 0.19 + t * 2.9) + 1.0 * np.sin(gx * 0.04 - t * 2.1)).astype(np.float32)
        my = (gy + 1.4 * np.sin(gx * 0.03 + t * 2.4)).astype(np.float32)
        return cv2.remap(r, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def render(self, f):
        t = f / FPS
        bob = int(round(1.6 * math.sin(2 * math.pi * 0.9 * t) + 0.9 * math.sin(2 * math.pi * 2.3 * t + 1)))
        w = [weight(t, k) for k in range(5)]
        img = np.empty((H, W, 3), np.float32)
        o = int(40 + 3 * t)
        img[:760] = self.sky[:, o:o + W]
        img[760:] = self.sky[-1:, o:o + W]
        # far band
        k01 = max(w[0], w[1])
        if k01 > 0:
            over(img, *self.skyline_big, int(-60 - 5 * t), 712 - self.skyline_big[0].shape[0] + bob, 0.92 * k01)
        if w[3] > 0:
            over(img, *self.skyline_mid, int(-80 - 3 * (t - 3 * SECT)), 730 - self.skyline_mid[0].shape[0] + bob, 0.85 * w[3])
        if w[4] > 0:
            strip(img, self.prairie_far, 200 + 12 * t, 712 + bob, w[4])
        # lake to the horizon, with the lighthouse and sailboats out on it
        if w[2] > 0:
            lk = self.water(self.lake, t, 14, 190)
            y0 = 600 + bob
            img[y0:y0 + 190] = img[y0:y0 + 190] * (1 - w[2]) + lk * w[2]
            for (rgb, a), tau, base in self.lake_far:
                over(img, rgb, a, int(round(960 + 24 * (tau - t) - a.shape[1] / 2)), base - a.shape[0] + bob, w[2])
        # ground for the land sections
        land = max(w[2], w[3], w[4])
        if land > 0:
            rgb, _, period = self.lawn
            o = int(110 * t) % period
            y0 = 745 + bob
            img[y0:] = img[y0:] * (1 - land) + rgb[:H - y0, o:o + W] * land
        # landmarks and buildings
        for (rgb, a), sec, tau, base in self.mid:
            x = int(round(960 + MID * (tau - t) - a.shape[1] / 2))
            if -a.shape[1] < x < W:
                over(img, rgb, a, x, base - a.shape[0] + bob)
        riv = max(w[0], w[1])
        if riv > 0:
            strip(img, self.trees, 150 + BAND * t, 742 + bob, riv)                   # riverwalk trees on the far bank
            y0 = 730 + bob
            rv = self.water(self.river, t, 62, H - y0)
            img[y0:] = img[y0:] * (1 - riv) + rv * riv
            for (rgb, a), tau, base in self.bridge:
                over(img, rgb, a, int(round(960 + BRIDGE * (tau - t) - a.shape[1] / 2)), base - a.shape[0] + bob, riv)
        if w[2] > 0:
            strip(img, self.trees, 900 + BAND * t, 850 + bob, w[2])                  # park trees
        if w[3] > 0:
            strip(img, self.fences, 300 + BAND * t, 850 + bob, w[3])
        if w[4] > 0:
            strip(img, self.prairie, 300 + BAND * t, 860 + bob, w[4])
        strip(img, self.near, 400 + NEAR * t, H + 40, 1.0)                           # the line's own embankment and railing
        for k in range(1, 5):                                                        # trees close to the track at each change
            x = int(W + 150 - 620 * (t - (k * SECT - 3.4)))
            if -self.treewall[1].shape[1] < x < W:
                over(img, *self.treewall, x, H + 60 - self.treewall[1].shape[0])
        return np.clip(img * (1 - self.fa) + self.frame, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--frames")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    f0, f1 = (int(x) for x in a.frames.split("-")) if a.frames else (0, SEC * FPS - 1)
    t0 = time.time()
    if a.still:
        J = Journey()
        for f in a.still:
            cv2.imwrite(f"{a.out}_{f:05d}.jpg", J.render(f), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print("stills", round(time.time() - t0, 1), "s")
        return
    if a.jobs > 1:
        per = -(-(f1 - f0 + 1) // a.jobs // 60) * 60
        parts = []
        procs = []
        for i, s in enumerate(range(f0, f1 + 1, per)):
            p = pathlib.Path(a.out).with_suffix(f".part{i}.mp4")
            parts.append(p)
            procs.append(subprocess.Popen([sys.executable, __file__, str(p), "--frames", f"{s}-{min(s + per - 1, f1)}", "--jobs", "1"]))
        if any(p.wait() for p in procs):
            sys.exit("a segment failed")
        lst = pathlib.Path(a.out).with_suffix(".txt")
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                        "-movflags", "+faststart", a.out], check=True)
        for p in parts:
            p.unlink()
        lst.unlink()
        print(json.dumps({"frames": f1 - f0 + 1, "wall_s": round(time.time() - t0, 1)}))
        return
    J = Journey()
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-g", "60", a.out], stdin=subprocess.PIPE)
    for f in range(f0, f1 + 1):
        ff.stdin.write(J.render(f).tobytes())
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main()
