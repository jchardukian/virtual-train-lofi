#!/usr/bin/env python3
"""Resumable per-city production job: build -> render (chunked) -> finish shots -> report.

  python3 pipeline/city_job.py --status            # queue and progress for every city
  python3 pipeline/city_job.py --run chicago       # advance one city as far as it can go
  python3 pipeline/city_job.py --run-next          # first city that is not done and has shots

Idempotent: a frame that already exists is never rendered again, so a killed
job continues where it stopped. Progress is written to state/<city>.json,
which is committed, so another session or machine can see what is done.
Rendered frames live under work/ and are NOT persisted by this script: on a
machine whose disk is wiped, frames must be re-rendered. Point `frames_dir`
at durable storage to make the job survive that.
"""
import argparse
import datetime
import json
import os
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLENDER = os.environ.get("BLENDER", str(ROOT / "work/tools/blender-3.6.23-linux-x64/blender"))
CHUNK = int(os.environ.get("CHUNK_FRAMES", "60"))
RETRIES = 2


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(cid):
    p = ROOT / "state" / f"{cid}.json"
    return json.loads(p.read_text()) if p.exists() else {"city": cid, "shots": {}, "log": []}


def save_state(st):
    (ROOT / "state").mkdir(exist_ok=True)
    st["updated"] = now()
    (ROOT / "state" / f"{st['city']}.json").write_text(json.dumps(st, indent=1) + "\n")


def shot_info(shot):
    scene = json.loads((ROOT / shot["scene"]).read_text())
    n = int(round(scene["camera"]["duration_s"] * scene["render"]["fps"]))
    d = ROOT / shot["frames_dir"]
    have = {int(p.stem.split("_")[-1]) for p in d.glob("f_*.png") if p.stat().st_size > 100_000} if d.exists() else set()
    return scene, n, d, have


def render_missing(shot, st_shot, parallel):
    scene, n, d, have = shot_info(shot)
    d.mkdir(parents=True, exist_ok=True)
    missing = [f for f in range(n) if f not in have]
    chunks, cur = [], []
    for f in missing:                       # contiguous runs, at most CHUNK long
        if cur and (f != cur[-1] + 1 or len(cur) >= CHUNK):
            chunks.append((cur[0], cur[-1]))
            cur = []
        cur.append(f)
    if cur:
        chunks.append((cur[0], cur[-1]))
    env = dict(os.environ, LIBGL_ALWAYS_SOFTWARE="1")
    t0 = time.time()
    while chunks:
        batch, chunks = chunks[:parallel], chunks[parallel:]
        procs = [subprocess.Popen(
            ["xvfb-run", "-a", "-s", "-screen 0 1920x1080x24", BLENDER, "-b", "--python", str(ROOT / "pipeline/blender_scene.py"),
             "--", str(ROOT / shot["scene"]), "--frames", f"{a}-{b}", "--out", str(d / "f"), "--engine", "EEVEE"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) for a, b in batch]
        for (a, b), p in zip(batch, procs):
            p.wait()
            _, _, _, have = shot_info(shot)
            bad = [f for f in range(a, b + 1) if f not in have]
            tries = st_shot.setdefault("retries", {}).get(f"{a}-{b}", 0)
            if bad and tries < RETRIES:
                st_shot["retries"][f"{a}-{b}"] = tries + 1
                chunks.append((bad[0], bad[-1]))
            elif bad:
                st_shot.setdefault("failed_chunks", []).append(f"{a}-{b}")
        st_shot["frames_done"], st_shot["frames_total"] = len(have), n
        st_shot["render_s"] = round(st_shot.get("render_s", 0) + time.time() - t0, 1)
        t0 = time.time()
        yield


def finish(city, shot, st_shot):
    scene, n, d, have = shot_info(shot)
    out_dir = ROOT / "output" / "cities" / city["id"]
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["python3", str(ROOT / "pipeline/stylize.py"), str(ROOT / shot["scene"]), "--frames", str(d / "f_%04d.png"),
                    "--styles", shot.get("style", "illustrated"), "--outdir", str(out_dir.relative_to(ROOT))], check=True)
    mp4 = out_dir / f"{scene['id']}_{shot.get('style', 'illustrated')}.mp4"
    qc = subprocess.run(["python3", str(ROOT / "pipeline/qc.py"), str(mp4), "--sheet-every", "3", "--fade", str(scene.get("fade", 1.0))],
                        capture_output=True, text=True)
    rep = json.loads(mp4.with_suffix(".qc.json").read_text())
    st_shot.update({"encoded": str(mp4.relative_to(ROOT)), "bytes": mp4.stat().st_size, "duration_s": rep["probe"]["duration_s"],
                    "qc_pass": qc.returncode == 0, "qc_checks": rep["checks"]})


def run(city, parallel):
    st = load_state(city["id"])
    if not city["shots"]:
        st["status"] = "blocked: no scene built for this city yet"
        save_state(st)
        return st
    for shot in city["shots"]:
        key = shot["scene"]
        ss = st["shots"].setdefault(key, {})
        _, n, _, have = shot_info(shot)
        ss["frames_done"], ss["frames_total"] = len(have), n
        if len(have) < n:
            st["status"] = f"rendering {key}"
            save_state(st)
            for _ in render_missing(shot, ss, parallel):
                save_state(st)
            _, n, _, have = shot_info(shot)
        if len(have) == n and not ss.get("encoded"):
            st["status"] = f"finishing {key}"
            save_state(st)
            finish(city, shot, ss)
            st["log"].append(f"{now()} finished {key}")
        save_state(st)
    done = all(s.get("encoded") for s in st["shots"].values()) and len(st["shots"]) == len(city["shots"])
    secs = sum(s.get("duration_s", 0) for s in st["shots"].values())
    st["master_seconds_available"] = secs
    st["status"] = ("shots complete; city master needs %.0f s more footage" % (300 - secs)) if done and secs < 300 else \
                   ("ready to assemble" if done else st.get("status", "in progress"))
    save_state(st)
    return st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--run")
    ap.add_argument("--run-next", action="store_true")
    ap.add_argument("--parallel", type=int, default=2)
    a = ap.parse_args()
    cities = json.loads((ROOT / "cities/manifest.json").read_text())["cities"]
    if a.status or not (a.run or a.run_next):
        for c in cities:
            st = load_state(c["id"])
            rows = []
            for shot in c["shots"]:
                _, n, _, have = shot_info(shot)
                rows.append(f"{pathlib.Path(shot['scene']).stem}: {len(have)}/{n} frames" + (" encoded" if st["shots"].get(shot["scene"], {}).get("encoded") else ""))
            print(f"{c['id']:10s} {st.get('status', 'not started'):55s} {'; '.join(rows) or 'no shots'}")
        return
    target = next((c for c in cities if c["id"] == a.run), None) if a.run else \
        next((c for c in cities if c["shots"] and load_state(c["id"]).get("status") != "ready to assemble"), None)
    if target:
        print(json.dumps(run(target, a.parallel), indent=1))


if __name__ == "__main__":
    main()
