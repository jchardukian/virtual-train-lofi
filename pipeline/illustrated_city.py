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
from illustrated_journey import rgba, tint, loop, over, strip, S, W, H, FPS, MID, BAND, NEAR, ROOT, ILL, CHI  # noqa: E402

SEC = 300
HAZE = (196, 208, 250)
ART, ART_X2 = "work/cities_v3/", ROOT / "work/cities_x2"     # 4K renders use the 2x-upscaled art where it exists


def art(src, scale=1.0):
    """file and resize factor for a layer at the current render scale"""
    if S > 1 and src.startswith(ART) and (ART_X2 / src[len(ART):]).exists():
        return ART_X2 / src[len(ART):], scale * S / 2
    return ROOT / src, scale * S


def odd(n):
    return int(round(n)) | 1


class City:
    def __init__(self, cfg):
        self.cfg = cfg
        self.no_grade = False
        self.n = len(cfg["sections"])
        self.sect = SEC / self.n
        SC = cv2.imread(str(ILL / "scene.png"))
        # sky: a city's own painted sky if given, otherwise the shared golden one
        sky_src = ROOT / cfg.get("sky", "work/chi/sky.png")
        sky = cv2.imread(str(sky_src))
        sky = cv2.resize(sky, None, fx=3000 * S / sky.shape[1], fy=3000 * S / sky.shape[1], interpolation=cv2.INTER_CUBIC)
        if cfg.get("sky_flip"):
            sky = sky[:, ::-1]
        y0 = max(0, min(sky.shape[0] - 760 * S, int(sky.shape[0] * cfg.get("sky_top", 0.33))))
        self.sky = np.ascontiguousarray(sky[y0:y0 + 760 * S]).astype(np.float32)
        self.horizon = self.sky[-40:].reshape(-1, 3).mean(axis=0)
        wt = cv2.resize(SC[775:1010, 505:775], (1300 * S, 420 * S), interpolation=cv2.INTER_LANCZOS4)
        self.river = loop((wt.astype(np.float32), np.ones(wt.shape[:2] + (1,), np.float32)), 200 * S) \
            if any(sc.get("ground") == "river" for sc in cfg["sections"]) else None
        # ground plane: a band cropped from one of the city's own strips, or the shared lawn
        gcfg = cfg.get("ground_src", {"src": "work/chi/sprites/strip_3.png", "rows": [70, 135]})
        if "colour" in gcfg:              # a plain field (fresh snow, sand): two colours, top to bottom, with faint texture
            c0, c1 = np.array(gcfg["colour"][0], np.float32), np.array(gcfg["colour"][1], np.float32)
            yy = np.linspace(0, 1, 420 * S, dtype=np.float32)[:, None, None]
            lawn = np.repeat(c0 + (c1 - c0) * yy, 1536 * S, axis=1)
            noise = np.random.default_rng(3).normal(0, 4, (420, 1536)).astype(np.float32)
            if S > 1:
                noise = cv2.resize(noise, (1536 * S, 420 * S), interpolation=cv2.INTER_LINEAR)
            lawn += cv2.GaussianBlur(noise, (0, 0), 2 * S)[..., None]
        else:
            g = cv2.imread(str(ROOT / gcfg["src"]), cv2.IMREAD_UNCHANGED)
            r0, r1 = gcfg["rows"]
            g = g[r0:r1, :, :3]
            if gcfg.get("tile"):              # repeat the texture downwards at its own scale instead of stretching it
                g = cv2.resize(g, None, fx=gcfg.get("scale", 1.0) * S, fy=gcfg.get("scale", 1.0) * S, interpolation=cv2.INTER_CUBIC)
                g = np.concatenate([g, g[::-1]], axis=0)
                lawn = np.tile(g, (420 * S // g.shape[0] + 1, 1, 1))[:420 * S]
                lawn = cv2.resize(lawn, (1536 * S, 420 * S), interpolation=cv2.INTER_AREA).astype(np.float32)
            else:
                lawn = cv2.resize(g, (1536 * S, 420 * S), interpolation=cv2.INTER_CUBIC).astype(np.float32)
        self.lawn = loop((lawn, np.ones(lawn.shape[:2] + (1,), np.float32)), 200 * S)
        # the line's own trackside, right below the window
        ncfg = cfg.get("near", {"src": "work/chi/sprites/strip_3.png", "scale": 1.7, "base": 40})
        emb = rgba(*art(ncfg["src"], ncfg.get("scale", 1.7)))
        nb = (int(ncfg.get("blur", 4)) | 1) if S == 1 else odd(int(ncfg.get("blur", 4)) * S)  # a light motion blur only; heavy blur read as out of focus
        nrgb, na = cv2.blur(emb[0], (nb, 1)), cv2.blur(emb[1], (nb, 1))
        if ncfg.get("focus", 3.0):                    # the eye is on the city, so the nearest things are a little soft
            sg = ncfg.get("focus", 3.0) * S
            nrgb, na = cv2.GaussianBlur(nrgb, (0, 0), sg), cv2.GaussianBlur(na, (0, 0), sg)
        if na.ndim == 2:
            na = na[..., None]
        if ncfg.get("shade", 0.3):                    # in the train's shadow: darker towards the window sill
            ramp = np.linspace(1 - 0.4 * ncfg.get("shade", 0.3), 1 - ncfg.get("shade", 0.3), nrgb.shape[0], dtype=np.float32)[:, None, None]
            nrgb = nrgb * ramp
        if ncfg.get("feather_top", 20):              # no hard top edge across the street behind
            ft = int(ncfg.get("feather_top", 20) * S)
            ys = np.where(na[..., 0].max(1) > 0.05)[0]
            if len(ys):
                r = np.clip((np.arange(nrgb.shape[0]) - ys[0]) / max(1, ft), 0, 1).astype(np.float32)[:, None, None]
                nrgb, na = nrgb * r, na * r
        self.near = loop((nrgb, na), 140 * S)
        self.near_base = ncfg.get("base", 40) * S
        # close objects that sweep past at each change of scenery
        tcfg = cfg.get("treewall_cfg", {"src": cfg.get("treewall", "work/chi/sprites/strip_0.png"), "crop": [20, 470, 0, 0.76]})
        tw = cv2.imread(str(ROOT / tcfg["src"]), cv2.IMREAD_UNCHANGED)
        x0, x1, ya, yb = tcfg["crop"]
        tw = tw[int(tw.shape[0] * ya):int(tw.shape[0] * yb), x0:x1]
        tw = cv2.resize(tw, None, fx=5.2 * 175 * S / tw.shape[0], fy=5.2 * 175 * S / tw.shape[0], interpolation=cv2.INTER_CUBIC).astype(np.float32)
        ramp = np.clip(np.minimum(np.arange(tw.shape[1]), tw.shape[1] - 1 - np.arange(tw.shape[1])) / (520.0 * S), 0, 1).astype(np.float32)
        ramp = (ramp * ramp * (3 - 2 * ramp))[None, :, None]
        tb = (odd(41 * S), odd(9 * S)) if S > 1 else (41, 9)
        self.treewall = (cv2.blur(tw[..., :3] * (tw[..., 3:] / 255.0), tb) * 0.8 * ramp, cv2.blur(tw[..., 3:] / 255.0, tb)[..., None] * ramp)
        # opening scene: a city-specific full painting for the first seconds, panning slowly, then dissolving into the ride
        self.opening = None
        if cfg.get("opening"):
            o = cfg["opening"]
            op = cv2.imread(str(art(o["src"])[0]))
            op = cv2.resize(op, None, fx=2200 * S / op.shape[1], fy=2200 * S / op.shape[1], interpolation=cv2.INTER_CUBIC).astype(np.float32)
            self.opening = (op, o.get("hold", 6.0), o.get("fade", 3.0))
        # weather: procedural particles between the scenery and the window glass
        self.weather = cfg.get("weather")
        rng = np.random.default_rng(7)
        n = {"snow": 420, "leaves": 70, "petals": 110, "rain": 260, "fireflies": 60}.get(self.weather, 0)
        self.px, self.py = rng.uniform(0, W, n), rng.uniform(0, H, n)
        self.pz = rng.uniform(0.3, 1.0, n)                   # depth: near flakes are bigger and faster
        self.pph = rng.uniform(0, 6.28, n)
        self.pcol = rng.choice(np.array([[40, 70, 220], [30, 110, 235], [40, 150, 240], [60, 60, 190]], np.float32), n)
        fr = cv2.resize(cv2.imread(str(ILL / "frame.png")), (W, 1280 * S), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        gg = fr[..., 1] - np.maximum(fr[..., 0], fr[..., 2])
        fa = 1 - np.clip((gg - 40) / 70, 0, 1)
        fa = cv2.GaussianBlur(cv2.erode(fa, np.ones((odd(3 * S - 1), odd(3 * S - 1)), np.uint8)), (0, 0), 1.0 * S)
        fr[..., 1] = np.where(fa < 0.999, np.minimum(fr[..., 1], np.maximum(fr[..., 0], fr[..., 2]) * 1.05), fr[..., 1])
        self.frame, self.fa = fr[120 * S:120 * S + H] * fa[120 * S:120 * S + H, :, None], fa[120 * S:120 * S + H, :, None]
        self.gy, self.gx = np.mgrid[0:420 * S, 0:W].astype(np.float32)
        self.cache = {}
        # layers
        self.backdrop = [self.far_layer(L) for L in cfg.get("backdrop", [])]        # shown for the whole ride (e.g. mountains)
        self.sections = []
        self.mid = []
        self.mid_front = cfg.get("mid_front", False)
        self.ground_first = cfg.get("ground_first", False)
        self.band_off = {}
        # owner 2026-11-24: no separate foreground strip; the street row runs down to the window sill instead
        self.keep_near = cfg.get("keep_near", False)
        self.mid_speed = MID
        SILL = 1040                                    # just below the window's lower edge at 1080p
        self.band_tops = []
        self.row_tops = []
        self.seam2 = bool(cfg.get("backdrop")) and cfg.get("seam_v2", True)   # owner 2026-11-24: no hazy strip between layers
        for k, sc in enumerate(cfg["sections"]):
            far = [self.far_layer(L) for L in sc.get("far", [])]
            band = None
            zoom = None
            if sc.get("band"):
                b = dict(sc["band"])
                drop = 0
                if not self.keep_near and sc.get("ground", "lawn") != "river":
                    # bring the row closer: its top stays where it was, its street now meets the window sill
                    hh = cv2.imread(str(ROOT / b["src"]), cv2.IMREAD_UNCHANGED).shape[0] * b.get("scale", 1.0)
                    top = b.get("base", 850) - hh
                    f = (SILL - top) / max(1.0, b.get("base", 850) - top)
                    zoom = (top, f)
                    b["scale"], b["base"], b["feather_bottom"] = b.get("scale", 1.0) * f, SILL, 0
                    b["speed"] = b.get("speed", BAND / S) * f
                    self.mid_speed = b["speed"] * S
                im = cv2.imread(str(ROOT / b["src"]), cv2.IMREAD_UNCHANGED)
                cov = (im[..., 3] > 200).mean(1) if im.shape[2] == 4 else np.ones(im.shape[0])
                thin = np.where(cov < 0.85)[0]               # top of the solid body (palms, spires above it don't count)
                thin = thin[thin < len(cov) * 0.9]
                r0 = int(thin[-1]) + 1 if len(thin) else 0
                rows = np.array([r0])
                self.row_tops.append(b.get("base", 850) - (im.shape[0] - r0) * b.get("scale", 1.0) + b.get("feather_top", 90))
                flat = len(rows) and (im[r0 + 2, :, 3] > 200).mean() > 0.9 if im.shape[2] == 4 else True
                if flat:                                    # straight-cut top: the skyline's edge would show above it
                    self.band_tops.append(b.get("base", 850) - (im.shape[0] - r0) * b.get("scale", 1.0) + b.get("feather_top", 90))
                bkey = ("band", b["src"], b.get("scale", 1.0), b.get("flip", False), b.get("feather_top", 90), b.get("feather_bottom", 45))
                if bkey not in self.cache:            # sections that share a strip share one copy of it (4K memory)
                    lay = self.load(b["src"], b.get("scale", 1.0), b.get("flip", False))
                    if zoom and not cfg.get("no_fill_down"):
                        lay = self.fill_down(lay)
                    self.cache[bkey] = loop(self.feather(lay, b.get("feather_top", 90) * S, b.get("feather_bottom", 45) * S, 0.0 if self.seam2 else 0.35), 140 * S)
                band = (self.cache[bkey], b.get("base", 850) * S, b.get("speed", BAND / S) * S, b.get("offset", 300) * S)
            self.sections.append({"ground": sc.get("ground", "lawn"), "far": far, "band": band})
            if band is not None:                       # one row, one position: the first section's offset wins
                self.band_off.setdefault((id(band[0][0]), band[1], band[2]), band[3])
            items = sc.get("mid", [])
            for i, m in enumerate(items):
                tau = k * self.sect + (i + 0.5) / len(items) * self.sect
                mb, ms = m.get("base", 775 if sc.get("ground", "lawn") != "river" else 722), m.get("scale", 1.0)
                if zoom:                                       # landmarks on the street come closer with it
                    mb, ms = zoom[0] + (mb - zoom[0]) * zoom[1], ms * zoom[1]
                self.mid.append((self.load(m["src"], ms, m.get("flip", False)), tau, int(round(mb * S))))

        # owner 2026-11-24 (Boston, Atlanta): the skyline picture's faded bottom edge showed as a blurry strip above the
        # street row. Keep that edge (its last ~60 px) hidden behind the row's top.
        if self.seam2 and self.row_tops and not cfg.get("hide_backdrop_edge"):
            reach = max(self.row_tops) + 30
            self.backdrop = [self.far_layer(L, reach) for L in cfg.get("backdrop", [])]
        if self.band_tops and cfg.get("hide_backdrop_edge"):
            need = max(self.band_tops) + cfg.get("backdrop_overlap", 75)
            self.backdrop = [self.far_layer(dict(L, base=int(round(max(L.get("base", 712), need))))) for L in cfg.get("backdrop", [])]
    def draw_ground(self, img, t, bob, w):
        if not self.keep_near:            # the street row now reaches the sill; a plain ground only showed through roof gaps
            return
        land = min(sum(w[k] for k, sc in enumerate(self.sections) if sc["ground"] == "lawn"), 1.0)
        if land > 0:
            rgb, _, period = self.lawn
            o = int(110 * S * t) % period
            y0 = 745 * S + bob
            img[y0:] = img[y0:] * (1 - land) + rgb[:H - y0, o:o + W] * land

    def draw_mids(self, img, t, bob):
        for (rgb, a), tau, base in self.mid:
            x = int(round(W / 2 + self.mid_speed * (tau - t) - a.shape[1] / 2))   # at the street's own speed
            if -a.shape[1] < x < W:
                over(img, rgb, a, x, base - a.shape[0] + bob)

    def load(self, src, scale=1.0, flip=False, haze=0.0):
        key = (src, scale, flip, haze)
        if key not in self.cache:
            L = rgba(*art(src, scale), flip)
            self.cache[key] = tint(L, HAZE, haze) if haze else L
        return self.cache[key]

    @staticmethod
    def fill_down(layer):
        """continue each column's lowest solid pixel down to the bottom of the strip, so the street reaches the sill
        with no see-through wedge under a sloping street; gaps higher up (between roofs, under palms) stay open"""
        rgb, a = layer
        rgb, a = rgb.copy(), a.copy()
        solid = a[..., 0] > 0.6
        h = a.shape[0]
        has = solid.any(0)
        last = np.where(has, h - 1 - np.argmax(solid[::-1], axis=0), -1)
        cols = np.nonzero(has & (last < h - 1))[0]
        for x in cols:
            y = last[x]
            c = rgb[y, x] / max(a[y, x, 0], 1e-3)
            rgb[y + 1:, x] = c
            a[y + 1:, x, 0] = 1.0
        return rgb, a

    def feather(self, layer, top, bottom, mist_k=0.35):
        """Soften a strip's straight top and bottom edges so it melts into the layer behind it instead of
        ending in a ruled line, and mist its top into the sky colour the way distance does."""
        rgb, a = layer
        h = a.shape[0]
        rows = np.arange(h, dtype=np.float32)
        opaque = np.where(a[..., 0].max(axis=1) > 0.5)[0]
        t0 = opaque[0] if len(opaque) else 0
        b1 = opaque[-1] if len(opaque) else h - 1
        k = np.ones(h, np.float32)
        if top:
            k *= np.clip((rows - t0) / top, 0, 1)
        if bottom:
            k *= np.clip((b1 - rows) / bottom, 0, 1)
        k = (k * k * (3 - 2 * k))[:, None, None]
        mist = np.clip(1 - (rows - t0) / max(1, top * 1.6), 0, 1)[:, None, None] * mist_k
        rgb = rgb * (1 - mist) + self.horizon * a * mist
        return rgb * k, a * k

    def far_layer(self, L, reach=None):
        lay = self.load(L["src"], L.get("scale", 1.6), L.get("flip", False), L.get("haze", 0.4))
        if reach is not None and L.get("base", 712) < reach + 60:
            # seam v2: no fade-out at the bottom; the picture's lowest rows continue (mirrored, softened) down to
            # below the street row's top, so the row's soft edge blends into scenery, never into a band of sky
            rgb, a = lay
            sol = np.where(a[..., 0].mean(axis=1) > 0.6)[0]
            b1 = int(sol[-1]) + 1 if len(sol) else a.shape[0]
            rgb, a = rgb[:b1], a[:b1]
            full = np.where(a[..., 0].mean(axis=1) > 0.97)[0]
            ext = int(round((reach + 60 - L.get("base", 712)) * S))
            # continue the picture's own lowest solid strip (ground, trees, water) by mirror-tiling a thin band of it,
            # so it reads as more of the same scenery, not as an upside-down copy of the skyline
            kk = max(4, int(28 * S))
            src_end = int(full[-1]) + 1 if len(full) else b1
            strip_r, strip_a = rgb[max(0, src_end - kk):src_end], np.clip(a[max(0, src_end - kk):src_end], 1e-3, 1)
            strip = strip_r / strip_a                                   # un-premultiply: no dark holes
            reps = []
            i = 0
            while sum(x.shape[0] for x in reps) < ext:
                reps.append(strip[::-1] if i % 2 == 0 else strip); i += 1
            er = np.concatenate(reps)[:ext]
            kb = odd(int(9 * S))
            er = cv2.GaussianBlur(er, (kb, kb), 0) * 0.94
            ea = np.ones(er.shape[:2] + (1,), np.float32) if a.ndim == 3 else np.ones(er.shape[:2], np.float32)
            er = er.reshape(ext, a.shape[1], -1)
            # fill the gap between the picture's last solid row and the strip source (if the source sat higher)
            lay = (np.concatenate([rgb[:src_end], er]), np.concatenate([a[:src_end], ea.reshape(ext, a.shape[1], -1)]))
            ext = ext - (b1 - src_end)
            L = dict(L, base=int(round(L.get("base", 712) + ext / S)))
            return self._far_tuple(L, lay)
        lay = self.feather(lay, 0, L.get("feather_bottom", 60) * S)
        return self._far_tuple(L, lay)

    def _far_tuple(self, L, lay):
        if L.get("tile"):
            return ("tile", loop(lay, 140 * S), L.get("base", 712) * S, L.get("speed", 8) * S, L.get("alpha", 0.9), L.get("offset", 200) * S)
        return ("one", lay, L.get("base", 712) * S, L.get("speed", 5) * S, L.get("alpha", 0.9), L.get("x0", -60) * S)

    def weight(self, t, k, fade=3.0):
        a, b = k * self.sect, (k + 1) * self.sect
        up = 1.0 if k == 0 else np.clip((t - (a - fade)) / (2 * fade), 0, 1)
        dn = 1.0 if k == self.n - 1 else np.clip(((b + fade) - t) / (2 * fade), 0, 1)
        return float(min(up, dn))

    def bands(self, w, river):
        """the street rows to draw now. Neighbouring sections that use the same row are one continuous row (same
        offset, weights added): cross-fading two copies of one row at different offsets showed a ghostly double
        exposure for ~6 s at every section change. Different rows still cross-fade."""
        out = {}
        for k, sc in enumerate(self.sections):
            if w[k] > 0 and sc["band"] and (sc["ground"] == "river") == river:
                lp, base, speed, _ = sc["band"]
                key = (id(lp[0]), base, speed)
                if key in out:
                    out[key][4] = min(1.0, out[key][4] + w[k])
                else:
                    out[key] = [lp, base, speed, self.band_off[key], w[k]]
        return out.values()

    def water(self, lp, t, speed, h):
        rgb, _, period = lp
        o = int(300 + speed * t) % period
        r = rgb[:h, o:o + W]
        gx, gy = self.gx[:h], self.gy[:h]
        mx = (gx + 1.8 * S * np.sin(gy * 0.19 / S + t * 2.9) + 1.0 * S * np.sin(gx * 0.04 / S - t * 2.1)).astype(np.float32)
        my = (gy + 1.4 * S * np.sin(gx * 0.03 / S + t * 2.4)).astype(np.float32)
        return cv2.remap(r, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

    def draw_far(self, img, lay, t, t0, bob, k):
        kind, L, base, speed, alpha, x = lay
        if kind == "tile":
            strip(img, L, x + speed * t, base + bob, alpha * k)
        else:
            over(img, L[0], L[1], int(x - speed * (t - t0)), base - L[0].shape[0] + bob, alpha * k)

    def render(self, f):
        t = f / FPS
        bob = int(round((1.6 * math.sin(2 * math.pi * 0.9 * t) + 0.9 * math.sin(2 * math.pi * 2.3 * t + 1)) * S))
        w = [self.weight(t, k) for k in range(self.n)]
        img = np.empty((H, W, 3), np.float32)
        o = int(40 + 3 * t) * S if S == 1 else int((40 + 3 * t) * S)
        img[:760 * S] = self.sky[:, o:o + W]
        img[760 * S:] = self.sky[-1:, o:o + W]
        if self.ground_first:                # ground lies behind the distant layers, which stand on it
            self.draw_ground(img, t, bob, w)
        for lay in self.backdrop:
            self.draw_far(img, lay, t, 0.0, bob, 1.0)
        for k, sc in enumerate(self.sections):
            if w[k] > 0:
                for lay in sc["far"]:
                    self.draw_far(img, lay, t, k * self.sect, bob, w[k])
        riv = min(sum(w[k] for k, sc in enumerate(self.sections) if sc["ground"] == "river"), 1.0)
        if not self.ground_first:
            self.draw_ground(img, t, bob, w)
        if not self.mid_front:
            self.draw_mids(img, t, bob)
        # river sections: the strip stands on the far bank, then the water in front of it
        for lp, base, speed, off, k in self.bands(w, river=True):
            strip(img, lp, off + speed * t, base + bob, k)
        if riv > 0:
            y0 = 730 * S + bob
            rv = self.water(self.river, t, 62 * S, H - y0)
            img[y0:] = img[y0:] * (1 - riv) + rv * riv
        for lp, base, speed, off, k in self.bands(w, river=False):
            strip(img, lp, off + speed * t, base + bob, k)
        if self.mid_front:                 # landmarks stand on the street in front of the row, not perched behind it
            self.draw_mids(img, t, bob)
        if self.keep_near:
            strip(img, self.near, 400 * S + NEAR * t, H + self.near_base, 1.0)
        for k in range(1, self.n):
            x = int(W + 150 * S - 620 * S * (t - (k * self.sect - 3.4)))
            if -self.treewall[1].shape[1] < x < W:
                over(img, *self.treewall, x, H + 60 * S - self.treewall[1].shape[0])
        if self.opening is not None:
            op, hold, fade = self.opening
            if t < hold + fade:
                k = 1.0 if t < hold else 1.0 - (t - hold) / fade
                k = k * k * (3 - 2 * k)
                ox = int(min(op.shape[1] - W, (40 + 26 * t) * S))    # the same slow drift as the ride
                oy = max(0, (op.shape[0] - H) // 2)
                view = op[oy:oy + H, ox:ox + W]
                img[:view.shape[0]] = img[:view.shape[0]] * (1 - k) + view * k
        self.particles(img, t)
        img = self.grade(img)
        return np.clip(img * (1 - self.fa) + self.frame, 0, 255).astype(np.uint8)

    def particles(self, img, t):
        if not self.weather:
            return
        if self.weather == "snow":
            x = (self.px - (NEAR * 0.55 * self.pz + 8 * S) * t + 14 * S * np.sin(t * 0.7 + self.pph)) % (W + 40 * S) - 20 * S
            y = (self.py + (38 + 70 * self.pz) * S * t) % (H + 40 * S) - 20 * S
            for xi, yi, zi in zip(x.astype(int), y.astype(int), self.pz):
                cv2.circle(img, (xi, yi), int((1 + 3 * zi) * S), (250, 248, 245), -1, lineType=cv2.LINE_AA)
        elif self.weather == "rain":           # fine slanted streaks, soft and cozy, not a storm
            x = (self.px - 260 * S * t * self.pz) % (W + 60 * S) - 30 * S
            y = (self.py + 900 * S * t * self.pz) % (H + 60 * S) - 30 * S
            for xi, yi, zi in zip(x.astype(int), y.astype(int), self.pz):
                cv2.line(img, (xi, yi), (int(xi - 6 * S * zi), int(yi + 26 * S * zi)), (225, 220, 215), S, lineType=cv2.LINE_AA)
        elif self.weather == "fireflies":      # warm glowing specks for summer nights
            x = (self.px - 25 * S * t * self.pz + 30 * S * np.sin(t * 0.5 + self.pph)) % W
            y = 500 * S + (self.py % (450 * S)) + 20 * S * np.sin(t * 0.8 + self.pph * 2)
            glow = 0.5 + 0.5 * np.sin(t * 2.5 + self.pph * 3)
            for xi, yi, g in zip(x.astype(int), y.astype(int), glow):
                cv2.circle(img, (xi, yi), 3 * S, (120 + 100 * g, 230, 255), -1, lineType=cv2.LINE_AA)
        elif self.weather == "petals":
            x = (self.px - (NEAR * 0.6 * self.pz + 15 * S) * t + 35 * S * np.sin(t * 0.8 + self.pph)) % (W + 60 * S) - 30 * S
            y = (self.py + (22 + 35 * self.pz) * S * t + 18 * S * np.sin(t * 1.1 + self.pph)) % (H + 60 * S) - 30 * S
            for xi, yi, zi, ph in zip(x.astype(int), y.astype(int), self.pz, self.pph):
                ang = int((ph * 57 + t * 90 * zi) % 360)
                cv2.ellipse(img, (xi, yi), (int((2 + 5 * zi) * S), int((1 + 3 * zi) * S)), ang, 0, 360, (205, 190, 250), -1, lineType=cv2.LINE_AA)
        elif self.weather == "leaves":
            x = (self.px - (NEAR * 0.7 * self.pz + 20 * S) * t + 30 * S * np.sin(t * 0.9 + self.pph)) % (W + 80 * S) - 40 * S
            y = (self.py + (30 + 45 * self.pz) * S * t + 20 * S * np.sin(t * 1.3 + self.pph)) % (H + 80 * S) - 40 * S
            for xi, yi, zi, ph, c in zip(x.astype(int), y.astype(int), self.pz, self.pph, self.pcol):
                ang = int((ph * 57 + t * 120 * zi) % 360)
                cv2.ellipse(img, (xi, yi), (int((4 + 9 * zi) * S), int((2 + 4 * zi) * S)), ang, 0, 360, tuple(float(v) for v in c), -1, lineType=cv2.LINE_AA)

    def grade(self, img):
        """Per-city light and colour, applied to the scenery only: the window frame stays the same in every city."""
        g = self.cfg.get("grade")
        if not g or self.no_grade:
            return img
        x = np.clip(img, 0, 255) / 255.0
        L = (0.114 * x[..., 0] + 0.587 * x[..., 1] + 0.299 * x[..., 2])[..., None]
        sh, hi = np.array(g.get("shadows", [1, 1, 1]), np.float32), np.array(g.get("highlights", [1, 1, 1]), np.float32)
        x = x * (sh * (1 - L) + hi * L)
        L2 = (0.114 * x[..., 0] + 0.587 * x[..., 1] + 0.299 * x[..., 2])[..., None]
        x = L2 + (x - L2) * g.get("saturation", 1.0)
        x = np.clip(x, 0, 1) ** g.get("gamma", 1.0)
        return x * 255.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config")
    ap.add_argument("out")
    ap.add_argument("--frames")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--still", type=int, nargs="*")
    ap.add_argument("--no-grade", action="store_true", help="ignore the city's grade (for before/after samples)")
    a = ap.parse_args()
    cfg = json.loads(pathlib.Path(a.config).read_text())
    f0, f1 = (int(x) for x in a.frames.split("-")) if a.frames else (0, SEC * FPS - 1)
    t0 = time.time()
    if a.still:
        C = City(cfg)
        C.no_grade = a.no_grade
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
    C.no_grade = a.no_grade
    ff = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", *(["-preset", "medium", "-crf", "17"] if S == 1 else ["-preset", "veryfast", "-crf", "14"]),
                           "-pix_fmt", "yuv420p", "-g", "60", str(out)], stdin=subprocess.PIPE)       # 4K: a fast near-lossless intermediate; the master is the quality encode
    for f in range(f0, f1 + 1):
        ff.stdin.write(C.render(f).tobytes())
    ff.stdin.close()
    if ff.wait():
        sys.exit("encoder failed")


if __name__ == "__main__":
    main()
