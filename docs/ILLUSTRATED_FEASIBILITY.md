# Illustrated 2.5D (Style C): feasibility of a five-minute continuous journey

Written 2026-11-22. Documentation only: nothing here has been built or generated
beyond the 10-second proof. Style C is a **candidate under visual review**, not
the production method.

## What is measured (from the 10-second Chicago proof)

| Item | Value |
|---|---|
| Model | OpenAI `gpt-image-2` (as requested; the API response does not echo a dated version) |
| Calls | 4: one generation (the plate), three edits of it (scene without window, window frame, foreground trees) |
| Size / quality | 1536x1024, high |
| Usage reported by the API | 5,488 image output tokens per call (21,952 total); input 243 + 1,645 + 1,608 + 1,640 tokens |
| Time per call | about 70 s (three edits ran in parallel) |
| Animation | 300 frames at 1080p in 54 s on 4 vCPU |
| Scenery travel achieved | about 330 px for the nearest layer over 10 s; no new scenery enters except foreground trees |
| Actual charge | **unknown** until read from the owner's OpenAI billing page |

Prompts, usage and file hashes: `data/illustrated/chicago_style_c_provenance.json`.

## Pricing (not verified against the official page)

Third-party listings agree on 30 USD per million image output tokens and
8 USD per million image input tokens for `gpt-image-2`. The official pricing
page (openai.com/api/pricing) could not be read from this session, so these
are **unverified**. At those rates one high-quality 1536x1024 call is about
0.165 USD of output plus about 0.013 USD of input when an image is supplied:
roughly 0.17 to 0.18 USD per call, and about 0.70 USD for the four calls
already made. Treat as an estimate.

## What continuous forward travel would need (all unproven)

The proof warps one painting sideways. A real journey needs scenery that keeps
arriving. The plausible construction is the classic multi-plane side view:
several long horizontal strips at different depths, each scrolling at its own
speed behind a fixed window.

Assumptions: 1080p output; the middle-distance strip scrolls 60 px/s (a slow
train); 300 s; each generated plate contributes about 1,900 px of strip after
scaling.

| Layer | Scroll speed | Strip length for 300 s | Plates |
|---|---|---|---|
| Sky | about 5 px/s | 1,500 px + one screen | 2 |
| Far skyline | about 20 px/s | 6,000 px + one screen | 4 to 5 |
| Middle (river, bridges, landmarks) | 60 px/s | 18,000 px + one screen | 10 to 11 |
| Near (riverwalk, trees, railings) | about 180 px/s | 54,000 px, or a shorter strip of repeating varied elements | 6 to 30 |
| Window frame | fixed | one image | 1 |

So about 25 to 50 accepted plates per city. Each plate after the first must be
generated as a continuation of its neighbour so seams match, and some will be
rejected for seams, style drift or wrong landmarks.

| Scenario | Calls per city (including retries) | Image cost per city | 200 cities |
|---|---|---|---|
| Low | 40 | about 7 USD | about 1,400 USD |
| Base | 120 | about 21 USD | about 4,200 USD |
| High | 300 | about 53 USD | about 10,500 USD |

These multiply an unverified price by unmeasured call counts. They are
planning ranges, not quotes.

## Open risks, none tested

1. **Seams.** Whether edits can extend a strip so that architecture, light and
   line weight continue across the join has not been tried.
2. **Layer consistency.** Each depth layer must be clean (nothing from other
   layers baked in) with usable transparency. The proof managed this once.
3. **Landmark fidelity.** The model paints an impression of a city. Someone who
   knows the city has to check each landmark; wrong or invented landmarks break
   the channel's own rule.
4. **Perspective.** A flat side-scrolling strip has no perspective change on
   near buildings. Whether that reads as a train ride or as a sliding backdrop
   needs a human judgement at playback speed.
5. **Moving life.** Boats, cars and water need their own small animations.
6. **Human QC.** Realistically 30 to 90 minutes of review per city on top of
   machine time; unmeasured.
7. **Throughput.** Machine time looks small (minutes of rendering, about an hour
   of generation per city if sequential), but that is extrapolated from one clip.

## Rights and terms (checked 2026-11-22, summaries only)

* **Output ownership.** OpenAI's Services Agreement (effective 1 May 2025,
  governing the API) states that the customer owns Output and that OpenAI
  assigns its rights in Output to the customer, to the extent permitted by
  law. Source: openai.com/policies/services-agreement and the business terms
  pages, read via search summaries, not the full text. **Not yet read in full
  by a person; do not rely on this summary for a commercial decision.**
* **Limits of that.** The same terms say outputs may not be unique. Whether a
  purely AI-generated image attracts copyright at all is unsettled in several
  jurisdictions, so exclusivity cannot be assumed.
* **Third-party rights are separate.** Ownership of output does not clear
  trademarks, building or artwork rights, or resemblance to an existing
  artist's or channel's work. The owner's TV photo was a quality reference
  only; it was not sent to the API and nothing in it was reproduced.
* **Platform disclosure.** YouTube and TikTok have their own rules on labelling
  synthetic or altered content; not yet checked for this use.

No blanket rights guarantee is given.

## Music and audio for the Style C clip

* Track: "Warm Horizon" by Purrple Cat, album "Mellow Skies", CC BY 4.0 as
  recorded in `data/music/purrplecat_manifest.json`, licence page snapshot in
  `licenses/snapshots/freelofi.com_2026-11-22.html`. Attribution is required
  wherever the clip is shown.
* `pipeline/audio_gate.py` result: **fail**. Audio present for the full 10 s, no
  silence, -13.1 LUFS, but true peak -0.5 dBFS against the -1 dBFS limit. The
  sample clips were cut straight from the track without the loudness
  normalisation the city assembly applies. **Blocker for release of this
  clip**; trivial to fix when a real cut is made.

## Blockers before any distribution of Style C

1. Owner's visual approval of the look.
2. Actual image charge confirmed from billing; price list verified.
3. Provider terms read in full; platform synthetic-content rules checked.
4. Audio gate passing; attribution text attached.
5. A continuity test (two joined plates with real forward travel) under an
   agreed cost ceiling.
