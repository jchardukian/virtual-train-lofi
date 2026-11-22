import cv2, numpy as np, json
def key(path):
    im = cv2.imread(path).astype(np.float32)
    g = im[..., 1] - np.maximum(im[..., 0], im[..., 2])
    a = 1 - np.clip((g - 35) / 60, 0, 1)
    a = cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8)), (0, 0), 0.8)
    im[..., 1] = np.where(a < 0.999, np.minimum(im[..., 1], np.maximum(im[..., 0], im[..., 2]) * 1.04), im[..., 1])   # de-spill
    return np.dstack([im, a * 255]).astype(np.uint8)
def runs(mask, gap):
    idx = np.where(mask)[0]; out = []; s = p = idx[0]
    for i in idx[1:]:
        if i - p > gap: out.append((s, p)); s = i
        p = i
    out.append((s, p)); return out
inv = {}
for sheet in ('loop', 'lake', 'hood', 'edge'):
    rgba = key(sheet + '.png'); a = rgba[..., 3] > 128
    inv[sheet] = []
    for i, (x0, x1) in enumerate(r for r in runs(a.any(0), 6) if r[1] - r[0] > 25):
        ys = np.where(a[:, x0:x1 + 1].any(1))[0]
        s = rgba[max(0, ys[0] - 3):ys[-1] + 2, max(0, x0 - 3):x1 + 4]
        cv2.imwrite(f'sprites/{sheet}_{i}.png', s); inv[sheet].append([s.shape[1], s.shape[0]])
rgba = key('strips.png'); a = rgba[..., 3] > 128
inv['strips'] = []
for i, (y0, y1) in enumerate(r for r in runs(a.mean(1) > 0.25, 4) if r[1] - r[0] > 30):
    ys0 = max(0, y0 - 60)                                        # keep treetops and poles that rise above the dense part
    while ys0 < y0 and not a[ys0].any(): ys0 += 1
    s = rgba[ys0:y1 + 1]; cv2.imwrite(f'sprites/strip_{i}.png', s); inv['strips'].append([s.shape[1], s.shape[0], int(ys0), int(y1)])
rgba = key('skyline.png'); a = rgba[..., 3] > 128; ys = np.where(a.any(1))[0]
cv2.imwrite('sprites/skyline.png', rgba[ys[0] - 2:ys[-1] + 1]); inv['skyline'] = [rgba.shape[1], int(ys[-1] - ys[0])]
json.dump(inv, open('sprites/inventory.json', 'w'), indent=1); print(json.dumps(inv))
cells = []
import glob
for f in sorted(glob.glob('sprites/[lhe]*_*.png')):
    v = cv2.imread(f, cv2.IMREAD_UNCHANGED); h = 200; w = max(1, int(v.shape[1] * h / v.shape[0])); r = cv2.resize(v, (w, h)); al = r[..., 3:] / 255.0
    c = (r[..., :3] * al + np.array([255, 0, 255]) * (1 - al)).astype(np.uint8); cv2.putText(c, f.split('/')[1][:-4], (2, 14), 0, 0.4, (0, 0, 0), 1); cells.append(c)
row1 = np.hstack(cells[:len(cells) // 2]); row2 = np.hstack(cells[len(cells) // 2:]); w = max(row1.shape[1], row2.shape[1])
pad = lambda r: np.hstack([r, np.full((200, w - r.shape[1], 3), 255, np.uint8)])
cv2.imwrite('sprites/sheet.jpg', np.vstack([pad(row1), pad(row2)]))
