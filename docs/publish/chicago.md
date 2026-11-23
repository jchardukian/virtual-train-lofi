# Chicago — publish package (draft, NOT published)

Nothing here is posted. Publishing needs the owner's explicit go-ahead in the
agent session, and the open items at the bottom closed.

## Long-form (YouTube, 5:00, 1920x1080)

**Title options**
1. Chicago by Train 🚆 Lofi Window Ride at Golden Hour | 5-Minute Chillhop Journey
2. A Cozy Train Ride Through Chicago | Lofi Beats & Illustrated City Views
3. Chicago Riverfront to the City's Edge | Relaxing Lofi Train Window

**Description**
```
Settle into a window seat for a slow, golden-hour train ride through an illustrated Chicago: the river and Marina City, the towers of the Loop, the lakefront, brick neighbourhoods and out to the edge of the city, with warm chillhop the whole way.

This is a stylised, illustrated journey inspired by Chicago. It is not a real route or real footage, and the artwork was created with AI image tools.

0:00 Riverfront and Marina City
1:00 The Loop: Wrigley Building, Tribune Tower, Willis Tower
2:00 Lakefront: Navy Pier, Field Museum, Buckingham Fountain, Adler Planetarium
3:00 Neighbourhoods
4:00 The edge of the city

Music: "Warm Horizon" and "Daydreams" by Purrple Cat (purrplecat.com), licensed under CC BY 4.0 (creativecommons.org/licenses/by/4.0/). Tracks were trimmed and cross-faded.

Next stop: coming soon.

#lofi #chicago #trainride #chillhop #studymusic
```

**Tags:** lofi, chillhop, chicago, train window, train ride, cozy, study music, relaxing music, illustrated, anime style, golden hour, chicago river, marina city, virtual train

**Settings:** category Music; not made for kids; altered/synthetic content flag: off (owner decision, 2026-11-22). The description states the artwork is illustrated and not real footage.

**Thumbnail:** `output/samples/chicago_thumbnail.jpg` (frame at 0:32, Marina City and the bridge, with title text).

## Short 1 (0:25, 1080x1920) — riverfront
**Title:** Golden hour train ride past Marina City 🚆 #lofi #chicago #shorts
**Description:** A cozy illustrated train-window ride along the Chicago River. Stylised, AI-illustrated artwork; not real footage. Music: "Warm Horizon" by Purrple Cat (purrplecat.com), CC BY 4.0, trimmed.

## Short 2 (0:25, 1080x1920) — lakefront
**Title:** Lofi train window: Chicago's lakefront at sunset 🌇 #lofi #chicago #shorts
**Description:** Field Museum, Buckingham Fountain and the lake from a train window. Stylised, AI-illustrated artwork; not real footage. Music: "Warm Horizon" by Purrple Cat (purrplecat.com), CC BY 4.0, trimmed.

(TikTok is deferred; these two clips are YouTube Shorts only for now.)

## Open before publishing
- [ ] Owner's explicit go-live in the agent session
- [ ] Owner has watched the final master at playback speed
- [ ] Which account and tool publishes (the session has a scheduling tool connected; which channels it reaches has not been checked)
- [ ] Provider terms and platform AI-content policies read in full
- [ ] Landmark check by someone who knows Chicago
- [ ] Masters stored somewhere durable

## Launch preflight — 2026-11-22 (nothing scheduled)

**Destination:** Buffer channel "Lofi Train POV" (YouTube), id `6b037e988541f09ecb6cd063`,
https://www.youtube.com/channel/UCLjE-J4o5HSXz1cCokDdZbQ, time zone America/Chicago, connected,
queue empty. The owner should confirm that URL is @lofitrainpov; the tool does not show the handle.

**What the scheduling tool can do**
- Upload a video to YouTube with title, description, category, privacy, made-for-kids flag, an
  AI-generated flag and a notify-subscribers switch, at a set time.
- It has no separate Shorts type: a vertical clip under three minutes is treated as a Short by YouTube.
- It takes the video from a **public direct file URL**. It cannot take a file from this machine.
- Custom thumbnail image: no field for one (only a frame offset). The thumbnail would be set in YouTube Studio.

**Blocker: the master has no public URL.** The 1080p master (270 MB) is on a temporary disk and in files
sent to the owner. It is too large for Git and no hosting is approved. The two full-resolution Shorts
(15 MB each) have the same problem. Ways forward, all free, owner's choice:
1. Owner uploads the three files in YouTube Studio by hand, using the text in this file. Simplest.
2. Owner puts the three files somewhere that gives a direct public link and names it; then the tool can schedule them.
3. Publish the 720p preview already public in this repository. Not recommended: lower quality than the master.

**Proposed first day (America/Chicago), for approval, not scheduled**
| When | What |
|---|---|
| Mon 23 Nov 2026, 12:00 | Short 1 (riverfront) |
| Mon 23 Nov 2026, 18:00 | Chicago long-form |
| Mon 23 Nov 2026, 20:30 | Short 2 (lakefront) |

Settings: category Music (10), public, not made for kids, AI-generated flag off (owner decision), standard YouTube licence.

**Limit enforcement:** `pipeline/publish_preflight.py` passes for this plan only once go-live is set
and the channel id above is supplied; it refuses a second long-form, a third Short, any TikTok post,
or any other channel. It is called by hand; there is no automatic scheduler.
