import cv2, numpy as np, json
S = cv2.imread('../illus/scene.png')            # 1536 x 1024
H, W = S.shape[:2]
def cut(name, x0, y0, x1, y1, fg=None, bg=None, pad=14, it=5):
    """GrabCut one object. fg/bg: lists of rectangles (in image coords) that are certainly object / certainly not."""
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    crop = S[Y0:Y1, X0:X1].copy()
    m = np.full(crop.shape[:2], cv2.GC_PR_BGD, np.uint8)
    m[y0 - Y0:y1 - Y0, x0 - X0:x1 - X0] = cv2.GC_PR_FGD
    b = 3
    m[:b] = m[-b:] = cv2.GC_BGD; m[:, :b] = cv2.GC_BGD; m[:, -b:] = cv2.GC_BGD
    for r in fg or []:
        m[r[1] - Y0:r[3] - Y0, r[0] - X0:r[2] - X0] = cv2.GC_FGD
    for r in bg or []:
        m[max(0, r[1] - Y0):r[3] - Y0, max(0, r[0] - X0):r[2] - X0] = cv2.GC_BGD
    cv2.grabCut(crop, m, None, np.zeros((1, 65)), np.zeros((1, 65)), it, cv2.GC_INIT_WITH_MASK)
    a = ((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD)).astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(a)
    if n > 1:
        a = (lab == 1 + np.argmax(st[1:, cv2.CC_STAT_AREA])).astype(np.uint8)
    a = cv2.morphologyEx(a, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    a = cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8)).astype(np.float32), (0, 0), 1.0)
    out = np.dstack([crop, (a * 255).astype(np.uint8)])
    cv2.imwrite(f'{name}.png', out)
    return out
sp = {}
sp['marina'] = cut('marina', 860, 60, 1132, 640, fg=[(900, 120, 1090, 520)], bg=[(1132, 60, 1150, 300), (1000, 60, 1020, 80)])
sp['brick'] = cut('brick', 1165, 245, 1420, 650, fg=[(1200, 320, 1380, 560)])
sp['glassL'] = cut('glassL', 0, 0, 325, 600, fg=[(20, 40, 280, 520)])
sp['glassR'] = cut('glassR', 1290, 0, 1536, 330, fg=[(1330, 20, 1520, 250)])
sp['house'] = cut('house', 352, 468, 470, 680, fg=[(372, 520, 450, 650)])
sp['bridge'] = cut('bridge', 455, 560, 1090, 740, fg=[(520, 610, 1040, 660)])
sp['tower'] = cut('tower', 590, 150, 680, 560, fg=[(610, 240, 660, 520)])
sp['deco'] = cut('deco', 320, 230, 470, 560, fg=[(345, 330, 440, 520)])
# sheet on magenta for inspection
cells = []
for k, v in sp.items():
    h = 360; w = int(v.shape[1] * h / v.shape[0]); r = cv2.resize(v, (w, h))
    a = r[..., 3:] / 255.0
    cells.append((r[..., :3] * a + np.array([255, 0, 255]) * (1 - a)).astype(np.uint8))
cv2.imwrite('sheet.jpg', np.hstack(cells))
