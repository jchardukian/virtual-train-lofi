#!/usr/bin/env python3
"""Reject a song that is a short loop on repeat (owner 2026-11-26: "I don't want a 30 second sound on repeat 6 times").

  python3 pipeline/song_check.py <song.mp3> [...]        exit 1 if any song fails

Compares every 4 s window's pitch-class profile (melody + harmony) with every window at least 8 s away. A song whose
windows are mostly near-copies (cosine > 0.97) of another part of itself is a loop. Calibrated on the owner's verdicts:
favourites d02_morning_glow_guitar 4% and s02_window_seat_guitar 0%; loops g05 96%, d04 90%, d01 67%, g03 65%.
Songs with a returning hook land around 30-45%, so the limit is 50%.
"""
import subprocess, sys
import numpy as np

LIMIT = 50.0


def near_copy_pct(path, sr=11025):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop, n = sr // 2, 4096
    win = np.hanning(n)
    S = np.array([np.abs(np.fft.rfft(x[i:i + n] * win)) for i in range(0, len(x) - n, hop)])
    f = np.fft.rfftfreq(n, 1 / sr)
    m = (f > 110) & (f < 2000)
    pc = (np.round(12 * np.log2(f[m] / 440)) % 12).astype(int)
    C = np.stack([S[:, m][:, pc == k].sum(1) for k in range(12)], 1)
    W, gap = 8, 16                                            # 4 s windows, 8 s apart (2 frames per second)
    V = np.array([C[i:i + W].ravel() for i in range(len(C) - W)])
    V /= np.linalg.norm(V, axis=1, keepdims=True) + 1e-9
    sim = V @ V.T
    best = np.array([max(np.max(sim[i, :max(0, i - gap)], initial=0), np.max(sim[i, i + gap:], initial=0))
                     for i in range(len(V))])
    return 100 * float((best > 0.97).mean())


if __name__ == "__main__":
    bad = 0
    for p in sys.argv[1:]:
        v = near_copy_pct(p)
        ok = v <= LIMIT
        bad += not ok
        print(f"{p}: {v:.1f}% near-copies {'OK' if ok else 'REJECT (loop)'}")
    sys.exit(1 if bad else 0)
