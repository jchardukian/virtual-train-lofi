# Current build + stream plan (supersedes the hourly check-in text where they differ) — 2026-11-25 05:20Z

Server 2 (177531685): run7 (paris los_angeles miami las_vegas istanbul hallstatt) -> run8 (chicago, new art)
-> lofi-stream-1126 (livestream/stream_day.sh 2026-11-26 2026-11-26T04:15:00Z; log stream_2026-11-26.log;
prints 'STREAM FILE READY', then waits for /var/lib/lofitrain/rtmp_2026-11-26 and streams at the start time)
-> run9 rebuilds after the stream file is ready (singapore rio san_francisco amsterdam new_orleans cairo seattle san_antonio).
Server 1 (177414097): run6..run9 main list -> run10 rebuilds (kansas_city dubai detroit london anchorage barcelona bangkok charleston boston) -> run11 (vancouver austin san_diego savannah washington_dc nyc).

Stream 1: Wed Nov 25 10:15pm CST = 04:15Z Nov 26, built and sent from SERVER 2.
- When STREAM FILE READY: server 2 PUTs a ~90 s preview + plan.json + music_used.json to control/pkg/; copy plan/music_used to
  work/stream/2026-11-26/ here; send the owner the preview.
- From ~04:05Z Nov 26 poll until live streaming is enabled, run `python3 pipeline/livestream_broadcast.py 2026-11-26 <start>`,
  write the rtmp URL from work/stream/2026-11-26/broadcast.json to server 2 /var/lib/lofitrain/rtmp_2026-11-26 (never print/commit).
- Tell the owner the watch link once live.
Stream 2: Thu Nov 26 7-11pm CST = 01:00Z Nov 27 (day 2026-11-27): stream_day.sh on whichever server is free.
Delete server 2 only after stream 1 ended and its rebuilds are done.

## Standing rules (owner 2026-11-25: get it right the first time)
1. Nothing is queued until `pipeline/preflight.py <city>` passes ON THE SERVER that will build it (art, music, test render).
2. Every change to a running system is verified by reading back its actual state (running processes, file contents) — never assumed.
3. Waiting systemd jobs read their script once at start: to change a queued list, rewrite the script AND restart the unit, then verify with pgrep.
4. Every sheet is reviewed before release; anything questionable is fixed before it builds, not after.
5. Morning report: facts only — what is done, what is not, the time it will be done.

## Content plan (owner 2026-11-25) — see publish/limits.json content_plan
- Daily until every city is posted (~50 days): 1 city long-form 11:00 CT + 2 Shorts 14:30/20:30 CT, plus 1 livestream.
- After that: if a new city batch exists, keep going with it; otherwise no more 5-min long-forms — Shorts ending with the tunnel + 1 livestream per day.

## 2026-11-25 19:10Z — street speed fix (owner: street row raced past the skyline, sky showing through in SF)
- Renderer: STREET_SPEED 32 px/s cap (was ~83). Every city rebuilds with it.
- Server 1: run10 (paris nyc kansas_city dubai detroit london anchorage barcelona bangkok charleston boston) -> run11 (vancouver austin san_diego savannah washington_dc) -> run12 (chicago miami las_vegas atlanta banff cape_town edinburgh hallstatt hong_kong honolulu istanbul kyoto lake_bled lisbon los_angeles marrakech)
- Server 2: lofi-stream-1126 (stream 1, built from current versions) -> run9 (singapore rio san_francisco amsterdam new_orleans cairo seattle san_antonio) -> run10 (mexico_city minneapolis nashville philadelphia phoenix_sedona pittsburgh portland_maine prague reykjavik salt_lake_city santorini seoul sydney tokyo venice)
- Releases from now on use the slowed versions (KC/Dubai/Detroit rebuild early in server 1 run10).
