# Product design: destination mood journey (proposed)

Written 2026-11-22 from owner direction relayed on PR #1 (comment 7083659998).
Design only. Nothing here is built, and motion quality is not yet approved.

## Two different products

| | Destination mood journey (recommended) | Exact route reconstruction |
|---|---|---|
| Promise to the viewer | "A relaxing train ride that feels like Denver" | "This is the view from a real line" |
| Content | A curated sequence of what the place is known for: a few landmarks plus fitting scenery (river, park, mountains, coast, countryside) | Every building along a real alignment |
| Geography | Plausible for the place; not a real continuous route | Accurate |
| Labelling | "Stylised journey", never "real route" or "real footage" | Could name the line |
| City-specific art | A handful of pieces | Dozens per city |

Rules that stay: no invented landmarks, no scenery the place does not have (no
mountains behind Chicago), nothing described as real footage or a real route.

## Shape of a five-minute video

Four to six environments of 45 to 75 seconds each, joined by smooth handoffs
(a tree line, an embankment, a short cutting or underpass closing over the
window, then opening on the next environment).

Example, Chicago: riverfront with Marina City and bascule bridges, then Loop
towers, then a lakefront park, then brick neighbourhoods, then the edge of the
city. Example, Denver: downtown towers and Union Station, then a park, then
foothills, then the Front Range.

Landmarks appear once each, in the "hero" environments. The scenic environments
between them carry no landmarks and come from a shared library.

## How much art that needs

Per video, at the measured layer speeds (landmark band 46 px/s):

| Need | Amount | Source |
|---|---|---|
| Hero landmarks | 4 to 8 cut-outs | city-specific; several can share one generated sheet |
| City skyline strips | 1 to 2 | city-specific |
| Scenic environments | 2 to 4, each with far, middle and near strips | shared library |
| Sky, water, window frame | 1 set | shared library, palette-shifted per city |

City-specific images per city: about 2 to 5, if landmarks are generated
several to a sheet; 5 to 10 if one per image.

Shared library, one-off: about 10 environment types (river city, park, brick
neighbourhood, suburb, countryside, forest, hills, mountains, coast, desert)
times three depth strips times two variants, plus props: 60 to 120 images.

## Repeat limits (proposed rules)

* A landmark appears once per video.
* No strip repeats inside one environment. A strip must be at least as long as
  its band travels in that environment: about 3,500 px for the landmark band
  over 75 s, about 1,100 px for the distant band.
* A scenic environment is not reused in back-to-back videos of a compilation
  without a palette or time-of-day change.
* Mirror tiling, used in the prototype, is not allowed in production.

## Cost ranges (image generation only; unverified price of about 0.18 USD per image; all unproven)

| | Low | Base | High |
|---|---|---|---|
| Shared library, one-off | 11 USD (60 images) | 30 USD (with rejects) | 65 USD |
| Per city | 0.4 USD (2 images) | 1 USD (5 with rejects) | 2.5 USD |
| 200 cities | 80 USD | 200 USD | 500 USD |
| Total | about 90 USD | about 230 USD | about 565 USD |

Compute is this machine: about 90 s per 30 s of video measured, so roughly
15 minutes per five-minute video plus encoding.

## What is uncertain

1. Whether generated sheets of several landmarks cut out cleanly. Untested.
2. Whether long seam-free strips can be generated. Untested; needs wider or
   tiled generation.
3. Whether the same scenic library makes different destinations feel alike.
4. Whether flat side-view travel is acceptable at playback speed. Owner's call.
5. The real price per image, and whether cheaper quality tiers hold the look.
6. Human time: choosing and checking landmarks per place, perhaps 20 to 40
   minutes each. Unmeasured.
7. Handoffs between environments are designed, not built.
