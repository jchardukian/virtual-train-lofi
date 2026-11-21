# Benchmarks and cost — Chicago baseline (24 s)

All numbers measured on the build machine: 4 vCPU, 15 GB RAM, no GPU,
Blender 3.6.23 EEVEE on Mesa software OpenGL, ffmpeg 6.1.

## Render

| Item | Measured |
|---|---|
| Frames | 720 (24 s at 30 fps, 1920x1080) |
| Wall time | 4,200 s (70 min), two Blender processes sharing 4 vCPU |
| Per frame | 5.8 s effective (7.7 s when one process runs alone) |
| Peak Blender memory | 253 MB per process |
| Frame store | 1.6 GB PNG |
| Settings | 6 TAA samples, 2 motion-blur steps, SSR half-res, AO, 2048 shadow cascades |

Running two processes gave about 1.3x over one; software GL already uses
most cores.

## Encode (per 24 s clip, libx264 preset slow, CRF 17)

| Style | Encode time | File | Bitrate |
|---|---|---|---|
| clean | 52 s | 43.6 MB | 14.5 Mbps |
| lofi | 89 s | 56.2 MB | 18.7 Mbps |
| anime | 104 s | 80.6 MB | 26.9 Mbps |

## Scene preparation (once per city)

| Step | Time | Output |
|---|---|---|
| OSM fetch (25 tiles) | ~1 min | 61 MB raw XML |
| Extract | ~20 s | 1.4 MB geometry JSON |
| Mesh build | ~40 s | 2,011 buildings, 3,351 trees, ~210k faces |

## Cost

| Item | Cost |
|---|---|
| This prototype | $0 (no paid service, API, asset or GPU used) |
| Data | OpenStreetMap, free under ODbL (attribution required) |
| Software | Blender, ffmpeg, Python: free |

## Extrapolation (not measured)

At 5.8 s/frame a five-minute segment (9,000 frames) is about 14.5 hours on
this machine. 200 segments would be about 2,900 machine-hours. That is too
slow for production; options to benchmark next are reduced samples,
simplified distant geometry, 720p upscaled, or a rented GPU (EEVEE on a real
GPU is typically well under 1 s per frame for a scene this light — to be
measured, not assumed).

## Automated QC (pipeline/qc.py)

| Check | clean | lofi | anime |
|---|---|---|---|
| H.264, 1920x1080, 30 fps, yuv420p | pass | pass | pass |
| No black frames mid-clip | pass | pass | pass |
| No frozen frames | pass | pass | pass |
| Jitter / rotation metric | see note | see note | see note |

Note on jitter: the optical-flow metric is not reliable on this content. On
the first encode it passed the lofi clip (0.67 px RMS) and failed clean and
anime with impossible values (jumps of 600-900 px) although all three come
from the same frames. Repeating window grids make the feature matcher lock
onto the wrong window. A direct frame-difference check on the clean clip
shows no discontinuity: the largest frame-to-frame change is 1.33x its
neighbours, and there is no seam where the two render processes meet
(frames 359/360). The camera path itself is analytic and smooth. The metric
needs replacing for synthetic scenes; treat its pass/fail here as void.

## Known visual limits of this baseline

- Reads as a clean architectural model, not a finished premium look.
- Facades are procedural window grids with invented colours; only massing,
  position and height are real.
- Bridges are flat red-brown slabs, not bascule trusses. Bridge houses are
  small windowed blocks.
- First ~2 s are dominated by a blank building wall before the river reveal.
- Far-field motion is slow (about 1 px/frame) at 19 km/h side-on.
- The lofi grade is pink/sunset rather than sunny afternoon; the window
  frame picks up a purple cast.
- No cars, people, signage or station detail; boats are simple boxes.
- No reflections or dirt on the train glass; the frame is a flat dark shape.
