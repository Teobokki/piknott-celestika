"""PIKNOTT CELESTIKA - PIKCEL ball generator (original design).
Run headless:  blender -b -P blender/pikcel_balls.py
Builds three toon-coloured ball variants (Pikcel / Nova / Astral), saves blender/pikcel_balls.blend,
exports assets/models/<variant>.glb and renders a cel-style preview to docs/pikcel_balls_render.png."""
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MODELS = os.path.join(ROOT, "assets", "models")
os.makedirs(OUT_MODELS, exist_ok=True)

VARIANTS = {
    # name: (top colour, bottom colour, band colour, star colour, accent)
    "pikcel_ball": ((0.20, 0.62, 0.98), (0.98, 0.95, 0.86), (0.10, 0.12, 0.22), (1.00, 0.82, 0.12), None),
    "nova_ball":   ((0.62, 0.30, 0.95), (0.98, 0.95, 0.86), (0.78, 0.80, 0.88), (1.00, 0.45, 0.70), "studs"),
    "astral_ball": ((0.07, 0.10, 0.30), (0.95, 0.80, 0.30), (0.98, 0.78, 0.18), (0.35, 0.95, 1.00), "halo"),
}

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)


def mat(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*rgb, 1.0)
    p.inputs["Roughness"].default_value = 0.8
    m["toon_rgb"] = list(rgb)
    return m


def smooth(o):
    for p in o.data.polygons:
        p.use_smooth = True


def hemisphere(name, top, m):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1.0)
    o = bpy.context.active_object; o.name = name
    bm = bmesh.new(); bm.from_mesh(o.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    off = 0.04 if top else -0.04
    bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, off), plane_no=(0, 0, 1), clear_inner=top, clear_outer=not top)
    # cap the open side so the ball looks solid when it opens
    edges = [e for e in bm.edges if e.is_boundary]
    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bm.to_mesh(o.data); bm.free()
    o.data.materials.append(m); smooth(o)
    return o


def torus(name, major, minor, m, z=0.0, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=48, minor_segments=10,
                                     location=(0, 0, z), rotation=rot)
    o = bpy.context.active_object; o.name = name
    o.data.materials.append(m); smooth(o)
    return o


def star(name, r_out, r_in, depth, m, loc, rot):
    bm = bmesh.new()
    pts = []
    for i in range(10):
        a = math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append((math.cos(a) * r, math.sin(a) * r))
    front = [bm.verts.new((x, y, depth / 2)) for x, y in pts]
    back = [bm.verts.new((x, y, -depth / 2)) for x, y in pts]
    cf = bm.verts.new((0, 0, depth / 2 + depth * 0.6)); cb = bm.verts.new((0, 0, -depth / 2))
    for i in range(10):
        j = (i + 1) % 10
        bm.faces.new((front[i], front[j], cf))
        bm.faces.new((back[j], back[i], cb))
        bm.faces.new((front[j], front[i], back[i], back[j]))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    o.data.materials.append(m)
    return o


def cylinder(name, r, depth, m, loc, rot):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=r, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(m)
    return o


def build(variant, x_off):
    top, bot, band, starc, accent = VARIANTS[variant]
    mt, mb, mband, ms = mat(variant + "_top", top), mat(variant + "_bottom", bot), mat(variant + "_band", band), mat(variant + "_star", starc)
    parts = [hemisphere(variant + "_top", True, mt), hemisphere(variant + "_bot", False, mb),
             torus(variant + "_band", 1.0, 0.075, mband)]
    # button: a ring socket on the front (-Y) with a glowing 5-point star
    parts.append(cylinder(variant + "_socket", 0.33, 0.16, mband, (0, -0.98, 0), (math.pi / 2, 0, 0)))
    parts.append(cylinder(variant + "_plate", 0.28, 0.10, mb, (0, -1.05, 0), (math.pi / 2, 0, 0)))
    parts.append(star(variant + "_star", 0.25, 0.11, 0.08, ms, (0, -1.11, 0), (math.pi / 2, 0, 0)))
    if accent == "studs":       # Nova: four little star studs orbiting the crown
        for k in range(4):
            a = k * math.pi / 2 + math.pi / 4
            p = Vector((math.cos(a) * 0.62, math.sin(a) * 0.62, 0.80))
            s = star(variant + "_stud%d" % k, 0.13, 0.055, 0.06, ms, p, (0, 0, 0))
            s.rotation_mode = 'QUATERNION'; s.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(p.normalized())
            parts.append(s)
    if accent == "halo":        # Astral: gold latitude stripes + a tilted orbit halo
        parts.append(torus(variant + "_stripe1", 0.80, 0.045, mband, z=0.60))
        parts.append(torus(variant + "_stripe2", 0.47, 0.045, mband, z=0.88))
        parts.append(torus(variant + "_halo", 1.32, 0.04, ms, rot=(math.radians(68), 0, math.radians(20))))
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    o = bpy.context.active_object; o.name = variant
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return o


balls = [build(v, 0) for v in VARIANTS]

# ---- export each variant on its own at the origin
for o in balls:
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT_MODELS, o.name + ".glb"), export_format='GLB',
                              use_selection=True, export_apply=True, export_yup=True)

# lay them out for the preview and save the source .blend
for i, o in enumerate(balls):
    o.location = ((i - 1) * 2.9, 0, 0)
    o.rotation_euler = (math.radians(8), 0, math.radians(-14 + i * 14))
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "pikcel_balls.blend"))

# ---- cel-style preview: stepped (constant ColorRamp) lighting into Emission + Freestyle ink lines
L = Vector((-0.45, -0.75, 0.55)).normalized()
for m in bpy.data.materials:
    if "toon_rgb" not in m:
        continue
    rgb = list(m["toon_rgb"])
    nt = m.node_tree; nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'; dot.inputs[1].default_value = L
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = 'CONSTANT'
    e = ramp.color_ramp.elements
    e[0].position = 0.0; e[0].color = (*[c * 0.55 for c in rgb], 1)
    e[1].position = 0.52; e[1].color = (*[c * 0.82 for c in rgb], 1)
    e3 = e.new(0.80); e3.color = (*rgb, 1)
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs[1].default_value = -1; mr.inputs[2].default_value = 1
    em = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    nt.links.new(dot.outputs["Value"], mr.inputs[0])
    nt.links.new(mr.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], em.inputs[0])
    nt.links.new(em.outputs[0], out.inputs[0])

sc = bpy.context.scene
sc.render.engine = 'CYCLES'; sc.cycles.samples = 12; sc.cycles.device = 'CPU'
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x, sc.render.resolution_y = 1600, 800
sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 3.5
ls = sc.view_layers[0].freestyle_settings.linesets[0]
ls.select_by_visibility = True; ls.select_silhouette = True; ls.select_border = True; ls.select_crease = False
ls.linestyle.color = (0.03, 0.03, 0.06)
w = sc.world or bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.90, 0.96, 1)
cam = bpy.data.cameras.new("cam"); cam.lens = 50
co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
co.location = (0, -13.5, 3.0)
co.rotation_euler = (Vector((0, 0, 0)) - co.location).to_track_quat('-Z', 'Y').to_euler()
sc.render.filepath = os.path.join(ROOT, "docs", "pikcel_balls_render.png")
bpy.ops.render.render(write_still=True)
print("PIKCEL_DONE")
