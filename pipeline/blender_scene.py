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
ap.add_argument("--engine", default=None, choices=["CYCLES", "EEVEE"])
A = ap.parse_args(argv)
S = json.loads(pathlib.Path(A.scene).read_text())
R = S["render"]
MESH = ROOT / S.get("mesh_dir", "work/meshes")

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene


# ------------------------------------------------------------------ helpers
def load(name, mat):
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


def facade():
    """Procedural facade: uv.x counts window bays, uv.y counts floors."""
    m, nt, out = material("facade")
    att = nt.n("ShaderNodeAttribute", attribute_name="Col")
    style = att.outputs["Alpha"]
    uv = nt.n("ShaderNodeUVMap")
    sep = nt.n("ShaderNodeSeparateXYZ")
    nt.link(uv.outputs[0], sep.inputs[0])
    u, v = sep.outputs[0], sep.outputs[1]
    fu, fv = nt.math("FRACT", u), nt.math("FRACT", v)

    def band(x, lo, hi):
        return nt.math("MULTIPLY", nt.math("GREATER_THAN", x, lo), nt.math("LESS_THAN", x, hi))

    punched = nt.math("MULTIPLY", band(fu, 0.24, 0.76), band(fv, 0.30, 0.80))
    curtain = nt.math("MULTIPLY", band(fu, 0.05, 0.95), band(fv, 0.22, 1.01))
    mask = nt.math("ADD", nt.math("MULTIPLY", punched, nt.math("SUBTRACT", 1.0, style)),
                   nt.math("MULTIPLY", curtain, style))
    # street level: taller dark storefront band on masonry buildings
    ground = nt.math("LESS_THAN", v, 1.25)
    mask = nt.math("MAXIMUM", mask, nt.math("MULTIPLY", ground, nt.math("MULTIPLY", band(fu, 0.1, 0.9), band(v, 0.15, 1.05))))

    cell = nt.n("ShaderNodeCombineXYZ")
    nt.link(nt.math("FLOOR", u), cell.inputs[0])
    nt.link(nt.math("FLOOR", v), cell.inputs[1])
    wn = nt.n("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    nt.link(cell.outputs[0], wn.inputs["Vector"])
    r = wn.outputs["Value"]

    base = att.outputs["Color"]
    # glass: curtain walls take the building tint; punched windows are dark blue-grey
    glass_tint = nt.mix(style, (0.07, 0.10, 0.13), base)
    shade = nt.math("ADD", 0.55, nt.math("MULTIPLY", r, 0.7))
    glass = nt.mix(1.0, glass_tint, (0, 0, 0))
    nt.t.nodes[-1].blend_type = "MULTIPLY"
    mul = nt.n("ShaderNodeVectorMath", operation="SCALE")
    nt.link(glass_tint, mul.inputs[0])
    nt.link(shade, mul.inputs["Scale"])
    glass = mul.outputs[0]
    # wall: slight large-scale weathering so big facades are not flat colour
    noise = nt.n("ShaderNodeTexNoise", i_Scale=0.02, i_Detail=3.0)
    geo = nt.n("ShaderNodeNewGeometry")
    nt.link(geo.outputs["Position"], noise.inputs["Vector"])
    wall_scale = nt.n("ShaderNodeVectorMath", operation="SCALE")
    nt.link(base, wall_scale.inputs[0])
    nt.link(nt.math("ADD", 0.86, nt.math("MULTIPLY", noise.outputs["Fac"], 0.28)), wall_scale.inputs["Scale"])
    spandrel = nt.mix(nt.math("MULTIPLY", style, 0.35), wall_scale.outputs[0], (0.05, 0.06, 0.07))
    colour = nt.mix(mask, spandrel, glass)

    b = nt.n("ShaderNodeBsdfPrincipled", i_Specular=0.5)
    nt.link(colour, b.inputs["Base Color"])
    nt.link(nt.math("SUBTRACT", nt.math("SUBTRACT", 0.85, nt.math("MULTIPLY", style, 0.45)),
                    nt.math("MULTIPLY", mask, nt.math("SUBTRACT", 0.77, nt.math("MULTIPLY", style, 0.42)))),
            b.inputs["Roughness"])
    nt.link(nt.math("MULTIPLY", mask, nt.math("ADD", 0.25, nt.math("MULTIPLY", style, 0.55))), b.inputs["Metallic"])
    nt.link(b.outputs[0], out.inputs[0])
    return m


def water():
    m, nt, out = material("water")
    b = nt.n("ShaderNodeBsdfPrincipled", i_Roughness=0.06, i_Specular=0.6, i_Metallic=0.0)
    b.inputs["Base Color"].default_value = (*R.get("water_colour", (0.035, 0.12, 0.11)), 1)
    geo = nt.n("ShaderNodeNewGeometry")
    mp = nt.n("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.35, 0.12, 1.0)
    mp.inputs["Rotation"].default_value = (0, 0, 0.2)
    nt.link(geo.outputs["Position"], mp.inputs["Vector"])
    noise = nt.n("ShaderNodeTexNoise", i_Scale=1.0, i_Detail=4.0, i_Roughness=0.6)
    nt.link(mp.outputs[0], noise.inputs["Vector"])
    bump = nt.n("ShaderNodeBump", i_Strength=0.12, i_Distance=0.4)
    nt.link(noise.outputs["Fac"], bump.inputs["Height"])
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
load("land", ground("sidewalk", (0.50, 0.49, 0.46)))
load("quay", ground("quay", (0.36, 0.34, 0.31), scale=0.3))
load("water", water())
load("roads", ground("asphalt", (0.085, 0.087, 0.092), 0.85))
load("parks", ground("park", (0.16, 0.30, 0.09), 0.95, 0.4, 0.15))
load("bridges", simple("bridge", (0.30, 0.085, 0.07), 0.6))
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

# sun + sky
sun_el, sun_az = math.radians(R["sun_elevation_deg"]), math.radians(R["sun_azimuth_deg"])
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
sun.data.energy = R.get("sun_strength", 4.0)
sun.data.angle = math.radians(R.get("sun_angle_deg", 1.5))
sun.data.color = R.get("sun_colour", (1.0, 0.93, 0.82))
to_sun = Vector((math.sin(sun_az) * math.cos(sun_el), math.cos(sun_az) * math.cos(sun_el), math.sin(sun_el)))
sun.rotation_euler = to_sun.to_track_quat("Z", "Y").to_euler()
scn.collection.objects.link(sun)

world = bpy.data.worlds.new("World")
scn.world = world
world.use_nodes = True
nt = NT(world.node_tree)
wout = nt.n("ShaderNodeOutputWorld")
sky = nt.n("ShaderNodeTexSky", sky_type="NISHITA", sun_disc=False, sun_elevation=sun_el,
           sun_rotation=sun_az, air_density=1.0, dust_density=R.get("dust", 1.5), ozone_density=1.0)
# painterly cumulus: fbm noise projected on a plane overhead, faded at the horizon
geo = nt.n("ShaderNodeTexCoord")
sep = nt.n("ShaderNodeSeparateXYZ")
nt.link(geo.outputs["Generated"], sep.inputs[0])  # for a world shader this is the view direction
up = nt.math("MULTIPLY", sep.outputs[2], 1.0)
inv = nt.math("DIVIDE", 1.0, nt.math("MAXIMUM", nt.math("ADD", up, 0.12), 0.05))
proj = nt.n("ShaderNodeCombineXYZ")
nt.link(nt.math("MULTIPLY", sep.outputs[0], inv), proj.inputs[0])
nt.link(nt.math("MULTIPLY", sep.outputs[1], inv), proj.inputs[1])
cn = nt.n("ShaderNodeTexNoise", i_Scale=R.get("cloud_scale", 0.55), i_Detail=7.0, i_Roughness=0.55, i_Distortion=0.25)
nt.link(proj.outputs[0], cn.inputs["Vector"])
ramp = nt.n("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = R.get("cloud_lo", 0.53)
ramp.color_ramp.elements[1].position = R.get("cloud_hi", 0.70)
nt.link(cn.outputs["Fac"], ramp.inputs[0])
horizon = nt.n("ShaderNodeMapRange", clamp=True)
horizon.inputs[1].default_value, horizon.inputs[2].default_value = 0.0, 0.14
nt.link(up, horizon.inputs[0])
cover = nt.math("MULTIPLY", nt.math("MULTIPLY", ramp.outputs[0], horizon.outputs[0]), R.get("cloud_amount", 0.9))
# cloud body brighter on top noise, slightly warm
cloud_col = nt.mix(cn.outputs["Fac"], tuple(R.get("cloud_shadow", (0.55, 0.60, 0.70))), tuple(R.get("cloud_light", (1.0, 0.97, 0.92))))
cs = nt.n("ShaderNodeVectorMath", operation="SCALE")
nt.link(cloud_col, cs.inputs[0])
cs.inputs["Scale"].default_value = R.get("cloud_brightness", 1.6)
sk = nt.n("ShaderNodeVectorMath", operation="SCALE")
nt.link(sky.outputs[0], sk.inputs[0])
sk.inputs["Scale"].default_value = R.get("sky_strength", 0.28)
final = nt.mix(cover, sk.outputs[0], cs.outputs[0])
bg = nt.n("ShaderNodeBackground")
nt.link(final, bg.inputs[0])
nt.link(bg.outputs[0], wout.inputs[0])

# ------------------------------------------------------------------ camera
C = S["camera"]
path = json.loads((MESH / "camera_path.json").read_text())
P = np.array(path["points"])
seg = np.hypot(*np.diff(P, axis=0).T)
cum = np.concatenate([[0], np.cumsum(seg)])
s0 = cum[np.argmin(np.hypot(P[:, 0] - C["start_xy"][0], P[:, 1] - C["start_xy"][1]))]
fps = R["fps"]


def at(s):
    s = min(max(s, 0.0), cum[-1] - 0.01)
    return np.array([np.interp(s, cum, P[:, 0]), np.interp(s, cum, P[:, 1])])


cam_data = bpy.data.cameras.new("Cam")
cam_data.sensor_width = 36
cam_data.lens = 18 / math.tan(math.radians(C["hfov_deg"]) / 2)
cam_data.shift_y = C.get("shift_y", 0.0)
cam_data.clip_start, cam_data.clip_end = 0.05, 20000
cam = bpy.data.objects.new("Cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam
eye_z = path["rail_top_z"] + C["eye_above_rail_m"]
yaw = math.radians(C["yaw_from_forward_deg"])
f0, f1 = (int(x) for x in A.frames.split("-"))
n_total = int(round(C["duration_s"] * fps))
for f in range(0, n_total + 1):
    t = f / fps
    s = s0 + C["speed_mps"] * t
    p = at(s)
    tan = at(s + 7.0) - at(s - 7.0)  # long baseline = no twitch at polyline vertices
    tan /= np.linalg.norm(tan)
    left = np.array([-tan[1], tan[0]])
    side = -1.0 if C.get("look", "left") == "right" else 1.0
    d = math.cos(yaw) * tan + math.sin(yaw) * left * side
    sway = C.get("sway", 1.0)
    z = eye_z + sway * 0.006 * math.sin(2 * math.pi * 0.9 * t) + sway * 0.004 * math.sin(2 * math.pi * 0.37 * t + 1)
    roll = math.radians(sway * (0.10 * math.sin(2 * math.pi * 0.31 * t) + 0.05 * math.sin(2 * math.pi * 0.83 * t + 2)))
    fwd = Vector((d[0], d[1], 0.0))
    rot = fwd.to_track_quat("-Z", "Y").to_matrix().to_4x4() @ Matrix.Rotation(roll, 4, "Z")
    off = left * side * C.get("seat_offset_m", 0.9)
    cam.matrix_world = Matrix.Translation((p[0] + off[0], p[1] + off[1], z)) @ rot
    cam.keyframe_insert("location", frame=f)
    cam.keyframe_insert("rotation_euler", frame=f)
for root, b in BOATS:
    for f in (0, n_total):
        x = b["x0"] + b["speed_mps"] * f / fps
        y = float(np.interp(x, rc[:, 0], rc[:, 1])) + b.get("offset", 0.0)
        y2 = float(np.interp(x + 5, rc[:, 0], rc[:, 1])) + b.get("offset", 0.0)
        root.location = (x, y, -4.0)
        root.rotation_euler = (0, 0, math.atan2(y2 - y, 5.0) + (math.pi if b["speed_mps"] < 0 else 0))
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
    for fc in root.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"
for fc in cam.animation_data.action.fcurves:
    for k in fc.keyframe_points:
        k.interpolation = "LINEAR"

# ------------------------------------------------------------------ train window
W = S.get("window", {})
if W.get("enabled", True):
    dist = 0.6
    hw = dist * math.tan(math.radians(C["hfov_deg"]) / 2)
    hh = hw * 9 / 16
    cy = cam_data.shift_y * 2 * hw  # lens shift moves the frame centre
    x0, x1 = -hw * (1 - 2 * W.get("side", 0.085)), hw * (1 - 2 * W.get("side", 0.085))
    y0, y1 = cy - hh * (1 - 2 * W.get("bottom", 0.13)), cy + hh * (1 - 2 * W.get("top", 0.07))
    rad, n = W.get("radius", 0.075), 14

    def rrect(x0, x1, y0, y1, r):
        pts = []
        for cx, cy_, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
            for k in range(n + 1):
                a = math.radians(a0 + 90 * k / n)
                pts.append((cx + r * math.cos(a), cy_ + r * math.sin(a)))
        return pts

    def ring_mesh(name, outer, inner, z, mat):
        me = bpy.data.meshes.new(name)
        m = len(inner)
        verts = [(x, y, z) for x, y in inner] + [(x, y, z) for x, y in outer]
        faces = [(i, (i + 1) % m, m + (i + 1) % m, m + i) for i in range(m)]
        me.from_pydata(verts, [], faces)
        me.materials.append(mat)
        ob = bpy.data.objects.new(name, me)
        ob.parent = cam
        scn.collection.objects.link(ob)
        ob.visible_shadow = False
        return ob

    inner = rrect(x0, x1, y0, y1, rad)
    big = 3.0
    # matching vertex count for the outer boundary: project inner ring outward
    outer = [(x * 1 + (big if x > (x0 + x1) / 2 else -big), y + (big if y > (y0 + y1) / 2 else -big)) for x, y in inner]
    ring_mesh("win_wall", outer, inner, -dist, flat_emission("car_wall", tuple(W.get("wall_colour", (0.030, 0.027, 0.025)))))
    g = 0.012
    gasket_outer = rrect(x0 - g, x1 + g, y0 - g, y1 + g, rad + g)
    ring_mesh("win_gasket", gasket_outer, inner, -dist + 0.002, flat_emission("gasket", (0.004, 0.004, 0.004)))
    lip = W.get("lip", 0.014)
    lip_outer = rrect(x0 - g - lip, x1 + g + lip, y0 - g - lip, y1 + g + lip, rad + g + lip)
    ring_mesh("win_lip", lip_outer, gasket_outer, -dist + 0.001, flat_emission("lip", tuple(W.get("lip_colour", (0.085, 0.078, 0.07)))))

# ------------------------------------------------------------------ render settings
r = scn.render
ENGINE = A.engine or R.get("engine", "CYCLES")
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
cy_.samples = A.samples or R["samples"]
cy_.use_adaptive_sampling = True
cy_.adaptive_threshold = R.get("adaptive_threshold", 0.05)
cy_.use_denoising = True
cy_.denoiser = "OPENIMAGEDENOISE"
cy_.denoising_input_passes = "RGB_ALBEDO_NORMAL"
cy_.max_bounces = 4
cy_.diffuse_bounces = 2
cy_.glossy_bounces = 2
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

if A.save_blend:
    bpy.ops.wm.save_as_mainfile(filepath=str(pathlib.Path(A.save_blend).resolve()))
if not A.no_render:
    out = ROOT / A.out
    out.parent.mkdir(parents=True, exist_ok=True)
    scn.frame_start, scn.frame_end, scn.frame_step = f0, f1, A.step
    r.filepath = str(out) + "_"
    bpy.ops.render.render(animation=True)
