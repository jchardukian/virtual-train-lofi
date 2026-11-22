# Decision record

The canonical current direction for Virtual Train Lofi. Newest decision
first. A decision is changed only by a new dated entry that names the one it
replaces; nothing here is reversed silently.

## Current direction (as of 2026-11-22 04:40 UTC) — ON HOLD pending the owner's direct confirmation

Between 04:15 and 04:36 UTC, eleven comments were posted to PR #1 from the
owner's GitHub account, each headed as an owner decision and several
superseding the one before. They move from "cheap seamless loop" to "200
five-minute cities in 18 days and 11 livestreams". The implementation agent
cannot tell which were written by the owner and which by the reviewing
assistant, and they reverse the owner's last direct instruction to the agent
(real footage primary; Blender paused). **No new production is started on
the strength of those comments alone.**

What is common to the latest comments, and already acted on:
1. **The flat layer-strip loop is rejected.** Work on it has stopped. The
   files remain for reference only.
2. **The Chicago v3 3D scene is the visual baseline.** It is intact and
   unchanged: `scenes/chicago_v3_combined.json`, rendered by
   `pipeline/blender_scene.py`, finished by the `illustrated` style in
   `pipeline/stylize.py`. Reviewed clip: `output/masters/chicago_v3_combined_illustrated.mp4`.
3. **Channels named:** YouTube and TikTok only; no Instagram.

Proposed in those comments, **not adopted until the owner confirms directly:**
* One distinct five-minute stylised video per city, plus two vertical cuts.
* About 200 cities in 14-18 days; daily publishing; livestreams from week 1.
* Multi-day CPU renders, batch city production, paid compute quotes.

Standing guardrails (unchanged): no spend, no paid compute, no
subscriptions, no publication, no account actions, no merge of PR #1
without the owner's explicit approval. The look is always described as a
stylised virtual journey, never as real footage. No large media in Git.

Measured facts any plan must respect:
* v3 renders at 12.8 s per 1080p frame on the 4-vCPU build machine: about
  32 hours per five-minute city.
* Rendering is not the only cost. Chicago's scene (landmark models, facade
  table, bridges, camera) took most of a working day to build by hand.
  Nothing yet shows a second city can be made faster.

## Log

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
