# Real-footage feasibility (Chicago)

Status: a real-footage sample exists, but it is **not train POV**. The only
train-POV source found is still unobtainable from this environment.

## Phase 1 — source validation

### Wikimedia Commons: "Leaving Chicago downtown by CTA green line train 4K" (rollingnet)

| Question | Finding |
|---|---|
| Still accessible? | Listed on Commons (API metadata reads fine). The file host returns HTTP 429 to this cloud IP on every attempt, including one fresh check for this report. Wayback has a snapshot of the file but resets the connection from here. **Blocker is this machine's network, not the file.** |
| Licence | CC BY 3.0, recorded by a Commons licence review dated 2017-05-06 of YouTube video `dpXtglg6iu8`. |
| Is the licence still good? | CC licences are irrevocable, so removal from YouTube does not withdraw it. The evidence is the Commons review record plus a Wayback snapshot of the YouTube page (2023-06-06 exists; not readable from here). Not independently re-verified by us. A human should open that snapshot and confirm the CC BY notice before relying on it. |
| Monetised YouTube use | CC BY allows commercial use and modification with attribution: author, title, source link, licence link, and a note that it was modified. |
| Visually suitable? | **Unknown.** No frame has been seen. Metadata says 3840x2160, 6 min 49 s, handheld iPhone SE, June 2016. |
| Stabilise/crop preserving landmarks? | Unknown until viewed. 4K to 1080p leaves room for about 2x crop; `pipeline/render.py` is ready. |

Other Chicago train-view files on Commons (same blocked host), from the
catalogue search: "Leaving Chicago downtown 4K, part 2" (16 min, CC BY 3.0),
"CTA Purple Line Express (Belmont-Howard) - July 2025" (12 min 50 s, 1080p,
CC BY 4.0, uploader's own work), "Red-Purple Bypass via Brown Line" (two
clips, ~1 min each, CC BY 4.0), "Green Line Lake branch" (2 min 40 s, 720p,
CC BY-SA 3.0), "Metra BNSF - Halsted to Union Station" (5 min 50 s, CC BY
3.0), "Amtrak Hiawatha 334 Dome View Chicago Arrival" (11 min, CC BY 3.0).
None viewed.

### Alternatives checked

| Source | Result |
|---|---|
| Pexels | File servers reachable. Web search found no Chicago view from inside a train. Found two real Chicago 'L' clips shot from outside (used below). Site search and API need a browser or a free API key. |
| Pixabay | Site blocked to this machine; API needs a free key. Not searched. |
| Mixkit | 11 Chicago clips, all skylines/time-lapses. No trains. |
| Coverr | No Chicago train clips in search. |
| Internet Archive | Nothing usable (old public-domain films only). |
| YouTube | Not used, per instruction. |

## Phase 2 — production test

`output/masters/chicago_footage_exterior_sample.mp4` — 16 s, 1920x1080,
30 fps, H.264, 17.1 MB.

* Two Pexels clips by Ricky Esquivel: an 'L' train rounding the curve by the
  Merchandise Mart in snow, and a train passing on the Loop elevated at dusk.
* 1 s crossfade, subtle grade, our overlay. No stabilisation (measured jitter
  0.1 px), no cropping, no 3D interior.
* Processing time 44 s on 4 vCPU. Cost $0.

Limits: exterior shots, not passenger POV; winter dusk, not sunny afternoon;
sources are 24 fps conformed to 30 fps by frame repetition; storefront
trademarks (Starbucks, Subway) are legible in the second clip.

## Phase 3 — scalability

| Question | Assessment |
|---|---|
| How many cities have reusable footage? | Not established. Train-window clips exist in bulk on free stock sites (Pexels lists hundreds of thousands under "view from train window"), but they are mostly 10-60 s, rarely name the city, and rarely show landmarks. Continuous 5-minute city rides under a commercial-use licence are rare; Chicago has a handful on Commons, all untested. |
| Sourcing difficulty per city | High and manual: find, verify location, verify licence, check quality. Expect many cities to have nothing suitable for free. |
| Licences | CC BY / CC BY-SA: attribution required, SA forces the derived video's licence. Pexels/Pixabay: commercial use, no attribution, but no warranty about people, trademarks or the uploader's right to license. |
| Acquisition cost | Free sources: $0 plus search labour. Paid stock or commissioned filming: not priced here; needs real quotes before any plan depends on it. |
| Enough transformation for monetisation? | Uncertain, and the main risk. YouTube's reused-content policy can deny monetisation to channels that mostly compile others' footage with light edits, regardless of licence. Original music, overlays, sequencing and a consistent format help; they do not guarantee approval. Stock clips can also attract Content ID claims from third parties who registered the same footage. |
| Two long uploads a week plus daily streams | Processing is trivial (44 s for 16 s here). Supply is the constraint: an 11-hour stream needs 132 five-minute segments or heavy looping. |

## Phase 4 — comparison

| | Real footage | Blender (v3) |
|---|---|---|
| Visual quality | Photographic. The exterior sample is clearly above v3. | 6/10, visibly computer-generated |
| Train immersion | Only if POV footage is found; the sample has none | Moderate: window frame, no interior |
| City recognition | Immediate | Good on a few landmarks |
| Licensing | Per-clip verification; people/trademark and reused-content risk | Clean: ODbL map data + CC0 |
| Production time | Seconds per clip once sourced; sourcing is hours per city | ~32 h render per 5 min on CPU, plus days of modelling per city |
| Cost | $0 for free sources; unknown for paid | $0 so far; GPU or artist time to go further |
| Scale to 200 cities | Blocked by supply of long POV rides | Blocked by per-city modelling and render time |

## Recommendation

Real footage wins on quality by a wide margin and is the better bet, but two
things are unproven: that long train-POV footage can be obtained for enough
cities, and that the result passes YouTube's reused-content review.

Next step: get one real POV file in hand. The owner downloads the Commons
original from a normal connection and attaches it to a GitHub release on the
repo; it is verified by SHA-1 and run through `pipeline/render.py`.
