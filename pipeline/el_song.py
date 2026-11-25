#!/usr/bin/env python3
"""Write an instrumental chillhop/lofi SONG (not a loop) with ElevenLabs Music, using an explicit song structure.

  python3 pipeline/el_song.py <name> --lead "Rhodes" --key "F major" --bpm 78 --mood "warm golden-hour" [--minutes 2.75]

Owner 2026-11-25: songs must have a hook and a melody like a song without words, in the lofi-girl style of
chillhop -- not 3 minutes of the same 30-second beat. So every song gets the arrangement a producer would write:
  Intro (lead plays a fragment of the hook, drums filtered/absent) -> Verse A (full beat, hook stated) ->
  Verse B (melody develops, answer phrase) -> Hook (catchy main theme, fullest) -> Breakdown (drums drop, chords +
  counter-melody) -> Hook return (theme with variation) -> Outro (hook fragment, beat fades).
The same motif is named in every section so the model keeps one memorable theme. Never: vinyl crackle, hiss, noise,
vocals (owner hates static). Output -> work/music_el/<name>.mp3 and a plan json beside it. Needs the owner's OK to spend
ElevenLabs credits.
"""
import argparse, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "work/music_el"
NEVER = ["vinyl crackle", "tape hiss", "static", "noise", "lo-fi distortion", "vocals", "singing", "rap",
         "repetitive loop without development", "aggressive drums", "EDM", "trap hi-hats"]


def plan(lead, key, bpm, mood, minutes):
    total = int(minutes * 60000)
    parts = [("Intro", 0.09, [f"{lead} plays the opening phrase of the main melody alone", "soft pad chords", "no drums yet", "gentle and inviting"]),
             ("Verse A", 0.17, ["laid-back swung boom-bap beat enters", "warm round bass", f"{lead} states the main melody hook clearly", "jazzy seventh and ninth chords"]),
             ("Verse B", 0.15, [f"{lead} develops the melody with an answering phrase", "chord change to the relative minor", "subtle percussion variation"]),
             ("Hook", 0.17, [f"the catchy main theme on {lead}, fullest and most memorable part", "harmony line doubles the hook", "beat and bass in full"]),
             ("Breakdown", 0.12, ["drums drop out", "soft chords with a gentle counter-melody", "airy and spacious", "builds back slowly"]),
             ("Hook return", 0.18, [f"main theme returns on {lead} with a small variation and ornament", "full beat", "warm and satisfying"]),
             ("Outro", 0.12, [f"{lead} plays the hook fragment one last time", "beat thins out", "fades out gently"])]
    secs = []
    for name, frac, styles in parts:
        secs.append({"section_name": name, "positive_local_styles": styles, "negative_local_styles": NEVER[:6],
                     "duration_ms": int(total * frac), "lines": []})
    secs[-1]["duration_ms"] += total - sum(s["duration_ms"] for s in secs)
    return {"positive_global_styles": ["instrumental chillhop", "lofi hip hop", "jazzy", "clean warm mix", f"{bpm} bpm", key, mood,
                                       f"{lead} lead melody", "catchy memorable hook", "song structure with development", "relaxing study beat"],
            "negative_global_styles": NEVER, "sections": secs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name"); ap.add_argument("--lead", required=True); ap.add_argument("--key", default="F major")
    ap.add_argument("--bpm", type=int, default=78); ap.add_argument("--mood", default="warm and cozy")
    ap.add_argument("--minutes", type=float, default=2.75)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    p = plan(a.lead, a.key, a.bpm, a.mood, a.minutes)
    req = OUT / f"{a.name}.plan.json"
    req.write_text(json.dumps({"composition_plan": p}, indent=1))
    mp3 = OUT / f"{a.name}.mp3"
    code = subprocess.run(["curl", "-sS", "-X", "POST", "https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192",
                           "-H", "xi-api-key: dummy", "-H", "Content-Type: application/json", "--data-binary", f"@{req}",
                           "-o", str(mp3), "-w", "%{http_code}"], capture_output=True, text=True).stdout
    if code != "200":
        sys.exit(f"{a.name}: HTTP {code} {mp3.read_text(errors='ignore')[:300] if mp3.exists() else ''}")
    print(a.name, "ok")


if __name__ == "__main__":
    main()
