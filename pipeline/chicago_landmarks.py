"""Hand-built procedural geometry for Chicago landmarks that OSM massing cannot convey.

Positions and overall dimensions come from the OSM extract; the shapes are
modelled here: Marina City's petal balconies and parking spiral, bascule
bridges with pony trusses and arched girders, limestone bridge houses, the
Reid-Murdoch clock tower, rooftop plant.

Vertex colour alpha = "glassiness" for the detail material
(0 = matte paint/concrete, 1 = dark reflective glass).
"""
import math

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Polygon

CONCRETE = (0.80, 0.78, 0.72)
BRIDGE_RED = (0.30, 0.065, 0.055)
STONE = (0.66, 0.62, 0.54)
COPPER = (0.20, 0.30, 0.26)


def ngon(cx, cy, r, n, rot=0.0):
    return [(cx + r * math.cos(rot + 2 * math.pi * k / n), cy + r * math.sin(rot + 2 * math.pi * k / n)) for k in range(n)]


def prism(m, ring, z0, z1, col, top=True, bottom=False):
    p = Polygon(ring)
    if not p.is_valid:
        p = p.buffer(0)
    if p.exterior.is_ccw is False:
        p = Polygon(list(p.exterior.coords)[::-1])
    m.walls(p, z0, z1, col)
    if top:
        m.flat(p, z1, col)
    if bottom:
        m.flat(p, z0, col)


def marina_tower(m, cx, cy, seed=0):
    rng = np.random.default_rng(seed)
    petals, rb, rl = 16, 13.6, 2.67
    scallop = []
    for k in range(petals):
        th = 2 * math.pi * k / petals
        ux, uy, tx, ty = math.cos(th), math.sin(th), -math.sin(th), math.cos(th)
        for j in range(9):
            ph = math.radians(-82 + 164 * j / 8)
            scallop.append((cx + rb * ux + rl * (math.cos(ph) * ux + math.sin(ph) * tx),
                            cy + rb * uy + rl * (math.cos(ph) * uy + math.sin(ph) * ty)))
    white = (*CONCRETE, 0.0)
    shadow = (0.05, 0.05, 0.055, 0.0)
    glass = (0.09, 0.11, 0.13, 0.85)
    # base podium
    prism(m, ngon(cx, cy, 17.5, 40), 0, 5.2, (0.55, 0.53, 0.50, 0.0))
    # parking spiral: stacked ramp decks with parked cars nose-out
    prism(m, ngon(cx, cy, 13.4, 40), 5.2, 56.0, shadow, top=False)
    car_cols = [(0.75, 0.75, 0.76), (0.08, 0.08, 0.09), (0.55, 0.06, 0.05), (0.35, 0.37, 0.40),
                (0.12, 0.20, 0.38), (0.85, 0.85, 0.83), (0.30, 0.30, 0.31)]
    z = 6.0
    while z < 55.0:
        ring = ngon(cx, cy, 16.3, 48)
        prism(m, ring, z, z + 0.32, white, bottom=True)
        for k in range(32):
            if rng.random() < 0.22:
                continue
            th = 2 * math.pi * (k + 0.5) / 32
            ux, uy = math.cos(th), math.sin(th)
            c = car_cols[int(rng.integers(len(car_cols)))]
            a, b = (cx + 12.9 * ux, cy + 12.9 * uy), (cx + 15.9 * ux, cy + 15.9 * uy)
            m.box_between(a, b, 1.75, z + 0.32, z + 1.55, (*c, 0.25))
        z += 2.72
    # mechanical / amenity floors
    prism(m, ngon(cx, cy, 16.3, 48), 56.0, 56.6, white, bottom=True)
    prism(m, ngon(cx, cy, 11.0, 32), 56.6, 61.6, (0.62, 0.60, 0.56, 0.0), top=False)
    # 40 apartment floors: scalloped balcony slabs, dark glass line, radial fins
    z0, fh, floors = 61.6, 2.65, 40
    prism(m, ngon(cx, cy, 11.9, 32), z0, z0 + fh * floors, glass, top=False)
    for k in range(petals):
        th = 2 * math.pi * (k + 0.5) / petals
        ux, uy = math.cos(th), math.sin(th)
        m.box_between((cx + 11.7 * ux, cy + 11.7 * uy), (cx + 13.9 * ux, cy + 13.9 * uy), 0.28, z0, z0 + fh * floors, white)
    for j in range(floors + 1):
        z = z0 + j * fh
        prism(m, scallop, z, z + 0.26, white, bottom=True)
        if j < floors:  # balcony upstand
            m.walls(Polygon(scallop), z + 0.26, z + 0.62, white)
    top = z0 + fh * floors
    prism(m, ngon(cx, cy, 11.9, 32), top + 0.26, top + 3.2, white)
    prism(m, ngon(cx, cy, 5.4, 24), top + 3.2, top + 12.0, white)
    prism(m, ngon(cx, cy, 0.25, 6), top + 12.0, top + 22.0, (0.5, 0.5, 0.5, 0.0))


def bascule_bridge(m, a, b, width, truss=True, houses=None):
    """Chicago-style double-leaf bascule: deck, arched girders below, pony trusses above."""
    a, b = np.array(a, float), np.array(b, float)
    L = float(np.linalg.norm(b - a))
    if L < 20:
        return
    u = (b - a) / L
    n = np.array([-u[1], u[0]])
    red = (*BRIDGE_RED, 0.0)
    steps = max(16, int(L / 2.5))
    ts = np.linspace(0, 1, steps + 1)

    def pt(t, off):
        q = a + u * (L * t) + n * off
        return (float(q[0]), float(q[1]))

    # deck + sidewalks
    m.box_between(pt(0, 0), pt(1, 0), width, -0.55, 0.12, (0.10, 0.10, 0.105, 0.0))
    for s in (1, -1):
        m.box_between(pt(0, s * (width / 2 - 1.3)), pt(1, s * (width / 2 - 1.3)), 2.6, 0.12, 0.30, (0.42, 0.41, 0.39, 0.0))
    # arched plate girders under the deck: deep at the trunnions, thin mid-span
    for off in (width / 2 - 0.4, 0.0, -(width / 2 - 0.4)):
        for t0, t1 in zip(ts[:-1], ts[1:]):
            d = 1.0 + 3.4 * (2 * abs((t0 + t1) / 2 - 0.5)) ** 2.2
            m.box_between(pt(t0, off), pt(t1, off), 0.55, -0.55 - d, -0.55, red)
    for s in (1, -1):
        edge = s * (width / 2 - 0.15)
        # railing: top rail, mid rail, close pickets
        m.box_between(pt(0, edge), pt(1, edge), 0.10, 1.22, 1.34, red)
        m.box_between(pt(0, edge), pt(1, edge), 0.06, 0.40, 0.48, red)
        for k in range(int(L / 1.2) + 1):
            t = k * 1.2 / L
            m.box_between(pt(t, edge - 0.05), pt(t, edge + 0.05), 0.07, 0.30, 1.22, red)
        if not truss:
            continue
        # pony truss between roadway and sidewalk
        toff = s * (width / 2 - 2.9)

        def h(t):
            x = 2 * abs(t - 0.5)
            rise = 1.5 + 3.6 * x ** 1.5
            return rise * min(1.0, (1 - x) / 0.06 + 0.25) if x > 0.94 else rise

        panels = max(8, int(round(L / 4.6)) // 2 * 2)
        tp = np.linspace(0.02, 0.98, panels + 1)
        for i, (t0, t1) in enumerate(zip(tp[:-1], tp[1:])):
            p0, p1 = pt(t0, toff), pt(t1, toff)
            h0, h1 = h(t0), h(t1)
            sloped(m, p0, p1, 0.30 + h0, 0.30 + h1, 0.42, 0.34, red)       # top chord
            m.box_between(p0, p1, 0.36, 0.30, 0.62, red)                    # bottom chord
            m.box_between(pt(t0, toff - 0.14), pt(t0, toff + 0.14), 0.26, 0.3, 0.3 + h0, red)  # vertical
            if i % 2 == 0:
                sloped(m, p0, p1, 0.62, 0.30 + h1 - 0.2, 0.22, 0.22, red)
            else:
                sloped(m, p0, p1, 0.30 + h0 - 0.2, 0.62, 0.22, 0.22, red)
        m.box_between(pt(tp[-1], toff - 0.14), pt(tp[-1], toff + 0.14), 0.26, 0.3, 0.3 + h(tp[-1]), red)
    # stone abutment piers at each bank
    for t in (0.0, 1.0):
        m.box_between(pt(t, -width / 2 - 1.0), pt(t, width / 2 + 1.0), 5.0, -4.6, -0.55, (*STONE, 0.0))


def sloped(m, p0, p1, z0, z1, depth, width, col):
    """Box member from (p0, z0) to (p1, z1): z is the member's centre-line height."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy) or 1e-6
    nx, ny = -dy / L * width / 2, dx / L * width / 2
    d = depth / 2
    c = [(x0 - nx, y0 - ny), (x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny)]
    zs = [z0, z0, z1, z1]
    top = [(x, y, z + d) for (x, y), z in zip(c, zs)]
    bot = [(x, y, z - d) for (x, y), z in zip(c, zs)]
    m.face(top, col=col)
    m.face(bot[::-1], col=col)
    for i in range(4):
        j = (i + 1) % 4
        m.face([bot[i], bot[j], top[j], top[i]], col=col)


def bridge_house(m, poly, deck_z=0.1, ornate=True):
    """Limestone bridge-tender house with a copper mansard roof, standing on a pier."""
    c = poly.centroid
    s = max(4.6, min(7.0, math.sqrt(poly.area)))
    ang = 0.0
    mrr = poly.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    ang = math.atan2(ys[1] - ys[0], xs[1] - xs[0])

    def sq(half, rot=ang):
        return ngon(c.x, c.y, half * math.sqrt(2), 4, rot + math.pi / 4)

    stone = (*STONE, 0.0)
    prism(m, sq(s / 2 + 0.5), -4.6, deck_z, (0.50, 0.48, 0.44, 0.0))        # pier
    prism(m, sq(s / 2 + 0.25), deck_z, deck_z + 0.9, stone)                  # plinth
    body_top = deck_z + (9.5 if ornate else 7.0)
    prism(m, sq(s / 2), deck_z + 0.9, body_top, stone)
    prism(m, sq(s / 2 + 0.35), body_top, body_top + 0.5, (0.72, 0.69, 0.62, 0.0))  # cornice
    # windows: dark glazed panels standing just proud of each face
    for k in range(4):
        th = ang + k * math.pi / 2
        ux, uy, tx, ty = math.cos(th), math.sin(th), -math.sin(th), math.cos(th)
        for zc in ((deck_z + 3.4, deck_z + 7.0) if ornate else (deck_z + 4.4,)):
            for off in (-s * 0.2, s * 0.2):
                px, py = c.x + ux * (s / 2 + 0.03) + tx * off, c.y + uy * (s / 2 + 0.03) + ty * off
                w, hh = s * 0.11, 1.0
                m.face([(px - tx * w, py - ty * w, zc - hh), (px + tx * w, py + ty * w, zc - hh),
                        (px + tx * w, py + ty * w, zc + hh), (px - tx * w, py - ty * w, zc + hh)],
                       col=(0.07, 0.09, 0.11, 0.8))
    # mansard roof: steep lower slope, flat cap
    lo, hi = sq(s / 2 + 0.2), sq(s / 2 - 1.3)
    z0, z1 = body_top + 0.5, body_top + (3.4 if ornate else 1.6)
    roof = (*COPPER, 0.0)
    for i in range(4):
        j = (i + 1) % 4
        m.face([(*lo[i], z0), (*lo[j], z0), (*hi[j], z1), (*hi[i], z1)], col=roof)
    m.face([(*p, z1) for p in hi], col=roof)
    if ornate:
        prism(m, ngon(c.x, c.y, 0.08, 6), z1, z1 + 5.0, (0.6, 0.6, 0.6, 0.0))
    return (c.x, c.y, z1)


def clock_tower(m, cx, cy, base_z, col, size=9.0, rot=0.0):
    """Reid-Murdoch style square clock tower with a pyramidal roof."""
    def sq(half):
        return ngon(cx, cy, half * math.sqrt(2), 4, rot + math.pi / 4)
    top = base_z + 20.0
    prism(m, sq(size / 2), base_z - 2, top, (*col, 0.0))
    prism(m, sq(size / 2 + 0.4), top, top + 0.6, (0.74, 0.70, 0.62, 0.0))
    for k in range(4):
        th = rot + k * math.pi / 2
        ux, uy, tx, ty = math.cos(th), math.sin(th), -math.sin(th), math.cos(th)
        px, py, zc, r = cx + ux * (size / 2 + 0.06), cy + uy * (size / 2 + 0.06), top - 5.0, 2.9
        ring = [(px + tx * r * math.cos(a), py + ty * r * math.cos(a), zc + r * math.sin(a))
                for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
        m.face(ring, col=(0.92, 0.90, 0.84, 0.0))
        for ang_h, ln in ((math.radians(60), 2.3), (math.radians(150), 1.6)):  # hands
            ex, ez = math.cos(ang_h) * ln, math.sin(ang_h) * ln
            w = 0.14
            qx, qy = px + ux * 0.04, py + uy * 0.04
            m.face([(qx - tx * w, qy - ty * w, zc), (qx + tx * w, qy + ty * w, zc),
                    (qx + tx * (ex + w), qy + ty * (ex + w), zc + ez), (qx + tx * (ex - w), qy + ty * (ex - w), zc + ez)],
                   col=(0.04, 0.04, 0.04, 0.0))
    lo = sq(size / 2 + 0.3)
    for i in range(4):
        j = (i + 1) % 4
        m.face([(*lo[i], top + 0.6), (*lo[j], top + 0.6), (cx, cy, top + 8.5)], col=(*COPPER, 0.0))


def roof_plant(m, poly, h, key_rand, col):
    """Mechanical penthouse / elevator overrun so roofs are not bare slabs."""
    if poly.area < 350 or h < 22:
        return
    k = 0.32 + 0.22 * key_rand
    pent = affinity.scale(poly.convex_hull, k, k, origin=poly.centroid)
    pent = affinity.translate(pent, (key_rand - 0.5) * math.sqrt(poly.area) * 0.2, 0)
    if not poly.contains(pent):
        pent = affinity.scale(poly.convex_hull, 0.3, 0.3, origin=poly.centroid)
    ph = 3.5 + 5.0 * key_rand + (4.0 if h > 120 else 0.0)
    c = tuple(x * 0.55 + 0.1 for x in col)
    prism(m, list(pent.exterior.coords)[:-1], h, h + ph, (*c, 0.0))
    # parapet
    ring = LineString(list(poly.exterior.coords)).buffer(0.25, cap_style=2).intersection(poly.buffer(0.01))
    if ring.geom_type == "Polygon":
        m.walls(ring, h, h + 1.0, (*[x * 0.9 for x in col], 0.0))
        m.flat(ring, h + 1.0, (*[x * 0.9 for x in col], 0.0))
