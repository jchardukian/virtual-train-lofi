#!/usr/bin/env python3
"""Fingerprint of a city render, so a rendered video is only ever reused for the exact inputs that made it.

  python3 pipeline/render_manifest.py write  <config.json> <video.mp4>   # after a successful render
  python3 pipeline/render_manifest.py verify <config.json> <video.mp4>   # exit 0 only if video and inputs still match
"""
import hashlib, json, os, pathlib, sys

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
    scale = int(os.environ.get("RENDER_SCALE", "1"))
    art = {s: sha(ROOT / s) for s in sources(cfg)}
    if scale > 1:                                   # the 2x-upscaled art a 4K render reads instead, where it exists
        for s in sources(cfg):
            x2 = ROOT / "work/cities_x2" / s[len("work/cities_v3/"):] if s.startswith("work/cities_v3/") else None
            if x2 is not None and x2.exists():
                art["x2:" + s] = sha(x2)
    return {"config_sha256": sha(config), "render_scale": scale, "code": {c: sha(ROOT / c) for c in CODE}, "art": art}


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
    for k in ("config_sha256", "render_scale", "code", "art"):
        if old.get(k, 1 if k == "render_scale" else None) != new[k]:
            sys.exit(f"{k} changed since this video was rendered: it must be rendered again")
    print("render manifest verified")


if __name__ == "__main__":
    main()
