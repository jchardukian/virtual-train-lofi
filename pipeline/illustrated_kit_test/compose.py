import cv2, numpy as np, subprocess, sys, time
W, H, FPS, SEC = 1920, 1080, 30, 30
t0 = time.time()
S = cv2.imread('../illus/scene.png')
def up(im, f): return cv2.resize(im, None, fx=f, fy=f, interpolation=cv2.INTER_LANCZOS4)
def tile(im, length):
    """mirror-tile horizontally to at least `length` px so joins are seamless"""
    out = [im, im[:, ::-1]]
    while sum(o.shape[1] for o in out) < length: out += [im, im[:, ::-1]]
    return np.hstack(out)
def spr(name, f):
    s = up(cv2.imread(name + '.png', cv2.IMREAD_UNCHANGED), f).astype(np.float32)
    return s[..., :3], s[..., 3:] / 255.0

# ---- strips
HOR = 700                                                       # horizon / quay line in the output
ys = np.linspace(0, 1, HOR, dtype=np.float32)[:, None, None]
top, mid, low = np.array([190, 150, 120.]), np.array([185, 190, 240.]), np.array([175, 215, 255.])
grad = np.where(ys < 0.5, top + (mid - top) * ys * 2, mid + (low - mid) * (ys - 0.5) * 2)
sky = np.repeat(grad, 4000, axis=1).astype(np.float32)
cl = up(S[0:150, 330:860], 2.6).astype(np.float32)             # painted clouds from the plate
clt = tile(cl, 4000)[:, :4000]
fade = np.clip((390 - np.arange(clt.shape[0], dtype=np.float32)) / 140, 0, 1)[:, None, None]
sky[:clt.shape[0]] = sky[:clt.shape[0]] * (1 - fade) + clt * fade
far = up(S[200:565, 330:860], 1.55).astype(np.float32)         # hazy distant skyline
fart = tile(far, 3000)[:, :3000]
fa_ = np.clip(np.arange(fart.shape[0], dtype=np.float32) / 150, 0, 1)[:, None, None] * 0.92
bank = tile(up(S[585:700, 1160:1536], 1.5), 5200)[:, :5200].astype(np.float32)   # far bank: trees and quay wall
ba = np.clip(np.arange(bank.shape[0], dtype=np.float32) / 40, 0, 1)[:, None, None]
river = tile(cv2.resize(S[775:1010, 505:775], (1300, 400), interpolation=cv2.INTER_LANCZOS4), 5200)[:, :5200].astype(np.float32)
near = tile(up(S[585:690, 1160:1536], 3.0), 9000)[:, :9000].astype(np.float32)   # near bank: the same tree line, much closer
near = cv2.blur(near, (15, 3))
na = np.clip(np.arange(near.shape[0], dtype=np.float32) / 110, 0, 1)[:, None, None]

# ---- sprites on the route: (name, scale, route x, layer speed px/s, base y)
MIDV, NEARV = 46.0, 78.0
plan = [('glassL', 1.45, 200, MIDV, 735), ('deco', 1.7, 820, MIDV, 735), ('marina', 1.4, 1330, MIDV, 760), ('tower', 1.75, 1960, MIDV, 735),
        ('brick', 1.3, 2330, MIDV, 745), ('glassR', 2.5, 2900, MIDV, 735),
        ('bridge', 1.5, 2250, NEARV, 800), ('house', 1.5, 2130, NEARV, 790), ('house', 1.5, 3180, NEARV, 790)]
sprites = [(spr(n, f), x, v, by) for n, f, x, v, by in plan]

frame = cv2.resize(cv2.imread('../illus/frame.png'), (W, 1280), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
g = frame[..., 1] - np.maximum(frame[..., 0], frame[..., 2])
fa = 1 - np.clip((g - 40) / 70, 0, 1)
fa = cv2.GaussianBlur(cv2.erode(fa, np.ones((3, 3), np.uint8)), (0, 0), 1.0)
frame[..., 1] = np.where(fa < 0.999, np.minimum(frame[..., 1], np.maximum(frame[..., 0], frame[..., 2]) * 1.05), frame[..., 1])
frame, fa = frame[120:120 + H], fa[120:120 + H, :, None]

def paste(img, rgb, a, x, y):
    h, w = a.shape[:2]
    xa, xb, ya, yb = max(0, x), min(W, x + w), max(0, y), min(H, y + h)
    if xb <= xa or yb <= ya: return
    A = a[ya - y:yb - y, xa - x:xb - x]
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - A) + rgb[ya - y:yb - y, xa - x:xb - x] * A

def crop(strip, off):
    off = int(off) % (strip.shape[1] - W)
    return strip[:, off:off + W]

ff = None
only = [int(a) for a in sys.argv[2:]]
if not only:
    ff = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', sys.argv[1]], stdin=subprocess.PIPE)
gy, gx = np.mgrid[0:400, 0:W].astype(np.float32)
for i in (only or range(SEC * FPS)):
    t = i / FPS
    bob = int(round(1.6 * np.sin(2 * np.pi * 0.9 * t) + 0.9 * np.sin(2 * np.pi * 2.3 * t + 1)))
    img = np.zeros((H, W, 3), np.float32)
    img[:HOR] = crop(sky, 100 + 5 * t)
    f = crop(fart, 200 + 15 * t); fy = HOR - f.shape[0] + 30
    k = HOR - fy
    img[fy:HOR] = img[fy:HOR] * (1 - fa_[:k]) + f[:k] * fa_[:k]
    for (rgb, a), x, v, by in sprites:
        if v == MIDV: paste(img, rgb, a, int(round(x - v * t)), by - a.shape[0] + bob)
    # river with moving ripples
    r = crop(river, 300 + 62 * t)
    mx = (gx + 1.8 * np.sin(gy * 0.19 + t * 2.9) + 1.0 * np.sin(gx * 0.04 - t * 2.1)).astype(np.float32)
    my = (gy + 1.4 * np.sin(gx * 0.03 + t * 2.4)).astype(np.float32)
    img[HOR - 20:] = cv2.remap(r, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    b = crop(bank, 150 + 58 * t); y0 = HOR - 120 + bob
    img[y0:y0 + b.shape[0]] = img[y0:y0 + b.shape[0]] * (1 - ba) + b * ba
    for (rgb, a), x, v, by in sprites:
        if v == NEARV: paste(img, rgb, a, int(round(x - v * t)), by - a.shape[0] + bob)
    n = crop(near, 400 + 175 * t); y0 = H - 250
    k = H - y0
    img[y0:] = img[y0:] * (1 - na[:k]) + n[:k] * na[:k]
    out = np.clip(img * (1 - fa) + frame * fa, 0, 255).astype(np.uint8)
    if only: cv2.imwrite(f'f_{i}.jpg', out)
    else: ff.stdin.write(out.tobytes())
if ff: ff.stdin.close(); ff.wait()
print('seconds', round(time.time() - t0, 1))
