#!/usr/bin/env python3
"""Cut a sample from real footage: trim, crossfade, subtle lo-fi grade, overlay.

No stabilisation and no cropping: the listed sources are tripod-steady.
Sources that need stabilising go through pipeline/render.py instead.

Usage: python3 pipeline/footage_sample.py scenes/chicago_footage_pexels.json
"""
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stylize import overlay  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
# gentle: slightly lifted blacks, a little warmth in the highlights, soft glow, fine grain
GRADE = ("curves=r='0/0.02 0.5/0.51 1/1':g='0/0.02 0.5/0.50 1/0.985':b='0/0.03 0.5/0.49 1/0.96',"
         "eq=contrast=1.03:saturation=1.06,"
         "split[ga][gb];[gb]gblur=sigma=18[gl];[ga][gl]blend=all_mode=screen:all_opacity=0.08,"
         "vignette=angle=PI/7,noise=alls=2:allf=t")


def main():
    scene = json.loads(pathlib.Path(sys.argv[1]).read_text())
    fps, xf, fade = scene["render"]["fps"], scene["crossfade"], scene["fade"]
    src = scene["sources"]
    total = sum(s["duration"] for s in src) - xf * (len(src) - 1)
    inputs, parts = [], []
    for i, s in enumerate(src):
        path = ROOT / s["local_path"]
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(["curl", "-s", "-L", "-A", "Mozilla/5.0", "-o", str(path), s["download_url"]], check=True)
        inputs += ["-ss", str(s["start"]), "-t", str(s["duration"]), "-i", str(path)]
        parts.append(f"[{i}:v]fps={fps},scale=1920:1080:flags=lanczos,setsar=1,format=yuv420p[v{i}]")
    cur, offset = "v0", 0.0
    for i in range(1, len(src)):
        offset += src[i - 1]["duration"] - xf
        parts.append(f"[{cur}][v{i}]xfade=transition=fade:duration={xf}:offset={offset}[x{i}]")
        cur = f"x{i}"
    parts.append(f"[{cur}]{GRADE},format=yuv420p,{overlay(scene, total)},"
                 f"fade=t=in:st=0:d={fade},fade=t=out:st={total - fade}:d={fade}[v]")
    out = ROOT / "output" / f"{scene['id']}_sample.mp4"
    out.parent.mkdir(exist_ok=True)
    t0 = time.time()
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(parts),
                    "-map", "[v]", "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
                    "-r", str(fps), "-movflags", "+faststart", str(out)], check=True)
    print(json.dumps({"file": str(out.relative_to(ROOT)), "bytes": out.stat().st_size,
                      "duration_s": total, "process_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
