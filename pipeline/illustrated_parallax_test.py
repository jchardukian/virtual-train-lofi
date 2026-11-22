import cv2, numpy as np, subprocess, sys, time
W, H, FPS, N = 1920, 1080, 30, 300
t0 = time.time()
scene = cv2.resize(cv2.imread('scene.png'), (2304, 1536), interpolation=cv2.INTER_LANCZOS4)
SH, SW = scene.shape[:2]

# --- sky mask (GrabCut seeded from the top band and the lower half)
small = cv2.resize(scene, (576, 384))
m = np.full(small.shape[:2], cv2.GC_PR_FGD, np.uint8)
hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
m[:150][(hsv[:150, :, 2] > 175) & (hsv[:150, :, 1] < 150)] = cv2.GC_PR_BGD
m[:26, 140:330] = cv2.GC_BGD
m[200:] = cv2.GC_FGD
cv2.grabCut(small, m, None, np.zeros((1, 65)), np.zeros((1, 65)), 4, cv2.GC_INIT_WITH_MASK)
sky = ((m == cv2.GC_BGD) | (m == cv2.GC_PR_BGD)).astype(np.uint8)
sky = cv2.morphologyEx(sky, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
sky = cv2.GaussianBlur(cv2.resize(sky.astype(np.float32), (SW, SH)), (0, 0), 2.5)
cv2.imwrite('dbg_sky.jpg', (cv2.resize(sky, (768, 512)) * 255).astype(np.uint8))
# sky plate with the city painted out, so it can drift on its own behind the buildings
hole = (sky < 0.6).astype(np.uint8)
s4 = cv2.resize(scene, (SW // 4, SH // 4)); h4 = cv2.dilate(cv2.resize(hole, (SW // 4, SH // 4)), np.ones((5, 5), np.uint8))
skyplate = cv2.resize(cv2.inpaint(s4, h4, 6, cv2.INPAINT_TELEA), (SW, SH), interpolation=cv2.INTER_CUBIC)
skyplate = np.where(hole[..., None] > 0, cv2.GaussianBlur(skyplate, (0, 0), 6), scene)

# --- parallax field: far skyline (around the vanishing point) barely moves, nearer things move more
ys, xs = np.mgrid[0:SH, 0:SW].astype(np.float32)
vx, vy = 0.42 * SW, 0.50 * SH
r = np.sqrt(((xs - vx) / SW * 1.7) ** 2 + (np.maximum(ys - vy, 0) / SH * 2.4) ** 2 + (np.minimum(ys - vy, 0) / SH * 0.5) ** 2)
P = cv2.GaussianBlur(np.clip(0.16 + 1.25 * r, 0.16, 1.0), (0, 0), 40)

# --- water mask for shimmer (teal river)
hs = cv2.cvtColor(scene, cv2.COLOR_BGR2HSV)
water = ((hs[..., 0] > 70) & (hs[..., 0] < 100) & (hs[..., 1] > 70) & (ys > 0.55 * SH)).astype(np.float32)
water = cv2.GaussianBlur(water, (0, 0), 6)

def key(path, w):
    im = cv2.imread(path); im = cv2.resize(im, (w, int(im.shape[0] * w / im.shape[1])), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
    g = im[..., 1] - np.maximum(im[..., 0], im[..., 2])
    a = 1 - np.clip((g - 40) / 70, 0, 1)
    a = cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8)), (0, 0), 1.0)
    spill = np.minimum(im[..., 1], np.maximum(im[..., 0], im[..., 2]) * 1.05)      # take the green cast off the edges
    im[..., 1] = np.where(a < 0.999, spill, im[..., 1])
    return im, a[..., None]

frame, fa = key('frame.png', W)                       # 1920 x 1280
fy = (frame.shape[0] - H) // 2 + 20
frame, fa = frame[fy:fy + H], fa[fy:fy + H]
fg, ga = key('fg.png', 2700)                          # wide foreground strip, 1800 tall
fg, ga = fg[-1150:], ga[-1150:]
fgb, gab = cv2.blur(fg * ga, (13, 1)), cv2.blur(ga, (13, 1))[..., None]   # near foliage is soft and motion-blurred

ff = subprocess.Popen(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS),
                       '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', sys.argv[1]], stdin=subprocess.PIPE)
X0, Y0 = (SW - W) // 2, 250
gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
Pv, wv, skv = P[Y0:Y0 + H, X0:X0 + W], water[Y0:Y0 + H, X0:X0 + W], sky[Y0:Y0 + H, X0:X0 + W]
only = int(sys.argv[2]) if len(sys.argv) > 2 else None
for i in ([only] if only is not None else range(N)):
    t = i / FPS
    u = t / 10 - 0.5                                             # -0.5 .. 0.5 across the clip
    bob = float(1.6 * np.sin(2 * np.pi * 0.9 * t) + 0.9 * np.sin(2 * np.pi * 2.3 * t + 1))
    shift = 330.0 * u                                            # how far the nearest scenery travels
    mx = X0 + gx + shift * Pv
    my = Y0 + gy + bob + wv * (1.6 * np.sin(gy * 0.21 + t * 3.1) + 1.1 * np.sin(gx * 0.05 - t * 2.2))   # ripples on the river
    mx, my = mx.astype(np.float32), my.astype(np.float32)
    city = cv2.remap(scene, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    img = city
    tw = 0.5 + 0.5 * np.sin(gx * 0.9 + gy * 1.3 + t * 9)          # sun sparkle on the water
    lum = img.mean(-1)
    img += (wv * np.clip((lum - 150) / 60, 0, 1) * tw * 38)[..., None]
    # foreground treetops sweep past, much faster than everything behind them
    fx = int(-250 + 1150 * (u + 0.5))
    crop = slice(fx, fx + W)
    yy = H - 780
    a = gab[:780, crop]; c = fgb[:780, crop]
    if a.shape[1] == W:
        img[yy:yy + 780] = img[yy:yy + 780] * (1 - a) + c
    out = img * (1 - fa) + frame * fa
    ff.stdin.write(np.clip(out, 0, 255).astype(np.uint8).tobytes())
    if only is not None:
        cv2.imwrite(f'dbg_{only}.jpg', np.clip(out, 0, 255).astype(np.uint8))
ff.stdin.close(); ff.wait()
print('seconds', round(time.time() - t0, 1))
