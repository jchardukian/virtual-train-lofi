# Approach evaluation (Phase 1)

Decision: **C — authentic, openly licensed railway footage, post-processed by an
automated ffmpeg pipeline.** Generated 3D (A/B) is kept as a fallback for cities
where no reusable footage exists.

## Build environment actually available

| Resource | Value |
|---|---|
| CPU | 4 vCPU, no GPU (`nvidia-smi` absent) |
| RAM / disk | 15 GB / ~60 GB free |
| Tools | ffmpeg 6.1 (libx264, libvidstab, drawtext), Python 3.13, OpenCV |
| Not available | Unreal Engine, any GPU renderer, paid APIs |

## Candidates

| Criterion | A. Unreal + geospatial | B. Blender + geospatial | C. Licensed real footage | D. AI video generation |
|---|---|---|---|---|
| Geographic accuracy | Building footprints right; facades are not (OSM/city data has shape + height only). Google Photorealistic 3D Tiles are accurate but look melted at street/track level. | Same data, same limits. | Exact by definition — it is the real route. | None. Invents buildings. |
| Landmark quality | Needs hand-modelled landmarks per city. | Same. | Real landmarks, real light. | Fails "no generic AI cities". |
| Visual realism | High only with weeks of art per city. | Medium; Cycles on CPU is far too slow. | Photographic. Limited by the camera used. | Warping/flicker; fails the reject list. |
| Camera movement | Fully controllable. | Fully controllable. | Whatever was shot; fixed with stabilisation + crop. | Uncontrolled. |
| Commercial rights | Google 3D Tiles terms forbid offline rendering/redistribution as video outside Earth Studio's attribution rules; OSM/city data is fine. | Same. | Fine **if** CC BY / CC0 / public domain (not NC, not ND). Attribution is mandatory. | Depends on vendor. |
| Rendering needs | GPU workstation/cloud (RTX-class, 24 GB VRAM for a downtown). | GPU strongly preferred. | CPU only. | Paid API. |
| Cost per 5-min video | GPU hours + large artist time. | Same. | ~$0 compute (minutes of 4 vCPU). | $$ per minute, recurring. |
| Scale to 200 segments | Poor without a content team. | Poor. | Limited by supply of suitably licensed footage per city — the real risk. | n/a |
| Automation | High once a city exists. | High once a city exists. | High: config file per segment, one command. | n/a |

## Why C

* It is the only option that can meet the "owner recognises Chicago" bar in this
  environment, and the only one whose realism does not depend on per-city art.
* It needs no GPU and no recurring API spend, so it fits the $250/month budget.
* It was explicitly allowed by the brief if licensing holds — and it does for
  the Chicago source (CC BY 3.0, licence-reviewed on Wikimedia Commons; see
  `licenses/ATTRIBUTION.md`).

## Known limits of C (be honest about these)

1. **Supply.** 200 five-minute segments need 200 reusable clips. Commons has
   enough to prototype; at scale the realistic options are (a) commissioning or
   self-shooting footage, (b) licensing from rail-video creators, (c) CC BY
   uploads found per city. Barcelona-sunny and Tokyo-rainy-night must each be
   found, not conjured.
2. **Quality is capped by the original camera.** The Chicago source is a
   handheld iPhone SE through train glass: real, 4K, but with reflections,
   rolling-shutter wobble and phone compression. Stabilisation helps; it cannot
   make it a cinema camera.
3. **Weather/time of day cannot be changed** without leaving reality. A colour
   grade is fine; turning day to night is not.
4. **No "window frame" unless it was filmed.** A composited fake frame is easy
   but should be an explicit owner choice.

## When to fall back to A/B

If a target city has no reusable footage, the credible 3D route is Blender or
Unreal + OSM/city open-data buildings + hand-finished landmarks, rendered on a
rented GPU. That needs explicit budget approval (see `docs/BENCHMARKS.md`).
