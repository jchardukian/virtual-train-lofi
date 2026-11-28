#!/usr/bin/env python3
"""Render a train-window segment from real source footage.

Reads a scene JSON (see scenes/chicago.json) and produces a 1920x1080,
30 fps, H.264 MP4: trim -> two-pass stabilise -> crop -> grade -> label ->
fades -> encode. Everything is ffmpeg on CPU; no GPU or paid service.

Usage:
  python3 pipeline/render.py scenes/chicago.json --preview
  python3 pipeline/render.py scenes/chicago.json
  python3 pipeline/render.py scenes/chicago.json --start 60 --duration 20 --out output/x.mp4
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/inter/Inter-Medium.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def run(cmd):
    print("+", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--preview", action="store_true", help="render the scene's short preview window")
    ap.add_argument("--start", type=float)
    ap.add_argument("--duration", type=float)
    ap.add_argument("--out")
    ap.add_argument("--no-label", action="store_true")
    a = ap.parse_args()

    scene = json.loads(pathlib.Path(a.scene).read_text())
    src = ROOT / scene["source"]["local_path"]
    if not src.exists():
        sys.exit(f"missing source footage {src}; run pipeline/fetch_source.py {a.scene}")

    if a.preview:
        start, dur, tag = scene["preview"]["start"], scene["preview"]["duration"], "preview"
    else:
        start, dur, tag = scene["start"], scene["duration"], "full"
    if a.start is not None:
        start, tag = a.start, "custom"
    if a.duration is not None:
        dur, tag = a.duration, "custom"

    o = scene["output"]
    out = pathlib.Path(a.out) if a.out else ROOT / "output" / f"{scene['id']}_{tag}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    fps = o["fps"]
    st = scene.get("stabilize", {})
    ww, wh = st.get("work_width", 2560), st.get("work_height", 1440)

    # Shared head of the filter chain. Stabilisation runs at a working
    # resolution above 1080p so the stabiliser's zoom-crop never upscales.
    head = [f"fps={fps}"]
    c = scene.get("pre_crop")  # optional crop in source pixels: w:h:x:y
    if c:
        head.append(f"crop={c}")
    head.append(f"scale={ww}:{wh}:flags=bicubic")

    seek = ["-ss", f"{start}", "-t", f"{dur}", "-i", str(src)]
    t0 = time.time()
    chain = list(head)
    if st.get("enabled", True):
        trf = work / f"{scene['id']}_{tag}.trf"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y", *seek, "-an", "-vf",
             ",".join(head + [
                 f"vidstabdetect=shakiness={st.get('shakiness', 6)}:accuracy=15:stepsize=6:"
                 f"mincontrast=0.25:result={trf}"]),
             "-f", "null", "-"])
        chain.append(
            f"vidstabtransform=input={trf}:smoothing={st.get('smoothing', 45)}:"
            f"optzoom=0:zoom={st.get('zoom_percent', 6)}:crop=black:interpol=bicubic:"
            f"maxangle={st.get('max_angle', 0.05)}")
    t_detect = time.time() - t0

    chain.append(f"scale={o['width']}:{o['height']}:flags=lanczos")
    g = scene.get("grade", {})
    if g:
        chain.append(f"eq=contrast={g.get('contrast', 1)}:saturation={g.get('saturation', 1)}:"
                     f"gamma={g.get('gamma', 1)}:brightness={g.get('brightness', 0)}")
    if scene.get("sharpen"):
        chain.append(f"unsharp=5:5:{scene['sharpen']}:5:5:0")
    if scene.get("label") and not a.no_label:
        font = next((f for f in FONT_CANDIDATES if pathlib.Path(f).exists()), None)
        if not font:
            sys.exit("no label font found; install fonts-inter or fonts-dejavu")
        text = scene["label"].replace(":", r"\:").replace(",", r"\,")
        # Small, bottom-left, inside the YouTube title-safe area.
        chain.append(
            f"drawtext=fontfile={font}:text='{text}':fontsize=30:fontcolor=white@0.88:"
            f"shadowcolor=black@0.55:shadowx=0:shadowy=2:x=64:y=h-th-56")
    fade = scene.get("fade", 1.5)
    if fade:
        chain += [f"fade=t=in:st=0:d={fade}", f"fade=t=out:st={dur - fade}:d={fade}"]
    chain.append("format=yuv420p")

    t1 = time.time()
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-stats", "-y", *seek, "-an",
         "-vf", ",".join(chain),
         "-c:v", "libx264", "-preset", o.get("preset", "slow"), "-crf", str(o.get("crf", 18)),
         "-profile:v", "high", "-level", "4.2", "-r", str(fps), "-g", str(fps * 2),
         "-movflags", "+faststart", "-color_primaries", "bt709", "-color_trc", "bt709",
         "-colorspace", "bt709", str(out)])
    t_encode = time.time() - t1

    stats = {
        "scene": scene["id"], "mode": tag, "start_s": start, "duration_s": dur,
        "output": str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
        "output_bytes": out.stat().st_size,
        "stabilise_analysis_s": round(t_detect, 1), "transform_encode_s": round(t_encode, 1),
        "total_s": round(time.time() - t0, 1),
        "realtime_factor": round((time.time() - t0) / dur, 2),
        "ffmpeg": shutil.which("ffmpeg"),
    }
    out.with_suffix(".render.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
