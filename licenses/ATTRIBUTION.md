# Asset attribution and licence records

## Used in the Chicago 3D prototype (`scenes/chicago_3d.json`)

| Asset | Source | Licence | What we use | Obligation |
|---|---|---|---|---|
| Building footprints, heights, river banks, bridges, roads, parks, CTA track centre-lines | OpenStreetMap, fetched via the OSM map API (`pipeline/fetch_osm.py`), bbox -87.646,41.874,-87.616,41.894 | ODbL 1.0 | Geometry for the 3D scene | Credit "© OpenStreetMap contributors" in every video description. The rendered video is a *Produced Work* (no share-alike on the video); the extracted geometry file `data/chicago_loop_geometry.json` is a *Derivative Database* and stays under ODbL if it is ever published. |
| Sky HDRI `kloofendal_48d_partly_cloudy_puresky` (4k) and textures `red_brick_03`, `brick_wall_001`, `concrete_wall_008`, `concrete_tile_facade`, `asphalt_01` (2k) | Poly Haven, fetched by `pipeline/fetch_assets.py` | CC0 1.0 | Lighting, sky and wall surface detail in the v2 scene | None (no attribution required; commercial use allowed) |
| Chicago municipal flag design | Drawn in code (`pipeline/blender_scene.py`) | Public domain (municipal flag, 1917/1939) | Flags on bridge houses | None |
| Blender 3.6 LTS | blender.org | GPL (tool only; output is unencumbered) | Renderer | None for output |
| Inter typeface | rsms.me/inter | SIL OFL 1.1 | Overlay text | None for rendered text |
| Facade colours, window grids, trees, boats, sky, train window frame | Generated procedurally by this repo's code | Owned by the project | Surface appearance | None |

Suggested description line:

> Scenery built from map data © OpenStreetMap contributors (ODbL). This is a
> stylised virtual sightseeing journey, not a recording of a real train ride.

## Identified but NOT used: real footage route (`scenes/chicago.json`)

| Asset | Source | Licence | Status |
|---|---|---|---|
| "Leaving Chicago downtown by CTA green line train 4K" by rollingnet | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Leaving_Chicago_downtown_by_CTA_green_line_train_4K.webm), SHA-1 `b7f84bbb61cc7f45d2c0312b05271a20fed9f80c` | CC BY 3.0 (Commons licence review, 2017) | Could not be downloaded from this environment (Wikimedia HTTP 429 on the cloud IP). Never viewed, never used. |

If it is used later: credit "rollingnet, CC BY 3.0" with a link, state that it
was modified, and keep this record.
