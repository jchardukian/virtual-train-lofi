# Quality-control checklist

Run for every segment before it is published. Part 1 is automated
(`pipeline/qc.py`, exits non-zero on failure). Part 2 needs a person — the
contact sheet (`*.contact.jpg`) and the video itself are the evidence.

## 1. Automated (pipeline/qc.py)

| Check | Threshold |
|---|---|
| Codec / container | H.264 in MP4, yuv420p |
| Resolution | 1920x1080 |
| Frame rate | >= 30 fps |
| Black frames | none outside the intentional fade in/out |
| Frozen frames | none >= 0.5 s (would mean a slideshow or a stall) |
| Camera jitter | RMS < 1.5 px per axis after removing 1 s average motion |
| Rotation jitter | RMS < 0.05 degrees |

The jitter numbers come from sparse optical flow, so heavy foreground
occlusion (a girder passing the window) inflates them. A failure here means
"look at this segment", not automatically "reject".

## 2. Human review

Geography
- [ ] Route is identified (line, direction, start/end stations) and written in the scene file
- [ ] Every landmark named in the scene file is actually visible at the stated timestamp
- [ ] Nothing in frame contradicts the stated city (signage, vehicles, skyline)
- [ ] Someone who knows the city has signed off (Chicago: owner)

Viewing comfort
- [ ] No sudden pans, zooms or handheld lurches
- [ ] Horizon stays level
- [ ] Speed looks like a train, not a time-lapse
- [ ] Stations/stops are either pleasant or trimmed out
- [ ] Watchable on a large screen for the full length without discomfort

Image quality
- [ ] No warping or "jelly" from stabilisation
- [ ] No black borders creeping in at the edges
- [ ] Window reflections, dirt or glare are not distracting
- [ ] No visible compression blocking in sky or shadows
- [ ] No identifiable passengers' faces held in frame

Presentation
- [ ] Location label is correct, small and legible
- [ ] Fade in/out is clean
- [ ] Attribution text for the source is ready for the video description

Rights
- [ ] Source licence allows commercial reuse and derivatives (CC BY, CC0, PD)
- [ ] Licence, author, URL and file hash recorded in `licenses/`
