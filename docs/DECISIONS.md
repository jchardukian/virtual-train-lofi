# Decision record

The canonical current direction for Virtual Train Lofi. Newest decision
first. A decision is changed only by a new dated entry that names the one it
replaces; nothing here is reversed silently.

## Current direction (as of 2026-11-22)

1. **Production method:** real, commercially usable footage is the primary
   method. Procedural Blender city production is paused.
2. **Format:** a cinematic virtual train journey — passenger view, exterior
   train shots, landmarks and city scenery — not one continuous five-minute
   passenger recording.
3. **Scaling is on hold.** No further stock-compilation episodes, major
   renders or purchases until an affordable, repeatable, visually consistent,
   commercially usable architecture for about 200 destinations is validated.
   **Approved next step:** a bounded 10-destination supply and consistency
   audit using sources reachable without keys. Not an episode.
3a. **Chicago journey v1 is not approved for publication.** 15 s of passenger
   view in 300 s and mixed seasons and light do not make a coherent premium
   train journey. No further compilations by the same approach until the
   audit reports. Reused-content eligibility is unproven whatever the licences.
4. **Barcelona and Tokyo:** not started.
5. **Money:** nothing is spent, rented or subscribed without owner approval.
6. **PR #1:** stays unmerged until the owner approves.
7. **Coordination:** GitHub is the source of truth. Progress, findings and
   blockers go on PR #1 as comments; code, evidence, benchmarks and licence
   records go on the branch.
8. **Large masters:** no more large media in Git history. The four parts of
   the journey v1 master stay in place for now; history is not rewritten and
   the parts are not deleted (deleting them in a new commit would not shrink
   the repository). Storage is revisited only after a separate durable copy
   is verified. Rebuild: `cat chicago_journey_v1.mp4.part* >
   chicago_journey_v1.mp4 && sha256sum -c SHA256SUMS` in
   `output/masters/chicago_journey_v1/`; SHA-256
   `c5e35d5c8cdd4cc273460952972e8ba8ceeab37da4dac955b8ac3cda43ea45ed`.
9. **Owner inputs:** API keys or the Wikimedia download are not prerequisites.
   If one would remove a documented audit blocker, the report says exactly
   what it unlocks. Credentials are never requested in PR comments.

## Log

| Date | Decision | Why | Replaces |
|---|---|---|---|
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
