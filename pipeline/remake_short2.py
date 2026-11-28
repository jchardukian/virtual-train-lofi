#!/usr/bin/env python3
"""Keep a city's two Shorts different.

Rides loop: at 5x speed a city's scenery can repeat every ~100 s, so a Short cut at 100 s may be the same picture as the
one cut at 2 s (Austin 2026-11-28: loop 97.5 s, both Shorts identical).

  python3 pipeline/remake_short2.py --pick <master.mp4> <v1_start> <v2_default>
      prints the Short 2 start to use: the default if it already looks different, else the most different start
  python3 pipeline/remake_short2.py <city>
      re-cuts output/cities/<city>/illustrated/<city>_illustrated_vertical_2.mp4 from the master (fetched from the archive
      if needed) at the picked start, with the build's exact settings, peak fix and audio gate, and updates SHA256SUMS
"""
import hashlib, json, pathlib, subprocess, sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEN = 25          # Short length, s
FPS = 2


def frames(p, rs=2):
    """low-res grey frames of the part of the picture the Shorts use (centre crop)"""
    vf = f"fps={FPS},crop={608 * rs}:{1080 * rs}:{656 * rs}:0,scale=54:96,format=gray"
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vf", vf, "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 96, 54).astype(np.float32)


def window_diff(f, a, b):
    n = LEN * FPS
    return float(np.abs(f[a:a + n] - f[b:b + n]).mean())


def pick(master, v1=2.0, v2=100.0, rs=2):
    f = frames(master, rs)
    dur = len(f) / FPS
    a = int(v1 * FPS)
    cands = [t for t in range(30, int(dur - LEN - 3)) if True]
    scores = {t: window_diff(f, a, t * FPS) for t in cands}
    best = max(scores, key=scores.get)
    d_default = window_diff(f, a, int(v2 * FPS)) if v2 + LEN < dur else 0.0
    # keep the default unless it is clearly closer to Short 1 than the best choice
    return (v2, d_default, scores[best]) if d_default >= 0.85 * scores[best] else (float(best), d_default, scores[best])


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest()


def remake(city):
    D = ROOT / f"output/cities/{city}/illustrated"
    m = D / f"{city}_illustrated_master.mp4"
    if not m.exists():
        sys.path.insert(0, str(ROOT / "pipeline"))
        import livestream_build as lb
        lb.fetch_master(city, m)
    rs = int((D / "RESOLUTION").read_text().split("x")[0]) // 1920 if (D / "RESOLUTION").exists() else 2
    v2, dd, db = pick(m, 2.0, 100.0, rs)
    print(f"{city}: default Short 2 difference {dd:.1f}, best {db:.1f}; Short 2 starts at {v2:.0f} s", flush=True)
    out = D / f"{city}_illustrated_vertical_2.mp4"
    (D / "SHORT2_START").write_text(f"{v2:.0f}\n")       # release_city.py credits the songs that play from here
    fx =(f"[0:v]crop={608 * rs}:{1080 * rs}:{656 * rs}:0,scale=1080:1920:flags=lanczos,fade=t=in:d=0.5,"
          f"fade=t=out:st=24.3:d=0.7[v];[0:a]afade=t=in:d=0.5,afade=t=out:st=24:d=1,loudnorm=I=-16:TP=-1.5:LRA=11,"
          f"alimiter=limit=0.6:level=false,aresample=48000[a]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(v2), "-i", str(m), "-t", str(LEN),
                    "-filter_complex", fx, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)], check=True)
    subprocess.run([str(ROOT / "pipeline/fix_peak.sh"), str(out)], check=True)
    g = subprocess.run(["python3", str(ROOT / "pipeline/audio_gate.py"), str(out)], capture_output=True, text=True)
    (D / f"{city}_illustrated_vertical_2.audio.json").write_text(g.stdout)
    if g.returncode:
        sys.exit(f"{city} vertical_2: AUDIO GATE FAILED")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vf", "fps=1/5,scale=360:640,tile=5x1",
                    "-frames:v", "1", str(D / f"{city}_illustrated_vertical_2.contact.jpg")], check=True)
    sums = D / "SHA256SUMS"
    lines = [l for l in sums.read_text().splitlines() if not l.strip().endswith("_vertical_2.mp4")] if sums.exists() else []
    lines.append(f"{sha(out)}  {out.relative_to(ROOT)}")
    sums.write_text("\n".join(lines) + "\n")
    print("ok", out)


if __name__ == "__main__":
    if sys.argv[1] == "--pick":
        v2, dd, db = pick(sys.argv[2], float(sys.argv[3]), float(sys.argv[4]))
        print(f"{v2:.0f}")
        print(f"short2 pick: default diff {dd:.1f}, best {db:.1f}", file=sys.stderr)
    else:
        remake(sys.argv[1])
