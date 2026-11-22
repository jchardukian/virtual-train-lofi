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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("city")
    ap.add_argument("--partial", action="store_true")
    ap.add_argument("--crossfade", type=float, default=1.0)
    a = ap.parse_args()
    man = json.loads((ROOT / "cities/manifest.json").read_text())
    city = next(c for c in man["cities"] if c["id"] == a.city)
    st_path = ROOT / "state" / f"{a.city}.json"
    st = json.loads(st_path.read_text())
    order = city.get("edit_order") or [s["scene"] for s in city["shots"]]
    shots = [(k, st["shots"][k]) for k in order if st["shots"].get(k, {}).get("qc_pass") and (ROOT / st["shots"][k]["encoded"]).exists()]
    if not shots:
        sys.exit("no QC-passed shots to assemble")
    xf = a.crossfade
    total = sum(s["duration_s"] for _, s in shots) - xf * (len(shots) - 1)
    if total < 299.0 and not a.partial:
        sys.exit(f"only {total:.1f} s of footage; a city master is 300 s. Use --partial to build a labelled partial.")
    label = "partial" if total < 299.0 else "master"
    out_dir = ROOT / "output" / "cities" / a.city
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
        if not f.exists():
            run(["curl", "-s", "-L", "-A", "Mozilla/5.0", "-o", str(f), url])
        d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                 capture_output=True, text=True).stdout)
        tracks.append((t, f, d))
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
    parts.append(f"[{cur}]{overlay(scene, total)},fade=t=in:st=0:d={fade},fade=t=out:st={total - fade}:d={fade}[v]")
    n = len(shots)
    for j, (_, f, _) in enumerate(tracks):
        inputs += ["-i", str(f)]
    acur = f"{n}:a"
    for j in range(1, len(tracks)):
        parts.append(f"[{acur}][{n + j}:a]acrossfade=d=3:c1=tri:c2=tri[am{j}]")
        acur = f"am{j}"
    parts.append(f"[{acur}]atrim=0:{total},loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=2,afade=t=out:st={total - 3.0}:d=3.0[a]")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30", "-g", "60",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", f"{total}", "-movflags", "+faststart", str(out)])

    vq = subprocess.run(["python3", str(ROOT / "pipeline/qc.py"), str(out), "--sheet-every", "4", "--fade", str(fade)], capture_output=True, text=True)
    ag = audio_gate.check(str(out))
    verticals = []
    for k, (start, x) in enumerate(city.get("verticals", [[2, 0.5], [max(2, total / 2), 0.55]]), 1):
        vf = out_dir / f"{a.city}_{label}_vertical_{k}.mp4"
        dur = min(25.0, total - start - 1)
        run(["python3", str(ROOT / "pipeline/vertical_cut.py"), str(out), str(vf), "--start", str(start), "--duration", str(dur),
             "--x", str(x), "--title", city["name"].upper()])
        vag = audio_gate.check(str(vf))
        pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                        "-of", "json", str(vf)], capture_output=True, text=True).stdout)["streams"][0]
        verticals.append({"file": str(vf.relative_to(ROOT)), "duration_s": dur, "audio_gate": vag["pass"],
                          "visual_qc": (pr["width"], pr["height"]) == (1080, 1920), "lufs": vag.get("integrated_lufs")})
    rights = out_dir / f"{a.city}_{label}_rights.json"
    rights.write_text(json.dumps({
        "city": city["name"], "kind": label, "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "visuals": {"description": "Stylised 3D render built from map data. Not real footage.",
                    "sources": [{"asset": "OpenStreetMap geometry", "licence": "ODbL 1.0", "credit": "© OpenStreetMap contributors"},
                                {"asset": "Poly Haven sky HDRI and textures", "licence": "CC0"}]},
        "music": [{"title": t["title"], "artist": "Purrple Cat", "record": t["album"], "source": t["mp3_url"], "licence": "CC BY 4.0",
                   "licence_statement_source": "https://www.freelofi.com/ (read 2026-11-22: CC BY 4.0, not in Content ID, credit required)"}
                  for t, _, _ in tracks],
        "required_credits": ["Scenery built from map data © OpenStreetMap contributors (ODbL).",
                             "Music by Purrple Cat (purrplecat.com), licensed under CC BY 4.0: creativecommons.org/licenses/by/4.0/"],
        "shots": [k for k, _ in shots]}, indent=1) + "\n")
    rel = {"kind": label, "master": str(out.relative_to(ROOT)) if label == "master" else None, "file": str(out.relative_to(ROOT)),
           "master_duration_s": round(total, 2), "master_visual_qc": vq.returncode == 0, "master_audio_gate": ag["pass"],
           "lufs": ag.get("integrated_lufs"), "true_peak_dbfs": ag.get("true_peak_dbfs"), "verticals": verticals,
           "rights_manifest": str(rights.relative_to(ROOT)), "bytes": out.stat().st_size}
    st["release"] = rel if label == "master" else {}
    st["partial"] = rel if label == "partial" else st.get("partial")
    st_path.write_text(json.dumps(st, indent=1) + "\n")
    print(json.dumps(rel, indent=1))


if __name__ == "__main__":
    main()
