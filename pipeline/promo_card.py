#!/usr/bin/env python3
"""The 'Departing daily' card (owner-approved 2026-11-26), burned into the UPLOADED copy only.

  python3 pipeline/promo_card.py <in.mp4> <out.mp4>          # long-form: card in the last 10 s
  python3 pipeline/promo_card.py <in.mp4> <out.mp4> --short  # Short: card in the last 4 s, above YouTube's caption area

The built city files stay clean: livestreams reuse them, and a card every 5 minutes mid-stream would be odd.
A small dark rounded panel, bottom-left, fades in and out:  ● Departing daily / Live train rides ... 24/7 on this channel
"""
import json, pathlib, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/opentype/inter/Inter-%s.otf"
TITLE = "Departing daily"
SUB_LONG = "Live train rides around the world, 24/7 on this channel"
SUB_SHORT = "Live train rides, 24/7 on this channel"


def font(weight, size):
    try:
        return ImageFont.truetype(FONT % weight, size)
    except OSError:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)


def card(w, h, short):
    """full-frame RGBA overlay, drawn at the video's own resolution"""
    k = (w / 1080) if short else (w / 1920)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ft, fs = font("Bold", int((56 if short else 46) * k)), font("Medium", int((36 if short else 32) * k))
    sub = SUB_SHORT if short else SUB_LONG
    pad, dot = int(28 * k), (0 if short else int(50 * k))
    tw = max(d.textlength(TITLE, font=ft), d.textlength(sub, font=fs))
    bw, bh = int(tw + dot + pad * 2.6), int((170 if short else 150) * k)
    if short:
        x0, y0 = (w - bw) // 2, int(h * 0.70)              # above the title/caption/buttons YouTube draws on Shorts
    else:
        x0, y0 = int(235 * k), int(790 * k)               # inside the window, clear of the frame's lower-left corner
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), int(28 * k), fill=(20, 16, 30, 175))
    tx = x0 + pad + (dot + int(22 * k) if dot else 0)
    if dot:
        cy = y0 + bh // 2
        d.ellipse((x0 + pad, cy - dot // 2, x0 + pad + dot, cy + dot // 2), fill=(235, 80, 70, 255))
        r = dot // 5
        d.ellipse((x0 + pad + dot // 2 - r, cy - r, x0 + pad + dot // 2 + r, cy + r), fill=(255, 255, 255, 255))
    d.text((tx, y0 + int(22 * k)), TITLE, font=ft, fill=(255, 236, 200, 255))
    d.text((tx, y0 + int((92 if short else 86) * k)), sub, font=fs, fill=(255, 255, 255, 255))
    return im


def probe(p):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:format=duration", "-of", "json", str(p)],
                                  capture_output=True, text=True, check=True).stdout)
    return j["streams"][0]["width"], j["streams"][0]["height"], float(j["format"]["duration"])


def apply(src, dst, short=False):
    w, h, dur = probe(src)
    span = 4.0 if short else 10.0
    st = max(0.0, dur - span)
    with tempfile.TemporaryDirectory() as td:
        png = pathlib.Path(td) / "card.png"
        card(w, h, short).save(png)
        fx = (f"[1:v]format=rgba,fade=t=in:st={st:.2f}:d=0.8:alpha=1,fade=t=out:st={dur - 0.9:.2f}:d=0.8:alpha=1[c];"
              f"[0:v][c]overlay=0:0:shortest=1:enable='gte(t,{st:.2f})'[v]")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-loop", "1", "-framerate", "30", "-i", str(png),
                        "-filter_complex", fx, "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "16" if not short else "18", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
                        "-t", f"{dur:.3f}", str(dst)], check=True)
    w2, h2, d2 = probe(dst)
    if (w2, h2) != (w, h) or abs(d2 - dur) > 0.2:
        sys.exit(f"card version differs: {w2}x{h2} {d2:.2f}s vs {w}x{h} {dur:.2f}s")
    return dst


if __name__ == "__main__":
    apply(sys.argv[1], sys.argv[2], "--short" in sys.argv)
    print("ok", sys.argv[2])
