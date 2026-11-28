#!/usr/bin/env python3
"""Assemble a city cut from its finished shots: crossfades, one overlay, soundtrack, gates, vertical cuts, rights manifest.

  python3 pipeline/assemble_city.py chicago [--partial]

Shots come from state/<city>.json (only shots whose encode passed QC). The
overlay and countdown are applied once here, timed to the whole cut. The
soundtrack is taken from the city's `music` list in cities/manifest.json
(tracks from data/music/purrplecat_manifest.json, CC BY 4.0), crossfaded to
cover the cut. A cut shorter than 300 s can only be built with --partial and
is named and recorded as a partial; it never satisfies the release gate.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import audio_gate  # noqa: E402
from stylize import overlay  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent


def run(cmd):
    subprocess.run(cmd, check=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("city")
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--crossfade", type=float, default=1.0)
    ap.add_argument("--state-file", help="read/write this state file instead of state/<city>.json (testing)")
    ap.add_argument("--tag", default="", help="suffix for output names (testing)")
    a = ap.parse_args()
    man = json.loads((ROOT / "cities/manifest.json").read_text())
    city = next(c for c in man["cities"] if c["id"] == a.city)
    st_path = pathlib.Path(a.state_file) if a.state_file else ROOT / "state" / f"{a.city}.json"
    st = json.loads(st_path.read_text())
    order = city.get("edit_order") or [s["scene"] for s in city["shots"]]
    excluded = set(city.get("exclude_shots", []))          # intentional omissions are declared, never inferred
    required = [k for k in order if k not in excluded]
    valid = {k for k in required if st["shots"].get(k, {}).get("qc_pass") and st["shots"][k].get("encoded")
             and (ROOT / st["shots"][k]["encoded"]).exists()}
    missing = [k for k in required if k not in valid]
    shots = [(k, st["shots"][k]) for k in required if k in valid]
    if not shots:
        sys.exit("no QC-passed shots to assemble")
    xf = a.crossfade
    total = sum(s["duration_s"] for _, s in shots) - xf * (len(shots) - 1)
    is_master = abs(total - 300.0) <= 1.0 and not missing    # a master needs every planned shot, not just 300 s
    if missing and not a.partial:
        sys.exit("cannot build a master: planned shots are missing or failed QC: " + ", ".join(missing))
    if not is_master and not a.partial:
        sys.exit(f"cut would be {total:.1f} s; a city master is 300 s +/- 1 of distinct footage. Use --partial to build a labelled partial.")
    label = ("master" if is_master else "partial") + a.tag
    out_dir = ROOT / "output" / "cities" / a.city
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{a.city}_{label}.mp4"
    fade = 1.5

    # --- soundtrack: download listed tracks, crossfade them to cover the cut
    lib = {t["mp3_url"]: t for t in json.loads((ROOT / "data/music/purrplecat_manifest.json").read_text())["tracks"]}
    music_dir = ROOT / "work" / "music"
    music_dir.mkdir(parents=True, exist_ok=True)
    tracks, have = [], 0.0
    for url in city["music"]:
        t = lib[url]
        f = music_dir / (url.split("/")[-2] + "__" + url.split("/")[-1])
        if t.get("license") != "CC BY 4.0":
            sys.exit(f"music track without a recorded CC BY 4.0 licence: {url}")
        d = None
        for attempt in range(3):
            if not f.exists():
                r = subprocess.run(["curl", "--fail", "-sS", "-L", "--max-time", "120", "--retry", "2", "-A", "Mozilla/5.0", "-o", str(f), url])
                if r.returncode != 0:
                    f.unlink(missing_ok=True)
                    continue
            pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name:format=duration",
                                 "-of", "json", str(f)], capture_output=True, text=True)
            try:
                info = json.loads(pr.stdout)
                codec, d = info["streams"][0]["codec_name"], float(info["format"]["duration"])
            except Exception:  # noqa: BLE001
                codec, d = None, None
            exp = t.get("duration_s")
            if codec == "mp3" and d and d > 30 and (not exp or abs(d - exp) < 5):
                break
            f.unlink(missing_ok=True)      # cached HTML error page or truncated file: discard and fetch again
            d = None
        if d is None:
            sys.exit(f"could not obtain a valid MP3 for {url} after 3 attempts")
        tracks.append((dict(t, file_sha256=sha256(f), file_bytes=f.stat().st_size), f, d))
        have += d - (3.0 if len(tracks) > 1 else 0)
        if have >= total + 1:
            break
    if have < total:
        sys.exit("listed music does not cover the cut; add tracks to the city's music list")

    inputs, parts = [], []
    for i, (_, s) in enumerate(shots):
        inputs += ["-i", str(ROOT / s["encoded"])]
        parts.append(f"[{i}:v]fps=30,setsar=1,format=yuv420p,setpts=PTS-STARTPTS[v{i}]")
    cur, off = "v0", 0.0
    for i in range(1, len(shots)):
        off += shots[i - 1][1]["duration_s"] - xf
        parts.append(f"[{cur}][v{i}]xfade=transition=fade:duration={xf}:offset={off:.3f}[x{i}]")
        cur = f"x{i}"
    scene = {"overlay": {"title": city["name"], "next": city.get("next", ""), "x": 110, "y": 830, "scale": 1.5}}
    parts.append(f"[{cur}]split[c1][c2];[c1]{overlay(scene, total)},fade=t=in:st=0:d={fade},fade=t=out:st={total - fade}:d={fade}[v];"
                 f"[c2]fade=t=in:st=0:d={fade},fade=t=out:st={total - fade}:d={fade}[vclean]")
    n = len(shots)
    for j, (_, f, _) in enumerate(tracks):
        inputs += ["-i", str(f)]
    acur = f"{n}:a"
    for j in range(1, len(tracks)):
        parts.append(f"[{acur}][{n + j}:a]acrossfade=d=3:c1=tri:c2=tri[am{j}]")
        acur = f"am{j}"
    parts.append(f"[{acur}]atrim=0:{total},loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=2,afade=t=out:st={total - 3.0}:d=3.0,asplit[a][a2]")
    clean = out_dir / f"{a.city}_{label}_clean.mp4"      # same cut without text: the source for vertical cuts
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total}", "-movflags", "+faststart", str(out),
         "-map", "[vclean]", "-map", "[a2]", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", "-r", "30",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total}", str(clean)])

    vq = subprocess.run(["python3", str(ROOT / "pipeline/qc.py"), str(out), "--sheet-every", "4", "--fade", str(fade), "--no-jitter"], capture_output=True, text=True)
    ag = audio_gate.check(str(out))
    (out.with_suffix(".audio.json")).write_text(json.dumps(ag, indent=1) + "\n")
    verticals = []
    for k, spec in enumerate(city.get("verticals", [[2, 0.5], [max(2, total / 2), 0.55]]), 1):
        start, x = spec[0], spec[1]
        vf = out_dir / f"{a.city}_{label}_vertical_{k}.mp4"
        dur = min(spec[2] if len(spec) > 2 else 25.0, total - start - 0.5)
        run(["python3", str(ROOT / "pipeline/vertical_cut.py"), str(clean), str(vf), "--start", str(start), "--duration", str(dur),
             "--x", str(x), "--title", city["name"].upper()])
        vag = audio_gate.check(str(vf))
        vf.with_suffix(".audio.json").write_text(json.dumps(vag, indent=1) + "\n")
        # the real visual QC, at the vertical size: spec, black frames, frozen frames, jitter
        vvq = subprocess.run(["python3", str(ROOT / "pipeline/qc.py"), str(vf), "--width", "1080", "--height", "1920",
                              "--sheet-every", "5", "--fade", "0.6", "--no-jitter"], capture_output=True, text=True)
        verticals.append({"file": str(vf.relative_to(ROOT)), "sha256": sha256(vf), "duration_s": dur, "audio_gate": vag["pass"],
                          "visual_qc": vvq.returncode == 0, "lufs": vag.get("integrated_lufs"),
                          "qc_report": str(vf.with_suffix(".qc.json").relative_to(ROOT)),
                          "audio_report": str(vf.with_suffix(".audio.json").relative_to(ROOT))})
    snap = sorted((ROOT / "licenses/snapshots").glob("freelofi.com_*.html"))
    if not snap:
        sys.exit("no dated licence snapshot for the music source in licenses/snapshots/; refusing to write a rights manifest")
    import fetch_assets
    geoms, hdris = set(), set()
    for k, _ in shots:
        sc = json.loads((ROOT / k).read_text())
        g = sc.get("osm", {}).get("geometry")
        h = sc.get("render", {}).get("hdri")
        if not g or not (ROOT / g).exists() or not h:
            sys.exit(f"scene {k} does not declare its map geometry and sky; provenance unverified")
        geoms.add(g)
        hdris.add(pathlib.Path(h).stem)
    unknown = [h for h in hdris if h not in fetch_assets.ASSETS]
    if unknown:
        sys.exit(f"sky asset(s) not in the recorded CC0 asset list: {unknown}")
    titles = ", ".join(f'"{t["title"]}"' for t, _, _ in tracks)
    credit_music = f"Music: {titles} by Purrple Cat (purrplecat.com), licensed under CC BY 4.0: creativecommons.org/licenses/by/4.0/"
    credit_map = "Scenery built from map data © OpenStreetMap contributors (ODbL). A stylised virtual journey, not real footage."
    rights = out_dir / f"{a.city}_{label}_rights.json"
    rights.write_text(json.dumps({
        "city": city["name"], "kind": label, "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "visuals": {"description": "Stylised 3D render built from map data. Not real footage.",
                    "sources": [{"asset": "OpenStreetMap geometry", "licence": "ODbL 1.0", "credit": "© OpenStreetMap contributors",
                                 "files": sorted(geoms), "fetched_by": "pipeline/fetch_osm.py"},
                                {"asset": "Poly Haven sky HDRI", "licence": "CC0", "ids": sorted(hdris), "fetched_by": "pipeline/fetch_assets.py"},
                                {"asset": "Poly Haven wall textures", "licence": "CC0",
                                 "ids": sorted(k for k, v in fetch_assets.ASSETS.items() if v[0] == "tex"), "fetched_by": "pipeline/fetch_assets.py"}]},
        "music": [{"title": t["title"], "artist": "Purrple Cat", "record": t["album"], "downloaded_from": t["mp3_url"],
                   "file_sha256": t["file_sha256"], "file_bytes": t["file_bytes"], "licence": "CC BY 4.0",
                   "licence_evidence": str(snap[-1].relative_to(ROOT)),
                   "note": "The source site states the music is not in Content ID. That is the publisher's statement, not a guarantee that no claim can occur."}
                  for t, _, _ in tracks],
        "required_credits": [credit_map, credit_music],
        "upload_description_block": credit_map + "\n" + credit_music,
        "shots": [{"scene": k, "encoded": s_["encoded"], "sha256": sha256(ROOT / s_["encoded"])} for k, s_ in shots]}, indent=1) + "\n")

    def probe(path):
        j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels:format=duration,size",
                                       "-of", "json", str(path)], capture_output=True, text=True).stdout)
        v = next(x for x in j["streams"] if x["codec_type"] == "video")
        au = next((x for x in j["streams"] if x["codec_type"] == "audio"), {})
        return {"duration_s": round(float(j["format"]["duration"]), 3), "bytes": int(j["format"]["size"]), "video": f'{v["codec_name"]} {v["width"]}x{v["height"]} {v["r_frame_rate"]}',
                "audio": f'{au.get("codec_name")} {au.get("sample_rate")} Hz {au.get("channels")}ch' if au else None}

    # continuity check for the edit: frames just before, during and after every transition, plus freeze/black scan there
    bounds, t_acc = [], 0.0
    for i in range(1, len(shots)):
        t_acc += shots[i - 1][1]["duration_s"] - xf
        bounds.append(round(t_acc, 3))
    trans_ok, sheet = True, None
    if bounds:
        times = [x for b_ in bounds for x in (max(0, b_ - 0.5), b_ + xf / 2, b_ + xf + 0.5)]
        sel = "+".join(f"eq(n\\,{int(round(t * 30))})" for t in times)
        sheet = out_dir / f"{a.city}_{label}_transitions.jpg"
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(out), "-vf",
             f"select='{sel}',scale=480:-2,tile=3x{len(bounds)}:padding=3", "-frames:v", "1", "-vsync", "0", "-q:v", "3", str(sheet)])
        det = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-an", "-vf",
                              "blackdetect=d=0.1:pix_th=0.08,freezedetect=n=0.002:d=0.3", "-f", "null", "-"], capture_output=True, text=True).stderr
        import re
        ev = [float(x) for x in re.findall(r"(?:black_start|freeze_start)[: ]+([\d.]+)", det)]
        trans_ok = not [e for e in ev if any(b_ - 1.0 <= e <= b_ + xf + 1.0 for b_ in bounds)]
    for v_ in verticals:
        v_["probe"] = probe(ROOT / v_["file"])
        v_["contact_sheet"] = str((ROOT / v_["file"]).with_suffix(".contact.jpg").relative_to(ROOT))
    rel = {"kind": label, "file": str(out.relative_to(ROOT)), "sha256": sha256(out), "bytes": out.stat().st_size,
           "master_duration_s": round(total, 2), "master_visual_qc": vq.returncode == 0, "master_audio_gate": ag["pass"],
           "lufs": ag.get("integrated_lufs"), "true_peak_dbfs": ag.get("true_peak_dbfs"), "silences": ag.get("silences"),
           "qc_report": str(out.with_suffix(".qc.json").relative_to(ROOT)), "audio_report": str(out.with_suffix(".audio.json").relative_to(ROOT)),
           "verticals": verticals, "rights_manifest": str(rights.relative_to(ROOT)),
           "input_shots": {k: s_.get("fingerprint") for k, s_ in shots}, "missing_shots": missing, "excluded_shots": sorted(excluded),
           "probe": probe(out), "transition_times_s": bounds, "transitions_clean": trans_ok,
           "transitions_sheet": str(sheet.relative_to(ROOT)) if sheet else None}
    all_ok = rel["transitions_clean"] and rel["master_visual_qc"] and rel["master_audio_gate"] and len(verticals) >= 2 and all(v["audio_gate"] and v["visual_qc"] for v in verticals)
    rel["all_gates_passed"] = all_ok
    # fail closed: release state is only written for a 300 s master whose every gate passed
    st["release"] = dict(rel, master=rel["file"]) if (is_master and all_ok and not a.tag) else {}
    if not is_master:
        st["partial"] = rel
    elif not all_ok:
        st["last_failed_master"] = rel
    st_path.write_text(json.dumps(st, indent=1) + "\n")
    print(json.dumps(rel, indent=1))
    sys.exit(0 if all_ok else 2)


if __name__ == "__main__":
    main()
