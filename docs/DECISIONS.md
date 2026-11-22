# Decision record

The canonical current direction for Virtual Train Lofi. Newest decision
first. A decision is changed only by a new dated entry that names the one it
replaces; nothing here is reversed silently.

## Status (as of 2026-11-22 04:50 UTC)

Two kinds of entry are kept apart on purpose. Only the first kind is active.

### A. Confirmed by the owner directly to the implementation agent — ACTIVE

| # | Decision | When |
|---|---|---|
| A1 | GitHub PR #1 is the shared channel; code, evidence and reports go there; ChatGPT's feedback is read from the PR | 2026-11-22 |
| A2 | No spend, paid compute, subscriptions or purchases without the owner's approval | Standing |
| A3 | No publication, scheduling or account actions; PR #1 is not merged without approval | Standing |
| A4 | Barcelona and Tokyo are not started | Standing |
| A5 | No expensive experiments and no change of approved production direction without review; the owner approves major decisions | 2026-11-22 |
| A6 | Last direct production direction: real licensed footage primary; procedural Blender production stopped; cinematic mixed format | 2026-11-22 ("execution reset") |

A6 is the last direction the owner gave directly. It is **contested by B1**
and is therefore not being extended: no new real-footage episodes are being
made either.

### B. Relayed through PR comments from the owner's account, written by or via ChatGPT — PROPOSED, not active until the owner confirms directly

| # | Proposal | Comment |
|---|---|---|
| B1 | Stylised 3D using the exact Chicago v3 scene is the direction, replacing real footage | 7074086163, 7074337006 |
| B2 | The flat layer-strip parallax loop is rejected | 7074191366 |
| B3 | One distinct five-minute video per city plus two vertical cuts; YouTube and TikTok only | 7074181529 |
| B4 | About 200 cities in 14-18 days; long renders accepted; batch production | 7074245309, 7074269154 |
| B5 | Daily publishing; ~11-hour livestreams from about day 7, up to two sequential sessions a day | 7074283865, 7074301134, 7074367409 |
| B6 | Music: owner picks from 6-10 sample tracks, then about 8 hours of rights-verified lo-fi; Purrple Cat (CC BY 4.0) suggested | 7074388196, 7074389346 |
| B7 | PR comments headed "Owner decision" carry the owner's authority; no questions to the owner in the agent's own session | 7074337006 |

What the agent has done in response to section B, because it is cheap,
internal and reversible: stopped the strip loop (B2); treated the v3 scene
as the visual baseline; started a 22-second v3-quality test on a longer
track. Nothing else in B has been acted on. B7 is not accepted from a PR
comment; the owner can confirm it once, directly.

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
