#!/usr/bin/env python3
"""Illustrated side-window journey for any city, driven by a settings file.

  python3 pipeline/illustrated_city.py cities/illustrated/<city>.json out.mp4 [--jobs 3] [--still f ...]

The settings file lists the sections of the ride. Each section names its distant layers, the
ground (river, lake or lawn), the landmarks and buildings that pass once each, and the
scenery strip in front of them. Shared pieces (sky, embankment, window frame, water) come
from the Chicago library. Video only; music is added by pipeline/illustrated_finish.sh.

Fails closed: a segment that errors stops the build and no output file is written.
"""
import argparse, json, math, pathlib, subprocess, sys, time
import cv2
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from illustrated_journey import rgba, tint, loop, over, strip, W, H, FPS, MID, BAND, NEAR, ROOT, ILL, CHI  # noqa: E402

SEC = 300
HAZE = (196, 208, 250)


class City:
    def __init__(self, cfg):
        self.cfg = cfg
        self.n = len(cfg["sections"])
        self.sect = SEC / self.n
        S = cv2.imread(str(ILL / "scene.png"))
        sky = cv2.resize(cv2.imread(str(ROOT / "work/chi/sky.png")), None, fx=1.9, fy=1.9, interpolation=cv2.INTER_CUBIC)
        if cfg.get("sky_flip"):
            sky = sky[:, ::-1]
        self.sky = np.ascontiguousarray(sky[560:560 + 760]).astype(np.float32)
        wt = cv2.resize(S[775:1010, 505:775], (1300, 420), interpolation=cv2.INTER_LANCZOS4)
        self.river = loop((wt.astype(np.float32), np.ones(wt.shape[:2] + (1,), np.float32)), 200)
        g = cv2.imread(str(CHI / "strip_3.png"), cv2.IMREAD_UNCHANGED)[70:135, :, :3]
        lawn = cv2.resize(g, (1536, 420), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        self.lawn = loop((lawn, np.ones(lawn.shape[:2] + (1,), np.float32)), 200)
        emb = rgba(CHI / "strip_3.png", 1.7)
        self.near = loop((cv2.blur(emb[0], (11, 1)), cv2.blur(emb[1], (11, 1))[..., None]))
        tw = cv2.imread(str(ROOT / cfg.get("treewall", "work/chi/sprites/strip_0.png")), cv2.IMREAD_UNCHANGED)
        tw = tw[:int(tw.shape[0] * 0.76), 20:470]
        tw = cv2.resize(tw, None, fx=5.2 * 175 / tw.shape[0], fy=5.2 * 175 / tw.shape[0], interpolation=cv2.INTER_CUBIC).astype(np.float32)
        ramp = np.clip(np.minimum(np.arange(tw.shape[1]), tw.shape[1] - 1 - np.arange(tw.shape[1])) / 520.0, 0, 1).astype(np.float32)
        ramp = (ramp * ramp * (3 - 2 * ramp))[None, :, None]
        self.treewall = (cv2.blur(tw[..., :3] * (tw[..., 3:] / 255.0), (41, 9)) * 0.8 * ramp, cv2.blur(tw[..., 3:] / 255.0, (41, 9))[..., None] * ramp)
        fr = cv2.resize(cv2.imread(str(ILL / "frame.png")), (W, 1280), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        gg = fr[..., 1] - np.maximum(fr[..., 0], fr[..., 2])
        fa = 1 - np.clip((gg - 40) / 70, 0, 1)
        fa = cv2.GaussianBlur(cv2.erode(fa, np.ones((3, 3), np.uint8)), (0, 0), 1.0)
        fr[..., 1] = np.where(fa < 0.999, np.minimum(fr[..., 1], np.maximum(fr[..., 0], fr[..., 2]) * 1.05), fr[..., 1])
        self.frame, self.fa = fr[120:120 + H] * fa[120:120 + H, :, None], fa[120:120 + H, :, None]
        self.gy, self.gx = np.mgrid[0:420, 0:W].astype(np.float32)
        self.cache = {}
        # layers
        self.backdrop = [self.far_layer(L) for L in cfg.get("backdrop", [])]        # shown for the whole ride (e.g. mountains)
        self.sections = []
        self.mid = []
        for k, sc in enumerate(cfg["sections"]):
            far = [self.far_layer(L) for L in sc.get("far", [])]
            band = None
            if sc.get("band"):
                b = sc["band"]
                band = (loop(self.load(b["src"], b.get("scale", 1.0), b.get("flip", False))), b.get("base", 850), b.get("speed", BAND), b.get("offset", 300))
            self.sections.append({"ground": sc.get("ground", "lawn"), "far": far, "band": band})
            items = sc.get("mid", [])
            for i, m in enumerate(items):
                tau = k * self.sect + (i + 0.5) / len(items) * self.sect
                self.mid.append((self.load(m["src"], m.get("scale", 1.0), m.get("flip", False)), tau, m.get("base", 775 if sc.get("ground", "lawn") != "river" else 722)))

    def load(self, src, scale=1.0, flip=False, haze=0.0):
        key = (src, scale, flip, haze)
        if key not in self.cache:
            L = rgba(ROOT / src, scale, flip)
            self.cache[key] = tint(L, HAZE, haze) if haze else L
        return self.cache[key]

    def far_layer(self, L):
        lay = self.load(L["src"], L.get("scale", 1.6), L.get("flip", False), L.get("haze", 0.4))
        if L.get("tile"):
            return ("tile", loop(lay), L.get("base", 712), L.get("speed", 8), L.get("alpha", 0.9), L.get("offset", 200))
        return ("one", lay, L.get("base", 712), L.get("speed", 5), L.get("alpha", 0.9), L.get("x0", -60))

    def weight(self, t, k, fade=3.0):
        a, b = k * self.sect, (k + 1) * self.sect
        up = 1.0 if k == 0 else np.clip((t - (a - fade)) / (2 * fade), 0, 1)
        dn = 1.0 if k == self.n - 1 else np.clip(((b + fade) - t) / (2 * fade), 0, 1)
        return float(min(up, dn))

    def water(self, lp, t, speed, h):
        rgb, _, period = lp
        o = int(300 + speed * t) % period
        r = rgb[:h, o:o + W]
        gx, gy = self.gx[:h], self.gy[:h]
        mx = (gx + 1.8 * np.sin(gy * 0.19 + t * 2.9) + 1.0 * np.sin(gx * 0.04 - t * 2.1)).astype(np.float32)
        my = (gy + 1.4 * np.sin(gx * 0.03 + t * 2.4)).astype(np.float32)
        return cv2.remap(r, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def draw_far(self, img, lay, t, t0, bob, k):
        kind, L, base, speed, alpha, x = lay
        if kind == "tile":
            strip(img, L, x + speed * t, base + bob, alpha * k)
        else:
            over(img, L[0], L[1], int(x - speed * (t - t0)), base - L[0].shape[0] + bob, alpha * k)

    def render(self, f):
        t = f / FPS
        bob = int(round(1.6 * math.sin(2 * math.pi * 0.9 * t) + 0.9 * math.sin(2 * math.pi * 2.3 * t + 1)))
        w = [self.weight(t, k) for k in range(self.n)]
        img = np.empty((H, W, 3), np.float32)
        o = int(40 + 3 * t)
        img[:760] = self.sky[:, o:o + W]
        img[760:] = self.sky[-1:, o:o + W]
        for lay in self.backdrop:
            self.draw_far(img, lay, t, 0.0, bob, 1.0)
        for k, sc in enumerate(self.sections):
            if w[k] > 0:
                for lay in sc["far"]:
                    self.draw_far(img, lay, t, k * self.sect, bob, w[k])
        land = sum(w[k] for k, sc in enumerate(self.sections) if sc["ground"] == "lawn")
        riv = sum(w[k] for k, sc in enumerate(self.sections) if sc["ground"] == "river")
        land, riv = min(land, 1.0), min(riv, 1.0)
        if land > 0:
            rgb, _, period = self.lawn
            o = int(110 * t) % period
            y0 = 745 + bob
            img[y0:] = img[y0:] * (1 - land) + rgb[:H - y0, o:o + W] * land
        for (rgb, a), tau, base in self.mid:
            x = int(round(960 + MID * (tau - t) - a.shape[1] / 2))
            if -a.shape[1] < x < W:
                over(img, rgb, a, x, base - a.shape[0] + bob)
        # river sections: the strip stands on the far bank, then the water in front of it
        for k, sc in enumerate(self.sections):
            if w[k] > 0 and sc["ground"] == "river" and sc["band"]:
                lp, base, speed, off = sc["band"]
                strip(img, lp, off + speed * t, base + bob, w[k])
        if riv > 0:
            y0 = 730 + bob
            rv = self.water(self.river, t, 62, H - y0)
            img[y0:] = img[y0:] * (1 - riv) + rv * riv
        for k, sc in enumerate(self.sections):
            if w[k] > 0 and sc["ground"] != "river" and sc["band"]:
                lp, base, speed, off = sc["band"]
                strip(img, lp, off + speed * t, base + bob, w[k])
        strip(img, self.near, 400 + NEAR * t, H + 40, 1.0)
        for k in range(1, self.n):
            x = int(W + 150 - 620 * (t - (k * self.sect - 3.4)))
            if -self.treewall[1].shape[1] < x < W:
                over(img, *self.treewall, x, H + 60 - self.treewall[1].shape[0])
        return np.clip(img * (1 - self.fa) + self.frame, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("out")
    ap.add_argument("--frames")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--still", type=int, nargs="*")
    a = ap.parse_args()
    cfg = json.loads(pathlib.Path(a.config).read_text())
    f0, f1 = (int(x) for x in a.frames.split("-")) if a.frames else (0, SEC * FPS - 1)
    t0 = time.time()
    if a.still:
        C = City(cfg)
        for f in a.still:
            cv2.imwrite(f"{a.out}_{f:05d}.jpg", C.render(f), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print("stills", round(time.time() - t0, 1), "s")
        return
    out = pathlib.Path(a.out)
    if a.jobs > 1:
        if out.exists():
            out.unlink()                                   # never leave an older video where a failed build could be mistaken for it
        per = -(-(f1 - f0 + 1) // a.jobs // 60) * 60
        parts, procs = [], []
        for i, s in enumerate(range(f0, f1 + 1, per)):
            p = out.with_suffix(f".part{i}.mp4")
            parts.append((p, min(s + per - 1, f1) - s + 1))
            procs.append(subprocess.Popen([sys.executable, __file__, a.config, str(p), "--frames", f"{s}-{min(s + per - 1, f1)}", "--jobs", "1"]))
        codes = [p.wait() for p in procs]
        if any(codes):
            sys.exit(f"segment(s) failed with exit codes {codes}; no output written")
        for p, n in parts:                                 # every segment must hold exactly the frames it was asked for
            got = int(subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v", "-show_entries", "stream=nb_read_packets",
                                      "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout.strip() or 0)
            if got != n:
                sys.exit(f"{p.name}: expected {n} frames, found {got}; no output written")
        lst = out.with_suffix(".txt")
        lst.write_text("".join(f"file '{p.resolve()}'\n" for p, _ in parts))
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                        "-movflags", "+faststart", str(out)], check=True)
        for p, _ in parts:
            p.unlink()
        lst.unlink()
        print(json.dumps({"frames": f1 - f0 + 1, "wall_s": round(time.time() - t0, 1)}))
        return
    C = City(cfg)
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-g", "60", str(out)], stdin=subprocess.PIPE)
    for f in range(f0, f1 + 1):
        ff.stdin.write(C.render(f).tobytes())
    ff.stdin.close()
    if ff.wait():
        sys.exit("encoder failed")


if __name__ == "__main__":
    main()
