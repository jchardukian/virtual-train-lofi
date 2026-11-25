#!/usr/bin/env python3
"""Check a city is buildable before it is queued: every art file in its config exists, its two music files exist,
and a 1080p test still renders. Exit code 1 lists every problem.   python3 pipeline/preflight.py <city> [...]"""
import json, pathlib, re, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
bad = 0
for c in sys.argv[1:]:
    p = []
    cfg = ROOT / f"cities/illustrated/{c}.json"
    if not cfg.exists():
        p.append("no config")
    else:
        for f in set(re.findall(r'"(work/[^"]+\.(?:png|jpg))"', cfg.read_text())):
            if not (ROOT / f).exists():
                p.append(f"missing art {f}")
        u = json.loads((ROOT / "data/music/used.json").read_text()).get(c, {})
        fs = u.get("files") or []
        if len(fs) < 2:
            p.append("music files not registered")
        p += [f"missing music {f}" for f in fs if not (ROOT / f).exists()]
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(ROOT / "pipeline/illustrated_city.py"), str(cfg), f"{d}/s", "--still", "3000"],
                               capture_output=True, text=True, env={"RENDER_SCALE": "1", "PATH": "/usr/bin:/usr/local/bin"})
            if r.returncode:
                p.append("test render failed: " + r.stderr.strip().splitlines()[-1][:150])
    print(c, "OK" if not p else "PROBLEMS: " + "; ".join(p))
    bad += bool(p)
sys.exit(1 if bad else 0)
