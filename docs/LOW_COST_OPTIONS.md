# Keeping the illustrated look at near-zero cost per city: options

Written 2026-11-22. Analysis only; nothing here is built. Owner constraint:
5 USD per city is rejected; target is well under that, ideally near zero in
API charges. Whether that is achievable is **not yet demonstrated**.

Prices marked (u) are unverified third-party figures. Hardware today: 4 vCPU,
15 GB RAM, no GPU, temporary disk, 2-hour limit on background jobs.

## Measured facts to build on

| Fact | Value |
|---|---|
| One illustrated image (1536x1024, high) | 5,488 output tokens; about 0.18 USD (u) |
| Animating layers at 1080p | 0.16 to 0.18 s per frame on 4 vCPU (a 5-minute video in about 25 minutes) |
| Existing 3D route engine | true forward travel and depth; 5-minute city in about 2 hours on this machine; rejected look |

## Options

### A. Reusable illustrated kit + procedural routes
Generate once a library in the approved style: sky strips, far-skyline strips,
generic building fronts, trees, bridges, water, quay walls, plus the window
frame. Every city is then assembled by code as scrolling depth layers.
* API cost: one-off, roughly 200 to 600 images, 35 to 110 USD (u). Per city: 0.
* Compute: this machine is enough.
* Human time: large up front (curating the kit, writing the assembler); small per city.
* Compromise: cities share the same buildings. Without city-specific landmarks
  this breaks the "recognisably itself" rule. Not sufficient alone.
* Forward travel: yes, genuinely continuous, as a side view with flat layers.
  Near buildings do not turn in perspective as they pass.

### B. Local or fixed-cost image generation
Run an open image model ourselves instead of paying per image.
* On this machine: no GPU. CPU generation of a 1-megapixel image is likely
  10 to 30 minutes each (unmeasured), and the open models I know do not match
  the plate we approved without style tuning. 30 plates per city would take most
  of a day per city. Not viable here.
* On a rented GPU: seconds per image, so cents per city in compute, perhaps
  0.2 to 0.6 USD per GPU-hour (u). That is new paid infrastructure and needs
  owner approval. Model licences differ (some open models forbid commercial
  use) and must be checked per model.
* Compromise: lower or less consistent quality than the approved plate until a
  style is tuned; real set-up effort.
* Forward travel: same as A or C; this only changes who paints the plates.

### C. Hybrid: shared kit + a few city-specific paintings (recommended to test)
The kit from A carries the generic scenery. Each city adds 3 to 6 generated
landmark pieces (for Chicago: Marina City, a bascule bridge, a skyline strip).
* API cost: kit one-off 35 to 110 USD (u); per city 3 to 6 calls plus retries,
  about 0.5 to 2 USD (u). 200 cities: roughly 100 to 400 USD plus the kit (u).
  Cheaper again with a lower quality tier or batch pricing, both untested for
  this look.
* Compute: this machine is enough.
* Human time: landmark choice and checking per city, perhaps 20 to 40 minutes
  (unmeasured).
* Compromise: the city reads through its landmarks and palette, not through
  every building. Honest label: stylised, not a map.
* Forward travel: as A.

### D. Illustrated materials on the existing 3D route engine
Keep the 3D camera path (the only thing we have with real perspective and
depth) and replace the plain materials with painted textures, painted sky,
drawn trees and outline shading, from a small shared texture kit.
* API cost: a small one-off kit, perhaps 10 to 40 USD (u); per city near 0.
* Compute: about 2 hours per city here (measured for the plain version).
* Human time: per-city scene building, which was the unmeasured bottleneck of
  the 3D route, plus look development.
* Compromise and risk: it may still read as 3D with nice wallpaper. The owner
  rejected the blocky look; this must clear that bar and has not been tried.
* Forward travel: the strongest of all options, including turning perspective.

### E. Free illustrated asset packs (CC0 / CC BY)
* Cost: 0. Compromise: styles will not match the approved plate or each other.
  Useful at most for small props. Not a route on its own.

## 200-city ranges (image and compute cost only; all unproven)

| Option | One-off | Per city | 200 cities | Human time |
|---|---|---|---|---|
| A kit only | 35 to 110 USD (u) | about 0 | 35 to 110 USD | high up front, low after; fails recognisability |
| B rented GPU | set-up effort | cents (u) | tens of USD plus GPU hours; needs approval | high up front |
| C hybrid | 35 to 110 USD (u) | 0.5 to 2 USD (u) | 135 to 510 USD | moderate per city |
| D painted 3D | 10 to 40 USD (u) | about 0 | 10 to 40 USD | high per city unless scene building is automated |
| One-plate-per-view (earlier estimate) | 0 | 7 to 53 USD | 1,400 to 10,500 USD | moderate |

## Honest assessment of continuous forward travel

* A side-scrolling stack of layers **is** continuous forward travel seen from
  a side window, and it can run for five minutes with new scenery arriving the
  whole time. It is what most 2D animation does for train shots. Its limit is
  that objects slide past flat.
* Only a 3D camera (D) gives turning perspective. D carries the largest
  quality risk.
* A single painting panned sideways, as in the 25-second clip, is neither.

## Cheapest proof with what already exists (no spend, not started)

Cut the pieces we already own out of the existing scene image by hand masks
(Marina City, the brick building, both bridge houses, the bridge, three or four
towers, the tree line, river, sky), then have code lay them out as four depth
layers on a 30-second route in a new order and scroll them at different speeds
behind the existing window frame, with the existing music.
* Shows: true multi-plane parallax; scenery entering and leaving for the whole
  clip; whether flat sliding layers are acceptable in this look.
* Does not show: a full kit, a second city, or seam-free generated strips.
  Cut-outs from one painting will have rough edges and repeated pieces.
* Cost: 0 USD. Effort: about 1 to 2 hours of work, a few minutes of rendering.
