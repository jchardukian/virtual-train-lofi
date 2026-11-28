#!/usr/bin/env python3
"""Build render-ready meshes (npz) from the extracted OSM geometry.

Everything stays at its real surveyed position: building footprints and
heights, river banks, bridges and the CTA track centre-lines come straight
from OpenStreetMap. Only surface appearance (facade colours, window grids)
is invented, because OSM does not carry it.

Usage: python3 pipeline/build_meshes.py scenes/chicago_3d.json
"""
import hashlib
import json
import math
import pathlib
import sys

import mapbox_earcut as earcut
import numpy as np
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import chicago_landmarks as CL  # noqa: E402

MASONRY = [(0.46, 0.25, 0.18), (0.62, 0.53, 0.42), (0.74, 0.69, 0.60), (0.50, 0.47, 0.44),
           (0.52, 0.30, 0.21), (0.63, 0.60, 0.55), (0.38, 0.24, 0.19), (0.78, 0.75, 0.68)]
GLASS = [(0.20, 0.33, 0.42), (0.16, 0.26, 0.34), (0.28, 0.40, 0.44), (0.12, 0.14, 0.17),
         (0.30, 0.36, 0.42), (0.22, 0.30, 0.30), (0.36, 0.30, 0.24)]
# name substring -> (colour, style)
# style: 0 masonry punched windows, 0.12 brick, 0.5 modernist piers + ribbon glass,
#        0.75 Miesian dark steel-and-glass grid, 1 glass curtain wall
LANDMARKS = {
    "willis tower": ((0.035, 0.035, 0.04), 1), "trump international": ((0.50, 0.62, 0.70), 1),
    "marina city": ((0.80, 0.76, 0.68), 0), "merchandise mart": ((0.82, 0.78, 0.69), 0),
    "333 wacker": ((0.18, 0.42, 0.36), 1), "aon center": ((0.88, 0.88, 0.86), 0),
    "river point": ((0.30, 0.46, 0.56), 1), "wolf point": ((0.34, 0.46, 0.54), 1),
    "77 west wacker": ((0.82, 0.82, 0.80), 0), "chicago board of trade": ((0.74, 0.70, 0.62), 0),
    "boeing": ((0.30, 0.34, 0.38), 1), "civic opera": ((0.78, 0.74, 0.66), 0),
    "leo burnett": ((0.42, 0.44, 0.42), 0), "225 west wacker": ((0.60, 0.60, 0.58), 0),
    "191 north wacker": ((0.30, 0.42, 0.48), 1), "155 north wacker": ((0.34, 0.46, 0.52), 1),
    "110 north wacker": ((0.36, 0.48, 0.56), 1), "lasalle - wacker": ((0.76, 0.72, 0.64), 0),
    "35 east wacker": ((0.84, 0.80, 0.70), 0), "wrigley": ((0.92, 0.90, 0.86), 0),
    "tribune": ((0.74, 0.70, 0.62), 0), "300 north lasalle": ((0.34, 0.44, 0.50), 1),
    "reid": ((0.47, 0.20, 0.14), 0.12), "kemper": ((0.20, 0.22, 0.24), 1),
    "330 north wabash": ((0.030, 0.030, 0.034), 0.75), "321 north clark": ((0.10, 0.13, 0.17), 0.75),
    "353 north clark": ((0.30, 0.42, 0.50), 1), "westin": ((0.52, 0.42, 0.33), 0.5),
    "helene curtis": ((0.62, 0.60, 0.55), 0), "amli": ((0.36, 0.44, 0.50), 1),
    "london guarantee": ((0.76, 0.72, 0.64), 0), "london house": ((0.76, 0.72, 0.64), 0),
    "royal sonesta": ((0.40, 0.46, 0.50), 1), "club quarters": ((0.70, 0.66, 0.58), 0),
    "kinzie hotel": ((0.50, 0.30, 0.22), 0.12), "sterling": ((0.55, 0.52, 0.48), 0.5),
}


def h01(key, salt=""):
    return int(hashlib.md5(f"{key}{salt}".encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def poly(pts):
    try:
        p = Polygon(pts)
    except Exception:  # noqa: BLE001
        return None
    if not p.is_valid:
        p = make_valid(p)
        if p.geom_type != "Polygon":
            polys = [g for g in getattr(p, "geoms", []) if g.geom_type == "Polygon"]
            if not polys:
                return None
            p = max(polys, key=lambda g: g.area)
    return p if p.area > 4 else None


def tri(p):
    """Triangulate a shapely polygon (with holes) -> (verts Nx2, tris Mx3)."""
    rings = [np.array(p.exterior.coords)[:-1]] + [np.array(r.coords)[:-1] for r in p.interiors]
    v = np.vstack(rings).astype(np.float64)
    ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
    t = earcut.triangulate_float64(v, ends).reshape(-1, 3)
    return v, t


class Mesh:
    """Non-indexed polygon soup with per-corner uv and per-corner colour."""

    def __init__(self):
        self.v, self.uv, self.col, self.sizes, self.uv2 = [], [], [], [], []
        self.aux = (0.0, 0.0)  # per-building constants written to the second UV layer

    def face(self, verts, uvs=None, col=(1, 1, 1, 1)):
        n = len(verts)
        self.uv2.extend([self.aux] * n)
        self.v.extend(verts)
        self.uv.extend(uvs if uvs is not None else [(0.0, 0.0)] * n)
        self.col.extend([col] * n)
        self.sizes.append(n)

    def flat(self, p, z, col=(1, 1, 1, 1), uv_scale=1.0):
        for g in (p.geoms if hasattr(p, "geoms") else [p]):
            if g.geom_type != "Polygon" or g.area < 0.5:
                continue
            v, t = tri(g)
            for a, b, c in t:
                pts = [v[a], v[b], v[c]]
                self.face([(x, y, z) for x, y in pts], [(x * uv_scale, y * uv_scale) for x, y in pts], col)

    def walls(self, p, z0, z1, col=(1, 1, 1, 1), bay=1.0, floor=1.0):
        for g in (p.geoms if hasattr(p, "geoms") else [p]):
            if g.geom_type != "Polygon":
                continue
            for r in [g.exterior] + list(g.interiors):
                c = np.array(r.coords)
                if r.is_ccw is False:
                    c = c[::-1]
                if r is not g.exterior:
                    c = c[::-1]
                d = 0.0
                for (x0, y0), (x1, y1) in zip(c[:-1], c[1:]):
                    L = math.hypot(x1 - x0, y1 - y0)
                    if L < 0.05:
                        continue
                    self.face([(x0, y0, z0), (x1, y1, z0), (x1, y1, z1), (x0, y0, z1)],
                              [(d / bay, z0 / floor), ((d + L) / bay, z0 / floor),
                               ((d + L) / bay, z1 / floor), (d / bay, z1 / floor)], col)
                    d += L

    def box_between(self, a, b, w, z0, z1, col=(1, 1, 1, 1)):
        """Axis-free box along segment a->b (xy), width w, from z0 to z1."""
        ls = LineString([a, b]).buffer(w / 2, cap_style=2)
        self.flat(ls, z1, col)
        self.walls(ls, z0, z1, col)

    def save(self, path):
        np.savez_compressed(path, v=np.array(self.v, np.float32), uv=np.array(self.uv, np.float32),
                            uv2=np.array(self.uv2, np.float32),
                            col=np.array(self.col, np.float32), sizes=np.array(self.sizes, np.int32))
        return len(self.sizes)


def offset_line(pts, d):
    """Polyline offset to the left by d metres (negative = right)."""
    ls = LineString(pts).parallel_offset(abs(d), "left" if d > 0 else "right", join_style=2)
    if ls.geom_type != "LineString":
        ls = max(ls.geoms, key=lambda g: g.length)
    c = list(ls.coords)
    if math.dist(c[0], pts[0]) > math.dist(c[-1], pts[0]):
        c = c[::-1]
    return c


def resample(pts, step):
    ls = LineString(pts)
    n = max(2, int(ls.length / step) + 1)
    return [ls.interpolate(i / (n - 1), normalized=True).coords[0] for i in range(n)]


def main():
    scene = json.loads(pathlib.Path(sys.argv[1]).read_text())
    geo = json.loads((ROOT / scene["osm"].get("geometry", "data/chicago_loop_geometry.json")).read_text())
    out = ROOT / scene.get("mesh_dir", "work/meshes")
    out.mkdir(parents=True, exist_ok=True)
    rz = scene["rail"]["rail_top_z"]
    stats = {}

    water_edge = unary_union([p for p in (poly(w) for w in geo["water"]) if p is not None]).buffer(0)

    # ---------------- buildings ----------------
    items = []
    for i, b in enumerate(geo["buildings"]):
        if i in scene.get("exclude_buildings", []):      # footprints the fictional track would cut through
            continue
        p = poly(b["p"])
        if p is not None:
            items.append((i, b, p))
    parts = [(i, b, p) for i, b, p in items if b["part"]]
    walls, roofs, detail = Mesh(), Mesh(), Mesh()
    n_b = 0
    marina, houses, flags = [], [], []
    for i, b, p in items:
        nm = (b["name"] or "").lower()
        if "marina city" in nm:
            marina.append(p)
        elif "bridgehouse" in nm or (p.area < 70 and (b["h"] or 0) < 26 and not b["part"] and p.distance(water_edge) < 6):
            houses.append((nm, p))
    house_ids = {id(q) for _, q in houses}
    marina_zone = unary_union([q.buffer(3) for q in marina]) if marina else None
    for i, b, p in items:
        nm = (b["name"] or "").lower()
        if "marina city" in nm or id(p) in house_ids:
            continue
        if marina_zone is not None and b["part"] and marina_zone.contains(p.representative_point()):
            continue
        lm = None
        if b["name"]:
            lm = next((v for k, v in LANDMARKS.items() if k in b["name"].lower()), None)
        if not b["part"]:
            inside = [q for q in parts if p.buffer(1.5).contains(q[2].representative_point())]
            for q in inside:  # parts inherit the parent's landmark look
                q[1]["_lm"] = lm or q[1].get("_lm")
                q[1]["_parent_h"] = b["h"]
            if inside and sum(q[2].area for q in inside if not q[1]["mh"]) > 0.5 * p.area:
                continue
        lm = lm or b.get("_lm")
        if lm is None and (b.get("kind") == "bridge_house" or (p.area < 160 and (b["h"] or 99) < 26 and p.distance(water_edge) < 14)):
            lm = ((0.70, 0.67, 0.60), 0)  # Chicago's limestone bridge houses
        h = b["h"]
        if h is None:
            h = b.get("_parent_h") or (12 + 14 * h01(i, "h"))
        if h - b["mh"] < 0.5:
            continue
        if lm:
            col, style = lm
        elif h > 95 or (h > 40 and h01(i, "s") < 0.45):
            col, style = GLASS[int(h01(i, "c") * len(GLASS)) % len(GLASS)], (0.75 if h01(i, "m") < 0.2 else 1)
        elif h > 45 and h01(i, "s") < 0.75:
            col, style = MASONRY[int(h01(i, "c") * len(MASONRY)) % len(MASONRY)], 0.5
        else:
            k = int(h01(i, "c") * len(MASONRY)) % len(MASONRY)
            col, style = MASONRY[k], (0.12 if k in (0, 4, 6) else 0)
        j = 0.92 + 0.16 * h01(i, "j")
        col = tuple(min(1.0, c * j) for c in col)
        bay = {1: 1.5, 0.75: 1.6, 0.5: 2.4}.get(style, 3.4 + 1.6 * h01(i, "b"))
        floor = 3.9 if style >= 0.5 else 3.5 + 0.5 * h01(i, "f")
        walls.aux = ((h - b["mh"]) / floor, h01(i, "r"))
        if p.exterior.is_ccw is False:
            p = Polygon(list(p.exterior.coords)[::-1], [list(r.coords) for r in p.interiors])
        walls.walls(p, b["mh"], h, (*col, float(style)), bay, floor)
        roofs.flat(p, h, (*[c * 0.55 + 0.12 for c in col], 1.0))
        if b["mh"] > 0.5:
            roofs.flat(p, b["mh"], (*[c * 0.5 for c in col], 1.0))
        if not b["part"]:
            CL.roof_plant(detail, p, h, h01(i, "p"), col)
        if "reid" in nm:
            CL.clock_tower(detail, p.centroid.x, p.bounds[1] + 7.0, h, col)
        n_b += 1
    for k, q in enumerate(marina):
        CL.marina_tower(detail, q.centroid.x, q.centroid.y, seed=k)
    for nm, q in houses:
        x, y, z = CL.bridge_house(detail, q, ornate=any(t in nm for t in ("lasalle", "clark", "wells", "michigan", "dusable")) or not nm)
        flags.append([round(x, 2), round(y, 2), round(z, 2)])
    stats["marina_towers"], stats["bridge_houses"] = len(marina), len(houses)
    stats["buildings"] = n_b
    stats["wall_faces"] = walls.save(out / "walls.npz")
    stats["roof_faces"] = roofs.save(out / "roofs.npz")

    # ---------------- land / water ----------------
    water = unary_union([p for p in (poly(w) for w in geo["water"]) if p is not None])
    lake = box(scene.get("lake_west_x", 2250), -9000, 9000, 9000)
    water = unary_union([water, lake]).buffer(0)
    world = box(-9000, -9000, 9000, 9000)
    land = world.difference(water)
    m = Mesh()
    m.flat(land, 0.0, (1, 1, 1, 1))
    stats["land_faces"] = m.save(out / "land.npz")
    m = Mesh()
    m.walls(land.intersection(box(-2500, -2500, 2600, 2500)), -4.5, 0.0, (1, 1, 1, 1), 1.0, 1.0)
    stats["quay_faces"] = m.save(out / "quay.npz")
    m = Mesh()
    m.face([(-9000, -9000, -4.0), (9000, -9000, -4.0), (9000, 9000, -4.0), (-9000, 9000, -4.0)])
    m.save(out / "water.npz")

    # ---------------- roads / bridges / parks ----------------
    W = {"motorway": 20, "trunk": 18, "primary": 17, "secondary": 14, "tertiary": 12,
         "residential": 9, "unclassified": 9, "motorway_link": 8, "service": 5}
    roads, decks = [], []
    for r in geo["roads"]:
        try:
            if r.get("layer") and float(r["layer"]) < 0:
                continue
        except ValueError:
            pass
        if len(r["p"]) < 2:
            continue
        ls = LineString(r["p"])
        w = max(W[r["kind"]], (r["lanes"] or 0) * 3.3 + 5)
        roads.append(ls.buffer(w / 2, cap_style=2))
    roads = unary_union(roads)
    m = Mesh()
    m.flat(roads.intersection(land), 0.06, (1, 1, 1, 1))
    stats["road_faces"] = m.save(out / "roads.npz")
    from shapely.ops import linemerge
    by_name = {}
    for r in geo["roads"]:
        if not r["name"] or "Lower" in r["name"] or len(r["p"]) < 2 or r["kind"] == "service":
            continue
        try:
            if r.get("layer") and float(r["layer"]) < 0:
                continue
        except ValueError:
            pass
        by_name.setdefault(r["name"], []).append((LineString(r["p"]), max(W[r["kind"]], (r["lanes"] or 0) * 3.3 + 5)))
    groups = {}
    wbuf = water.buffer(5)
    for name, lst in by_name.items():
        merged = unary_union([l for l, _ in lst])
        if merged.geom_type == "MultiLineString":
            merged = linemerge(merged)
        cut = merged.intersection(wbuf)
        for g in (cut.geoms if hasattr(cut, "geoms") else [cut]):
            if g.geom_type != "LineString" or not 45 < g.length < 140:
                continue
            c = list(g.coords)
            a0, b0 = c[0], c[-1]
            if (a0[1], a0[0]) > (b0[1], b0[0]):
                a0, b0 = b0, a0
            # carriageways of one bridge sit within ~25 m of each other
            key = next((k for k, v in groups.items() if k[0] == name and math.dist(v[0][0], a0) < 25), (name, len(groups)))
            groups.setdefault(key, []).append((a0, b0, max(w for _, w in lst)))
    # spans whose deck way is absent from the extract: endpoints taken from the
    # ends of the same street's approach ways on each bank
    for e in scene.get("extra_bridges", []):
        groups[(e["name"], len(groups))] = [(tuple(e["a"]), tuple(e["b"]), e["width"] - 5.0)]
    bridge_lines = []
    for (name, _k), parts_ in groups.items():
        a0 = np.mean([q[0] for q in parts_], axis=0)
        b0 = np.mean([q[1] for q in parts_], axis=0)
        spread = max(math.dist(q[0], a0) for q in parts_)
        width = min(30.0, max(q[2] for q in parts_) + 2 * spread + 5.0)
        if math.dist(a0, b0) > 140:
            continue  # not a river span (long viaduct)
        CL.bascule_bridge(detail, a0, b0, width, truss="Wacker" not in name)
        bridge_lines.append({"name": name, "a": [float(a0[0]), float(a0[1])], "b": [float(b0[0]), float(b0[1])], "width": float(width)})
    (out / "bridges.json").write_text(json.dumps(bridge_lines))
    (out / "flags.json").write_text(json.dumps(flags))
    stats["bridges"] = [q["name"] for q in bridge_lines]
    stats["detail_faces"] = detail.save(out / "detail.npz")
    parks = unary_union([p for p in (poly(x) for x in geo["parks"]) if p is not None])
    m = Mesh()
    m.flat(parks.intersection(land).difference(roads), 0.1, (1, 1, 1, 1))
    stats["park_faces"] = m.save(out / "parks.npz")

    # ---------------- elevated railway ----------------
    by_id = {r["id"]: r["p"] for r in geo["rail"]}
    tracks = []
    for spec in scene["rail"]["tracks"]:
        if "points" in spec:               # an invented alignment (fictional route), given directly in scene metres
            tracks.append([tuple(q) for q in spec["points"]])
            continue
        pts = []
        for wid in spec["ways"]:
            seg = by_id[wid.lstrip("-")]
            seg = seg[::-1] if wid.startswith("-") else seg
            pts += seg if not pts or math.dist(pts[-1], seg[0]) > 0.5 else seg[1:]
        tracks.append(pts)
    used = {w.lstrip("-") for s in scene["rail"]["tracks"] for w in s.get("ways", [])}
    others = [r["p"] for r in geo["rail"] if r["kind"] == "subway" and r["bridge"] and r["id"] not in used]

    deckm, steel, wood = Mesh(), Mesh(), Mesh()
    GAUGE = 1.435

    def lay_track(pts, detailed):
        pts = resample(pts, 2.0)
        ls = LineString(pts)
        # timber open deck: uv.y runs along the track so the shader can draw ties
        left, right = offset_line(pts, 1.55), offset_line(pts, -1.55)
        n = min(len(left), len(right))
        d = 0.0
        for k in range(n - 1):
            L = math.dist(left[k], left[k + 1])
            wood.face([(*right[k], rz - 0.18), (*right[k + 1], rz - 0.18), (*left[k + 1], rz - 0.18), (*left[k], rz - 0.18)],
                      [(0, d), (0, d + L), (1, d + L), (1, d)])
            d += L
        for side in (GAUGE / 2, -GAUGE / 2):
            rail = offset_line(pts, side)
            for a, b in zip(rail[:-1], rail[1:]):
                steel.box_between(a, b, 0.075, rz - 0.18, rz, (0.55, 0.55, 0.58, 1))
        # longitudinal girders under each track
        for side in (1.3, -1.3):
            g = offset_line(pts, side)
            for a, b in zip(g[:-1], g[1:]):
                steel.box_between(a, b, 0.35, rz - 1.5, rz - 0.3, (0.16, 0.17, 0.18, 1))
        return ls

    lines = [lay_track(t, True) for t in tracks] + [lay_track(t, False) for t in others if len(t) >= 2]

    # steel bents (cross-girder on two columns) every ~14 m, only over land
    corridor = unary_union([l.buffer(3.0, cap_style=2) for l in lines])
    for l in lines:
        n = int(l.length / 14)
        for k in range(n + 1):
            c = l.interpolate(k * 14.0)
            if water.contains(c):
                continue
            t2 = l.interpolate(min(l.length, k * 14.0 + 1.0))
            dx, dy = t2.x - c.x, t2.y - c.y
            L = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / L, dx / L
            for s in (2.6, -2.6):
                px, py = c.x + nx * s, c.y + ny * s
                steel.box_between((px - dx / L * 0.2, py - dy / L * 0.2), (px + dx / L * 0.2, py + dy / L * 0.2),
                                  0.4, 0.0, rz - 1.5, (0.14, 0.15, 0.16, 1))
            steel.box_between((c.x + nx * 3.0, c.y + ny * 3.0), (c.x - nx * 3.0, c.y - ny * 3.0), 0.4,
                              rz - 2.1, rz - 1.5, (0.14, 0.15, 0.16, 1))

    # walkway railing on the outer edge of the main double track
    outer = corridor.buffer(0.3)
    for g in (outer.geoms if hasattr(outer, "geoms") else [outer]):
        ring = list(g.exterior.coords)
        ring = resample(ring, 2.4)
        for a, b in zip(ring[:-1], ring[1:]):
            steel.box_between(a, b, 0.05, rz + 0.95, rz + 1.02, (0.2, 0.21, 0.22, 1))
            steel.box_between(a, b, 0.04, rz + 0.48, rz + 0.53, (0.2, 0.21, 0.22, 1))
            steel.box_between(a, (a[0] + (b[0] - a[0]) * 0.03, a[1] + (b[1] - a[1]) * 0.03), 0.06,
                              rz - 0.2, rz + 1.0, (0.2, 0.21, 0.22, 1))
        deckm.walls(g, rz - 0.42, rz - 0.2, (0.2, 0.21, 0.22, 1))
    stats["wood_faces"] = wood.save(out / "ties.npz")
    stats["steel_faces"] = steel.save(out / "steel.npz")
    deckm.save(out / "deck_edge.npz")

    # ---------------- trees + river centre-line ----------------
    from shapely.geometry import Point
    rng = np.random.default_rng(7)
    green = parks.intersection(land).difference(roads.buffer(1.0))
    bfoot = unary_union([p for _, b, p in items if not b["mh"]]).buffer(1.5)
    green = green.difference(bfoot).difference(corridor.buffer(14)).intersection(box(-1300, -1700, 1700, 800))
    trees = []
    for g in (green.geoms if hasattr(green, "geoms") else [green]):
        if g.geom_type != "Polygon" or g.area < 12:
            continue
        x0, y0, x1, y1 = g.bounds
        for _ in range(int(min(40, max(1, g.area / 110)))):
            for _try in range(6):
                pt = Point(rng.uniform(x0, x1), rng.uniform(y0, y1))
                if g.contains(pt):
                    trees.append([round(pt.x, 2), round(pt.y, 2), round(float(rng.uniform(4, 7.5)), 2)])
                    break
    # street trees along the river-front streets within sight of the track
    for r in geo["roads"]:
        if r["name"] and ("Wacker" in r["name"] or "Kinzie" in r["name"] or "Riverwalk" in r["name"]) and len(r["p"]) >= 2:
            ls = LineString(r["p"])
            for side in (8.5, -8.5):
                for d in np.arange(6, ls.length, 13.0):
                    c, c2 = ls.interpolate(d), ls.interpolate(min(ls.length, d + 1))
                    dx, dy = c2.x - c.x, c2.y - c.y
                    L = math.hypot(dx, dy) or 1
                    pt = Point(c.x - dy / L * side, c.y + dx / L * side)
                    if land.contains(pt) and not bfoot.contains(pt) and not corridor.buffer(14).contains(pt):
                        trees.append([round(pt.x, 2), round(pt.y, 2), round(float(rng.uniform(4.5, 6.5)), 2)])
    (out / "trees.json").write_text(json.dumps(trees))
    stats["trees"] = len(trees)
    centre = []
    main = water.intersection(box(-420, -400, 2200, 320))
    for x in range(-380, 2160, 20):
        cut = main.intersection(LineString([(x, -400), (x, 320)]))
        segs = [g for g in (cut.geoms if hasattr(cut, "geoms") else [cut]) if g.geom_type == "LineString"]
        if segs:
            sgm = max(segs, key=lambda g: g.length)
            if sgm.length > 25:
                centre.append([x, round(sgm.centroid.y, 1), round(sgm.length, 1)])
    (out / "river_centre.json").write_text(json.dumps(centre))

    # camera path = first configured track
    path = resample(tracks[0], 0.5)
    (out / "camera_path.json").write_text(json.dumps({"points": path, "rail_top_z": rz,
                                                      "tracks": [resample(t, 0.5) for t in tracks]}))
    stats["camera_path_m"] = round(LineString(path).length, 1)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
