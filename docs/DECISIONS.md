# Decision record

The canonical current direction for Virtual Train Lofi. Newest decision
first. A decision is changed only by a new dated entry that names the one it
replaces; nothing here is reversed silently.

## CURRENT STATUS — 2026-11-23 00:15 UTC (read this first)

* **Method:** illustrated 2.5D "destination mood journey"; stylised, never presented as
  a real route or real footage. Earlier 3D and real-footage work is history only.
* **Built, all automated gates passed:** Chicago, Denver, Paris, Tokyo. Each has a 300 s
  1080p master and two 25 s vertical Shorts.
* **Approved by the owner:** Chicago only (frozen). Denver, Paris and Tokyo await review.
* **Per-city looks:** graded samples exist for Denver (softened v2), Paris and Tokyo
  (cool overcast day, not blue hour). Rail-piece fixes for Denver and Tokyo are in their
  settings. No rebuild until the owner approves the looks; current masters are kept.
* **Platform:** YouTube only at launch; TikTok deferred (limit zero). Channel: Buffer
  destination "Lofi Train POV", YouTube channel `UCLjE-J4o5HSXz1cCokDdZbQ`, confirmed by the
  owner as @LofiTrainPOV. Limit: one long-form and two Shorts per day.
* **Publishing:** nothing scheduled or published. Blocked on (1) a public link for the
  master, see `docs/MEDIA_ORIGIN.md` (proposal, nothing created), (2) the owner's explicit
  go-live, (3) rights closeout. `pipeline/publish_queue.py` and `publish_preflight.py` are
  tested gates; there is no unattended scheduler.
* **Spend (computed, billed amounts unverified):** style test about 0.70 USD; Chicago
  1.25 of 4 USD; Denver, Paris, Tokyo 2.14 of 3 USD. No further spend authorised.
* **Durability:** masters are on a temporary build disk and in files sent to the owner.
* **Hard gates:** no spend, paid or public infrastructure, merge, scheduling, publication
  or livestream without the owner's explicit approval.

## Short 2 scheduled; long-form blocked by the scheduling tool — 2026-11-23 00:45 UTC

The owner said in the agent session to schedule the other Short and the long-form for tomorrow.
* Chicago Short 2: scheduled for 23 November 2026, 20:30 Central (Buffer post `6b038bc4d5eabfb8ccf12944`).
* Chicago long-form: **not scheduled.** The tool refused it: its YouTube integration accepts only vertical
  videos of three minutes or less. Long-form uploads need YouTube Studio or YouTube's own API with the
  owner's authorisation. This also means daily long-form publishing cannot be automated through this tool.

## No on-video AI label — 2026-11-23 00:25 UTC

The owner said in the agent session that they do not want the AI label shown on the video;
and then that descriptions should not say AI either, on any video, until they change their mind.
YouTube's altered/synthetic-content flag is therefore off on all uploads and titles and
descriptions do not mention AI. Basis as understood from a summary of YouTube's help page (not read in
full): the flag is required for realistic content and clearly animated content is exempt.
Descriptions keep a line saying the artwork is illustrated and not real footage. Applied to
the scheduled Chicago Short 1.

## Storage created; first post scheduled — 2026-11-23 00:15 UTC

The owner said in the agent session: "Yes to storage and yes to posting tonight."

* **Storage:** `lofitrain-archive` (private) and `lofitrain-delivery` (public read, release
  files only) created in the owner's Cloudflare account, 3 USD per month ceiling.
  Archived and fingerprint-verified by download: Chicago final master and both Shorts;
  the original Denver, Paris and Tokyo masters and Shorts. Denver's master (319 MB) exceeds
  the 300 MB single-upload limit of the API route available here, so it is stored as two
  verified parts (join with `cat`).
* **First post:** Chicago Short 1 scheduled for 22 November 2026, 20:30 Central, public,
  AI-generated flag on, on Lofi Train POV. Buffer post `6b0384d9d5eabfb8ccee6db4`.
  Log: `publish/release_log.json`.
* **Not scheduled:** Chicago long-form and Short 2 (proposed for 23 November). Each needs
  the owner's go.
* Rights reading (provider terms, YouTube AI-content policy in full) and the landmark
  check were still open when this was scheduled; the owner was told before confirming.

## YouTube-only launch; TikTok deferred — 2026-11-22 23:40 UTC (relayed on PR #1, comment 7087747366)

* Launch on YouTube only. TikTok is deferred and is not a launch blocker; no
  TikTok account, integration or posting until the owner asks for it.
* The two vertical clips per city are YouTube Shorts.
* Daily maximum unchanged: one long-form and two Shorts. `publish/limits.json`
  now sets the TikTok limit to zero.
* Livestream target (about 2 December) and all publishing gates unchanged.

## HARD publishing limit — 2026-11-22 21:35 UTC (relayed on PR #1, comment 7086149051)

* At most **three regular YouTube uploads per calendar day in total: one
  long-form city video and two Shorts.** Never more long-form because
  production is ahead; extra cities wait in a backlog, one per day.
* TikTok, if connected: at most two posts per day, the same two vertical clips.
* Livestreams (target about 2 December 2026, 8 to 10 hours) are in addition and
  need separate authorisation; they do not change the three-upload limit.
* Machine-readable copy: `publish/limits.json`. Any scheduling must check it.
* Still required before anything is posted: the LofiTrain channels connected and
  named by the owner, and an explicit go-live.

## Chicago visually approved — 2026-11-22 21:35 UTC (relayed on PR #1, comment 7086115277)

Relayed as the owner's words after watching the corrected video: "Chicago looks
good let's move on to the next. I'll get the channels created so they can get
the long form and shorts posted."

* **Approved:** the corrected 300 s illustrated Chicago, master SHA-256
  `a2b52ffd78d4d1947cbf2d47913ebb7a4e663fe2a8ea17bd2d58921686d15adc`, and its two verticals.
  Chicago is frozen; no further changes.
* **Not yet authorised:** publishing. That needs the new LofiTrain YouTube and
  TikTok accounts connected, the channel identified, and an explicit go-live from
  the owner in the agent session. Nothing goes to existing unrelated channels.
* Cities approved for visual quality: 1 (Chicago). Published: 0.
* Next: Denver, Paris, Tokyo (art bought, 2.14 USD computed of a 3 USD ceiling),
  then a four-city comparison for visual distinctiveness.

## Channel cadence and livestream window — 2026-11-22 20:45 UTC (relayed on PR #1, comments 7085461103 and 7085486398)

* **Cadence target:** one 5-minute city video and two Shorts per day, the Shorts
  cut from that city. Building several cities ahead is to hold a buffer, not to
  post them at once. Every format carries continuous melodic lofi audio.
* **Livestream target:** first 8 to 10 hour stream around 2 to 6 December 2026,
  built from a varied library of finished cities and a music rotation, not one
  5-minute loop repeated. Rights for live use of the music, channel live
  eligibility and stream infrastructure are still to be checked; nothing paid
  is provisioned.
* **Chicago:** to be published after the station and wheel fixes pass. Publishing
  still needs the owner's explicit go-live and choice of channel in the agent
  session; a PR comment alone does not publish.
* **Next cities:** plan in `data/illustrated/next_cities_plan.json` (Denver, Paris,
  Tokyo; 12 calls, about 2.14 USD). No image call until the owner approves a
  combined cap. The 1 USD per city figure is a target, not an authorisation.
* These are targets, not commitments. Supersedes the earlier 200-cities-in-18-days target.

## Illustrated Chicago built under the 4 USD ceiling — 2026-11-22 19:45 UTC

The owner confirmed the one-time 4 USD ceiling in the agent session. Stage 1 only
was used: 7 image calls, 1.25 USD computed from API usage at published rates
(billing page not read), no rejects. Ledger: `data/illustrated/chicago_generation_ledger.json`.
Source art: `assets_illustrated/chicago/`. Composer: `pipeline/illustrated_journey.py`.

* Built: a 300 s master and two 25 s verticals, all passing the audio and video gates.
* Status: **awaiting the owner's watch-through.** Not approved for release, not published.
* Stage 2 budget (2.75 USD) is unspent and stays unspent unless the owner asks for changes that need it.
* No second city, merge or publication.

## Proposed product definition — 2026-11-22 18:35 UTC (awaiting owner approval of motion quality)

Relayed on PR #1 (comment 7083659998): a five-minute video does not have to
depict the whole city or stay downtown. It needs a compelling, recognisable
selection of what the destination is known for, mixed with fitting scenery.

* Recommended product: a **destination mood journey**, not an exact route
  reconstruction. Design and estimates: `docs/DESTINATION_JOURNEY_DESIGN.md`.
* Must be labelled as a stylised journey. Never presented as a real route or
  real footage. No invented landmarks, no scenery the place does not have.
* City-specific art is reserved for a handful of landmark moments; scenic
  environments come from a shared library.
* This replaces the earlier estimate that each city needs about 28 unique
  buildings. Cost gate and approved look are unchanged.
* Documentation only. No paid images, builds, renders or new cities.

## Owner cost gate — 2026-11-22 18:15 UTC

Relayed on PR #1 (comment 7083431537): the owner rejects 5 USD per city, and so
also the 7 / 21 / 53 USD projections. The proposed 2 USD two-plate test was
**not approved** and will not be run.

* No paid image calls, renders on paid machines, or subscriptions.
* Design target: well under 5 USD incremental generation cost per city, ideally
  near zero in API charges. Not asserted achievable until demonstrated.
* The approved illustrated look stands; no return to the blocky 3D look.
* Options and the cheapest no-spend proof: `docs/LOW_COST_OPTIONS.md`. Awaiting review.

## Illustrated 2.5D aesthetic approved; production animation NOT approved — 2026-11-22 18:05 UTC

Relayed on PR #1 (comments 7083241979 and 7083276874) as the owner's verdict after
watching Style C at playback speed: "Yes the new 2.5 is so much better. Besides
the random tree/leaves that pop up and disappear at the bottom everything else
looks great." This replaces the "candidate awaiting visual verdict" status in the
18:00 entry below, which is kept for the record.

* **Approved:** the illustrated 2.5D look (plate, palette, lighting, window frame).
  Clean reference: `output/samples/style_C2_illustrated_no_foliage_10s.mp4`.
  No return to the blocky 3D look or to filters over it.
* **Not approved:** the animation technique, continuous forward travel, a
  five-minute city, any spend, scaling, merge, scheduling or publication.
* Foreground foliage layer removed (it popped in and out).
* `style_C3_traverse_25s.mp4` is a motion diagnostic on the one existing painting.
  It does not prove joins, depth separation, fresh scenery or five-minute routes.
* Next gate: a two-plate continuity test. No paid image call until the owner
  sets a cost ceiling.

## Proposed direction awaiting owner approval — 2026-11-22 18:00 UTC

**Style C, illustrated 2.5D, is a candidate under visual review. It is not the
production method.** Nothing below takes effect until the owner approves the
look after watching the clip at playback speed.

* What exists: one 10-second Chicago proof (`output/samples/style_C_illustrated_2p5d_10s.mp4`),
  made from one generated painting plus three layer edits, after the owner
  authorised image generation in the agent session. Provenance:
  `data/illustrated/chicago_style_c_provenance.json`. Feasibility, cost ranges,
  rights and audio status: `docs/ILLUSTRATED_FEASIBILITY.md`.
* What it does not show: continuous forward travel with new scenery, a
  five-minute city, verified landmark accuracy, or 200-city economics.
* If the owner approves the look, the next step is one bounded continuity test
  under a cost ceiling agreed first. Approval of the look does not authorise a
  city queue, spend beyond that ceiling, merge, scheduling or publication.
* If the owner rejects it, the 15:00 UTC fast-3D entry below remains the
  working method and the first fast-path Chicago master
  (`work/fast/v1/`, previews in `output/samples/`) stands as built.
* Stopped by owner instruction on 2026-11-22 about 17:05 UTC: the Chicago
  rebuild (vehicle motion, two buildings removed), tunnel handoff work, and any
  second city. Code for these is committed; none of it is running.
* Also on the record: comparison B (colour and outline restyle of the 3D frames)
  was judged not a valid illustrated comparison. The actual image-generation
  charge is unknown until confirmed from billing.

## Direction update — 2026-11-22 15:00 UTC (replaces "render every frame" as the production method)

Given by the owner directly in the agent session (about 14:50 UTC) and on PR #1
(comments 7080403379 to 7080633490). Everything in "Active direction" below still
holds unless listed here.

1. **The every-frame Blender CPU render (24 to 32 hours per city) is no longer the
   production method.** Its 1,182 riverfront frames are kept on disk; the job is not
   the critical path and is not to consume another day.
2. **Production method under proof: keyframes + depth reprojection** (`pipeline/fast_city.py`,
   `pipeline/fast_shot.py`). Same scene, route, window and "illustrated" look. One sharp
   keyframe per second is rendered with depth; in-between frames are synthesised through
   the true scene depth. This machine has no GPU (4 vCPU, software OpenGL), so no
   real-time renderer is available here.
3. **One art direction for the whole catalogue**: stylised, cinematic, slightly
   anime-influenced 3D, identical engine, grade, window and camera for every city.
   An anime/lofi restyle is permitted only if 3D cannot meet speed; it is not needed so far.
4. **It must be a genuine moving train view**: continuous forward travel, true parallax,
   city-specific recognisable scenery, no slideshow, no loop, no static picture.
5. **City handoff for compilations and livestreams**: a reusable 5 to 10 second tunnel with a
   "NEXT STOP: [CITY]" sign, continuous motion and music. Built after the Chicago master.
6. **End product**: an 11-hour continuous journey assembled from 5-minute city masters.
7. **Autonomy**: routine creative and technical choices are the agent's; no per-city approval.
8. **Unchanged owner-only gates**: no spend or paid services, no merge, no publication,
   scheduling or livestream, no repository visibility change.

## SUPERSEDED status as of 2026-11-22 12:00 UTC (history only; the stylised 3D direction below is no longer active)

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
* Building Chicago's scene by hand took most of a working day; finding a route that reaches 300 s took a further 31 minutes and two candidates. Nothing yet
  shows a second city can be built faster.
* A 300 s Chicago plan now exists (five shots; see the dated status table). 45 s of it is rendered and QC-passed; the 255 s riverfront shot is rendering and unreviewed in motion. Finished cities: 0.
* Restart-loss exposure: rendered frames and any local compressed checkpoints live only on the build session's disk. If the session is reclaimed, the riverfront render (about 23 h) is lost; only `state/` and committed files survive. Git LFS and GitHub Actions are **not** enabled (decided on PR 7078729192).
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

## Historic open issues (superseded; kept for the record)

O2, O3, O4 and O5 below were written while real footage was the direction. They are superseded by the Active direction and Owner-only gates above. O3 (reused-content risk) no longer applies to stylised renders in the same way; O4 (music) is replaced by active decision 5.

| ID | Issue | Options |
|---|---|---|
| O5 | Direction after the supply audit: free stock has zero verified landscape passenger view in ten cities | (a) city-scenery format with trains as a motif; (b) paid or commissioned passenger-view footage (needs quotes); (c) stylised generated look |
| O2 | Passenger-view footage supply. The only long Chicago rides found are on Wikimedia, whose file host blocks the build machine. | Owner downloads and supplies the files; or free Pexels/Pixabay API keys for full catalogue search; or paid/commissioned footage (unpriced) |
| O3 | Monetisation risk for stock-based episodes under YouTube's reused-content policy | Needs a policy read by a person and probably a small live test; not resolvable from the build machine |
| O4 | Music: v1 uses a CC BY library track as a placeholder | Keep as placeholder; or original/licensed lo-fi before publishing |
