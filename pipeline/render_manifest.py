#!/usr/bin/env python3
"""Fingerprint of a city render, so a rendered video is only ever reused for the exact inputs that made it.

  python3 pipeline/render_manifest.py write  <config.json> <video.mp4>   # after a successful render
  python3 pipeline/render_manifest.py verify <config.json> <video.mp4>   # exit 0 only if video and inputs still match
"""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CODE = ["pipeline/illustrated_city.py", "pipeline/illustrated_journey.py"]
SHARED = ["work/illus/scene.png", "work/illus/frame.png", "work/chi/sky.png", "work/chi/sprites/strip_3.png"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sources(cfg):
    found = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("src", "treewall") and isinstance(v, str):
                    found.add(v)
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(cfg)
    return sorted(found | set(SHARED))


def inputs(config):
    cfg = json.loads(pathlib.Path(config).read_text())
    return {"config_sha256": sha(config), "code": {c: sha(ROOT / c) for c in CODE}, "art": {s: sha(ROOT / s) for s in sources(cfg)}}


def main():
    mode, config, video = sys.argv[1:4]
    man = pathlib.Path(video).with_suffix(".render.json")
    if mode == "write":
        man.write_text(json.dumps(dict(inputs(config), video_sha256=sha(video)), indent=1) + "\n")
        print("render manifest written")
        return
    if not man.exists():
        sys.exit("no render manifest: this video's inputs are unknown, it must be rendered again")
    old = json.loads(man.read_text())
    if old.get("video_sha256") != sha(video):
        sys.exit("video file does not match its render manifest")
    new = inputs(config)
    for k in ("config_sha256", "code", "art"):
        if old.get(k) != new[k]:
            sys.exit(f"{k} changed since this video was rendered: it must be rendered again")
    print("render manifest verified")


if __name__ == "__main__":
    main()
