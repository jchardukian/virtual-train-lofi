# Virtual Train Lofi

Pipeline for first-person train-window journeys through real cities.
Phase 1: a Chicago prototype.

**Status:** stylised 3D prototype of the Wells Street 'L' crossing of the
Chicago River, built from real OpenStreetMap geometry, in three visual
treatments. See `docs/BENCHMARKS.md` for measured results and limits.

This is a *virtual sightseeing* render. Building positions, heights, the
river, bridges and the track line are real map data; facades, colours,
trees, boats and sky are generated.

## Layout

```
pipeline/
  fetch_osm.py       download OSM tiles for a bounding box
  osm_extract.py     OSM XML -> compact geometry JSON (metres)
  build_meshes.py    geometry -> render meshes (buildings, river, track, trees)
  blender_scene.py   Blender scene, camera move, train window, frame render
  stylize.py         frames -> styled H.264 MP4s + countdown overlay
  qc.py              automated checks + contact sheet
  fetch_source.py    (real-footage route) download + verify source video
  render.py          (real-footage route) stabilise/grade/label
scenes/
  chicago_3d.json    the 3D Chicago scene: bbox, track, camera, light, overlay
  chicago.json       real-footage alternative (source not obtainable yet)
data/chicago_loop_geometry.json   extracted OSM geometry (ODbL)
docs/                approach evaluation, benchmarks, QC checklist
licenses/            attribution and licence records
output/samples/      small review clips
```

## Setup

Linux, CPU only. No GPU and no paid services are needed.

```bash
apt-get install -y ffmpeg xvfb libegl1 libgl1 fonts-inter
pip install numpy shapely mapbox-earcut opencv-python-headless
mkdir -p work/tools && cd work/tools
curl -LO https://download.blender.org/release/Blender3.6/blender-3.6.23-linux-x64.tar.xz
tar xf blender-3.6.23-linux-x64.tar.xz && cd ../..
```

## Render the Chicago prototype

```bash
S=scenes/chicago_3d.json
B=work/tools/blender-3.6.23-linux-x64/blender

python3 pipeline/fetch_osm.py   $S     # ~1 min, 61 MB raw (skip: geometry JSON is committed)
python3 pipeline/osm_extract.py $S     # writes data/chicago_loop_geometry.json
python3 pipeline/build_meshes.py $S    # writes work/meshes/*.npz

# frames (software OpenGL; ~8 s per 1080p frame on 4 vCPU)
LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a -s "-screen 0 1920x1080x24" \
  $B -b --python pipeline/blender_scene.py -- $S --frames 0-719 --out work/frames/final/f

# three styles + overlay -> output/chicago_loop_3d_{clean,lofi,anime}.mp4
python3 pipeline/stylize.py $S --frames work/frames/final/f_%04d.png

python3 pipeline/qc.py output/chicago_loop_3d_lofi.mp4 --sheet-every 3
```

Single test frame: add `--frames 200-200 --out work/frames/test`.

## Changing the journey

Everything is in `scenes/chicago_3d.json`: `camera` (start point, speed,
duration, view angle), `render` (sun, sky, clouds, haze, quality), `window`
(frame thickness), `overlay` (title, next stop), `boats`. A new city needs a
new bbox, a track (OSM way ids) and a landmark colour table in
`build_meshes.py`.
