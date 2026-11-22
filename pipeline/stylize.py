#!/usr/bin/env python3
"""Encode rendered frames into styled MP4s with the on-screen overlay.

One 3D render feeds every visual treatment; each style is a deterministic
ffmpeg filter chain (no per-frame AI, so nothing can morph or flicker).

Usage:
  python3 pipeline/stylize.py scenes/chicago_3d.json --frames work/frames/final/f_%04d.png
  python3 pipeline/stylize.py scenes/chicago_3d.json --frames ... --styles lofi
"""
import argparse
import json
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT_B = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FONT_R = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"

STYLES = {
    # the render as it comes out of Blender, lightly finished
    "clean": "eq=contrast=1.04:saturation=1.08",
    # v2 finish: gentle contrast, a touch of afternoon warmth, soft highlight roll-off, no tint
    "natural": ("curves=r='0/0 0.5/0.515 1/1':b='0/0 0.5/0.49 1/0.985',eq=contrast=1.05:saturation=1.10,"
                "split[a][b];[b]gblur=sigma=16[bl];[a][bl]blend=all_mode=screen:all_opacity=0.07,vignette=angle=PI/7"),
    # Style B - cinematic lo-fi: warm light, lifted soft blacks, bloom, vignette, fine grain
    # Option B - illustrated lo-fi: flattened colour fields, cool shadows / warm lights,
    # thin ink line, soft glow. Neutral white balance: no pink or orange cast.
    "illustrated": (
        "bilateral=sigmaS=5:sigmaR=0.07,"
        "curves=all='0/0.02 0.25/0.23 0.5/0.52 0.75/0.79 1/0.98',eq=saturation=1.28,"
        "colorbalance=rs=-0.03:bs=0.05:rh=0.035:bh=-0.03,"
        "split[a][b];[b]format=gray,gblur=sigma=0.9,edgedetect=low=0.07:high=0.18,negate,format=gbrp[e];"
        "[a]format=gbrp[a2];[a2][e]blend=all_mode=multiply:all_opacity=0.38,"
        "split[c][d];[d]gblur=sigma=18[g];[c][g]blend=all_mode=screen:all_opacity=0.10,vignette=angle=PI/7"
    ),
    "lofi": (
        "curves=r='0/0.045 0.5/0.55 1/1':g='0/0.04 0.5/0.51 1/0.96':b='0/0.035 0.5/0.42 1/0.80',"
        "eq=contrast=1.05:saturation=1.05,"
        "split[a][b];[b]gblur=sigma=20[bl];[a][bl]blend=all_mode=screen:all_opacity=0.16,"
        "eq=brightness=-0.03,vignette=angle=PI/6,noise=alls=3:allf=t"
    ),
    # Style C - anime/realism hybrid: flattened colour fields, saturated palette, ink outlines
    "anime": (
        "bilateral=sigmaS=6:sigmaR=0.08,"
        "curves=all='0/0 0.3/0.26 0.7/0.72 1/0.97',eq=saturation=1.5:contrast=1.06,"
        "colorbalance=bs=0.05:bm=0.02:rh=0.02,"
        "split[a][b];[b]format=gray,gblur=sigma=0.7,edgedetect=low=0.05:high=0.14,negate,format=gbrp[e];"
        "[a]format=gbrp[a2];[a2][e]blend=all_mode=multiply:all_opacity=0.8"
    ),
}


def overlay(scene, dur):
    o = scene["overlay"]

    def esc(t):
        return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "").replace(",", "\\,")

    k = o.get("scale", 1.0)            # 1.0 = original small size; 1.5 reads on a phone
    x, y = o.get("x", 150), o.get("y", 806)
    f1, f2 = int(30 * k), int(22 * k)
    w = int(o.get("box_w", 452) * k)
    common = "shadowcolor=black@0.55:shadowx=0:shadowy=2"
    rem = f"max(0\\,ceil({dur}-t))"
    count = (f"%{{eif\\:floor({rem}/60)\\:d\\:2}}\\:%{{eif\\:mod({rem}\\,60)\\:d\\:2}}")
    return ",".join([
        f"drawbox=x={x - int(22 * k)}:y={y - int(18 * k)}:w={w}:h={int(132 * k)}:color=black@0.38:t=fill",
        f"drawtext=fontfile={FONT_B}:text='{esc(o['title'].upper())}':fontsize={f1}:fontcolor=white@0.96:{common}:x={x}:y={y}",
        f"drawtext=fontfile={FONT_R}:text='{esc('Next destination: ' + o['next'])}':fontsize={f2}:fontcolor=white@0.9:{common}:x={x}:y={y + int(44 * k)}",
        f"drawtext=fontfile={FONT_R}:text='Next journey in {count}':fontsize={f2}:fontcolor=white@0.9:{common}:x={x}:y={y + int(74 * k)}",
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--frames", required=True, help="printf pattern, e.g. work/frames/final/f_%%04d.png")
    ap.add_argument("--styles", default="clean,lofi,anime")
    ap.add_argument("--outdir", default="output")
    ap.add_argument("--limit", type=int, help="only encode the first N frames")
    ap.add_argument("--still", help="write one styled PNG of the first frame here instead of a video")
    ap.add_argument("--start-number", type=int, default=0)
    a = ap.parse_args()
    scene = json.loads(pathlib.Path(a.scene).read_text())
    fps = scene["render"]["fps"]
    n = a.limit or len(list(pathlib.Path(a.frames).parent.glob(pathlib.Path(a.frames).name.split("%")[0] + "*.png")))
    dur = n / fps
    fade = scene.get("fade", 1.0)
    out_dir = ROOT / a.outdir
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for style in a.styles.split(","):
        out = out_dir / f"{scene['id']}_{style}.mp4"
        graph = (f"[0:v]{STYLES[style]},format=yuv420p,{overlay(scene, dur)},"
                 f"fade=t=in:st=0:d={fade},fade=t=out:st={dur - fade}:d={fade}[v]")
        if a.still:
            g2 = f"[0:v]{STYLES[style]},format=yuv420p,{overlay(scene, scene['camera']['duration_s'])}[v]"
            dest = a.still.replace("{style}", style)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-start_number", str(a.start_number),
                            "-i", a.frames, "-frames:v", "1", "-filter_complex", g2, "-map", "[v]", dest], check=True)
            print("still", dest)
            continue
        t0 = time.time()
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(fps), "-start_number", str(a.start_number), "-i", a.frames,
             "-frames:v", str(n), "-filter_complex", graph, "-map", "[v]",
             "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high", "-pix_fmt", "yuv420p",
             "-r", str(fps), "-g", str(fps * 2), "-movflags", "+faststart",
             "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(out)], check=True)
        report[style] = {"file": str(out.relative_to(ROOT)), "bytes": out.stat().st_size,
                         "encode_s": round(time.time() - t0, 1), "frames": n, "duration_s": dur}
        print(style, report[style], flush=True)
    (out_dir / f"{scene['id']}_encode.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
