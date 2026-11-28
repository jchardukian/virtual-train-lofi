#!/usr/bin/env python3
"""Pick a stream thumbnail automatically and set it on a broadcast (owner 2026-11-26: custom thumbnails, never manual).
  python3 pipeline/stream_thumbnail.py <video.mp4> <broadcast_id> [--out thumb.jpg]
Samples ~40 frames away from tunnels/cards, scores colour + detail + brightness, crops the best to 1280x720 with a small
'LIVE 🚆' badge, uploads it via thumbnails.set."""
import argparse, subprocess, sys, pathlib, json
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
F = "/usr/share/fonts/opentype/inter/"

def frames(video, n=40):
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                             capture_output=True, text=True).stdout)
    for i in range(n):
        t = d * (i + 0.5) / n
        b = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.1f}", "-i", video, "-frames:v", "1", "-f", "image2pipe",
                            "-vcodec", "png", "-"], capture_output=True).stdout
        im = cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_COLOR)
        if im is not None:
            yield t, im

def score(im):
    h, w = im.shape[:2]
    c = im[int(h * .08):int(h * .92), int(w * .1):int(w * .9)]
    hsv = cv2.cvtColor(c, cv2.COLOR_BGR2HSV).astype(np.float32)
    sat, val = hsv[..., 1].mean() / 255, hsv[..., 2].mean() / 255
    detail = cv2.Laplacian(cv2.cvtColor(c, cv2.COLOR_BGR2GRAY), cv2.CV_32F).var()
    if val < 0.25:                                  # tunnel / dark frame
        return -1
    return sat * 1.5 + min(detail / 400, 1.5) + (0.4 - abs(val - 0.6))

def make(video, out):
    best = max(frames(video), key=lambda x: score(x[1]))
    im = cv2.resize(best[1], (1280, 720), interpolation=cv2.INTER_AREA)
    pil = Image.fromarray(cv2.cvtColor(im, cv2.COLOR_BGR2RGB)).convert("RGBA")
    ov = Image.new("RGBA", pil.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    f = ImageFont.truetype(F + "InterDisplay-SemiBold.otf", 46)
    d.rounded_rectangle((1060, 36, 1244, 104), radius=18, fill=(220, 30, 40, 235))
    d.text((1082, 44), "LIVE", font=f, fill=(255, 255, 255, 255))
    Image.alpha_composite(pil, ov).convert("RGB").save(out, quality=92)
    return best[0]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("broadcast"); ap.add_argument("--out", default="/tmp/stream_thumb.jpg")
    a = ap.parse_args()
    t = make(a.video, a.out)
    from youtube_upload import API, access_token, call
    call("POST", f"{API}/upload/youtube/v3/thumbnails/set?videoId={a.broadcast}", access_token(),
         data=open(a.out, "rb").read(), headers={"Content-Type": "image/jpeg"})
    print(json.dumps({"broadcast": a.broadcast, "frame_at_s": round(t, 1), "thumbnail": a.out}))

if __name__ == "__main__":
    main()
