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
        if not p:   # motion + layering checks on the actual renderer setup
            r = subprocess.run([sys.executable, "-c", f"""
import json,sys; sys.path.insert(0,'{ROOT}/pipeline'); sys.argv=['x']
import numpy as np, illustrated_city as ic
C=ic.City(json.load(open('{cfg}')))
sp=[s['band'][2]/ic.S for s in C.sections if s['band']]
print('SPEED', max(sp) if sp else 0, ic.STREET_SPEED)
for s in C.sections:
    if not s['band']: continue
    a=s['band'][0][1][...,0]; h=a.shape[0]; low=a[int(h*0.55):]
    print('HOLES', float((low<0.5).mean()))
"""], capture_output=True, text=True, env={"RENDER_SCALE": "1", "PATH": "/usr/bin:/usr/local/bin"})
            for line in r.stdout.splitlines():
                k, *v = line.split()
                if k == "SPEED" and float(v[0]) > float(v[1]) + 0.5:
                    p.append(f"street row too fast ({float(v[0]):.0f} px/s > {float(v[1]):.0f})")
                if k == "HOLES" and float(v[0]) > 0.04 and not json.loads(cfg.read_text()).get("gaps_ok"):
                    p.append(f"street row has see-through gaps ({float(v[0])*100:.1f}% of its lower half)")
            if r.returncode:
                p.append("motion check failed to run")
    print(c, "OK" if not p else "PROBLEMS: " + "; ".join(sorted(set(p))))
    bad += bool(p)
sys.exit(1 if bad else 0)
