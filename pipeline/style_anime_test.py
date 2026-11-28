import sys, time, json, subprocess, pathlib
import cv2, numpy as np
sys.path.insert(0, 'pipeline'); import fast_shot as F

def sky_layer(H, W, t):
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    top, mid, hor = np.array([196, 142, 98.]), np.array([214, 178, 150.]), np.array([186, 214, 255.])   # BGR: blue -> lilac -> peach
    a = np.clip(y / 0.42, 0, 1); b = np.clip((y - 0.25) / 0.45, 0, 1)
    g = (top * (1 - a[..., None]) + mid * a[..., None]) * (1 - b[..., None]) + hor * b[..., None]
    return np.repeat(g, W, axis=1).astype(np.float32)

def stylise(img, depth, base_sky):
    H, W = depth.shape
    im = img.astype(np.float32)
    sky = depth > 60000
    # flat, painted colour fields
    small = cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    small = cv2.bilateralFilter(small, 7, 26, 5)
    flat = cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC).astype(np.float32)
    im = flat
    # sunset sky: gradient, original clouds kept as warm cream shapes
    lum = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    blue = img[..., 0].astype(np.float32) - img[..., 2].astype(np.float32)
    cloud = np.clip((lum - 0.62) / 0.2, 0, 1) * np.clip(1 - blue / 70, 0, 1)
    cloud = cv2.GaussianBlur(cloud, (0, 0), 3)
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    ccol = np.array([205, 222, 255.]) * (1 - 0.25 * y[..., None]) + np.array([150, 150, 235.]) * 0.25 * y[..., None]
    skyc = base_sky * (1 - cloud[..., None]) + ccol * cloud[..., None]
    sm = cv2.GaussianBlur(sky.astype(np.float32), (0, 0), 1.2)[..., None]
    # golden-hour grade on the world: warm lights, violet-teal shadows, richer colour
    g = im / 255
    L = (0.114 * g[..., 0] + 0.587 * g[..., 1] + 0.299 * g[..., 2])[..., None]
    g = L + (g - L) * 1.55
    warm, cool = np.array([0.80, 0.93, 1.10]), np.array([1.10, 0.92, 0.98])
    g = g * (cool * (1 - L) + warm * L)
    g = np.clip(g, 0, 1)
    g = g * g * (3 - 2 * g) * 0.55 + g * 0.45          # gentle S-curve for punch
    g = g ** 0.78
    hsv = cv2.cvtColor((g * 255).clip(0, 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float32)
    green = (np.abs(hsv[..., 0] - 55) < 28) & (hsv[..., 1] > 60)             # foliage and grass: deeper teal-green, more saturated
    hsv[..., 0] = np.where(green, hsv[..., 0] + 9, hsv[..., 0]); hsv[..., 1] = np.where(green, np.minimum(hsv[..., 1] * 1.25, 255), hsv[..., 1])
    g = cv2.cvtColor(hsv.clip(0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    # warm atmospheric haze with distance
    hz = (1 - np.exp(-np.maximum(np.minimum(depth, 4000) - 120, 0) / 1600.0))[..., None] * 0.42
    g = g * (1 - hz) + np.array([190, 205, 255.]) * hz
    out = g * (1 - sm) + skyc * sm
    # ink lines from real depth edges (clean, no texture noise) plus strong colour edges
    ld = np.log(np.minimum(depth, 5000) + 1).astype(np.float32)
    e = cv2.morphologyEx(ld, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    line = np.clip((e - 0.045) / 0.05, 0, 1)
    ce = cv2.Canny(cv2.cvtColor(flat.astype(np.uint8), cv2.COLOR_BGR2GRAY), 60, 140).astype(np.float32) / 255
    line = np.maximum(line, ce * 0.45) * np.clip(1.3 - depth / 900.0, 0.25, 1)
    line = cv2.GaussianBlur(line, (0, 0), 0.8)[..., None]
    out = out * (1 - 0.7 * line) + np.array([70, 40, 60.]) * 0.7 * line
    return out

def finish(img):
    # warm bloom and a gentle vignette over the whole picture, carriage included
    bl = cv2.GaussianBlur(img, (0, 0), 22)
    out = 255 - (255 - img) * (255 - bl * 0.22) / 255
    H, W = out.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - 0.22 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    return out * v[..., None]

if __name__ == '__main__':
    f0, f1 = int(sys.argv[1]), int(sys.argv[2]); mode = sys.argv[3]; outdir = pathlib.Path(sys.argv[4]); outdir.mkdir(parents=True, exist_ok=True)
    sh = F.Shot('work/fast/riverfront', 30)
    rgba = cv2.imread('work/fast/riverfront/carriage_0000.png', cv2.IMREAD_UNCHANGED).astype(np.float32)
    al = rgba[..., 3:] / 255
    car = rgba[..., :3]
    carB = car * np.array([0.86, 0.95, 1.08])                                   # cabin picks up the warm light
    base_sky = sky_layer(sh.H, sh.W, 0)
    tA = tB = 0.0
    for f in range(f0, f1 + 1):
        t = time.time(); img, _ = sh.frame(f); d = sh.last_depth.copy(); tA += time.time() - t
        cv2.imwrite(str(outdir / f'a_{f:04d}.png'), np.clip(img * (1 - al) + car * al, 0, 255).astype(np.uint8))
        t = time.time()
        b = stylise(img, np.where(np.isfinite(d), d, 65504).astype(np.float32), base_sky)
        b = finish(np.clip(b * (1 - al) + carB * al, 0, 255))
        cv2.imwrite(str(outdir / f'b_{f:04d}.jpg'), np.clip(b, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 96]); tB += time.time() - t
    print(json.dumps({'frames': f1 - f0 + 1, 'synth_s': round(tA, 1), 'style_s': round(tB, 1)}))
