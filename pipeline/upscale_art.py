#!/usr/bin/env python3
"""Upscale a city's artwork 2x for 4K renders, on this machine (free; no image API).

  python3 pipeline/upscale_art.py <city> [--model path] [--threads 4]

Every layer the city's settings use (except the sky, which is a soft gradient, and the treewall,
which is blurred anyway) is enlarged 4x with Real-ESRGAN x4plus and brought back down to 2x,
which keeps the painted texture while sharpening edges. Output mirrors work/cities_v3/<city>/...
under work/cities_x2/<city>/...; the renderer picks those files up when RENDER_SCALE=2.
Transparent pixels are filled from their neighbours first so cut-out edges get no colour fringe,
and fully transparent tiles are skipped.
"""
import argparse, json, pathlib, sys, time
import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODEL = ROOT / "work/models/RealESRGAN_x4plus.pth"
TILE, PAD = 256, 12


def sources(city):
    cfg = json.loads((ROOT / f"cities/illustrated/{city}.json").read_text())
    found = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "src" and isinstance(v, str) and v.startswith("work/cities_v3/"):
                    found.add(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(cfg)
    found.discard(cfg.get("treewall_cfg", {}).get("src"))
    found.discard(cfg.get("sky"))
    return sorted(found)


def fill_transparent(rgb, a):
    """give fully transparent pixels the colour of the nearest visible ones (normalised blur), so no key colour bleeds in"""
    out, filled = rgb.copy(), a >= 0.02
    for s in (2, 6, 18, 54, 160):
        wv = filled.astype(np.float32)
        bw = cv2.GaussianBlur(wv, (0, 0), s)
        ba = cv2.GaussianBlur(out * wv[..., None], (0, 0), s)
        m = ~filled & (bw > 1e-3)
        out[m] = ba[m] / bw[m][:, None]
        filled |= m
    return out


def upscale(model, torch, rgb, a):
    H, W = a.shape
    x = torch.from_numpy(np.ascontiguousarray(rgb[..., ::-1].transpose(2, 0, 1)))[None]   # BGR -> RGB
    y = np.zeros((H * 4, W * 4, 3), np.float32)
    with torch.no_grad():
        for i in range(0, H, TILE):
            for j in range(0, W, TILE):
                i0, j0, i1, j1 = max(0, i - PAD), max(0, j - PAD), min(H, i + TILE + PAD), min(W, j + TILE + PAD)
                ie, je = min(H, i + TILE), min(W, j + TILE)
                if a[i0:i1, j0:j1].max() < 0.01:
                    continue
                r = model(x[:, :, i0:i1, j0:j1]).clamp(0, 1)[0].numpy().transpose(1, 2, 0)
                y[i * 4:ie * 4, j * 4:je * 4] = r[(i - i0) * 4:(ie - i0) * 4, (j - j0) * 4:(je - j0) * 4]
    y = cv2.resize(y[..., ::-1], (W * 2, H * 2), interpolation=cv2.INTER_AREA)
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("city")
    ap.add_argument("--model", default=str(MODEL))
    ap.add_argument("--threads", type=int, default=4)
    a = ap.parse_args()
    import torch
    from spandrel import ModelLoader
    torch.set_num_threads(a.threads)
    model = ModelLoader().load_from_file(a.model).eval()
    t0 = time.time()
    for src in sources(a.city):
        dst = ROOT / "work/cities_x2" / src[len("work/cities_v3/"):]
        srcp = ROOT / src
        if dst.exists() and dst.stat().st_mtime > srcp.stat().st_mtime:
            continue
        im = cv2.imread(str(srcp), cv2.IMREAD_UNCHANGED)
        if im.ndim == 2:
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGR)
        rgb = im[..., :3].astype(np.float32) / 255
        alpha = im[..., 3].astype(np.float32) / 255 if im.shape[2] == 4 else np.ones(im.shape[:2], np.float32)
        if im.shape[2] == 4:
            rgb = fill_transparent(rgb, alpha)
        up = upscale(model, torch, rgb, alpha)
        out = np.clip(up * 255 + 0.5, 0, 255).astype(np.uint8)
        if im.shape[2] == 4:
            a2 = cv2.resize(im[..., 3], (im.shape[1] * 2, im.shape[0] * 2), interpolation=cv2.INTER_LANCZOS4)
            out = np.dstack([out, a2])
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp.png")
        cv2.imwrite(str(tmp), out)
        tmp.replace(dst)                          # never leave a half-written file the renderer could pick up
        print(f"  {src} {im.shape[1]}x{im.shape[0]} -> 2x", flush=True)
    print(f"{a.city} art upscaled in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    sys.exit(main())
