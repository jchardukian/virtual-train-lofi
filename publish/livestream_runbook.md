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
Server 2 is now PERMANENT (owner 2026-11-26, review late Jan 2027). Never delete it.

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
- Renderer: STREET_SPEED 7 px/s (owner: almost the skyline pace of 5); close-ups off at this speed. Every city rebuilds with it.
- Server 1: run10 (paris nyc kansas_city dubai detroit london anchorage barcelona bangkok charleston boston) -> run11 (vancouver austin san_diego savannah washington_dc) -> run12 (chicago miami las_vegas atlanta banff cape_town edinburgh hallstatt hong_kong honolulu istanbul kyoto lake_bled lisbon los_angeles marrakech)
- Server 2: lofi-stream-1126 (stream 1, built from current versions) -> run9 (singapore rio san_francisco amsterdam new_orleans cairo seattle san_antonio) -> run10 (mexico_city minneapolis nashville philadelphia phoenix_sedona pittsburgh portland_maine prague reykjavik salt_lake_city santorini seoul sydney tokyo venice)
- Releases from now on use the slowed versions (KC/Dubai/Detroit rebuild early in server 1 run10).

## Decisions 2026-11-25 19:20Z (owner: figure it out, stop asking)
- Stream 1 runs tonight 10:15pm CST as planned (current versions). After it ends, set its saved VOD to PRIVATE so only the corrected (slow-street) versions become evergreen.
- From stream 2 on, streams use only rebuilt (slow-street) cities; stream_day.sh exclude list = cities not yet rebuilt.
- Scheduled long-forms built at the old speed (amsterdam Nov 26, new_orleans Nov 27, cairo Nov 28, seattle Nov 29, san_antonio Nov 30) are swapped with replace_release.py as each rebuild finishes (server 2 run9), then their Buffer posts edited. Do not ask the owner.
- Every city: render and review a moving clip (not only stills) before release.

## 2026-11-25 19:40Z — quality gates now enforced
- preflight.py checks: art + music present, test render, street speed <= cap, see-through gaps (unless gaps_ok reviewed).
- Renderer: street rows (incl. river rows) and close-ups capped at 32 px/s; the fast blurred tree sweep at section changes is OFF.
- After ANY renderer change: verify on each server that builds already running started after the code file changed (ps lstart vs stat); restart those that didn't.
- Before release: pull the city, watch a 20 s moving clip (pipeline output 720p preview) — not just the sheet.

## 2026-11-25 21:40Z — SINGLE LAYER (owner): one picture per city, ~40-50% sky, no street row, no close-ups
- pipeline/single_layer.py converted all 55 configs (backups *.two_layer.json). All rebuild.
- Server 1: unit lofi-build-single (log lofi-build-single.log): kansas_city dubai detroit amsterdam new_orleans cairo seattle san_antonio san_francisco chicago london anchorage barcelona bangkok charleston boston vancouver austin san_diego savannah washington_dc paris nyc miami las_vegas atlanta banff
- Server 2: lofi-stream-1126 (tonight) then lofi-build-single: singapore rio cape_town edinburgh hallstatt hong_kong honolulu istanbul kyoto lake_bled lisbon los_angeles marrakech mexico_city minneapolis nashville philadelphia phoenix_sedona pittsburgh portland_maine prague reykjavik salt_lake_city santorini seoul sydney tokyo venice
- Tonight's stream uses the old two-layer versions; make its VOD private after it ends.
- Swap scheduled long-forms (amsterdam..san_antonio) to single-layer versions as they finish.

## GO-LIVE CHECKLIST (mandatory, every stream) — owner 2026-11-26: double check everything
Before the public start time:
1. Stream file: ffprobe shows h264 1920x1080 30fps AND aac 48000 Hz stereo; silencedetect finds no gap > 3 s.
2. Watch 3 random 20 s clips from the file (incl. one tunnel): picture right, music audible.
3. 20 minutes before start: run a PRIVATE test broadcast for 2 minutes from the same server/command; API must show
   streamStatus active, health good, NO configurationIssues (audio sample rate, resolution, bitrate). Then end it and delete it.
4. Create the public broadcast; start; within 2 minutes re-check API health has no configurationIssues.
5. Only then tell the owner it is live, with the link.
If any step fails: fix it before the start time, never after.

## Streams from Sat Nov 28: three 8-hour streams per day, 24/7 (owner-approved, both servers kept)
Slots CST: 8am-4pm, 4pm-12am, 12am-8am. Each needs its own file (~7-8 h build) — build each one at least 12 h ahead,
alternate servers. Thu Nov 26 7pm stream and Fri Nov 27 streams: 8 h each from the rebuilt cities as available.

## Next phase (owner 2026-11-26): plan the next 50 cities + more songs — WAIT one week: review ~Sun Dec 6 with a performance summary first
Only after: all 55 final cities built and checked, daily releases running hands-off, the three daily streams running
24/7 without intervention for at least a day. Then bring the owner a short plan: proposed 50 cities (variety of
regions, seasons, times of day; no repeats), art cost estimate (~$1.10 per city in OpenAI images, needs the owner's
approval of the total), song plan (structured songs via pipeline/el_song.py, ElevenLabs credits remaining, needs the
owner's OK), build time on the two servers.
- Owner changed this: run everything for a week first. On ~Sun Dec 6 send a one-week summary (views, watch time,
  subscribers, best/worst cities, Short title styles, stream titles/times by viewers) before any new-cities plan.

## Promotion (owner approved all three, 2026-11-26)
- Card: pipeline/promo_card.py burns the 'Departing daily' card into the UPLOADED long-form (last 10 s) and Shorts
  (last 4 s); release_city.py and replace_release.py do it automatically. Built city files and streams stay clean.
- Description line (first line of every long-form description AND every Shorts caption in Buffer):
  "Departing daily: live train rides around the world, 24/7 → youtube.com/@LofiTrainPOV/streams"
- End screens: owner adds in YouTube Studio (no API): Subscribe + playlist "Live Train Rides 🚆 24/7 Lofi"
  (PLbQ1U8WIvfRE). livestream_broadcast.py adds every new broadcast to that playlist.

## Automated stream schedule (set up 2026-11-26)
Slots CST: Fri Nov 27 8am-4pm and 4pm-12am, then from Sat 12am: 12am-8am, 8am-4pm, 4pm-12am every day (24/7).
Stream id = <date>-<HHMM CST> (e.g. 2026-11-27-0800). Scheduled task "Stream slot" fires at 05:25/13:25/21:25 UTC:
 1. go-live for the slot starting at the next :00 UTC (if one is planned): GO-LIVE CHECKLIST above, then
    pipeline/livestream_broadcast.py <id> <start UTC> and write /var/lib/lofitrain/rtmp_<id> on the building server
    (never print it); health check; message the owner the link only when the stream is healthy (first few days; later
    only problems).
 2. start the build for the slot 16 h later (>= 12 h ahead): even slot index = server 1, odd = server 2 (slot index =
    hours since 2026-11-27T14:00Z / 8). Exclude file = every city not in publish/stream_ok.json; rebuild stream.tgz if
    pipeline/livestream_build.py changed. Unit lofi-stream-<id>: MINUTES=480 TRANS_JOBS=2 nice -n 10 stream_day.sh.
 3. clean up the stream that ended: delete work/stream/<id>/ on its server (keep the VOD on YouTube, public, evergreen),
    delete /var/lib/lofitrain/rtmp_<id>; prune work/stream/t files older than 3 days.
Lessons 2026-11-26 (first slot build):
- A 4K city build uses ~7 GB of the 7.7 GB RAM: NEVER run a stream build next to one. Before starting a stream build
  on a server, stop that server's city build units (waiters first, then the running one) and queue every city not yet
  rebuilt (no control/built/<c>.json) on the OTHER server, after its current queue.
- Each stream build runs a private copy: cp livestream/stream_day.sh /usr/local/bin/stream_day_<id>.sh and run that
  (stream_day.sh re-extracts stream.tgz over the repo copy at start; a running bash must never have its file replaced).
  The 2026-11-27-0800 run on server 1 still uses the repo path: do NOT change livestream/stream_day.sh before it ends
  (2026-11-27T22:00Z).
- Every stream gets a cleanup watcher (unit lofi-cleanup-<id>) that deletes work/stream/<id>/stream.mp4, audio.m4a and
  /var/lib/lofitrain/rtmp_<id> 1 min after 'STREAM ENDED' (a 22 GB file per stream; server disk is ~75 GB).
- Timing (server 2, 8 h stream): prep ~10 min/city if not cached, transitions ~34/h with 3 jobs, audio ~2.3 h,
  assemble (full re-encode at 6 Mbps) ~2.5 h.
- Before livestream_broadcast.py: fetch control/pkg/<id>_plan.json and <id>_music_used.json into work/stream/<id>/
  (the description is built from them). Python requests to the Worker need a 'User-Agent: curl/8.5.0' header.
- Private test broadcasts need recordFromStart True (new channels may not disable recording).
- 2026-11-27: Ubuntu's daily unattended upgrade (06:16Z/06:30Z) restarted our systemd-run units through needrestart:
  stream 2 stopped 2.5 h early, a city build was OOM-killed, the 0800 stream build restarted. Disabled on BOTH servers:
  unattended-upgrades.service, apt-daily.timer, apt-daily-upgrade.timer; needrestart set to list-only
  (/etc/needrestart/conf.d/99-lofitrain.conf). Any new server needs the same before it runs anything.
- 2026-11-27: a trickling download hung stream prep for 2 h (urllib timeout is per read). get() now uses curl with
  --max-time 900 and 4 attempts. Never list server processes with full arguments (ps args / --forest): the agent's
  own curl carries the control key; list by name only (pgrep -c, ps -o comm).
- 2026-11-27 ~10:00Z: server 2's downloads THROUGH THE WORKER dropped to ~30 KB/s (server 1: 74 MB/s; server 2's general
  internet: 87 MB/s). Before starting a stream build on a server, time one 90 MB part download through the Worker; if it
  is under 5 MB/s, build that slot on the other server, or start it with only the rides already in work/stream/v
  (exclude everything else) and a stream_day copy without the stream.tgz download line. The 1600 build ran that way.
