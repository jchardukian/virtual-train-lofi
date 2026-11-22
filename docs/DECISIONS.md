# Decision record

The canonical current direction for Virtual Train Lofi. Newest decision
first. A decision is changed only by a new dated entry that names the one it
replaces; nothing here is reversed silently.

## Current direction (as of 2026-11-22, late)

**Source of this direction:** PR #1 comment 7074086163, posted from the
owner's GitHub account and headed "Owner decision". It supersedes the
feasibility-gate request (comment 7074070619) and pauses the source
acquisition brief (comment 7074048701). The implementation agent has acted
on it; the owner has not yet confirmed it to the agent directly.

1. **Production method:** return to the stylised Chicago scene (about 6/10
   visually) and make it economical. Re-evaluation and a proof are
   authorised; **production is not.**
2. **Technique:** a short seamless train-window loop built from a few still
   layer renders scrolled as parallax, looped at streaming time. Not the
   12 s/frame 3D render, and not hours of unique frames.
3. **Paused, preserved:** the source acquisition brief (Commons ride files,
   paid routes), real-footage episodes, the Chicago journey v1 compilation.
4. **Not authorised:** new episodes, long renders, GPU rental,
   subscriptions, purchases, vendor contact, publication, merging PR #1.
5. **Honesty rule:** the look is described as a stylised virtual journey
   built from map data, never as real footage.
6. **Barcelona and Tokyo:** not started.
7. **Coordination:** GitHub PR #1 is the shared channel; this file is the
   decision record.
8. **Large masters:** no more large media in Git history. The four parts of
   the journey v1 master stay in place; history is not rewritten. Rebuild:
   `cat chicago_journey_v1.mp4.part* > chicago_journey_v1.mp4 && sha256sum
   -c SHA256SUMS` in `output/masters/chicago_journey_v1/`.
9. **Wording rule:** audit clips were probed and frame-sampled, not watched
   at speed; reports say so.

## Log

| Date | Decision | Why | Replaces |
|---|---|---|---|
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
| Chicago seamless loop v1, 90 s, stylised parallax | `output/samples/chicago_loop_v1_720p.mp4`, `scenes/chicago_loop_v1.json`, `pipeline/parallax_loop.py` | Awaiting owner review of the visual |
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
