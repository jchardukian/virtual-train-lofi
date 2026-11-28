#!/usr/bin/env python3
"""Assemble a city journey from a clip list: trim, conform, crossfade, grade, overlay, music.

Usage: python3 pipeline/journey.py scenes/chicago_journey_v1.json [--out output/x.mp4]

Clips are conformed to 1920x1080 at the scene frame rate. Vertical phone
clips are cropped to a 16:9 window (and optionally stabilised first).
"""
import argparse
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from stylize import overlay  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
CAND = ROOT / "footage" / "candidates"
# subtle unifying finish: slightly lifted blacks, gentle warmth, soft glow, vignette, fine grain
GRADE = ("curves=r='0/0.02 0.5/0.51 1/1':g='0/0.02 0.5/0.50 1/0.985':b='0/0.03 0.5/0.49 1/0.96',"
         "eq=contrast=1.03:saturation=1.06,"
         "split[ga][gb];[gb]gblur=sigma=18[gl];[ga][gl]blend=all_mode=screen:all_opacity=0.08,"
         "vignette=angle=PI/7,noise=alls=2:allf=t")


def run(cmd):
    subprocess.run(cmd, check=True)


def stabilised(clip, fps):
    """Two-pass vidstab on the trimmed clip; returns the intermediate path."""
    work = ROOT / "work"
    work.mkdir(exist_ok=True)
    out = work / f"stab_{clip['src']}_{clip['start']}_{clip['duration']}.mp4"
    if out.exists():
        return out
    trf = out.with_suffix(".trf")
    seek = ["-ss", str(clip["start"]), "-t", str(clip["duration"] + 0.5), "-i", str(CAND / f"{clip['src']}.mp4")]
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *seek, "-an", "-vf",
         f"fps={fps},vidstabdetect=shakiness=5:accuracy=15:result={trf}", "-f", "null", "-"])
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *seek, "-an", "-vf",
         f"fps={fps},vidstabtransform=input={trf}:smoothing=25:optzoom=0:zoom=4:interpol=bicubic",
         "-c:v", "libx264", "-preset", "fast", "-crf", "12", str(out)])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--out")
    a = ap.parse_args()
    scene = json.loads(pathlib.Path(a.scene).read_text())
    fps, xf, fade = scene["render"]["fps"], scene["crossfade"], scene["fade"]
    clips = scene["clips"]
    total = sum(c["duration"] for c in clips) - xf * (len(clips) - 1)
    inputs, parts = [], []
    for i, c in enumerate(clips):
        if c.get("stabilize"):
            inputs += ["-t", str(c["duration"]), "-i", str(stabilised(c, fps))]
        else:
            inputs += ["-ss", str(c["start"]), "-t", str(c["duration"]), "-i", str(CAND / f"{c['src']}.mp4")]
        chain = [f"fps={fps}"]
        if "vertical_crop_y" in c:
            chain.append(f"crop=iw:iw*9/16:0:(ih-iw*9/16)*{c['vertical_crop_y']}")
        chain += ["scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos", "crop=1920:1080",
                  "setsar=1", "format=yuv420p", "setpts=PTS-STARTPTS"]
        parts.append(f"[{i}:v]{','.join(chain)}[v{i}]")
    cur, offset = "v0", 0.0
    for i in range(1, len(clips)):
        offset += clips[i - 1]["duration"] - xf
        parts.append(f"[{cur}][v{i}]xfade=transition=fade:duration={xf}:offset={offset:.3f}[x{i}]")
        cur = f"x{i}"
    parts.append(f"[{cur}]{GRADE},format=yuv420p,{overlay(scene, total)},"
                 f"fade=t=in:st=0:d={fade},fade=t=out:st={total - fade}:d={fade}[v]")
    maps = ["-map", "[v]"]
    m = scene.get("music")
    if m:
        inputs += ["-i", str(ROOT / m["file"])]
        parts.append(f"[{len(clips)}:a]atrim=0:{total},loudnorm=I={m['target_lufs']}:TP=-1.5:LRA=11,"
                     f"afade=t=in:st=0:d={m['fade_in']},afade=t=out:st={total - m['fade_out']}:d={m['fade_out']}[a]")
        maps += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        maps += ["-an"]
    out = pathlib.Path(a.out) if a.out else ROOT / "output" / f"{scene['id']}.mp4"
    out.parent.mkdir(exist_ok=True)
    t0 = time.time()
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(parts), *maps,
         "-c:v", "libx264", "-preset", "slow", "-crf", str(scene["render"].get("crf", 19)), "-pix_fmt", "yuv420p",
         "-profile:v", "high", "-r", str(fps), "-g", str(fps * 2), "-t", f"{total}", "-movflags", "+faststart",
         "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", str(out)])
    print(json.dumps({"file": str(out), "bytes": out.stat().st_size, "duration_s": total,
                      "process_s": round(time.time() - t0, 1)}))


if __name__ == "__main__":
    main()
