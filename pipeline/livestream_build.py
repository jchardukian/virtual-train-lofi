#!/usr/bin/env python3
"""Build a ~4-hour livestream file: city rides joined by the 'next stop' countdown and the tunnel, over one continuous
music mix. Runs on a stream server (reads the private archive through the control Worker) or here (Cloudflare API).

  python3 pipeline/livestream_build.py plan <date> [--minutes 240]        # city order + playlist for that day -> work/stream/<date>/plan.json
  python3 pipeline/livestream_build.py prep <city> [<city> ...] [--src FILE] # master -> 1080p30 ride (video only)
  python3 pipeline/livestream_build.py trans <date>                        # tunnel transitions for the day's order
  python3 pipeline/livestream_build.py audio <date>                        # music mix with tunnel rumble -> audio.m4a
  python3 pipeline/livestream_build.py assemble <date>                     # -> work/stream/<date>/stream.mp4 (stream-ready)
  python3 pipeline/livestream_build.py all <date>                          # every step

Each ride shows from just after its fade-in to the start of the countdown; the transition clip (tunnel_transition.py)
covers the last 60 s of a ride, the tunnel and the first second of the next, so pieces meet exactly. The stream file
is H.264 1080p30 at a steady ~6 Mbit/s with a keyframe every 2 s and AAC audio, so streaming is `ffmpeg -re -c copy`.
Music: Purrple Cat (CC BY, credited) and the owner-approved ElevenLabs songs, shuffled per day, cross-faded; never
the locally composed tracks. The day's date seeds every choice, so a day's stream is reproducible and days differ.
"""
import argparse, datetime, hashlib, json, os, pathlib, random, re, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "work/stream"
VID = WORK / "v"                       # 1080p rides, shared by every day's stream
W, H, FPS, SR = 1920, 1080, 30, 48000
FADE, TAIL, HEAD = 1.6, 60.0, 1.0      # must match tunnel_transition.py (FADE) and the trans call below
T_IN, T_DARK, T_OUT = 1.0, 3.0, 1.0
WORKER = "https://lofitrain-control.jchardukian.workers.dev"
EL_OK = ["el_1_rainy_rhodes", "el_2_golden_guitar", "el_3_night_train", "g01_golden_hour_guitar", "g02_morning_coffee_guitar",
         "g03_seaside_guitar", "g04_city_lights_guitar", "g05_autumn_guitar", "g06_summer_drive_guitar", "p01_golden_piano",
         "p02_rainy_window_piano", "p03_night_city_piano", "p04_sunny_rhodes"]


def sh(*a, **k):
    return subprocess.run(a, check=True, **k)


def probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True).stdout
    return float(out.strip())


# ---------- archive access ----------
def _key():
    p = pathlib.Path("/etc/lofitrain/key")
    return p.read_text().strip() if p.exists() else (ROOT / "work/secrets/control_key").read_text().strip()


def get(obj, dest=None):
    """Read an archive object (through the control Worker). Returns bytes, or writes to dest; None if missing."""
    r = urllib.request.Request(f"{WORKER}/obj/{obj}", headers={"X-Key": _key(), "User-Agent": "curl/8.5.0"})
    try:
        with urllib.request.urlopen(r, timeout=600) as f:
            if dest is None:
                return f.read()
            with open(dest, "wb") as o:
                while True:
                    b = f.read(1 << 22)
                    if not b:
                        break
                    o.write(b)
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def fetch_master(city, dest):
    sums = get(f"{city}/SHA256SUMS")
    if not sums:
        sys.exit(f"{city}: no SHA256SUMS in the archive")
    want = next(l.split()[0] for l in sums.decode().splitlines() if l.strip().endswith("_master.mp4"))
    parts, i = [], 0
    while True:
        p = dest.with_suffix(f".part{i:02d}")
        if not get(f"{city}/{city}_illustrated_master.mp4.part{i:02d}", p):
            break
        parts.append(p); i += 1
    if not parts:
        if not get(f"{city}/{city}_illustrated_master.mp4", dest):
            sys.exit(f"{city}: master not in the archive")
    else:
        for n in range(len(parts), 0, -1):              # a rebuilt master can need fewer parts: ignore stale ones
            with open(dest, "wb") as o:
                for p in parts[:n]:
                    o.write(p.read_bytes())
            if sha(dest) == want:
                break
        for p in parts:
            p.unlink()
    if sha(dest) != want:
        dest.unlink(missing_ok=True)
        sys.exit(f"{city}: master failed verification")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


# ---------- steps ----------
def prep(cities, src=None):
    VID.mkdir(parents=True, exist_ok=True)
    for c in cities:
        out = VID / f"{c}.mp4"
        if out.exists():
            print(c, "already prepared"); continue
        m = pathlib.Path(src) if src else VID / f"{c}_master.mp4"
        if not src:
            try:
                fetch_master(c, m)
            except SystemExit as e:                     # not built yet: leave it out of the stream
                print("skip:", e); continue
        tmp = out.with_suffix(".tmp.mp4")
        sh("ffmpeg", "-v", "error", "-y", "-i", str(m), "-an", "-vf", f"scale={W}:{H}:flags=lanczos,fps={FPS}",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-g", str(2 * FPS), "-pix_fmt", "yuv420p", str(tmp))
        tmp.rename(out)
        if not src:
            m.unlink()
        print(c, "prepared", round(probe(out), 1), "s")


def names():
    spec = {}
    for f in sorted((ROOT / "cities/specs").glob("*.json")):
        for x in json.loads(f.read_text()):
            spec[x["id"]] = x["name"]
    fix = {"washington_dc": ("Washington DC", "USA"), "portland_maine": ("Portland", "Maine, USA"), "phoenix_sedona": ("Sedona", "Arizona, USA"),
           "nyc": ("New York City", "USA")}
    def nm(c):
        if c in fix:
            return fix[c]
        n = spec.get(c, c.replace("_", " ").title())
        a, _, b = n.partition(",")
        return a.strip(), b.strip()
    return nm


def music_pool():
    pc = sorted((ROOT / "work/music_lib").glob("*.mp3"))
    el = [ROOT / f"work/music_el/{n}.mp3" for n in EL_OK]
    return [str(p) for p in pc], [str(p) for p in el]


def plan(day, minutes=240, cities=None):
    rnd = random.Random(f"lofitrain-{day}")
    avail = cities or sorted(p.stem for p in VID.glob("*.mp4") if not p.stem.endswith(("_master", ".tmp")))
    rnd.shuffle(avail)
    per = 300 - 2 * FADE + T_IN + T_DARK                 # seconds each ride adds to the stream
    order = avail[:max(2, min(len(avail), round(minutes * 60 / per)))]
    pc, el = music_pool()
    rnd.shuffle(pc); rnd.shuffle(el)
    # mostly Purrple Cat, with an ElevenLabs song every third track (the owner's favourite, el_2, early on)
    tracks, i, j = [], 0, 0
    while len(tracks) < 120:
        if len(tracks) % 3 == 2 and el:
            tracks.append(el[j % len(el)]); j += 1
        else:
            tracks.append(pc[i % len(pc)]); i += 1
    gold = str(ROOT / "work/music_el/el_2_golden_guitar.mp3")
    if gold in tracks:
        tracks.remove(gold)
    tracks.insert(1, gold)
    d = WORK / day
    d.mkdir(parents=True, exist_ok=True)
    p = {"date": day, "order": order, "tracks": tracks}
    (d / "plan.json").write_text(json.dumps(p, indent=1) + "\n")
    print(day, len(order), "cities:", " ".join(order))
    return p


def trans(day):
    p = json.loads((WORK / day / "plan.json").read_text())
    nm = names()
    for a, b in zip(p["order"], p["order"][1:]):
        out = WORK / "t" / f"{a}__{b}.mp4"
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            continue
        n, where = nm(b)
        sh(sys.executable, str(ROOT / "pipeline/tunnel_transition.py"), str(VID / f"{a}.mp4"), str(VID / f"{b}.mp4"), str(out),
           "--next", n, "--where", where, "--tail", str(TAIL), "--head", str(HEAD), "--crf", "17")
        print("transition", a, "->", b)


def pieces(day):
    """[(file, inpoint, outpoint, kind)], with exact cut points (the cuts are re-encoded in assemble)."""
    p = json.loads((WORK / day / "plan.json").read_text())
    o, out = p["order"], []
    for k, c in enumerate(o):
        f = VID / f"{c}.mp4"
        d = probe(f)
        start = FADE if k == 0 else FADE + HEAD
        end = d - FADE - TAIL if k < len(o) - 1 else d
        out.append((f, start, end, "ride"))
        if k < len(o) - 1:
            t = WORK / "t" / f"{c}__{o[k + 1]}.mp4"
            out.append((t, 0.0, probe(t), "trans"))
    return out


def audio(day):
    import numpy as np
    p = json.loads((WORK / day / "plan.json").read_text())
    ps = pieces(day)
    total = sum(b - a for _, a, b, _ in ps)
    tunnels, t = [], 0.0
    for f, a, b, kind in ps:
        if kind == "trans":
            tunnels.append(t + TAIL - 0.4)                # the tunnel mouth arrives 0.4 s before the ride ends
        t += b - a
    n = int(round(total * SR))
    out = WORK / day / "audio.m4a"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
                            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", str(out)], stdin=subprocess.PIPE)
    XF = int(3 * SR)                                      # cross-fade between songs
    rng = np.random.default_rng(7)
    used, pos, carry, ti = [], 0, None, 0

    def dec(path):
        b = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
        x = np.frombuffer(b, np.float32).reshape(-1, 2).copy()
        # trim each song's silent/near-silent head and tail (fade-outs, dead air) so music never drops out
        env = np.sqrt(np.convolve((x ** 2).mean(1), np.ones(SR // 10) / (SR // 10), "same"))
        loud = np.where(env > 10 ** (-38 / 20))[0]
        return x[loud[0]:loud[-1] + 1] if len(loud) else x[:0]

    def shape(x, at):
        """duck the music in the tunnels and add the rumble; at = sample index of x[0] in the stream"""
        tt = (at + np.arange(len(x))) / SR
        env = np.zeros(len(x), np.float32)
        for s in tunnels:
            if s - 1 > tt[-1] or s + 8 < tt[0]:
                continue
            u = tt - s
            env = np.maximum(env, np.clip(u / 0.4, 0, 1) * np.clip((T_IN + T_DARK + 0.6 - u) / 0.8, 0, 1))
        if env.max() > 0:
            noise = np.cumsum(rng.normal(0, 1, (len(x), 2)), axis=0).astype(np.float32)
            noise -= np.linspace(noise[0], noise[-1], len(x)).astype(np.float32)
            noise /= np.abs(noise).max() + 1e-6
            x = x * (1 - 0.45 * env)[:, None] + noise * (0.07 * env)[:, None]   # music stays audible in the tunnel
        return x

    while pos < n:
        path = p["tracks"][ti % len(p["tracks"])]; ti += 1
        if not os.path.exists(path):
            continue
        x = dec(path)
        if len(x) < 30 * SR:
            continue
        used.append(path)
        ramp = np.linspace(0, np.pi / 2, XF)                 # equal-power cross-fade: no dip between songs
        x[:XF] *= np.sin(ramp)[:, None]
        x[-XF:] *= np.cos(ramp)[:, None]
        if carry is not None:
            x[:XF] += carry
        body, carry = x[:-XF], x[-XF:].copy()
        body = body[:n - pos]
        enc.stdin.write(shape(body, pos).astype(np.float32).tobytes())
        pos += len(body)
    enc.stdin.close(); enc.wait()
    (WORK / day / "music_used.json").write_text(json.dumps(used, indent=1) + "\n")
    print("audio", round(total / 60, 1), "min,", len(used), "songs")


def assemble(day):
    d = WORK / day
    lst = d / "list.txt"
    with open(lst, "w") as f:
        for path, a, b, _ in pieces(day):
            f.write(f"file '{path}'\ninpoint {a:.4f}\noutpoint {b:.4f}\n")
    out = d / "stream.mp4"
    # re-encoding through the concat filter graph makes every cut frame-exact; steady bitrate for streaming
    sh("ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-segment_time_metadata", "1", "-i", str(lst), "-i", str(d / "audio.m4a"),
       "-map", "0:v", "-map", "1:a", "-vf", f"select=concatdec_select,setpts=N/{FPS}/TB,fps={FPS}",
       "-c:v", "libx264", "-preset", "veryfast", "-b:v", "6000k", "-maxrate", "6800k", "-bufsize", "12000k",
       "-g", str(2 * FPS), "-keyint_min", str(2 * FPS), "-sc_threshold", "0", "-pix_fmt", "yuv420p", "-c:a", "copy",
       "-shortest", "-movflags", "+faststart", str(out))
    print("stream file", out, round(probe(out) / 3600, 2), "h")


def credits(day):
    """Description text in the owner's order: summary, channel blurb, footage line + music credit, hashtags."""
    d = WORK / day
    p = json.loads((d / "plan.json").read_text())
    used = json.loads((d / "music_used.json").read_text())
    nm = names()
    pc = sorted({pathlib.Path(u).stem.replace("_", " ") for u in used if "/music_lib/" in u})
    limits = json.loads((ROOT / "publish/limits.json").read_text())
    stops = ", ".join(nm(c)[0] for c in p["order"])
    summary = (f"Ride the train around the world for four hours of lofi and chillhop. Settle in by the window as the train "
               f"rolls through {len(p['order'])} cities, with a tunnel and a 'next stop' countdown between each one.\n\nTonight's route: {stops}.")
    credit = ("Music: " + ", ".join(f'"{t}"' for t in pc) + " by Purrple Cat (purrplecat.com), licensed under CC BY 4.0 "
              "(creativecommons.org/licenses/by/4.0/). Tracks were trimmed and cross-faded.")
    tags = "#lofi #chillhop #studymusic #trainride #lofihiphop"
    return "\n\n".join([summary, limits["channel_blurb"], "Stylised illustrated artwork; not real footage.\n" + credit, tags])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step"); ap.add_argument("args", nargs="*")
    ap.add_argument("--minutes", type=float, default=240); ap.add_argument("--src")
    a = ap.parse_intermixed_args()
    if a.step == "prep":
        prep(a.args, a.src)
    elif a.step == "plan":
        plan(a.args[0], a.minutes, a.args[1:] or None)
    elif a.step in ("trans", "audio", "assemble"):
        globals()[a.step](a.args[0])
    elif a.step == "credits":
        print(credits(a.args[0]))
    elif a.step == "all":
        day = a.args[0]
        plan(day, a.minutes); trans(day); audio(day); assemble(day)
    else:
        sys.exit("unknown step")


if __name__ == "__main__":
    main()
