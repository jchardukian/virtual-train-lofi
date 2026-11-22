#!/usr/bin/env python3
"""Release gate: a file may not be published unless it carries an audible soundtrack throughout.

Fails (exit 1) when: no audio stream; audio shorter than the video; a silent
or near-silent gap of 1.5 s or more anywhere except the final fade; integrated
loudness outside -24..-10 LUFS; true peak above -1.0 dBFS (clipping risk).

Usage: python3 pipeline/audio_gate.py <file.mp4> [more files]
"""
import json
import re
import subprocess
import sys


def check(path):
    pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,duration,channels:format=duration",
                                    "-of", "json", path], capture_output=True, text=True).stdout or "{}")
    streams = pr.get("streams", [])
    v = next((s for s in streams if s["codec_type"] == "video"), None)
    a = next((s for s in streams if s["codec_type"] == "audio"), None)
    dur = float(pr.get("format", {}).get("duration", 0))
    rep = {"file": path, "duration_s": round(dur, 2), "has_audio": bool(a), "checks": {}}
    if not a:
        rep["checks"]["audio_stream_present"] = False
        rep["pass"] = False
        return rep
    adur = float(a.get("duration") or dur)
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af",
                          "silencedetect=n=-45dB:d=1.5,ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    sil = [(float(s), float(e)) for s, e in re.findall(r"silence_start: ([\d.]+).*?silence_end: ([\d.]+)", err, flags=re.S)]
    open_sil = re.findall(r"silence_start: ([\d.]+)(?!.*silence_end)", err, flags=re.S)
    gaps = [g for g in sil if g[0] < dur - 3.0]
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
    peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)[-1])
    rep.update({"audio_codec": a["codec_name"], "channels": a.get("channels"), "integrated_lufs": lufs, "true_peak_dbfs": peak,
                "silent_gaps": gaps})
    rep["checks"] = {
        "audio_stream_present": True,
        "audio_covers_video": adur >= (float(v["duration"]) if v and v.get("duration") else dur) - 0.15,
        "no_silent_gap_over_1.5s": not gaps and not [s for s in open_sil if float(s) < dur - 3.0],
        "loudness_-24_to_-10_lufs": -24.0 <= lufs <= -10.0,
        "true_peak_below_-1dbfs": peak <= -1.0,
    }
    rep["pass"] = all(rep["checks"].values())
    return rep


if __name__ == "__main__":
    reports = [check(p) for p in sys.argv[1:]]
    print(json.dumps(reports, indent=1))
    sys.exit(0 if all(r["pass"] for r in reports) else 1)
