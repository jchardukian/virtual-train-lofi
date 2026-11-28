#!/usr/bin/env python3
"""Cut a 9:16 vertical clip (1080x1920) from a 16:9 master for Shorts / TikTok.

Usage: vertical_cut.py <master.mp4> <out.mp4> --start 4 --duration 20 [--x 0.5] [--title "CHICAGO, ILLINOIS"]
The picture is a centre (or --x fraction) crop of the master scaled to fill;
a blurred copy fills nothing because the crop already covers the frame.
"""
import argparse
import subprocess

FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
ap = argparse.ArgumentParser()
ap.add_argument("master")
ap.add_argument("out")
ap.add_argument("--start", type=float, default=0)
ap.add_argument("--duration", type=float, default=20)
ap.add_argument("--x", type=float, default=0.5, help="horizontal centre of the crop, 0..1")
ap.add_argument("--title", default="")
a = ap.parse_args()
vf = f"crop=ih*9/16:ih:(iw-ih*9/16)*{a.x}:0,scale=1080:1920:flags=lanczos,setsar=1"
if a.title:
    t = a.title.replace(":", "\\:").replace(",", "\\,").replace("'", "")
    vf += f",drawtext=fontfile={FONT}:text='{t}':fontsize=64:fontcolor=white@0.96:shadowcolor=black@0.6:shadowy=3:x=(w-tw)/2:y=220"
vf += f",fade=t=in:d=0.5,fade=t=out:st={a.duration - 0.6}:d=0.6,format=yuv420p"
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(a.start), "-t", str(a.duration), "-i", a.master,
                "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                "-movflags", "+faststart", a.out], check=True)
print(a.out)
