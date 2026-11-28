#!/usr/bin/env python3
"""Sample still frames from a Wikimedia Commons video via the thumbnail service.

The original-file host blocks the build machine, but thumb.wikimedia.org
serves a JPEG of any video at any timestamp (seek=<seconds>). This lets a
video be inspected frame by frame without downloading it. Frames are 960 px
wide: enough to judge content and framing, not fine sharpness.

Usage: commons_frames.py "File:Title.webm" <out_dir> [n_frames]
"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.parse
import urllib.request

UA = "TrainFootageAudit/0.1 (still-frame inspection)"


def get(url, binary=False, tries=6):
    for attempt in range(tries):  # Wikimedia rate-limits anonymous clients: back off and retry
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60)
            return r.read() if binary else json.load(r)
        except Exception:  # noqa: BLE001
            if attempt == tries - 1:
                raise
            time.sleep(30 * (attempt + 1))


def main():
    title, out, n = sys.argv[1], pathlib.Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 16
    out.mkdir(parents=True, exist_ok=True)
    api = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(
        action="query", titles=title, prop="imageinfo", iiprop="url|size|extmetadata|sha1", iiurlwidth=960, format="json",
        iiextmetadatafilter="LicenseShortName|Artist|Credit|DateTimeOriginal"))
    ii = next(iter(get(api)["query"]["pages"].values()))["imageinfo"][0]
    dur, thumb = ii["duration"], ii["thumburl"]
    meta = {"title": title, "width": ii["width"], "height": ii["height"], "duration_s": round(dur, 1), "bytes": ii["size"],
            "sha1": ii["sha1"], "url": ii["descriptionurl"],
            "meta": {k: v.get("value") for k, v in ii.get("extmetadata", {}).items()}, "frames": []}
    files = []
    for i in range(n):
        t = int(dur * (i + 0.5) / n)
        f = out / f"f_{t:05d}.jpg"
        if not f.exists():
            for attempt in range(4):
                try:
                    f.write_bytes(get(thumb.replace("/960px--", f"/960px-seek={t}-"), binary=True))
                    break
                except Exception as e:  # noqa: BLE001
                    time.sleep(8 * (attempt + 1))
            time.sleep(4)
        if f.exists():
            files.append((t, f))
            meta["frames"].append(t)
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    args = []
    for t, f in files:
        args += ["-i", str(f)]
    lab = ";".join(f"[{k}:v]scale=480:270:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=480:270:(ow-iw)/2:(oh-ih)/2,"
                   f"drawtext=text='{t // 60}\\:{t % 60:02d}':fontcolor=yellow:fontsize=20:x=6:y=6:box=1:boxcolor=black@0.6[v{k}]"
                   for k, (t, _) in enumerate(files))
    cols = 4
    rows = -(-len(files) // cols)
    lay = "|".join(f"{(k % cols) * 480}_{(k // cols) * 270}" for k in range(len(files)))
    graph = lab + ";" + "".join(f"[v{k}]" for k in range(len(files))) + f"xstack=inputs={len(files)}:layout={lay}:fill=black"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, "-filter_complex", graph, "-q:v", "3",
                    str(out / "sheet.jpg")], check=True)
    print(json.dumps({k: meta[k] for k in ("title", "width", "height", "duration_s")}), len(files), "frames", rows, "rows")


if __name__ == "__main__":
    main()
