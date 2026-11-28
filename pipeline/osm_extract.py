#!/usr/bin/env python3
"""Turn raw OSM tiles into a compact scene-geometry JSON (local metres).

Output: buildings (footprint rings + height/min_height + tags that matter),
water polygons, elevated rail centre-lines, roads and parks.

Usage: python3 pipeline/osm_extract.py scenes/chicago_3d.json
"""
import glob
import json
import math
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
M_PER_LEVEL = 3.6


def num(v):
    if v is None:
        return None
    v = v.strip().lower().replace("m", "").replace(",", ".").strip()
    if v.endswith("'") or "ft" in v:
        try:
            return float(v.replace("ft", "").replace("'", "")) * 0.3048
        except ValueError:
            return None
    try:
        return float(v.split(";")[0])
    except ValueError:
        return None


def main():
    scene = json.loads(pathlib.Path(sys.argv[1]).read_text())
    cfg = scene["osm"]
    lon0, lat0 = cfg["origin"]
    kx = 111320.0 * math.cos(math.radians(lat0))
    ky = 110540.0

    nodes, ways, rels = {}, {}, {}
    files = []
    for rd in cfg.get("raw_dirs", [cfg["raw_dir"]]):   # several fetched areas can be merged into one scene
        files += sorted(glob.glob(str(ROOT / rd / "*.osm")))
    for f in files:
        for el in ET.parse(f).getroot():
            if el.tag == "node":
                nodes[el.get("id")] = (round((float(el.get("lon")) - lon0) * kx, 2),
                                       round((float(el.get("lat")) - lat0) * ky, 2))
            elif el.tag == "way":
                ways[el.get("id")] = ([n.get("ref") for n in el.findall("nd")],
                                      {t.get("k"): t.get("v") for t in el.findall("tag")})
            elif el.tag == "relation":
                rels[el.get("id")] = ([(m.get("type"), m.get("ref"), m.get("role")) for m in el.findall("member")],
                                      {t.get("k"): t.get("v") for t in el.findall("tag")})

    def ring(wid):
        if wid not in ways:
            return None
        pts = [nodes[n] for n in ways[wid][0] if n in nodes]
        return pts if len(pts) >= 3 else None

    def stitch(wids):
        """Join member ways end-to-end into closed rings."""
        segs = [[n for n in ways[w][0] if n in nodes] for w in wids if w in ways]
        segs = [s for s in segs if len(s) >= 2]
        rings = []
        while segs:
            cur = segs.pop(0)
            changed = True
            while cur[0] != cur[-1] and changed:
                changed = False
                for i, s in enumerate(segs):
                    if s[0] == cur[-1]:
                        cur += s[1:]
                    elif s[-1] == cur[-1]:
                        cur += s[-2::-1]
                    elif s[-1] == cur[0]:
                        cur = s[:-1] + cur
                    elif s[0] == cur[0]:
                        cur = s[::-1][:-1] + cur
                    else:
                        continue
                    segs.pop(i)
                    changed = True
                    break
            if len(cur) >= 4:
                rings.append([nodes[n] for n in cur])
        return rings

    def bld(tags, pts, part):
        h = num(tags.get("height")) or num(tags.get("building:height"))
        lv = num(tags.get("building:levels"))
        if h is None and lv:
            h = lv * M_PER_LEVEL
        mh = num(tags.get("min_height"))
        if mh is None and num(tags.get("building:min_level")):
            mh = num(tags.get("building:min_level")) * M_PER_LEVEL
        return {"p": pts, "h": h, "mh": mh or 0.0, "part": part, "name": tags.get("name"),
                "shape": tags.get("roof:shape"), "kind": tags.get("building") or tags.get("building:part"),
                "colour": tags.get("building:colour"), "material": tags.get("building:material")}

    out = {"buildings": [], "water": [], "rail": [], "roads": [], "parks": []}
    used_outline = set()
    for rid, (members, tags) in rels.items():
        if tags.get("type") == "building":
            for t, ref, role in members:
                if role == "outline":
                    used_outline.add(ref)
    for wid, (nds, tags) in ways.items():
        closed = len(nds) > 3 and nds[0] == nds[-1]
        pts = ring(wid)
        if not pts:
            continue
        if closed and (tags.get("building") or tags.get("building:part")):
            part = bool(tags.get("building:part")) and tags.get("building:part") != "no"
            if tags.get("building") in ("roof",) or tags.get("location") == "underground":
                continue
            out["buildings"].append(bld(tags, pts, part))
        elif closed and (tags.get("natural") == "water" or tags.get("waterway") == "riverbank"):
            out["water"].append(pts)
        elif closed and tags.get("leisure") in ("park", "garden"):
            out["parks"].append(pts)
        elif tags.get("railway") in ("subway", "light_rail", "rail") and tags.get("tunnel") != "yes":
            out["rail"].append({"p": pts, "kind": tags["railway"], "bridge": tags.get("bridge"),
                                "layer": tags.get("layer"), "name": tags.get("name"), "id": wid})
        elif tags.get("highway") in ("motorway", "trunk", "primary", "secondary", "tertiary",
                                     "residential", "unclassified", "motorway_link", "service"):
            if tags.get("tunnel") == "yes" or tags.get("highway") == "service" and not tags.get("name"):
                continue
            out["roads"].append({"p": pts, "kind": tags["highway"], "name": tags.get("name"),
                                 "lanes": num(tags.get("lanes")), "layer": tags.get("layer"),
                                 "bridge": tags.get("bridge")})
    seen = set()
    for rid, (members, tags) in rels.items():
        if tags.get("type") != "multipolygon":
            continue
        outers = [ref for t, ref, role in members if t == "way" and role in ("outer", "")]
        key = tuple(sorted(outers))
        if key in seen:
            continue
        seen.add(key)
        if tags.get("building") or tags.get("building:part"):
            for r in stitch(outers):
                out["buildings"].append(bld(tags, r, bool(tags.get("building:part"))))
        elif tags.get("natural") == "water" or tags.get("waterway") == "riverbank":
            for r in stitch(outers):
                out["water"].append(r)

    dest = ROOT / cfg.get("geometry", "data/chicago_loop_geometry.json")
    dest.write_text(json.dumps(out, separators=(",", ":")))
    print({k: len(v) for k, v in out.items()}, dest, dest.stat().st_size)


if __name__ == "__main__":
    main()
