#!/usr/bin/env python3
"""Download a scene's source footage and verify it against the recorded SHA-1.

Usage: python3 pipeline/fetch_source.py scenes/chicago.json
"""
import hashlib
import os
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = os.environ.get("FETCH_USER_AGENT", "TrainFootagePipeline/0.1 (single-file fetch)")


def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    scene = json.loads(pathlib.Path(sys.argv[1]).read_text())
    src = scene["source"]
    dest = ROOT / src["local_path"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and sha1(dest) == src["sha1"]:
        print(f"ok (cached): {dest}")
        return
    # Wikimedia rate-limits anonymous bulk downloads (HTTP 429, Retry-After
    # 600 s), so resume and back off instead of hammering.
    for attempt in range(8):
        r = subprocess.run(
            ["curl", "-L", "-sS", "-C", "-", "-A", UA, "-o", str(dest),
             "-w", "%{http_code}", src["download_url"]],
            capture_output=True, text=True)
        code = r.stdout.strip()
        if dest.exists() and dest.stat().st_size > 0.99 * src["approx_bytes"]:
            break
        print(f"attempt {attempt + 1}: HTTP {code}, retrying in 10 min")
        if code == "429" and dest.exists():
            dest.unlink()  # body was the error page, not video
        time.sleep(600)
    got = sha1(dest)
    if got != src["sha1"]:
        sys.exit(f"SHA-1 mismatch for {dest}: {got} != {src['sha1']}")
    print(f"ok: {dest}")


if __name__ == "__main__":
    main()
