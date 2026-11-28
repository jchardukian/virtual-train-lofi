#!/usr/bin/env python3
"""Release gate: a file may not be published unless it carries an audible soundtrack throughout.

Fails closed. Any of these is a failure (exit 1): the file cannot be probed;
no audio stream; audio duration unknown or shorter than the video; a silent
or near-silent gap of 1.5 s or more anywhere except the final 3 s fade;
loudness unmeasurable or outside -24..-10 LUFS; true peak above -1.0 dBFS.

Usage: python3 pipeline/audio_gate.py <file.mp4> [more files]
"""
import json
import math
import re
import subprocess
import sys

MIN_GAP_S = 1.5
TAIL_S = 3.0


def parse_silences(stderr, duration):
    """Pair silencedetect start/end events in the order they appear. An unclosed
    start runs to the end of the file."""
    out, start = [], None
    for line in stderr.splitlines():
        m = re.search(r"silence_start:\s*(-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
            continue
        m = re.search(r"silence_end:\s*(-?[\d.]+)", line)
        if m and start is not None:
            out.append((start, float(m.group(1))))
            start = None
    if start is not None:
        out.append((start, duration))
    return out


def blocking_gaps(silences, duration):
    """Gaps that count: at least MIN_GAP_S long and not confined to the closing fade."""
    return [(a, b) for a, b in silences if b - a >= MIN_GAP_S and a < duration - TAIL_S]


def last_float(pattern, text):
    m = re.findall(pattern, text)
    if not m:
        return None
    try:
        v = float(m[-1])
    except ValueError:
        return None
    return None if math.isnan(v) or math.isinf(v) else v


def evaluate(video_dur, audio_dur, has_audio, silences, lufs, peak):
    """Pure decision logic so it can be unit-tested without media files."""
    checks = {"audio_stream_present": bool(has_audio)}
    if not has_audio:
        return checks, False
    checks["audio_duration_known"] = audio_dur is not None and video_dur is not None and video_dur > 0
    checks["audio_covers_video"] = bool(checks["audio_duration_known"]) and audio_dur >= video_dur - 0.15
    checks["no_silent_gap_over_1.5s"] = silences is not None and not blocking_gaps(silences, video_dur or 0)
    checks["loudness_-24_to_-10_lufs"] = lufs is not None and -24.0 <= lufs <= -10.0
    checks["true_peak_below_-1dbfs"] = peak is not None and peak <= -1.0
    return checks, all(checks.values())


def check(path):
    rep = {"file": path, "pass": False, "checks": {}}
    try:
        pr = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,duration,channels:format=duration",
                             "-of", "json", path], capture_output=True, text=True, timeout=120)
        info = json.loads(pr.stdout or "{}")
        streams = info.get("streams", [])
        if pr.returncode != 0 or not streams:
            rep["error"] = "ffprobe failed or found no streams"
            return rep
        v = next((s for s in streams if s.get("codec_type") == "video"), None)
        a = next((s for s in streams if s.get("codec_type") == "audio"), None)

        def num(x):
            try:
                return float(x)
            except (TypeError, ValueError):
                return None
        fdur = num(info.get("format", {}).get("duration"))
        vdur = num(v.get("duration")) if v else None
        vdur = vdur if vdur else fdur
        adur = num(a.get("duration")) if a else None
        silences = lufs = peak = None
        if a:
            run = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn", "-af",
                                  "silencedetect=n=-45dB:d=1.5,ebur128=peak=true", "-f", "null", "-"],
                                 capture_output=True, text=True, timeout=1800)
            if run.returncode == 0:
                silences = parse_silences(run.stderr, vdur or 0)
                lufs = last_float(r"I:\s+(-?[\d.]+|nan|-inf|inf) LUFS", run.stderr)
                peak = last_float(r"Peak:\s+(-?[\d.]+|nan|-inf|inf) dBFS", run.stderr)
            else:
                rep["error"] = "ffmpeg audio analysis failed"
        checks, ok = evaluate(vdur, adur, bool(a), silences, lufs, peak)
        rep.update({"duration_s": vdur, "audio_duration_s": adur, "integrated_lufs": lufs, "true_peak_dbfs": peak,
                    "silences": silences, "checks": checks, "pass": ok})
    except Exception as e:  # noqa: BLE001  - a gate must report failure, never crash open
        rep["error"] = f"{type(e).__name__}: {e}"
    return rep


if __name__ == "__main__":
    reports = [check(p) for p in sys.argv[1:]]
    print(json.dumps(reports, indent=1))
    sys.exit(0 if reports and all(r["pass"] for r in reports) else 1)
