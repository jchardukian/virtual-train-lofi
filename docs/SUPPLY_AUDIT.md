# Ten-destination footage supply audit

> **Reading note (added after review):** "verified" in this report means
> downloaded, probed with ffprobe and sampled at four still frames. No clip
> was watched at speed, so motion quality and whole-shot suitability are
> unverified. The result is a negative screening, not proof that no free
> footage exists: 182 candidates were unfetched, Pixabay was unsearched and
> the Commons candidates were unviewed at the time of writing.

Scope approved on PR #1 (2026-11-22): how many **verified playable** seconds
of commercial-use footage at 1080p or better exist per city, by category,
from sources reachable without API keys. No episode was produced.

## Method

* Source: Pexels (Pexels License: commercial use and modification allowed).
  Its website is blocked on the build machine, so clips were found through
  web search restricted to pexels.com (10 searches per city) and fetched
  from the public file CDN.
* Every counted clip was downloaded, probed with ffprobe and viewed as four
  frames. A clip counts for a city only if the frames show that city, or the
  title names it and nothing in frame contradicts it.
* Main totals: landscape, at least 1920x1080. Vertical phone clips are
  reported separately.
* Evidence: `data/audit/<city>.json` (one record per clip: source, file URL,
  size, duration, category, what identifies the city, season, time of day,
  camera, people/brands) and `data/audit/sheets/<city>/` (the frames viewed).

## Results — verified, landscape, 1080p or better (seconds)

| City | Passenger view | Exterior trains | Landmarks | Clips viewed | Not this city / unconfirmed | Unfetched candidates |
|---|---|---|---|---|---|---|
| Tokyo | 0 | 63.8 | 243.3 | 27 | 12 | 20 |
| Barcelona | 0 | 0 | 150.6 | 18 | 10 | 15 |
| London | 0 | 21.7 | 263.7 | 20 | 12 | 20 |
| New York | 0 | 44.7 | 187.2 | 22 | 8 | 13 |
| Paris | 0 | 21.2 | 76.9 | 21 | 10 | 24 |
| Istanbul | 0 | 10.1 | 93.1 | 19 | 5 | 29 |
| Hong Kong | 0 | 68.3 | 105.6 | 17 | 5 | 12 |
| Bangkok | 0 | 33.3 | 53.2 | 14 | 5 | 11 |
| Sydney | 0 | 0 | 20.0 | 17 | 12 | 20 |
| Rio de Janeiro | 0 | 0 | 283.9 | 17 | 6 | 18 |
| **Total** | **0** | **263.1** | **1,477.5** | **192** | **85** | **182** |
| Chicago (earlier audit, for reference) | 0 | 101.7 | about 220 | 27 | 3 | 7 |

Vertical clips, all ten cities: passenger view 17.5 s (one Paris clip),
exterior trains 90.4 s, landmarks 319.3 s. Chicago adds 23.5 s of vertical
passenger view.

Tokyo's split between exterior and landmark is an estimate: one 141 s night
aerial of a train bridge was divided by eye (39 s / 102 s).

## What the clips are actually like

* **Passenger view:** none, in any of ten cities, in landscape. Every
  generic "view from train window" clip that was fetched turned out to be
  somewhere else (Kuala Lumpur repeatedly, Japan outside Tokyo, Zurich,
  rural Europe).
* **Exterior trains:** 0 to 68 s per city, median 21.5 s; three cities have
  none. Much of it is weak: underground platforms with no city visible
  (Paris), sped-up night clips dominated by a brand logo (Hong Kong), a
  black-and-white clip and identifiable faces (New York), one clip in a
  suburb (Bangkok).
* **Landmarks:** plentiful but one-note. Rio is all drone aerials; Paris is
  all time-lapses; Tokyo and Hong Kong are mostly night; London is the same
  three monuments.
* **Mislabelling is the norm.** 85 of 192 viewed clips (44%) were not the
  city searched for or could not be confirmed. Titles and tags cannot be
  trusted; every clip has to be watched.
* **Consistency:** only three cities have a block of footage that holds one
  look: Barcelona (daytime landmarks, about 150 s), Rio (sunny drone, about
  220 s), Tokyo (night landmarks, about 165 s). None includes a train.

## Limits of this evidence

1. **Recent uploads are unmeasured.** The CDN file name could not be
   resolved for any Pexels clip with an id above roughly 20-26 million. 182
   candidates are therefore unviewed and counted as zero. All totals are
   floors. Among those 182, the pages whose titles suggest passenger view
   are few: one London Underground ride and two Hong Kong tram clips (both
   listed as vertical).
2. **Web search is not Pexels search.** A correctly located clip with a
   generic title can exist unseen.
3. **One catalogue only.** Pixabay was not searched (site blocked, API needs
   a key). Mixkit and Coverr were checked for Chicago only.
4. **Frames, not playback.** Steadiness and people/brand notes come from four
   stills per clip.
5. **Some files are smaller than their name says** (720p inside a
   "1920_1080" file name); those were excluded.

## Unviewed candidates on Wikimedia Commons (metadata only)

`data/audit/commons_candidates.json`, produced by
`pipeline/audit/commons_scan.py`. Commons' file host blocks the build
machine, so **none of this has been seen**. Title matches at landscape
1080p+ under a free commercial licence:

| City | Files | Minutes | What the titles suggest |
|---|---|---|---|
| Chicago | 9 | 47 | CTA and Metra ride videos, an Amtrak dome view |
| Barcelona | 3 | 27 | A metro video, a funicular video, a sleeper-train vlog |
| New York | 6 | 25 | Mostly drone aerials of subway trains on bridges |
| Tokyo | 1 | 12 | A bullet-train trip to Kyoto, not the city |
| Sydney | 1 | 7 | "Sydney Train Rides" |
| London, Hong Kong | 1 each | 3 each | A sleeper-train vlog; an airport people-mover |
| Paris, Istanbul, Bangkok, Rio | 0 | 0 | — |

Most are YouTube imports under CC BY 3.0 and read like travel vlogs, which
usually means talking heads, burned-in titles and music. Expect a small
fraction to be clean passenger view.

## Answers to the audit questions

**Is a strict train-centred format feasible from free stock?** No. Zero
verified seconds of landscape passenger view across ten major cities and 192
viewed clips. Even counting exterior train shots, the best city has 68 s
against a 300 s episode.

**Is the mixed "train spine" format feasible?** Not at a premium standard.
A five-minute episode needs roughly 300 s of coherent footage; no city
reaches that in verified material, and the three cities with a coherent
block have no train in it.

**Projection for 20 and 200 cities.** The evidence supports a direction,
not a number:
* Supply of free passenger-view footage per city is at or near zero for
  famous cities, and will not be better for less-filmed ones. Twenty cities
  cannot be built this way; 200 certainly cannot.
* Labour: each city took 15-35 minutes of automated search, download and
  frame review to reach "not enough". A person watching clips properly would
  take longer. At 200 cities that is on the order of 100 hours of sourcing
  with a mostly negative result.
* I am not extrapolating a seconds-per-city figure for the wider catalogue:
  182 unfetched candidates and an unsearched second catalogue make that
  unsound.

**What would change the picture, precisely:**
| Action | Unlocks |
|---|---|
| Free Pexels API key | File URLs for the 182 unfetched candidates and true catalogue search (by query, orientation and size) instead of a web index. Would firm up the floors; unlikely to turn zero passenger view into minutes. |
| Free Pixabay API key | A second catalogue, unsearched so far. |
| Wikimedia files downloaded on a normal connection | First look at the only multi-minute ride candidates: Chicago (47 min listed), Barcelona (27), New York (25). Decides whether Commons ride videos are usable at all. |
| Paid stock or commissioned filming | Not priced. The only route that can supply consistent multi-minute passenger view per city. |

## Conclusion

Free stock footage cannot supply this channel's core shot. The realistic
choices are: (a) change the format so trains are an occasional motif in a
city-scenery film; (b) pay for or commission passenger-view footage; or
(c) accept a stylised, generated look. That is a direction decision for the
owner.
