#!/usr/bin/env python3
"""Compose and render an instrumental lofi / chillhop track from scratch (no samples, no outside service).

  python3 pipeline/compose_lofi.py <out.mp3> --seed 1 --bpm 78 --key 2 --style rhodes|guitar|night --minutes 2.5

Writes jazzy seventh/ninth-chord progressions, a bass line, a motif-based melody and a swung boom-bap kit,
synthesises each part (electric-piano, plucked-guitar or pad timbres; sine bass; synthetic drums), then gives
the mix the usual lofi treatment: gentle low-pass, wow and flutter, tape saturation, vinyl crackle and a little
room reverb, mastered to about -16 LUFS by ffmpeg.
"""
import argparse, pathlib, subprocess, tempfile
import numpy as np

SR = 44100
PROGS = [  # scale degrees (semitones from the key) and chord shapes, four bars each
    [(2, "m9"), (7, "13"), (0, "maj9"), (9, "m9")],          # ii V I vi
    [(0, "maj9"), (9, "m9"), (5, "maj9"), (4, "m7")],         # I vi IV iii
    [(5, "maj9"), (4, "m7"), (2, "m9"), (0, "maj9")],         # IV iii ii I
    [(9, "m9"), (5, "maj9"), (7, "13"), (0, "maj9")],         # vi IV V I
]
SHAPES = {"maj9": [0, 4, 7, 11, 14], "m9": [0, 3, 7, 10, 14], "m7": [0, 3, 7, 10], "13": [0, 4, 10, 14, 21]}
PENTA = [0, 2, 4, 7, 9]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a=0.005, d=0.3, s=0.6, r=0.25):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a) * (s + (1 - s) * np.exp(-t / d))
    rel = int(r * SR)
    if rel < n:
        e[-rel:] *= np.linspace(1, 0, rel)
    return e


def rhodes(f, n):
    t = np.arange(n) / SR
    mod = np.sin(2 * np.pi * f * 14 * t) * 1.2 * np.exp(-t * 9)          # the bell-like attack of a tine
    x = np.sin(2 * np.pi * f * t + mod) + 0.25 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t * 2)
    return x * env(n, 0.004, 0.8, 0.35, 0.3) * (1 + 0.12 * np.sin(2 * np.pi * 4.5 * t))  # tremolo


def guitar(f, n):  # plucked string: harmonics that die away faster the higher they are
    t = np.arange(n) / SR
    x = sum((0.8 ** k) * np.sin(2 * np.pi * f * k * t) * np.exp(-t * (1.5 + 2.2 * k)) for k in range(1, 9))
    return x * env(n, 0.002, 1.0, 0.0, 0.1)


def pad(f, n):
    t = np.arange(n) / SR
    x = sum(np.sin(2 * np.pi * f * (1 + d) * t) for d in (-0.004, 0, 0.005)) / 3
    return x * env(n, 0.6, 2.0, 0.8, 0.8)


def kick(n):
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * (45 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 7)


def snare(n, rng):
    t = np.arange(n) / SR
    nz = rng.normal(0, 1, n)
    nz = np.convolve(nz, np.ones(6) / 6, "same")
    return (0.6 * nz * np.exp(-t * 18) + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25))


def hat(n, rng):
    t = np.arange(n) / SR
    nz = rng.normal(0, 1, n)
    nz = nz - np.convolve(nz, np.ones(4) / 4, "same")
    return nz * np.exp(-t * 60)


def place(buf, x, at, g=1.0):
    i = int(at * SR)
    if i >= len(buf):
        return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += x[:m] * g


def compose(seed, bpm, key, style, minutes):
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    bars = int(minutes * 60 / (4 * beat)) // 4 * 4
    n = int(bars * 4 * beat * SR) + SR * 3
    keys, bass, mel, drums = (np.zeros(n) for _ in range(4))
    prog = PROGS[seed % len(PROGS)]
    alt = PROGS[(seed + 1) % len(PROGS)]
    inst = {"rhodes": rhodes, "guitar": guitar, "night": pad}[style]
    motif = [int(x) for x in rng.choice(len(PENTA), 6)]                  # one idea, repeated and varied
    swing = 0.62
    for b in range(bars):
        sec = (b // 16) % 3                                              # A A' B form
        root, shape = (prog if sec != 2 else alt)[b % 4]
        t0 = b * 4 * beat
        base = 48 + key + root
        voicing = [base + 12 + s for s in SHAPES[shape]]
        dur = 4 * beat
        for j, m in enumerate(voicing):                                  # gently rolled chord
            place(keys, inst(hz(m), int(dur * SR)), t0 + j * 0.018, 0.16)
        if style == "guitar":
            place(keys, rhodes(hz(voicing[0]), int(dur * SR)), t0, 0.07)
        bl = [(0, base - 12), (2.5, base - 12 + 7), (3, base - 12 + (10 if "m" in shape else 7))]
        for at, m in bl:
            nn = int(beat * 1.3 * SR)
            tt = np.arange(nn) / SR
            place(bass, np.sin(2 * np.pi * hz(m) * tt) * env(nn, 0.01, 0.4, 0.7, 0.1) + 0.2 * np.sin(4 * np.pi * hz(m) * tt) * env(nn), t0 + at * beat, 0.5)
        intro, outro = b < 4, b >= bars - 2
        if not intro:                                                    # drums enter after the intro
            for s in range(8):
                at = t0 + (s // 2) * beat + (s % 2) * beat * swing
                if s in (0, 5) or (s == 3 and rng.random() < 0.3):
                    place(drums, kick(int(0.5 * SR)), at, 0.9)
                if s in (2, 6):
                    place(drums, snare(int(0.3 * SR), rng), at, 0.45)
                place(drums, hat(int(0.08 * SR), rng), at, 0.12 + 0.06 * (s % 2 == 0))
        if not intro and not outro and (b % 8) >= 2:                      # melody: the motif over the changes
            var = motif if (b // 4) % 2 == 0 else motif[::-1]
            for j, deg in enumerate(var):
                if rng.random() < 0.28:
                    continue
                m = 72 + key + PENTA[(deg + (b % 4)) % 5] + (12 if sec == 2 and j == 0 else 0)
                at = t0 + j * beat * 0.66 + (beat * 0.08 if j % 2 else 0)
                note = inst(hz(m), int(beat * 1.2 * SR)) if style != "night" else rhodes(hz(m), int(beat * 1.6 * SR))
                place(mel, note, at, 0.14 + 0.04 * rng.random())
    mix = 0.9 * keys + 0.8 * bass + 0.75 * drums + 0.8 * mel
    t = np.arange(n) / SR
    wow = (0.0018 * np.sin(2 * np.pi * 0.5 * t) + 0.0006 * np.sin(2 * np.pi * 5.3 * t)) * SR  # tape wow and flutter
    idx = np.clip(np.arange(n) + wow, 0, n - 1)
    mix = np.interp(idx, np.arange(n), mix)
    mix = np.tanh(mix * 1.4) / 1.4                                          # soft tape saturation
    crackle = (rng.random(n) < 0.0009) * rng.normal(0, 0.25, n)
    hiss = np.convolve(rng.normal(0, 0.004, n), np.ones(3) / 3, "same")
    mix = mix + crackle + hiss
    fade = int(4 * SR)
    mix[:int(1.5 * SR)] *= np.linspace(0, 1, int(1.5 * SR))
    mix[-fade:] *= np.linspace(1, 0, fade)
    st = np.stack([mix, np.roll(mix, 220) * 0.96 + 0.04 * mix], 1)       # a touch of stereo width
    return (st / (np.abs(st).max() + 1e-9) * 0.8).astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out"); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--bpm", type=float, default=78)
    ap.add_argument("--key", type=int, default=2); ap.add_argument("--style", default="rhodes"); ap.add_argument("--minutes", type=float, default=2.5)
    a = ap.parse_args()
    x = compose(a.seed, a.bpm, a.key, a.style, a.minutes)
    with tempfile.TemporaryDirectory() as d:
        raw = pathlib.Path(d) / "x.f32"
        x.tofile(raw)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(raw), "-af",
                        "lowpass=f=6500,highpass=f=35,aecho=0.8:0.5:45|90:0.18|0.10,loudnorm=I=-16:TP=-1.5:LRA=11",
                        "-ar", "44100", "-b:a", "192k", a.out], check=True)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
