"""Blender (3.6) scene builder + renderer for the 3D train-window journey.

Run through Blender, not system Python:

  blender -b --python pipeline/blender_scene.py -- scenes/chicago_3d.json \
      --frames 0-749 --out work/frames/chicago

Loads the meshes written by build_meshes.py, creates materials, sky, sun,
the train-window frame and the camera move, then renders PNG frames.
"""
import argparse
import json
import math
import pathlib
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = pathlib.Path(__file__).resolve().parent.parent
argv = sys.argv[sys.argv.index("--") + 1:]
ap = argparse.ArgumentParser()
ap.add_argument("scene")
ap.add_argument("--frames", default="0-0")
ap.add_argument("--step", type=int, default=1)
ap.add_argument("--out", default="work/frames/test")
ap.add_argument("--samples", type=int)
ap.add_argument("--scale", type=int, default=100)
ap.add_argument("--save-blend")
ap.add_argument("--no-render", action="store_true")
ap.add_argument("--layers", action="store_true", help="render the orthographic depth-layer strips for the parallax loop")
ap.add_argument("--engine", default=None, choices=["CYCLES", "EEVEE"])
ap.add_argument("--keys", action="store_true", help="fast path: sharp world-only keyframes + depth EXR + poses.json (no carriage, blur or DOF)")
ap.add_argument("--carriage-only", action="store_true", help="fast path: the static carriage interior alone, RGBA")
A = ap.parse_args(argv)
S = json.loads(pathlib.Path(A.scene).read_text())
R = S["render"]
MESH = ROOT / S.get("mesh_dir", "work/meshes")

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene


# ------------------------------------------------------------------ helpers
def load(name, mat):
    if not (MESH / f"{name}.npz").exists():
        return None
    d = np.load(MESH / f"{name}.npz")
    n = len(d["v"])
    if n == 0:
        return None
    me = bpy.data.meshes.new(name)
    sizes = d["sizes"]
    me.vertices.add(n)
    me.vertices.foreach_set("co", d["v"].ravel())
    me.loops.add(n)
    me.loops.foreach_set("vertex_index", np.arange(n, dtype=np.int32))
    me.polygons.add(len(sizes))
    me.polygons.foreach_set("loop_start", np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int32))
    me.polygons.foreach_set("loop_total", sizes)
    me.update(calc_edges=True)
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", d["uv"].ravel())
    if "uv2" in d.files and len(d["uv2"]) == n:
        me.uv_layers.new(name="UV2").data.foreach_set("uv", d["uv2"].ravel())
    ca = me.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="CORNER")
    ca.data.foreach_set("color", d["col"].ravel())
    me.validate()
    ob = bpy.data.objects.new(name, me)
    scn.collection.objects.link(ob)
    me.materials.append(mat)
    return ob


class NT:
    """Tiny node-tree builder."""

    def __init__(self, tree):
        self.t = tree
        tree.nodes.clear()

    def n(self, kind, **kw):
        node = self.t.nodes.new(kind)
        for k, v in kw.items():
            if k.startswith("i_"):
                key = k[2:]
                node.inputs[int(key) if key.isdigit() else key.replace("_", " ")].default_value = v
            else:
                setattr(node, k, v)
        return node

    def link(self, a, b):
        self.t.links.new(a, b)

    def math(self, op, a, b=None, c=None, clamp=False):
        node = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, x in enumerate((a, b, c)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                node.inputs[i].default_value = x
            else:
                self.link(x, node.inputs[i])
        return node.outputs[0]

    def mix(self, fac, a, b):
        node = self.n("ShaderNodeMixRGB")
        for sock, x in zip(node.inputs, (fac, a, b)):
            if isinstance(x, (int, float)):
                sock.default_value = x
            elif isinstance(x, tuple):
                sock.default_value = (*x, 1.0) if len(x) == 3 else x
            else:
                self.link(x, sock)
        return node.outputs[0]


def material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = NT(m.node_tree)
    out = nt.n("ShaderNodeOutputMaterial")
    return m, nt, out


def simple(name, colour, rough=0.8, metallic=0.0, vcol=False, spec=0.3):
    m, nt, out = material(name)
    b = nt.n("ShaderNodeBsdfPrincipled", i_Roughness=rough, i_Metallic=metallic, i_Specular=spec)
    if vcol:
        a = nt.n("ShaderNodeAttribute", attribute_name="Col")
        nt.link(a.outputs["Color"], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*colour, 1)
    nt.link(b.outputs[0], out.inputs[0])
    return m


TEX = ROOT / "assets" / "polyhaven"


def image(nt, name, uv_socket, scale):
    """Tiling CC0 texture sampled in facade UV space (bays x floors)."""
    path = TEX / name
    if not path.exists():
        return None
    mp = nt.n("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (*scale, 1.0)
    nt.link(uv_socket, mp.inputs["Vector"])
    tex = nt.n("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path), check_existing=True)
    nt.link(mp.outputs[0], tex.inputs["Vector"])
    return tex.outputs["Color"]


def facade():
    """Procedural facades. uv = (window bays, floors); uv2 = (total floors, per-building random).

    Vertex-colour alpha picks the building type:
    0 masonry with Chicago windows, 0.12 brick, 0.5 concrete piers + ribbon glass,
    0.75 Miesian dark grid, 1.0 glass curtain wall.
    """
    m, nt, out = material("facade")
    M = nt.math
    att = nt.n("ShaderNodeAttribute", attribute_name="Col")
    style, base = att.outputs["Alpha"], att.outputs["Color"]
    uv = nt.n("ShaderNodeUVMap", uv_map="UVMap")
    uv2 = nt.n("ShaderNodeUVMap", uv_map="UV2")
    sep, sep2 = nt.n("ShaderNodeSeparateXYZ"), nt.n("ShaderNodeSeparateXYZ")
    nt.link(uv.outputs[0], sep.inputs[0])
    nt.link(uv2.outputs[0], sep2.inputs[0])
    u, v, total, brand = sep.outputs[0], sep.outputs[1], sep2.outputs[0], sep2.outputs[1]
    fu, fv = M("FRACT", u), M("FRACT", v)

    def band(x, lo, hi):
        return M("MULTIPLY", M("GREATER_THAN", x, lo), M("LESS_THAN", x, hi))

    def near(x, c, w):
        return M("LESS_THAN", M("ABSOLUTE", M("SUBTRACT", x, c)), w)

    def AND(a, b):
        return M("MULTIPLY", a, b)

    def OR(a, b):
        return M("MAXIMUM", a, b)

    def NOT(a):
        return M("SUBTRACT", 1.0, a)

    is_brick, is_pier, is_mies = near(style, 0.12, 0.06), near(style, 0.5, 0.1), near(style, 0.75, 0.1)
    is_glass = M("GREATER_THAN", style, 0.9)
    is_mas = M("LESS_THAN", style, 0.3)
    ground = M("LESS_THAN", v, 1.25)
    cornice = AND(is_mas, M("GREATER_THAN", v, M("SUBTRACT", total, 0.75)))

    w_mas = AND(AND(band(fu, 0.15, 0.85), band(fv, 0.24, 0.80)), NOT(cornice))
    mull = AND(w_mas, OR(near(fu, 0.36, 0.012), near(fu, 0.64, 0.012)))
    sill = AND(AND(band(fu, 0.11, 0.89), band(fv, 0.18, 0.24)), is_mas)
    w_pier = AND(band(fu, 0.17, 0.83), band(fv, 0.34, 0.88))
    sp_pier = AND(band(fu, 0.17, 0.83), NOT(band(fv, 0.34, 0.88)))
    w_mies = AND(band(fu, 0.07, 0.93), band(fv, 0.20, 0.96))
    w_glass = AND(band(fu, 0.035, 0.965), band(fv, 0.27, 1.01))
    sp_glass = AND(band(fu, 0.035, 0.965), NOT(band(fv, 0.27, 1.01)))
    w_ground = AND(ground, AND(band(fu, 0.08, 0.92), band(v, 0.14, 1.06)))

    win = OR(OR(AND(is_mas, AND(w_mas, NOT(mull))), AND(is_pier, w_pier)), OR(AND(is_mies, w_mies), AND(is_glass, w_glass)))
    win = OR(AND(win, NOT(ground)), w_ground)
    spandrel = AND(OR(AND(is_pier, sp_pier), AND(is_glass, sp_glass)), NOT(ground))

    cell = nt.n("ShaderNodeCombineXYZ")
    nt.link(M("FLOOR", M("ADD", u, 0.0005)), cell.inputs[0])
    nt.link(M("FLOOR", M("ADD", v, 0.0005)), cell.inputs[1])
    nt.link(M("FLOOR", M("MULTIPLY", brand, 997.0)), cell.inputs[2])  # quantised: interpolation jitter must not reseed the noise
    wn = nt.n("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    nt.link(cell.outputs[0], wn.inputs["Vector"])
    r, rc = wn.outputs["Value"], wn.outputs["Color"]
    sepr = nt.n("ShaderNodeSeparateXYZ")
    nt.link(rc, sepr.inputs[0])
    r2 = sepr.outputs[1]

    # ---- wall
    conc = image(nt, "concrete_wall_008_diffuse.jpg", uv.outputs[0], (0.23, 0.31))
    brick = image(nt, "red_brick_03_diffuse.jpg", uv.outputs[0], (1.7, 1.9))

    def scaled(col, fac):
        n_ = nt.n("ShaderNodeVectorMath", operation="SCALE")
        if isinstance(col, tuple):
            n_.inputs[0].default_value = col
        else:
            nt.link(col, n_.inputs[0])
        if isinstance(fac, (int, float)):
            n_.inputs["Scale"].default_value = fac
        else:
            nt.link(fac, n_.inputs["Scale"])
        return n_.outputs[0]

    def lum(col):
        n_ = nt.n("ShaderNodeRGBToBW")
        nt.link(col, n_.inputs[0])
        return n_.outputs[0]

    geo = nt.n("ShaderNodeNewGeometry")
    streak = nt.n("ShaderNodeTexNoise", i_Scale=1.0, i_Detail=4.0)
    smap = nt.n("ShaderNodeMapping")
    smap.inputs["Scale"].default_value = (0.35, 0.35, 0.012)
    nt.link(geo.outputs["Position"], smap.inputs["Vector"])
    nt.link(smap.outputs[0], streak.inputs["Vector"])
    weather = M("ADD", 0.80, M("MULTIPLY", streak.outputs["Fac"], 0.34))
    wall = scaled(base, weather)
    if conc is not None:
        wall = scaled(wall, M("ADD", 0.55, M("MULTIPLY", lum(conc), 1.0)))
    if brick is not None:
        bw = nt.mix(1.0, brick, base)
        nt.t.nodes[-1].blend_type = "OVERLAY"
        wall = nt.mix(is_brick, wall, scaled(bw, weather))
    wall = nt.mix(cornice, wall, scaled(base, 1.18))
    wall = nt.mix(sill, wall, scaled(base, 1.25))
    wall = nt.mix(AND(is_mas, mull), wall, (0.10, 0.10, 0.10))
    alu = nt.mix(is_mies, (0.42, 0.44, 0.46), base)
    wall = nt.mix(OR(is_glass, is_mies), wall, alu)
    wall = nt.mix(spandrel, wall, scaled(nt.mix(is_glass, scaled(base, 0.55), scaled(base, 0.5)), 1.0))

    # ---- glazing
    tint = nt.mix(is_glass, (0.045, 0.06, 0.075), base)
    tint = nt.mix(is_mies, tint, (0.05, 0.048, 0.042))
    pane = scaled(tint, M("ADD", 0.80, M("MULTIPLY", r, 0.35)))
    # lintel shadow at the head of punched windows fakes the reveal depth
    head = nt.n("ShaderNodeMapRange", clamp=True)
    head.inputs[1].default_value, head.inputs[2].default_value = 0.62, 0.80
    head.inputs[3].default_value, head.inputs[4].default_value = 1.0, 0.35
    nt.link(fv, head.inputs[0])
    pane = nt.mix(is_mas, pane, scaled(pane, head.outputs[0]))
    blinds = AND(M("GREATER_THAN", r2, 0.80), OR(is_mas, is_pier))
    pane = nt.mix(blinds, pane, scaled((0.50, 0.47, 0.41), M("ADD", 0.7, M("MULTIPLY", r, 0.4))))
    colour = nt.mix(win, wall, pane)

    glassy = AND(win, NOT(blinds))
    b = nt.n("ShaderNodeBsdfPrincipled", i_Specular=0.5)
    nt.link(colour, b.inputs["Base Color"])
    nt.link(M("SUBTRACT", 0.82, M("MULTIPLY", glassy, 0.79)), b.inputs["Roughness"])
    met_w = M("ADD", 0.55, M("MULTIPLY", OR(is_glass, is_mies), 0.35))
    nt.link(M("ADD", M("MULTIPLY", glassy, met_w), M("MULTIPLY", AND(spandrel, is_glass), 0.5)), b.inputs["Metallic"])
    # every pane sits at a slightly different angle, so reflections break up like real curtain wall
    tilt = nt.n("ShaderNodeVectorMath", operation="SUBTRACT")
    nt.link(rc, tilt.inputs[0])
    tilt.inputs[1].default_value = (0.5, 0.5, 0.5)
    tscale = scaled(tilt.outputs[0], M("MULTIPLY", glassy, R.get("pane_tilt", 0.045)))
    nadd = nt.n("ShaderNodeVectorMath", operation="ADD")
    nt.link(geo.outputs["Normal"], nadd.inputs[0])
    nt.link(tscale, nadd.inputs[1])
    nn = nt.n("ShaderNodeVectorMath", operation="NORMALIZE")
    nt.link(nadd.outputs[0], nn.inputs[0])
    nt.link(nn.outputs[0], b.inputs["Normal"])
    nt.link(b.outputs[0], out.inputs[0])
    return m


def detail_mat():
    """Landmark geometry: vertex colour, alpha = glassiness."""
    m, nt, out = material("detail")
    a = nt.n("ShaderNodeAttribute", attribute_name="Col")
    b = nt.n("ShaderNodeBsdfPrincipled", i_Specular=0.4)
    nt.link(a.outputs["Color"], b.inputs["Base Color"])
    nt.link(nt.math("SUBTRACT", 0.72, nt.math("MULTIPLY", a.outputs["Alpha"], 0.66)), b.inputs["Roughness"])
    nt.link(nt.math("MULTIPLY", a.outputs["Alpha"], 0.85), b.inputs["Metallic"])
    nt.link(b.outputs[0], out.inputs[0])
    return m


def water():
    m, nt, out = material("water")
    b = nt.n("ShaderNodeBsdfPrincipled", i_Roughness=R.get("water_roughness", 0.035), i_Specular=R.get("water_spec", 0.65), i_Metallic=0.0)
    b.inputs["Base Color"].default_value = (*R.get("water_colour", (0.012, 0.045, 0.034)), 1)
    geo = nt.n("ShaderNodeNewGeometry")

    def waves(scale, detail, rot):
        mp = nt.n("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = scale
        mp.inputs["Rotation"].default_value = (0, 0, rot)
        nt.link(geo.outputs["Position"], mp.inputs["Vector"])
        n_ = nt.n("ShaderNodeTexNoise", i_Scale=1.0, i_Detail=detail, i_Roughness=0.62)
        nt.link(mp.outputs[0], n_.inputs["Vector"])
        return n_.outputs["Fac"]

    h = nt.math("ADD", nt.math("MULTIPLY", waves((0.22, 0.07, 1.0), 3.0, 0.15), 1.0),
                nt.math("MULTIPLY", waves((1.3, 0.55, 1.0), 5.0, -0.4), 0.35))
    bump = nt.n("ShaderNodeBump", i_Strength=R.get("water_bump", 0.22), i_Distance=0.5)
    nt.link(h, bump.inputs["Height"])
    nt.link(bump.outputs[0], b.inputs["Normal"])
    nt.link(b.outputs[0], out.inputs[0])
    return m


def ground(name, colour, rough=0.9, vary=0.18, scale=0.08):
    m, nt, out = material(name)
    b = nt.n("ShaderNodeBsdfPrincipled", i_Roughness=rough, i_Specular=0.2)
    geo = nt.n("ShaderNodeNewGeometry")
    noise = nt.n("ShaderNodeTexNoise", i_Scale=scale, i_Detail=4.0)
    nt.link(geo.outputs["Position"], noise.inputs["Vector"])
    sc = nt.n("ShaderNodeVectorMath", operation="SCALE")
    sc.inputs[0].default_value = colour
    nt.link(nt.math("ADD", 1.0 - vary / 2, nt.math("MULTIPLY", noise.outputs["Fac"], vary)), sc.inputs["Scale"])
    nt.link(sc.outputs[0], b.inputs["Base Color"])
    nt.link(b.outputs[0], out.inputs[0])
    return m


def flat_emission(name, colour):
    m, nt, out = material(name)
    e = nt.n("ShaderNodeEmission")
    e.inputs[0].default_value = (*colour, 1)
    nt.link(e.outputs[0], out.inputs[0])
    return m


# ------------------------------------------------------------------ scene
load("walls", facade())
load("roofs", simple("roof", None, 0.9, vcol=True))
load("land", ground("sidewalk", (0.36, 0.355, 0.34)))
load("quay", ground("quay", (0.36, 0.34, 0.31), scale=0.3))
load("water", water())
load("roads", ground("asphalt", (0.085, 0.087, 0.092), 0.85))
load("parks", ground("park", (0.16, 0.30, 0.09), 0.95, 0.4, 0.15))
load("detail", detail_mat()) if (MESH / "detail.npz").exists() else None
load("ties", ground("ties", (0.10, 0.075, 0.055), 0.9, 0.3, 1.5))
load("steel", simple("steel", None, 0.45, 0.5, vcol=True))
load("deck_edge", simple("deck_edge", None, 0.6, 0.3, vcol=True))

# stylised trees: one merged mesh of low-poly canopies on trunks
trees = json.loads((MESH / "trees.json").read_text()) if (MESH / "trees.json").exists() else []
if trees:
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    cv = np.array([v.co[:] for v in bm.verts])
    cf = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    rng = np.random.default_rng(3)
    V, F, COL = [], [], []
    for x, y, h in trees:
        r = h * rng.uniform(0.30, 0.42)
        base = len(V)
        lump = cv * (r * rng.uniform(0.85, 1.15, 3)) * (1 + 0.12 * rng.standard_normal((len(cv), 1)))
        V.extend((lump + (x, y, h - r * 0.8)).tolist())
        F.extend([[base + i for i in f] for f in cf])
        g = rng.uniform(0.8, 1.2)
        COL.append(g)
        b2 = len(V)
        t = 0.18
        V.extend([(x - t, y - t, 0), (x + t, y - t, 0), (x + t, y + t, 0), (x - t, y + t, 0),
                  (x - t, y - t, h - r), (x + t, y - t, h - r), (x + t, y + t, h - r), (x - t, y + t, h - r)])
        F.extend([[b2 + a, b2 + b, b2 + c, b2 + d] for a, b, c, d in ((0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))])
    me = bpy.data.meshes.new("trees")
    me.from_pydata(V, [], F)
    for poly in me.polygons:
        poly.use_smooth = len(poly.vertices) == 3
    me.materials.append(ground("leaves", (0.045, 0.10, 0.035), 0.95, 0.6, 0.25))
    scn.collection.objects.link(bpy.data.objects.new("trees", me))


def box_obj(name, size, loc, mat, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale, ob.location = size, loc
    ob.data.materials.append(mat)
    if parent:
        ob.parent = parent
    return ob


# tour boats moving slowly along the real river centre-line
BOATS = []
rc = json.loads((MESH / "river_centre.json").read_text()) if (MESH / "river_centre.json").exists() else []
if rc:
    rc = np.array(rc)
    hull_m, cabin_m, deck_m = simple("hull", (0.05, 0.10, 0.22), 0.4), simple("cabin", (0.92, 0.92, 0.90), 0.5), simple("deckb", (0.75, 0.62, 0.42), 0.8)
    for i, b in enumerate(S.get("boats", [])):
        root = bpy.data.objects.new(f"boat{i}", None)
        scn.collection.objects.link(root)
        L = b.get("length", 24)
        box_obj("hull", (L, 5.6, 1.6), (0, 0, 0.3), hull_m, root)
        box_obj("cabin", (L * 0.62, 4.8, 2.0), (-L * 0.08, 0, 2.0), cabin_m, root)
        box_obj("top", (L * 0.66, 5.0, 0.15), (-L * 0.08, 0, 3.1), deck_m, root)
        box_obj("wheel", (L * 0.14, 3.2, 1.5), (L * 0.2, 0, 3.9), cabin_m, root)
        BOATS.append((root, b))

# flags on the bridge houses (the Chicago municipal flag is public domain)
def chicago_flag():
    w, h = 384, 256
    img = np.ones((h, w, 4), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    blue = (0.33, 0.62, 0.86)
    for lo, hi in ((0.12, 0.29), (0.71, 0.88)):
        img[int(lo * h):int(hi * h), :, :3] = blue

    def tri(cx, cy, r, rot):
        pts = [(cx + r * math.cos(rot + k * 2 * math.pi / 3), cy + r * math.sin(rot + k * 2 * math.pi / 3)) for k in range(3)]
        mask = np.ones((h, w), bool)
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            mask &= ((x1 - x0) * (yy - y0) - (y1 - y0) * (xx - x0)) >= 0
        return mask
    for k in range(4):
        cx = w * (0.2 + 0.2 * k)
        star = tri(cx, h / 2, h * 0.115, math.pi / 2) | tri(cx, h / 2, h * 0.115, -math.pi / 2)
        img[star, :3] = (0.78, 0.05, 0.08)
    im = bpy.data.images.new("chicago_flag", w, h)
    im.pixels.foreach_set(img.ravel())
    return im


fl = json.loads((MESH / "flags.json").read_text()) if (MESH / "flags.json").exists() else []
if fl:
    fm, fnt, fout = material("flag")
    ft = fnt.n("ShaderNodeTexImage")
    ft.image = chicago_flag()
    fb = fnt.n("ShaderNodeBsdfPrincipled", i_Roughness=0.8)
    fnt.link(ft.outputs["Color"], fb.inputs["Base Color"])
    fnt.link(fb.outputs[0], fout.inputs[0])
    V, F, UVS = [], [], []
    for x, y, z in fl:
        if not (-250 < x < 1300 and -250 < y < 250):
            continue
        top, fw, fh, nseg = z + 5.0, 3.0, 2.0, 8
        base_i = len(V)
        for k in range(nseg + 1):  # frozen ripple so the cloth is not a flat card
            t = k / nseg
            dy = 0.16 * math.sin(t * 7.0 + x) * t
            V += [(x + fw * t, y + dy, top - fh), (x + fw * t, y + dy, top)]
            UVS += [(t, 0.0), (t, 1.0)]
        for k in range(nseg):
            a = base_i + 2 * k
            F.append((a, a + 2, a + 3, a + 1))
    if V:
        me = bpy.data.meshes.new("flags")
        me.from_pydata(V, [], F)
        uvl = me.uv_layers.new(name="UVMap")
        for poly in me.polygons:
            for li in poly.loop_indices:
                uvl.data[li].uv = UVS[me.loops[li].vertex_index]
        me.materials.append(fm)
        scn.collection.objects.link(bpy.data.objects.new("flags", me))

# traffic crossing the bridges
CARS = []
bl = json.loads((MESH / "bridges.json").read_text()) if (MESH / "bridges.json").exists() else []
car_cols = [(0.70, 0.70, 0.72), (0.05, 0.05, 0.06), (0.45, 0.05, 0.04), (0.30, 0.32, 0.35), (0.10, 0.17, 0.32),
            (0.85, 0.85, 0.83), (0.85, 0.62, 0.05)]
car_mats = [simple(f"car{i}", c, 0.25, 0.3) for i, c in enumerate(car_cols)]
glass_m = simple("carglass", (0.03, 0.04, 0.05), 0.05, 0.8)
crng = np.random.default_rng(11)
for bi, b in enumerate(bl):
    a, bb = np.array(b["a"]), np.array(b["b"])
    L = float(np.linalg.norm(bb - a))
    uvec = (bb - a) / L
    nvec = np.array([-uvec[1], uvec[0]])
    for lane, direction in ((2.2, 1), (5.4, 1), (-2.2, -1), (-5.4, -1)):
        if abs(lane) > b["width"] / 2 - 4.5:
            continue
        for k in range(3):
            root = bpy.data.objects.new(f"car_{bi}_{lane}_{k}", None)
            scn.collection.objects.link(root)
            bus = crng.random() < 0.12
            ln, ht = (11.0, 2.9) if bus else (4.5, 1.25)
            box_obj("body", (ln, 2.5 if bus else 1.85, ht * 0.62), (0, 0, 0.45 + ht * 0.31), car_mats[int(crng.integers(len(car_mats)))], root)
            box_obj("cab", (ln * (0.92 if bus else 0.52), 2.3 if bus else 1.65, ht * 0.4), (-0.2, 0, 0.45 + ht * 0.62 + ht * 0.2), glass_m, root)
            root["bus"] = bool(bus)
            CARS.append((root, a, uvec, nvec, L, lane, direction, float(crng.uniform(0, 1)), float(crng.uniform(7.0, 11.0))))

# ------------------------------------------------------------------ light
sun_az = math.radians(R["sun_azimuth_deg"])
world = bpy.data.worlds.new("World")
scn.world = world
world.use_nodes = True
nt = NT(world.node_tree)
wout = nt.n("ShaderNodeOutputWorld")
hdr = bpy.data.images.load(str(ROOT / R["hdri"]))
px = np.empty(hdr.size[0] * hdr.size[1] * 4, np.float32)
hdr.pixels.foreach_get(px)
px = px.reshape(hdr.size[1], hdr.size[0], 4)[:, :, :3].sum(axis=2)
sy, sx = np.unravel_index(int(np.argmax(px)), px.shape)
phi = (sx / hdr.size[0] - 0.5) * 2 * math.pi
sun_el = (sy / hdr.size[1] - 0.5) * math.pi
alpha0 = math.atan2(math.sin(phi), -math.cos(phi))       # where the HDRI's sun sits (Blender equirect)
alpha1 = math.atan2(math.cos(sun_az), math.sin(sun_az))  # where the scene wants it (compass azimuth)
tc = nt.n("ShaderNodeTexCoord")
mp = nt.n("ShaderNodeMapping", vector_type="POINT")
mp.inputs["Rotation"].default_value = (0, 0, alpha0 - alpha1)
nt.link(tc.outputs["Generated"], mp.inputs["Vector"])
env = nt.n("ShaderNodeTexEnvironment")
env.image = hdr
nt.link(mp.outputs[0], env.inputs["Vector"])
bg = nt.n("ShaderNodeBackground")
bg.inputs["Strength"].default_value = R.get("hdri_strength", 1.0)
nt.link(env.outputs[0], bg.inputs[0])
nt.link(bg.outputs[0], wout.inputs[0])
print(f"HDRI sun elevation {math.degrees(sun_el):.1f} deg, rotated to azimuth {R['sun_azimuth_deg']}")
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = R.get("sun_strength", 3.0)
sun.data.angle = math.radians(1.0)
sun.data.color = R.get("sun_colour", (1.0, 0.95, 0.88))
sun_el = math.radians(R["sun_elevation_deg"]) if R.get("sun_elevation_deg") else sun_el
to_sun = Vector((math.sin(sun_az) * math.cos(sun_el), math.cos(sun_az) * math.cos(sun_el), math.sin(sun_el)))
sun.rotation_euler = to_sun.to_track_quat("Z", "Y").to_euler()
ENGINE = A.engine or R.get("engine", "CYCLES")
if ENGINE != "CYCLES":  # Cycles takes its sun and shadows from the HDRI itself
    scn.collection.objects.link(sun)

# ------------------------------------------------------------------ camera + carriage
C = S["camera"]
path = json.loads((MESH / "camera_path.json").read_text())
P = np.array(path.get("tracks", [path["points"]])[C.get("track", 0)])
if C.get("reverse"):
    P = P[::-1]
seg = np.hypot(*np.diff(P, axis=0).T)
cum = np.concatenate([[0], np.cumsum(seg)])
s0 = cum[np.argmin(np.hypot(P[:, 0] - C["start_xy"][0], P[:, 1] - C["start_xy"][1]))]
fps = R["fps"]


def at(s):
    s = min(max(s, 0.0), cum[-1] - 0.01)
    return np.array([np.interp(s, cum, P[:, 0]), np.interp(s, cum, P[:, 1])])


side = -1.0 if C.get("look", "left") == "right" else 1.0   # car frame: +X forward, +Y left
FLOOR, EYE, HALF = 1.1, 1.25, 1.40
seat_y = side * (HALF - 0.05 - C.get("eye_to_glass_m", 0.6))
car = bpy.data.objects.new("car", None)
scn.collection.objects.link(car)
cam_data = bpy.data.cameras.new("Cam")
cam_data.sensor_width = 36
cam_data.lens = 18 / math.tan(math.radians(C["hfov_deg"]) / 2)
cam_data.shift_y = C.get("shift_y", 0.0)
cam_data.clip_start, cam_data.clip_end = 0.05, 20000
if C.get("fstop"):
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = C.get("focus_m", 80.0)
    cam_data.dof.aperture_fstop = C["fstop"]
cam = bpy.data.objects.new("Cam", cam_data)
cam.parent = car
scn.collection.objects.link(cam)
scn.camera = cam
yaw = math.radians(C["yaw_from_forward_deg"])
look = Vector((math.cos(yaw), side * math.sin(yaw), 0.0))
cam.location = (0.0, seat_y, EYE)
cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()

f0, f1 = (int(x) for x in A.frames.split("-"))
n_total = int(round(C["duration_s"] * fps))
rail_z = path["rail_top_z"]
# Key only the frames this run renders (plus neighbours for motion blur): keying a whole
# five-minute shot for every 60-frame chunk would cost minutes per chunk.
_wanted = set()
for _f in range(f0, f1 + 1, max(1, A.step)):
    _wanted.update((_f - 1, _f, _f + 1))
def car_pose(f):
    t = f / fps
    s = s0 + C["speed_mps"] * t
    p = at(s)
    tan = at(s + 7.0) - at(s - 7.0)  # long baseline: no twitch at polyline vertices
    heading = math.atan2(tan[1], tan[0])
    sway = C.get("sway", 1.0)
    z = rail_z + FLOOR + sway * (0.005 * math.sin(2 * math.pi * 0.9 * t) + 0.003 * math.sin(2 * math.pi * 0.37 * t + 1))
    roll = math.radians(sway * (0.09 * math.sin(2 * math.pi * 0.31 * t) + 0.04 * math.sin(2 * math.pi * 0.83 * t + 2)))
    return (p[0], p[1], z), (roll, 0.0, heading)


for f in sorted(_wanted):
    t = f / fps
    car.location, car.rotation_euler = car_pose(f)
    car.keyframe_insert("location", frame=f)
    car.keyframe_insert("rotation_euler", frame=f)
    for root, a, uvec, nvec, L, lane, direction, ph, spd in CARS:
        span = L + 160.0
        d = ((ph * span + spd * t) % span) - 80.0
        if direction < 0:
            d = L - d
        q = a + uvec * d + nvec * lane * -direction
        root.location = (q[0], q[1], 0.12)
        root.rotation_euler = (0, 0, math.atan2(uvec[1], uvec[0]) + (math.pi if direction < 0 else 0))
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
for root, b in BOATS:
    for f in (min(_wanted), max(_wanted)):
        x = b["x0"] + b["speed_mps"] * f / fps
        y = float(np.interp(x, rc[:, 0], rc[:, 1])) + b.get("offset", 0.0)
        y2 = float(np.interp(x + 5, rc[:, 0], rc[:, 1])) + b.get("offset", 0.0)
        root.location = (x, y, -4.0)
        root.rotation_euler = (0, 0, math.atan2(y2 - y, 5.0) + (math.pi if b["speed_mps"] < 0 else 0))
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
for ob in [car] + [c[0] for c in CARS] + [b[0] for b in BOATS]:
    for fc in ob.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"

# ------------------------------------------------------------------ carriage interior
W = S.get("window", {})
if W.get("enabled", True) and not A.keys:
    wall_y = side * (HALF - 0.05)          # inner face of the car side
    out_y = side * (HALF + 0.03)           # outer skin
    x0, x1 = W.get("x0", 0.03), W.get("x1", 1.30)
    zb, zt = EYE - W.get("below_eye", 0.40), EYE + W.get("above_eye", 0.66)
    rad, n = W.get("radius", 0.07), 10

    def rrect(x0, x1, z0, z1, r):
        pts = []
        for cx, cz, a0 in ((x1 - r, z1 - r, 0), (x0 + r, z1 - r, 90), (x0 + r, z0 + r, 180), (x1 - r, z0 + r, 270)):
            for k in range(n + 1):
                a = math.radians(a0 + 90 * k / n)
                pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
        return pts

    def obj(name, verts, faces, mat):
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        ob.parent = car
        scn.collection.objects.link(ob)
        return ob

    panel = simple("car_panel", tuple(W.get("panel_colour", (0.58, 0.56, 0.52))), 0.55)
    rubber = simple("car_rubber", (0.012, 0.012, 0.012), 0.6)
    trim = simple("car_trim", tuple(W.get("trim_colour", (0.30, 0.30, 0.31))), 0.35, 0.6)
    X0, X1, Z0, Z1 = -2.5, 6.5, 0.0, 2.45
    wins = W.get("windows") or [[x0, x1]]
    g = 0.022
    lift = wall_y - side * 0.006
    for wi, (wa, wb) in enumerate(wins):
        inner = rrect(wa, wb, zb, zt, rad)
        m_ = len(inner)
        ca = X0 if wi == 0 else (wins[wi - 1][1] + wa) / 2       # each window owns a cell of wall
        cb = X1 if wi == len(wins) - 1 else (wb + wins[wi + 1][0]) / 2
        outer = [(cb if x > (wa + wb) / 2 else ca, Z1 if z > (zb + zt) / 2 else Z0) for x, z in inner]
        ring = [(i, (i + 1) % m_, m_ + (i + 1) % m_, m_ + i) for i in range(m_)]
        obj(f"wall{wi}", [(x, wall_y, z) for x, z in inner] + [(x, wall_y, z) for x, z in outer], ring, panel)
        obj(f"reveal{wi}", [(x, wall_y, z) for x, z in inner] + [(x, out_y, z) for x, z in inner], ring, rubber)
        gasket = rrect(wa - g, wb + g, zb - g, zt + g, rad + g)
        obj(f"trim{wi}", [(x, lift, z) for x, z in inner] + [(x, lift, z) for x, z in gasket], ring, trim)
    x0, x1 = wins[0][0], wins[-1][1]
    # sill ledge
    sy0, sy1 = wall_y, wall_y - side * 0.075
    sv = [(x0 - 0.06, sy0, zb - 0.03), (x1 + 0.06, sy0, zb - 0.03), (x1 + 0.06, sy1, zb - 0.03), (x0 - 0.06, sy1, zb - 0.03),
          (x0 - 0.06, sy0, zb), (x1 + 0.06, sy0, zb), (x1 + 0.06, sy1, zb), (x0 - 0.06, sy1, zb)]
    obj("sill", sv, [(4, 5, 6, 7), (3, 2, 6, 7), (0, 1, 2, 3), (1, 2, 6, 5), (0, 3, 7, 4)], trim)
    # shell: roof, far wall and floor keep direct sun off the interior
    oy = -side * HALF
    obj("shell", [(X0, wall_y, Z1), (X1, wall_y, Z1), (X1, oy, Z1), (X0, oy, Z1),
                  (X0, oy, Z0), (X1, oy, Z0), (X1, wall_y, Z0), (X0, wall_y, Z0),
                  (X0, wall_y, Z1), (X0, oy, Z1), (X0, oy, Z0), (X0, wall_y, Z0)],
        [(0, 1, 2, 3), (3, 2, 5, 4), (4, 5, 6, 7), (8, 9, 10, 11)], simple("car_shell", (0.45, 0.44, 0.42), 0.7))
    lamp = bpy.data.lights.new("cabin", "AREA")
    lamp.shape, lamp.size, lamp.size_y = "RECTANGLE", 2.4, 0.5
    lamp.energy = W.get("cabin_light_w", 40.0)
    lamp.color = (1.0, 0.93, 0.84)
    lo = bpy.data.objects.new("cabin", lamp)
    lo.parent = car
    lo.location = (0.9, wall_y - side * 0.75, 2.3)
    lo.rotation_euler = Vector((0, side * 0.55, -1)).to_track_quat("-Z", "Y").to_euler()
    lo.visible_camera = False
    scn.collection.objects.link(lo)

# ------------------------------------------------------------------ render settings
r = scn.render
r.engine = "CYCLES" if ENGINE == "CYCLES" else "BLENDER_EEVEE"
r.resolution_x, r.resolution_y, r.resolution_percentage = R["width"], R["height"], A.scale
r.fps = fps
r.film_transparent = False
r.image_settings.file_format = "PNG"
r.image_settings.color_mode = "RGB"
r.image_settings.compression = 15
r.use_motion_blur = R.get("motion_blur", True)
r.motion_blur_shutter = R.get("shutter", 0.5)
cy_ = scn.cycles
cy_.device = "CPU"
cy_.samples = A.samples or R.get("samples", 48)
cy_.use_adaptive_sampling = True
cy_.adaptive_threshold = R.get("adaptive_threshold", 0.05)
cy_.use_denoising = True
cy_.denoiser = "OPENIMAGEDENOISE"
cy_.denoising_input_passes = "RGB_ALBEDO_NORMAL"
cy_.max_bounces = 5
cy_.diffuse_bounces = 2
cy_.glossy_bounces = 3
cy_.transmission_bounces = 0
cy_.volume_bounces = 0
cy_.caustics_reflective = cy_.caustics_refractive = False
cy_.sample_clamp_indirect = 4.0
cy_.use_persistent_data = True  # keep BVH between frames; only the camera moves
r.threads_mode = "AUTO"
ee = scn.eevee
ee.taa_render_samples = R.get("eevee_samples", 16)
ee.use_gtao = R.get("ao", True)
ee.gtao_distance = 6.0
ee.use_ssr = R.get("ssr", True)
ee.use_ssr_halfres = R.get("ssr_halfres", True)
ee.ssr_quality = 0.5
ee.ssr_max_roughness = 0.4
ee.ssr_thickness = 2.0
ee.use_soft_shadows = True
ee.shadow_cascade_size = str(R.get("shadow_size", 2048))
ee.shadow_cube_size = "1024"
ee.use_shadow_high_bitdepth = True
ee.use_motion_blur = R.get("motion_blur", True)
ee.motion_blur_shutter = R.get("shutter", 0.5)
ee.motion_blur_steps = R.get("eevee_blur_steps", 4)
sun.data.shadow_cascade_count = 4
sun.data.shadow_cascade_max_distance = 1500
sun.data.shadow_cascade_exponent = 0.9
scn.view_settings.view_transform = "Filmic"
scn.view_settings.look = R.get("look", "Medium High Contrast")
scn.view_settings.exposure = R.get("exposure", 0.0)

# aerial haze: blend geometry toward a haze colour by distance, then lay it over the sky
vl = scn.view_layers[0]
vl.use_pass_mist = True
world.mist_settings.start = R.get("haze_start", 120)
world.mist_settings.depth = R.get("haze_depth", 3500)
world.mist_settings.falloff = "LINEAR"
scn.use_nodes = True
ct = NT(scn.node_tree)
rl = ct.n("CompositorNodeRLayers")
hz = ct.n("CompositorNodeMixRGB")
hz.inputs[2].default_value = (*R.get("haze_colour", (0.62, 0.72, 0.84)), 1)
fac = ct.n("CompositorNodeMath", operation="MULTIPLY")
fac.inputs[1].default_value = R.get("haze_amount", 0.6)
ct.link(rl.outputs["Mist"], fac.inputs[0])
# the sky sits at mist == 1; leave it (and its clouds) untouched
not_sky = ct.n("CompositorNodeMath", operation="LESS_THAN")
not_sky.inputs[1].default_value = 0.999
ct.link(rl.outputs["Mist"], not_sky.inputs[0])
fac2 = ct.n("CompositorNodeMath", operation="MULTIPLY")
ct.link(fac.outputs[0], fac2.inputs[0])
ct.link(not_sky.outputs[0], fac2.inputs[1])
ct.link(fac2.outputs[0], hz.inputs[0])
ct.link(rl.outputs["Image"], hz.inputs[1])
comp = ct.n("CompositorNodeComposite")
ct.link(hz.outputs[0], comp.inputs[0])

if A.keys:
    # Fast path (pipeline/fast_shot.py): a sharp world-only keyframe with its depth, plus the camera
    # pose of every frame of the shot, so the in-between frames can be synthesised by reprojection.
    from mathutils import Euler, Matrix
    r.use_motion_blur = ee.use_motion_blur = False
    cam_data.dof.use_dof = False
    cam_data.clip_start = 0.75   # nothing nearer than the window glass: the carriage wall would hide it
    vl.use_pass_z = True
    fo = ct.n("CompositorNodeOutputFile")
    fo.base_path = str((ROOT / A.out).parent)
    fo.format.file_format, fo.format.color_depth, fo.format.color_mode = "OPEN_EXR", "32", "RGB"
    fo.file_slots[0].path = "z_"
    ct.link(rl.outputs["Depth"], fo.inputs[0])
    local = Matrix.Translation(cam.location) @ cam.rotation_euler.to_matrix().to_4x4()
    poses = []
    for f in range(n_total + 1):
        loc, rot = car_pose(f)
        poses.append([list(row) for row in (Matrix.Translation(loc) @ Euler(rot).to_matrix().to_4x4() @ local)])
    (ROOT / A.out).parent.mkdir(parents=True, exist_ok=True)
    ((ROOT / A.out).parent / "poses.json").write_text(json.dumps({
        "fps": fps, "frames": n_total, "width": R["width"], "height": R["height"], "hfov_deg": C["hfov_deg"],
        "shift_y": C.get("shift_y", 0.0), "cam_to_world": poses,
        "cars": [{"a": list(map(float, a)), "u": list(map(float, u)), "n": list(map(float, nv)), "L": float(L), "lane": float(lane),
                  "dir": float(d), "phase": ph, "speed": spd, "bus": bool(root_["bus"])} for root_, a, u, nv, L, lane, d, ph, spd in CARS],
        "boats": [b for _, b in BOATS], "river_centre": [list(map(float, q)) for q in rc] if len(rc) else None}))

if A.carriage_only:
    # The interior is rigid with the camera, so one RGBA still of it serves the whole shot.
    for ob in scn.objects:
        if ob.parent is not car and ob not in (car, cam, sun):
            ob.hide_render = True
    r.film_transparent = True
    r.image_settings.color_mode = "RGBA"
    r.use_motion_blur = ee.use_motion_blur = False
    ct.link(rl.outputs["Image"], comp.inputs[0])

if A.layers:
    # Orthographic elevation strips, one per depth slab, with alpha. They are
    # scrolled at different speeds by pipeline/parallax_loop.py: a handful of
    # still renders instead of thousands of 3D frames.
    L = S["layers"]
    scn.use_nodes = False
    r.film_transparent = True
    r.image_settings.color_mode = "RGBA"
    r.use_motion_blur = False
    ee.use_motion_blur = False
    ee.taa_render_samples = L.get("samples", 16)
    for m_ in bpy.data.materials:
        m_.use_backface_culling = True
    x0, x1, cam_y = L["x0"], L["x1"], L["cam_y"]
    od = bpy.data.cameras.new("ortho")
    od.type = "ORTHO"
    oc = bpy.data.objects.new("ortho", od)
    scn.collection.objects.link(oc)
    scn.camera = oc
    oc.rotation_euler = (math.pi / 2, 0, 0)
    outd = ROOT / L["out_dir"]
    outd.mkdir(parents=True, exist_ok=True)
    meta = []
    for sl in L["slabs"]:
        ppm = L["focal_px"] / sl["ref_depth"]
        wpx, hpx = int(round((x1 - x0) * ppm)), int(round((sl["z_max"] - sl["z_min"]) * ppm))
        r.resolution_x, r.resolution_y, r.resolution_percentage = wpx, hpx, 100
        od.ortho_scale = max(x1 - x0, sl["z_max"] - sl["z_min"])
        od.clip_start, od.clip_end = sl["y_lo"] - cam_y, sl["y_hi"] - cam_y
        oc.location = ((x0 + x1) / 2, cam_y, (sl["z_min"] + sl["z_max"]) / 2)
        scn.frame_set(0)
        r.filepath = str(outd / f"layer_{sl['name']}.png")
        import time as _t
        t0 = _t.time()
        bpy.ops.render.render(write_still=True)
        meta.append({**sl, "px_per_m": ppm, "width": wpx, "height": hpx, "render_s": round(_t.time() - t0, 1),
                     "file": f"layer_{sl['name']}.png"})
        print("LAYER", meta[-1], flush=True)
    (outd / "layers.json").write_text(json.dumps({"x0": x0, "x1": x1, "cam_y": cam_y, "focal_px": L["focal_px"],
                                                  "eye_z": L["eye_z"], "slabs": meta}, indent=1))
    sys.exit(0)

if A.save_blend:
    bpy.ops.wm.save_as_mainfile(filepath=str(pathlib.Path(A.save_blend).resolve()))
if not A.no_render:
    out = ROOT / A.out
    out.parent.mkdir(parents=True, exist_ok=True)
    scn.frame_start, scn.frame_end, scn.frame_step = f0, f1, A.step
    r.filepath = str(out) + "_"
    bpy.ops.render.render(animation=True)
