#!/usr/bin/env python3
"""Fast path for a whole city: sparse keyframes -> reprojected shots -> the normal assembly and gates.

  python3 pipeline/fast_city.py chicago [--step 30] [--parallel 2] [--no-assemble]

For each shot in the city's edit order:
  1. render the static carriage interior once (RGBA),
  2. render one sharp world keyframe + depth every `step` frames (resumable: only missing keys),
  3. synthesise every frame by depth reprojection and encode it in the shot's style (fast_shot.py),
  4. run the same per-shot QC the full renderer's shots get.
Then assemble_city.py builds the cut from a separate state file (work/fast/state_<city>.json), so the
result is named <city>_master_fast.mp4 and never touches the city's real release state. Wall time of
every stage is written to work/fast/<city>_timing.json.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLENDER = str(ROOT / "work/tools/blender-3.6.23-linux-x64/blender")


def blender(scene, out, extra, log):
    return subprocess.Popen(["xvfb-run", "-a", "-s", "-screen 0 1920x1080x24", BLENDER, "-b", "--python",
                             str(ROOT / "pipeline/blender_scene.py"), "--", str(ROOT / scene), "--out", str(out), "--engine", "EEVEE"] + extra,
                            env=dict(os.environ, LIBGL_ALWAYS_SOFTWARE="1"), stdout=open(log, "w"), stderr=subprocess.STDOUT)


def have_key(d, k):
    p, z = d / f"k_{k:04d}.png", d / f"z_{k:04d}.exr"
    return p.exists() and z.exists() and p.stat().st_size > 100_000 and z.stat().st_size > 10_000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("city")
    ap.add_argument("--step", type=int, default=30)
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--no-assemble", action="store_true")
    a = ap.parse_args()
    man = json.loads((ROOT / "cities/manifest.json").read_text())
    city = next(c for c in man["cities"] if c["id"] == a.city)
    by_scene = {s["scene"]: s for s in city["shots"]}
    order = city.get("edit_order") or list(by_scene)
    fast = ROOT / "work" / "fast"
    out_dir = ROOT / "output" / "cities" / a.city / "fast"
    out_dir.mkdir(parents=True, exist_ok=True)
    tpath = fast / f"{a.city}_timing.json"
    timing = json.loads(tpath.read_text()) if tpath.exists() else {"step": a.step, "shots": {}}
    state = {"city": a.city, "shots": {}, "log": [], "method": f"keyframes every {a.step} frames + depth reprojection"}
    for key in order:
        shot = by_scene[key]
        scene = json.loads((ROOT / key).read_text())
        n = int(round(scene["camera"]["duration_s"] * scene["render"]["fps"]))
        d = fast / scene["id"].replace("chicago_v3_", "")
        d.mkdir(parents=True, exist_ok=True)
        T = timing["shots"].setdefault(key, {"frames": n})
        t0 = time.time()
        if not (d / "carriage_0000.png").exists():
            blender(key, d / "carriage", ["--frames", "0-0", "--carriage-only"], d / "carriage.log").wait()
            T["carriage_s"] = round(time.time() - t0, 1)
        t0 = time.time()
        for attempt in range(3):
            missing = [k for k in range(0, n + 1, a.step) if not have_key(d, k)]
            if not missing:
                break
            per = -(-len(missing) // a.parallel)
            groups = [missing[i:i + per] for i in range(0, len(missing), per)]
            procs = [blender(key, d / "k", ["--frames", f"{g[0]}-{g[-1]}", "--step", str(a.step), "--keys"], d / f"keys{i}.log")
                     for i, g in enumerate(groups)]
            for p in procs:
                p.wait()
            T["keys_rendered"] = T.get("keys_rendered", 0) + len(missing) - len([k for k in missing if not have_key(d, k)])
        if [k for k in range(0, n + 1, a.step) if not have_key(d, k)]:
            sys.exit(f"{key}: keyframes still missing after 3 attempts")
        T["keys_s"] = round(T.get("keys_s", 0) + time.time() - t0, 1)
        T["keys_total"] = n // a.step + 1
        t0 = time.time()
        style = shot.get("style", "illustrated")
        mp4 = out_dir / f"{scene['id']}_{style}.mp4"
        r = subprocess.run(["python3", str(ROOT / "pipeline/fast_shot.py"), str(d), "--step", str(a.step), "--out", str(mp4),
                            "--carriage", str(d / "carriage_0000.png"), "--style", style], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"{key}: synthesis failed\n{r.stderr[-2000:]}")
        T["synth_encode_s"] = round(time.time() - t0, 1)
        t0 = time.time()
        qc = subprocess.run(["python3", str(ROOT / "pipeline/qc.py"), str(mp4), "--sheet-every", "3", "--fade", "0"],
                            capture_output=True, text=True)
        rep = json.loads(mp4.with_suffix(".qc.json").read_text())
        T["qc_s"] = round(time.time() - t0, 1)
        passed = qc.returncode == 0 and rep.get("pass") is True
        state["shots"][key] = {"frames_done": n, "frames_total": n, "qc_checks": rep["checks"], "qc_pass": passed,
                               "fast": json.loads(mp4.with_suffix(".fast.json").read_text())}
        if passed:
            state["shots"][key].update({"encoded": str(mp4.relative_to(ROOT)), "bytes": mp4.stat().st_size,
                                        "duration_s": rep["probe"]["duration_s"]})
        tpath.write_text(json.dumps(timing, indent=1) + "\n")
        print(key, T, "qc", passed, flush=True)
    spath = fast / f"state_{a.city}.json"
    spath.write_text(json.dumps(state, indent=1) + "\n")
    if not a.no_assemble:
        t0 = time.time()
        r = subprocess.run(["python3", str(ROOT / "pipeline/assemble_city.py"), a.city, "--state-file", str(spath), "--tag", "_fast"])
        timing["assemble_s"] = round(time.time() - t0, 1)
        timing["assemble_exit"] = r.returncode
    timing["total_s"] = round(sum(sum(v for k, v in T.items() if k.endswith("_s")) for T in timing["shots"].values())
                              + timing.get("assemble_s", 0), 1)
    tpath.write_text(json.dumps(timing, indent=1) + "\n")
    print(json.dumps(timing, indent=1))


if __name__ == "__main__":
    main()
