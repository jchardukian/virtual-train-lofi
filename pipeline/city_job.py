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
import hashlib
import json
import os
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLENDER = os.environ.get("BLENDER", str(ROOT / "work/tools/blender-3.6.23-linux-x64/blender"))
CHUNK = int(os.environ.get("CHUNK_FRAMES", "60"))
RETRIES = 2
ENCODE_VERSION = "2-no-overlay"   # bump to force every shot to be re-encoded (never re-rendered)


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(cid):
    p = ROOT / "state" / f"{cid}.json"
    return json.loads(p.read_text()) if p.exists() else {"city": cid, "shots": {}, "log": []}


def save_state(st):
    (ROOT / "state").mkdir(exist_ok=True)
    st["updated"] = now()
    (ROOT / "state" / f"{st['city']}.json").write_text(json.dumps(st, indent=1) + "\n")


def fingerprint(shot):
    """Hash of the scene file plus the frame set (name, size). A changed scene or
    re-rendered frames invalidate anything encoded from the old ones."""
    h = hashlib.sha256((ROOT / shot["scene"]).read_bytes() + ENCODE_VERSION.encode())
    d = ROOT / shot["frames_dir"]
    for f in sorted(d.glob("f_*.png")) if d.exists() else []:
        h.update(f"{f.name}:{f.stat().st_size}".encode())
    return h.hexdigest()[:16]


def validate_cached(shot, ss):
    """Drop a recorded encode that is missing, failed QC, or was made from other inputs."""
    enc = ss.get("encoded")
    if not enc:
        return
    why = None
    if not (ROOT / enc).exists():
        why = "encoded file missing"
    elif not ss.get("qc_pass"):
        why = "QC did not pass"
    elif ss.get("fingerprint") != fingerprint(shot):
        why = "scene or frames changed since encode"
    if why:
        ss.setdefault("invalidated", []).append(f"{now()} {why}")
        for k in ("encoded", "qc_pass", "qc_checks", "bytes", "duration_s", "fingerprint"):
            ss.pop(k, None)


def release_blockers(city, st):
    """Everything that must be true before a city may be called finished. Fail closed."""
    out = []
    rel = st.get("release", {})
    master = rel.get("master")
    if not master or not (ROOT / master).exists():
        out.append("no assembled city master")
    elif rel.get("sha256") and hashlib.sha256((ROOT / master).read_bytes()).hexdigest() != rel["sha256"]:
        out.append("master file does not match the hash recorded at assembly")
    elif rel.get("input_shots") and any(st.get("shots", {}).get(k, {}).get("fingerprint") != fp for k, fp in rel["input_shots"].items()):
        out.append("master is stale: a shot changed after assembly")
    elif abs(rel.get("master_duration_s", 0) - 300) > 1.0:
        out.append("master is not 300 s")
    if not rel.get("master_visual_qc"):
        out.append("master visual QC not passed")
    if not rel.get("master_audio_gate"):
        out.append("master audio gate not passed")
    if rel.get("missing_shots"):
        out.append("master was assembled without planned shots")
    if master and not rel.get("transitions_clean", False):
        out.append("edit transitions not verified clean")
    good = 0
    for v in rel.get("verticals", []):
        f = ROOT / v.get("file", "")
        reports = [ROOT / v.get(k, "missing") for k in ("qc_report", "audio_report")]
        if (v.get("audio_gate") and v.get("visual_qc") and f.is_file() and all(r.is_file() for r in reports)
                and v.get("sha256") and hashlib.sha256(f.read_bytes()).hexdigest() == v["sha256"]):
            good += 1
    if good < 2:
        out.append("fewer than 2 vertical cuts that exist, match their recorded hash, and passed audio and visual QC with reports")
    rm = ROOT / rel["rights_manifest"] if rel.get("rights_manifest") else None
    try:
        rj = json.loads(rm.read_text()) if rm and rm.is_file() else None
    except ValueError:
        rj = None
    if not rj or not rj.get("music") or not rj.get("required_credits") or not all(m.get("licence_evidence") and (ROOT / m["licence_evidence"]).is_file() for m in rj["music"]):
        out.append("rights manifest missing, unreadable, or without licence evidence")
    return out


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
                    "--styles", shot.get("style", "illustrated"), "--outdir", str(out_dir.relative_to(ROOT)), "--no-overlay"], check=True)
    mp4 = out_dir / f"{scene['id']}_{shot.get('style', 'illustrated')}.mp4"
    qc = subprocess.run(["python3", str(ROOT / "pipeline/qc.py"), str(mp4), "--sheet-every", "3", "--fade", "0"],
                        capture_output=True, text=True)
    rep = json.loads(mp4.with_suffix(".qc.json").read_text())
    passed = qc.returncode == 0 and rep.get("pass") is True and mp4.exists()
    st_shot["qc_checks"] = rep["checks"]
    st_shot["qc_pass"] = passed
    if passed:   # an encode is only recorded when it exists AND passed; otherwise it will be redone
        st_shot.update({"encoded": str(mp4.relative_to(ROOT)), "bytes": mp4.stat().st_size,
                        "duration_s": rep["probe"]["duration_s"], "fingerprint": fingerprint(shot)})
    else:
        st_shot["qc_failures"] = st_shot.get("qc_failures", 0) + 1


def run(city, parallel):
    st = load_state(city["id"])
    if not city["shots"]:
        st["status"] = "blocked: no scene built for this city yet"
        save_state(st)
        return st
    for shot in city["shots"]:
        key = shot["scene"]
        ss = st["shots"].setdefault(key, {})
        validate_cached(shot, ss)
        _, n, _, have = shot_info(shot)
        ss["frames_done"], ss["frames_total"] = len(have), n
        if len(have) < n:
            st["status"] = f"rendering {key}"
            save_state(st)
            for _ in render_missing(shot, ss, parallel):
                save_state(st)
            _, n, _, have = shot_info(shot)
        if len(have) == n and not ss.get("encoded") and ss.get("qc_failures", 0) <= RETRIES:
            st["status"] = f"finishing {key}"
            save_state(st)
            finish(city, shot, ss)
            st["log"].append(f"{now()} finished {key}")
        save_state(st)
    shots_ok = len(st["shots"]) == len(city["shots"]) and all(x.get("encoded") and x.get("qc_pass") for x in st["shots"].values())
    secs = sum(x.get("duration_s", 0) for x in st["shots"].values() if x.get("qc_pass"))
    st["footage_seconds_passed_qc"] = secs
    st["release_blockers"] = release_blockers(city, st)
    if not st["release_blockers"]:
        st["status"] = "RELEASE-READY (still needs owner visual approval before any publication)"
    elif shots_ok:
        st["status"] = "shots complete; NOT a finished city: " + "; ".join(st["release_blockers"])
    elif any(x.get("qc_failures", 0) > RETRIES for x in st["shots"].values()):
        st["status"] = "stopped: a shot failed QC repeatedly"
    save_state(st)
    return st


def persist(msg):
    """Commit and push state/ so progress survives this machine. Frames are not included."""
    subprocess.run(["git", "-C", str(ROOT), "add", "state"], check=False)
    if subprocess.run(["git", "-C", str(ROOT), "diff", "--cached", "--quiet"]).returncode != 0:
        subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m", msg], check=False)
        subprocess.run(["git", "-C", str(ROOT), "push", "-q"], check=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--run")
    ap.add_argument("--run-next", action="store_true")
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--worker", action="store_true", help="keep advancing cities in queue order until none can progress")
    ap.add_argument("--max-hours", type=float, default=24.0)
    ap.add_argument("--persist", action="store_true", help="git commit+push state/ after each city pass")
    a = ap.parse_args()
    cities = json.loads((ROOT / "cities/manifest.json").read_text())["cities"]
    if a.worker:
        t_end = time.time() + a.max_hours * 3600
        while time.time() < t_end:
            progressed = False
            for c in cities:
                if not c["shots"]:
                    continue                     # blocked city: skip, do not halt the queue
                before = json.dumps(load_state(c["id"]).get("shots", {}), sort_keys=True)
                st = run(c, a.parallel)
                if a.persist:
                    persist(f"State: {c['id']} - {st.get('status', '')[:60]}")
                progressed |= json.dumps(st.get("shots", {}), sort_keys=True) != before
            if not progressed:
                break
        return
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
