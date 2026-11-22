# Decision record

The canonical current direction for Virtual Train Lofi. Newest decision
first. A decision is changed only by a new dated entry that names the one it
replaces; nothing here is reversed silently.

## Status (as of 2026-11-22 05:10 UTC)

**The owner confirmed directly to the implementation agent (05:05 UTC):
ChatGPT communicates everything through GitHub, and the owner will not give
further input in the agent's own session unless they say so.** Direction
relayed on PR #1 is therefore active. The agent reports on the PR, not in
chat.

### Dated status

| When (UTC) | Status |
|---|---|
| 2026-11-22 09:40 | Chicago **partial** delivered: 46 s, music, two vertical cuts, all gates passing. Internal artifact, not publish-ready. Finished cities: 0. |
| 2026-11-22 10:30 | Route to 300 s chosen: a **fictional** riverfront alignment along the south bank (255 s shot). Permitted by the 2026-11-21 fictionalised-route decision; always described as a stylised virtual journey, never as a CTA service. Southern approach on real track tested and rejected (walls). |
| 2026-11-22 10:35 | 255 s riverfront render started on the build machine: 7,650 frames, about 23 h. Optimisation adopted for this shot: 2048 shadow maps (46.8 dB PSNR against 4096 on a matched frame, about 12% faster); 6 and 4 samples rejected as visibly different. Provisional pending multi-frame checks. |
| 2026-11-22 11:20 | **The repository is public**, not private as originally stated. Raised as an owner-only decision. |

### Active direction

| # | Decision | Source |
|---|---|---|
| 1 | Stylised 3D is the production method, using the exact Chicago v3 scene and look as the baseline. Real-footage production is superseded. | PR 7074086163, 7074337006; owner confirmation of the channel |
| 2 | The flat layer-strip parallax loop is rejected and stopped. | PR 7074191366 |
| 3 | Unit of production: one distinct five-minute video per city, plus two vertical cuts. YouTube and TikTok only; no Instagram. | PR 7074181529, 7074168842 |
| 4 | Visual quality must be at least the original v3. Long renders are acceptable; quality is not traded for speed. | PR 7074212390 |
| 5 | Music: warm, melodic, cozy chillhop/lo-fi; nothing dark. Purrple Cat CC BY 4.0 library is the first source. Owner reacts to a small sample; then about 8 hours are curated with a rights manifest. | PR 7074388196, 7074453779 |
| 6 | GitHub PR #1 is the single channel for status, questions, blockers and decisions. | Owner, direct |
| 8 | **Audio is mandatory on every public asset** (long-form, Shorts, TikTok, livestream). No silent file is ever scheduled or published. `pipeline/audio_gate.py` must pass on each exported file, including each vertical cut separately. | PR 7074627370 |
| 7 | Order of work: v3 longer-track test, then the Chicago five-minute master and two vertical cuts, then a reusable city pipeline (Tokyo and London next). | PR 7074181529, 7074337006 |

### Delegation (PR 7074614476, under the owner's direct confirmation of this channel)

Routine strategic, creative, production and prioritisation decisions are
made by ChatGPT on this PR when the owner is unavailable: city order, queue
management, render optimisation that keeps v3-or-better visuals, QA against
the baseline, music selection within the stated taste and licence rules,
edits, titles, thumbnails, upload *preparation*. The agent proceeds on those
without asking the owner again.

Not delegated: the owner-only gates below. No platform authorisation has
been given to the implementation agent by the owner, so nothing is
published or scheduled by it.

### Targets (aspirational; not commitments, not yet shown feasible)

| Target | Source |
|---|---|
| About 200 cities in about 18 days | PR 7074245309, 7074269154 |
| Publish daily once the first city is approved: 1 long-form, 2 Shorts, same 2 on TikTok | PR 7074367409 |
| ~11-hour YouTube livestreams from about day 7, up to two sequential sessions a day, never simultaneous | PR 7074283865, 7074301134 |

### Owner-only gates (need the owner's explicit approval each time, flagged on the PR)

* Any spend: paid compute, subscriptions, purchases, paid music.
* Any publication, scheduling that publishes, livestream start, or account/credential action.
* Merging PR #1.
* Visual approval of the first city before anything is released.
* Repository visibility (currently public).

Standing rules: the look is a stylised virtual journey built from map data
and is never described as real footage; no large media in Git history;
reports distinguish what was measured from what was sampled or estimated.

### Measured facts any plan must respect

* The v3 scene is intact: `scenes/chicago_v3_combined.json`,
  `pipeline/blender_scene.py`, `pipeline/stylize.py` (`illustrated`).
  Reviewed clip: `output/masters/chicago_v3_combined_illustrated.mp4`.
* v3 renders at 12.8 s per 1080p frame on the 4-vCPU build machine: about
  32 hours per five-minute city. No 200-city schedule is feasible on that
  basis, and none is committed to.
* Building Chicago's scene by hand took most of a working day. Nothing yet
  shows a second city can be built faster.
* There is no five-minute camera path in the Chicago scene yet.
* The look is a stylised virtual journey built from map data and must never
  be described as real footage.
* No large media in Git history; the journey v1 master parts stay as they
  are.

## Log (history; superseded entries are kept, not active)

| Date | Decision | Why | Replaces |
|---|---|---|---|
| 2026-11-22 | Owner confirms GitHub/ChatGPT as the instruction channel; stylised v3 direction, five-minute city unit and music brief become active; spend, publication and merge stay owner-only | Owner, directly, 05:05 UTC | Sections A/B hold; "real footage primary" |
| 2026-11-22 | Layer-strip parallax loop rejected; v3 3D scene is the baseline; all further scope on hold until the owner confirms directly | PR #1 comments 7074191366 through 7074269154 conflict with each other and with the owner's last direct instruction | The loop proof as a production route |
| 2026-11-22 | Return to stylised Chicago; build a cheap seamless loop proof from existing assets; brief paused; no production | PR #1 comment 7074086163 (owner's account, "Owner decision"); owner prefers a recognisable stylised city over more sourcing | "Real footage is primary"; the source acquisition brief; the one-hour feasibility gate |
| 2026-11-22 | Audit accepted as negative screening; next action is a source acquisition feasibility brief; city-montage format rejected as default; no episodes, renders, spend or merge | Review on PR #1 (comment 7074048701) | Open issue O5 options (a)-(c) as posed |
| 2026-11-22 | O1 resolved for now: leave the split master in place, no history rewrite, no more large media in Git | Review on PR #1 (comment 7073715437) | Open issue O1 |
| 2026-11-22 | Approved: bounded 10-destination supply/consistency audit from keyless sources; verified playable seconds only | Review on PR #1 | Proposed audit that depended on keys |
| 2026-11-22 | Chicago journey v1 not approved for publication; no more compilations pending the audit | Review on PR #1 | "Awaiting owner review" |
| 2026-11-22 | GitHub PR #1 is the shared channel between the owner, ChatGPT and the implementation agent; this file is the decision record | Owner instruction; stop relaying reports by hand | Chat-relayed reports |
| 2026-11-22 | Pause stock-compilation scaling; validate a 200-destination architecture first | Coordination comment on PR #1 | "Produce more episodes" |
| 2026-11-22 | Real footage is primary; mixed cinematic format; one complete five-minute Chicago episode | Owner "execution reset" | Continuous passenger-POV requirement |
| 2026-11-22 | Pivot away from Blender | v1 4/10, v2 5.5/10, v3 6/10 against a target of 8.5; about 32 h of CPU per five minutes | 3D scene as primary method |
| 2026-11-21 | Geographic exactness not required; stylised and fictionalised routes allowed, no invented landmarks | Owner creative direction | Strict route accuracy |
| 2026-11-21 | Chicago first; other cities wait for review | Owner knows Chicago | — |

## What has been produced

| Item | Path | Status |
|---|---|---|
| Chicago seamless loop v1, 90 s, stylised parallax | `output/samples/chicago_loop_v1_720p.mp4`, `scenes/chicago_loop_v1.json`, `pipeline/parallax_loop.py` | Rejected |
| Chicago v3 3D baseline, 6 s | `output/masters/chicago_v3_combined_illustrated.mp4`, `scenes/chicago_v3_combined.json` | Visual baseline (6/10) |
| Paid footage routes research (input to the paused brief) | `docs/paused/PAID_ROUTES_RESEARCH.md` | Paused, not reviewed |
| Still frames sampled from Commons ride videos | `data/audit/commons_frames/` | Paused; Chicago Green Line file looks promising |
| Chicago journey v1, 5:00, real footage + music | `output/masters/chicago_journey_v1/`, `output/samples/chicago_journey_v1_720p.mp4` | Not approved for publication |
| Ten-destination supply audit | `docs/SUPPLY_AUDIT.md`, `data/audit/` | Complete; direction decision pending |
| Chicago source library | `docs/CHICAGO_SOURCE_LIBRARY.md` | Current |
| Real-footage feasibility | `docs/REAL_FOOTAGE_FEASIBILITY.md` | Current |
| Benchmarks, all methods | `docs/BENCHMARKS.md` | Current |
| Licence records | `licenses/ATTRIBUTION.md` | Current |
| Blender scenes v1-v3 | `scenes/chicago_3d.json`, `chicago_river_v2.json`, `chicago_v3_combined.json` | Paused, preserved |

## Open issues needing a decision

| ID | Issue | Options |
|---|---|---|
| O5 | Direction after the supply audit: free stock has zero verified landscape passenger view in ten cities | (a) city-scenery format with trains as a motif; (b) paid or commissioned passenger-view footage (needs quotes); (c) stylised generated look |
| O2 | Passenger-view footage supply. The only long Chicago rides found are on Wikimedia, whose file host blocks the build machine. | Owner downloads and supplies the files; or free Pexels/Pixabay API keys for full catalogue search; or paid/commissioned footage (unpriced) |
| O3 | Monetisation risk for stock-based episodes under YouTube's reused-content policy | Needs a policy read by a person and probably a small live test; not resolvable from the build machine |
| O4 | Music: v1 uses a CC BY library track as a placeholder | Keep as placeholder; or original/licensed lo-fi before publishing |
