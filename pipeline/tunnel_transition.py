#!/usr/bin/env python3
"""Join two city rides for a livestream: a 'next stop' countdown, a 5-second tunnel, and the next city.

  python3 pipeline/tunnel_transition.py <cityA.mp4> <cityB.mp4> <out.mp4> --next "San Francisco" --where "California, USA"
        [--tail 20] [--head 12] [--countdown 60]

Writes the last --tail seconds of A, the tunnel, and the first --head seconds of B (for a preview; the stream
builder uses the same pieces over whole rides). Only the view through the window changes: the window frame
stays exactly as rendered. Scenery moves right to left, so the tunnel mouth arrives from the right at
foreground speed, the inside is dark with warm lamps flashing past, and daylight returns from the right on
the new city. Any resolution with the 16:9 window frame (720p previews, 1080p, 4K masters).

During the last --countdown seconds of A a small 'Next stop' card with a running timer sits in the top left
of the window; in the tunnel the next city's name is shown large. Music fades into the tunnel's rumble and
the next city's music fades up as the train comes out.
"""
import argparse, pathlib, subprocess, sys, tempfile
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FPS, SR = 30, 48000
T_IN, T_DARK, T_OUT = 1.0, 3.0, 1.0            # tunnel: mouth sweeps in, inside, daylight sweeps in
FONT = "/usr/share/fonts/opentype/inter/"
FADE = 1.6                                     # each ride fades in/out over 1.5 s; the stream skips those


def window_mask(W, H):
    """1 where the scenery shows (inside the window), 0 on the frame; same maths as the renderer."""
    s = W / 1920
    fr = cv2.resize(cv2.imread(str(ROOT / "work/illus/frame.png")), (W, int(1280 * s)), interpolation=cv2.INTER_AREA).astype(np.float32)
    gg = fr[..., 1] - np.maximum(fr[..., 0], fr[..., 2])
    fa = 1 - np.clip((gg - 40) / 70, 0, 1)
    k = max(1, int(3 * s - 1)) | 1
    fa = cv2.GaussianBlur(cv2.erode(fa, np.ones((k, k), np.uint8)), (0, 0), max(0.5, s))
    y0 = int(120 * s)
    return (1 - fa[y0:y0 + H])[..., None]


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                          "-of", "csv=p=0:s=,", str(p)], capture_output=True, text=True).stdout.split()
    w, h = (int(x) for x in out[0].split(",")[:2])
    return w, h, float(out[-1].split(",")[-1])


def frames(p, start, dur, W, H):
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", str(p), "-t", f"{dur:.3f}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    pr = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    n = W * H * 3
    while True:
        b = pr.stdout.read(n)
        if len(b) < n:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    pr.wait()


def audio(p, start, dur):
    b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", str(p), "-t", f"{dur:.3f}", "-f", "f32le", "-ac", "2",
                        "-ar", str(SR), "-"], capture_output=True).stdout
    a = np.frombuffer(b, np.float32).reshape(-1, 2).copy()
    want = int(round(dur * SR))
    return np.pad(a, ((0, max(0, want - len(a))), (0, 0)))[:want]


class Tunnel:
    def __init__(self, W, H, name, where):
        self.W, self.H, self.s = W, H, W / 1920
        s = self.s
        rng = np.random.default_rng(3)
        # stone portal face: dark blocks with mortar lines, lit warm from one side
        pw = int(170 * s)
        face = np.full((H, pw, 3), (46, 50, 58), np.float32)
        bh = int(46 * s)
        for r, y in enumerate(range(0, H, bh)):
            off = (r % 2) * int(60 * s)
            face[y:y + max(1, int(3 * s))] = (24, 26, 30)
            for x in range(-off, pw, int(120 * s)):
                if x > 0:
                    face[y:y + bh, x:x + max(1, int(3 * s))] = (24, 26, 30)
            face[y:y + bh] *= rng.uniform(0.85, 1.12)
        face *= np.linspace(1.25, 0.55, pw)[None, :, None]               # light falls off into the tunnel
        self.face = face
        # inside: near-black wall with ribs, scrolled; lamps drawn per frame
        self.dark = np.array((20, 16, 14), np.float32)
        self.rib = int(220 * s)
        self.lamp_gap = int(760 * s)
        self.speed = W / T_IN                                             # px per second, as fast as the near scenery
        self.card = self.title_card(name, where)

    def title_card(self, name, where):
        s = self.s
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        f1 = ImageFont.truetype(FONT + "Inter-Medium.otf", int(34 * s))
        f2 = ImageFont.truetype(FONT + "InterDisplay-SemiBold.otf", int(118 * s))
        f3 = ImageFont.truetype(FONT + "Inter-Regular.otf", int(38 * s))
        cx, cy = self.W // 2, int(self.H * 0.47)
        cream = (255, 238, 205, 255)
        label = "N E X T   S T O P"
        for txt, f, y, col in ((label, f1, cy - int(118 * s), (246, 196, 120, 255)), (name, f2, cy, cream), (where, f3, cy + int(98 * s), (225, 215, 195, 235))):
            w = d.textlength(txt, font=f)
            d.text((cx - w / 2, y - f.size * 0.6), txt, font=f, fill=col)
        ln = int(64 * s)
        d.line((cx - ln, cy - int(74 * s), cx + ln, cy - int(74 * s)), fill=(246, 196, 120, 200), width=max(1, int(2 * s)))
        a = np.asarray(im).astype(np.float32)
        glow = cv2.GaussianBlur(a[..., 3], (0, 0), 14 * s) / 255 * 0.55    # soft shadow so it reads on any background
        return a[..., 2::-1].copy(), a[..., 3:] / 255, glow[..., None]

    def inside(self, t):
        """the tunnel interior at time t (seconds since the tunnel began)"""
        W, H, s = self.W, self.H, self.s
        x = np.arange(W, dtype=np.float32)
        shift = self.speed * t
        rib = ((x + shift) % self.rib) / self.rib
        col = 1 + 0.35 * np.exp(-((rib - 0.5) ** 2) / 0.004)                  # faint ribs catching the carriage light
        img = np.empty((H, W, 3), np.float32)
        img[:] = self.dark
        img *= col[None, :, None]
        yy = np.linspace(-1, 1, H)[:, None, None]
        img *= 1 - 0.45 * yy ** 2                                              # darker towards top and bottom
        # warm lamps on the wall, streaking past
        ly = int(H * 0.30)
        for k in range(-1, W // self.lamp_gap + 3):
            lx = k * self.lamp_gap - (shift % self.lamp_gap) + self.lamp_gap * 0.5
            if -300 * s < lx < W + 300 * s:
                cv2.ellipse(img, (int(lx), ly), (int(150 * s), int(16 * s)), 0, 0, 360, (90, 170, 255), -1)
        blur = cv2.GaussianBlur(img, (0, 0), sigmaX=40 * s, sigmaY=10 * s)
        img = np.maximum(img, blur * 1.6)
        return img

    def overlay_card(self, img, k):
        if k <= 0:
            return img
        rgb, a, glow = self.card
        img = img * (1 - glow * k)
        return img * (1 - a * k) + rgb * a * k


def countdown_card(W, H, name, secs, box):
    s = W / 1920
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(FONT + "Inter-Medium.otf", int(24 * s))
    f2 = ImageFont.truetype(FONT + "InterDisplay-SemiBold.otf", int(40 * s))
    m, sec = divmod(max(0, int(np.ceil(secs))), 60)
    x0, y0 = box[0] + int(70 * s), box[1] + int(60 * s)
    t1, t2 = "NEXT STOP", f"{name}  ·  {m}:{sec:02d}"
    w = max(d.textlength(t1, font=f1), d.textlength(t2, font=f2)) + 48 * s
    d.rounded_rectangle((x0, y0, x0 + w, y0 + 104 * s), radius=int(22 * s), fill=(18, 20, 30, 150))
    d.text((x0 + 24 * s, y0 + 14 * s), t1, font=f1, fill=(246, 196, 120, 255))
    d.text((x0 + 24 * s, y0 + 42 * s), t2, font=f2, fill=(255, 240, 215, 255))
    a = np.asarray(im).astype(np.float32)
    return a[..., 2::-1].copy(), a[..., 3:] / 255


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b"); ap.add_argument("out")
    ap.add_argument("--next", required=True); ap.add_argument("--where", default="")
    ap.add_argument("--tail", type=float, default=20); ap.add_argument("--head", type=float, default=12)
    ap.add_argument("--countdown", type=float, default=60)
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()
    W, H, durA = probe(a.a)
    durA -= FADE
    mask = window_mask(W, H)
    ys, xs = np.where(mask[..., 0] > 0.5)
    box = (int(xs.min()), int(ys.min()))
    tun = Tunnel(W, H, a.next, a.where)
    t0 = durA - a.tail                                   # where in A this clip starts
    t_tun = a.tail - 0.4                                 # the tunnel mouth arrives 0.4 s before A ends ...
    T = T_IN + T_DARK + T_OUT                            # ... and B starts as daylight returns
    tB = t_tun + T_IN + T_DARK                           # clip time at which B's first frame shows
    total = tB + a.head
    srcA = frames(a.a, t0, a.tail, W, H)
    srcB = frames(a.b, FADE, a.head, W, H)
    cards = {}
    tmp = tempfile.mkdtemp()
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p", f"{tmp}/v.mp4"], stdin=subprocess.PIPE)
    lastA = lastB = None
    for i in range(int(round(total * FPS))):
        t = i / FPS
        fa = next(srcA, None) if t < a.tail else None
        lastA = fa if fa is not None else lastA
        fb = next(srcB, None) if t >= tB else None
        lastB = fb if fb is not None else lastB
        tt = t - t_tun
        if tt < 0:                                           # city A, with the countdown card
            img = lastA.astype(np.float32)
            left = (durA - (t0 + t)) + T_IN + T_DARK - 0.4   # seconds until we come out at the next city
            if left <= a.countdown:
                key = int(np.ceil(left))
                if key not in cards:
                    cards[key] = countdown_card(W, H, a.next, left, box)
                rgb, al = cards[key]
                k = min(1, (a.countdown - left) / 0.6) * min(1, max(0, (left - T_IN - T_DARK + 0.4 - 0.2)) / 0.4)
                img = img * (1 - al * k) + rgb * al * k
            out = img
        elif tt < T_IN:                                      # mouth sweeps in from the right over A
            src = lastA.astype(np.float32)
            edge = int(W - tun.speed * tt)
            view = tun.inside(tt)
            pw = tun.face.shape[1]
            x0 = max(0, edge)
            view[:, :x0] = src[:, :x0]
            if edge < W:
                lo, hi = max(0, edge), min(W, edge + pw)
                view[:, lo:hi] = tun.face[:, lo - edge:hi - edge]
            out = view
        elif tt < T_IN + T_DARK:                             # inside: name of the next city
            u = tt - T_IN
            view = tun.inside(tt)
            k = np.clip((u - 0.25) / 0.5, 0, 1) * np.clip((T_DARK - 0.3 - u) / 0.5, 0, 1)
            out = tun.overlay_card(view, k)
        else:                                                # daylight sweeps in from the right with city B
            u = tt - T_IN - T_DARK
            src = lastB.astype(np.float32)
            bloom = 1 + 0.55 * np.exp(-u / 0.35)             # eyes adjusting to the light
            src = np.clip(src * bloom + 40 * (bloom - 1), 0, 255)
            edge = int(W - tun.speed * u)
            if edge > 0:
                view = tun.inside(tt)
                pw = tun.face.shape[1]
                view[:, max(0, edge):] = src[:, max(0, edge):]
                lo, hi = max(0, edge - pw), min(W, edge)
                if hi > lo:
                    view[:, lo:hi] = tun.face[:, ::-1][:, lo - (edge - pw):hi - (edge - pw)]
                out = view
            else:
                out = src
        base = (lastB if t >= tB else lastA).astype(np.float32)
        dim = 1 - 0.35 * np.clip(min(tt / T_IN, (T_IN + T_DARK + T_OUT * 0.6 - tt) / (T_OUT * 0.6)), 0, 1)
        img = base * dim * (1 - mask) + out * mask           # the frame keeps its shape, only loses the daylight
        enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait()

    # sound: A's music fades into the tunnel rumble, B's music fades up on the way out
    n = int(round(total * SR))
    mix = np.zeros((n, 2), np.float32)
    aA = audio(a.a, t0, a.tail)
    ts = np.arange(len(aA)) / SR
    mix[:len(aA)] += aA * np.clip(1 - (ts - t_tun) / 2.0, 0, 1)[:, None]
    aB = audio(a.b, FADE, a.head)
    sB = int(tB * SR) - int(0.6 * SR)
    seg = aB[:n - sB] if sB >= 0 else aB
    rampB = np.clip(np.arange(len(seg)) / SR / 1.6, 0, 1)[:, None]
    mix[sB:sB + len(seg)] += seg * rampB
    rng = np.random.default_rng(1)
    noise = np.cumsum(rng.normal(0, 1, (n, 2)), axis=0).astype(np.float32)          # brown noise: low rumble
    c = np.cumsum(np.pad(noise, ((2401, 2400), (0, 0)), mode="edge"), axis=0)
    noise = noise - (c[4801:] - c[:-4801]) / 4801                                   # remove the slow drift
    noise /= np.abs(noise).max() + 1e-6
    tt = np.arange(n) / SR - t_tun
    env = np.clip(tt / 0.4, 0, 1) * np.clip((T_IN + T_DARK + 0.6 - tt) / 0.8, 0, 1)
    mix += noise * (0.09 * env)[:, None]
    wav = f"{tmp}/a.f32"
    np.clip(mix, -1, 1).astype(np.float32).tofile(wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"{tmp}/v.mp4", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", wav,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out], check=True)
    print(f"wrote {a.out}: {total:.1f} s, tunnel at {t_tun:.1f}-{t_tun + T:.1f} s")


if __name__ == "__main__":
    sys.exit(main())
