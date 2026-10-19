"""Cel shading for PIKNOTT CELESTIKA: stepped toon-ramp lighting + inverted-hull black ink outlines,
plus a tiny procedural mesh builder (vertex colours, per-vertex 'ink' extrusion normals)."""
import math
import numpy as np
from panda3d.core import (Shader, GeomVertexFormat, GeomVertexArrayFormat, GeomVertexData, GeomVertexWriter, Geom,
                          GeomTriangles, GeomNode, InternalName, CullFaceAttrib, NodePath, Vec3, Vec4,
                          MaterialAttrib, ColorAttrib, TransparencyAttrib)

TOON_VERT = """#version 120
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
attribute vec4 p3d_Vertex;
attribute vec3 p3d_Normal;
attribute vec4 p3d_Color;
varying vec3 v_n;
varying vec4 v_c;
varying vec3 v_w;
void main() {
  gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
  v_w = (p3d_ModelMatrix * p3d_Vertex).xyz;
  v_n = mat3(p3d_ModelMatrix) * p3d_Normal;
  v_c = p3d_Color;
}
"""
TOON_FRAG = """#version 120
uniform mat4 p3d_ViewMatrixInverse;
uniform vec4 p3d_ColorScale;
uniform vec3 light_dir;
uniform vec3 fog_col;
uniform float fog_far;
uniform float flash;
uniform float rim_k;
uniform float spec_k;
uniform float unlit;
varying vec3 v_n;
varying vec4 v_c;
varying vec3 v_w;
void main() {
  vec4 c = v_c * p3d_ColorScale;
  vec3 camp = p3d_ViewMatrixInverse[3].xyz;
  float dist = length(v_w - camp);
  vec3 col;
  if (unlit > 0.5) {
    col = c.rgb;
  } else {
    vec3 n = normalize(v_n);
    if (!gl_FrontFacing) n = -n;
    vec3 L = normalize(light_dir);
    vec3 V = normalize(camp - v_w);
    float d = dot(n, L);
    // hard anime ramp: lit / half-tone / cool shadow with a crisp terminator
    float lit = smoothstep(0.08, 0.13, d);
    float mid = smoothstep(-0.32, -0.27, d);
    vec3 shade_cool = c.rgb * vec3(0.50, 0.55, 0.78);
    vec3 half_tone = c.rgb * vec3(0.80, 0.80, 0.92);
    vec3 sunlit = c.rgb * vec3(1.05, 1.02, 0.96);
    col = mix(shade_cool, mix(half_tone, sunlit, lit), mid);
    // specular highlight band
    float sp = dot(normalize(L + V), n);
    col += vec3(1.0, 0.98, 0.9) * smoothstep(0.955, 0.965, sp) * 0.35 * spec_k * lit;
    // rim light (anime back-light)
    float r = 1.0 - max(dot(n, V), 0.0);
    col += vec3(0.95, 0.97, 1.0) * smoothstep(0.66, 0.70, r) * 0.32 * rim_k * (0.4 + 0.6 * mid);
  }
  col = mix(col, vec3(1.0), flash);
  float f = clamp((dist - fog_far * 0.25) / (fog_far * 0.75), 0.0, 1.0);
  f = f * f * (3.0 - 2.0 * f);
  gl_FragColor = vec4(mix(col, fog_col, f * 0.9 * (1.0 - unlit)), c.a);
}
"""
INK_VERT = """#version 120
uniform mat4 p3d_ViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
uniform mat4 p3d_ViewMatrixInverse;
uniform float ink_w;
attribute vec4 p3d_Vertex;
attribute vec3 %s;
void main() {
  vec4 wp = p3d_ModelMatrix * p3d_Vertex;
  vec3 n = normalize(mat3(p3d_ModelMatrix) * %s);
  float dist = length(wp.xyz - p3d_ViewMatrixInverse[3].xyz);
  wp.xyz += n * ink_w * clamp(dist * 0.1, 0.8, 4.0);
  gl_Position = p3d_ViewProjectionMatrix * wp;
}
"""
INK_FRAG = """#version 120
uniform vec4 ink_col;
void main() { gl_FragColor = ink_col; }
"""

_shaders = {}
LIGHT = Vec3(-0.55, -0.45, 0.70).normalized()


def shaders():
    if not _shaders:
        _shaders["toon"] = Shader.make(Shader.SL_GLSL, TOON_VERT, TOON_FRAG)
        _shaders["ink"] = Shader.make(Shader.SL_GLSL, INK_VERT % ("ink", "ink"), INK_FRAG)
        _shaders["ink_n"] = Shader.make(Shader.SL_GLSL, INK_VERT % ("p3d_Normal", "p3d_Normal"), INK_FRAG)
    return _shaders


def setup_root(render, fog=(0.80, 0.86, 0.94), fog_far=260.0):
    s = shaders()
    render.set_shader(s["toon"])
    render.set_shader_input("light_dir", LIGHT)
    render.set_shader_input("fog_col", Vec3(*fog))
    render.set_shader_input("fog_far", float(fog_far))
    render.set_shader_input("flash", 0.0)
    render.set_shader_input("rim_k", 1.0)
    render.set_shader_input("spec_k", 0.0)
    render.set_shader_input("unlit", 0.0)
    render.set_shader_input("ink_w", 0.03)
    render.set_shader_input("ink_col", Vec4(0.05, 0.05, 0.09, 1))


def outlined(geom_np, parent, width=0.03, use_normals=False, name="obj"):
    """Return a holder node: the toon model plus an inverted-hull ink copy (instanced, so it follows edits)."""
    holder = parent.attach_new_node(name)
    body = holder.attach_new_node("body")
    geom_np.reparent_to(body)
    ink = holder.attach_new_node("ink")
    geom_np.instance_to(ink)
    ink.set_shader(shaders()["ink_n" if use_normals else "ink"], 10)
    ink.set_shader_input("ink_w", width)
    ink.set_attrib(CullFaceAttrib.make_reverse(), 10)
    ink.set_texture_off(10)
    ink.set_bin("opaque", 0)
    return holder


def material_to_flat_colour(np_):
    """glTF (Blender) models: copy the material base colour into a flat ColorAttrib so the toon shader sees it."""
    for gnp in np_.find_all_matches("**/+GeomNode"):
        gn = gnp.node()
        for i in range(gn.get_num_geoms()):
            st = gn.get_geom_state(i)
            ma = st.get_attrib(MaterialAttrib)
            if ma and ma.get_material():
                c = ma.get_material().get_base_color()
                gn.set_geom_state(i, st.add_attrib(ColorAttrib.make_flat(c)))
    np_.set_texture_off(5)


_FMT = None


def vformat():
    global _FMT
    if _FMT is None:
        a = GeomVertexArrayFormat()
        a.add_column(InternalName.get_vertex(), 3, Geom.NT_float32, Geom.C_point)
        a.add_column(InternalName.get_normal(), 3, Geom.NT_float32, Geom.C_normal)
        a.add_column(InternalName.get_color(), 4, Geom.NT_uint8, Geom.C_color)
        a.add_column(InternalName.make("ink"), 3, Geom.NT_float32, Geom.C_vector)
        _FMT = GeomVertexFormat.register_format(GeomVertexFormat(a))
    return _FMT


class Mesh:
    """Accumulates triangles as numpy-friendly lists then builds one GeomNode."""
    def __init__(self):
        self.v = []; self.n = []; self.c = []; self.k = []; self.i = []

    def add(self, verts, normals, color, inks, tris):
        base = len(self.v)
        self.v.extend(verts); self.n.extend(normals); self.k.extend(inks)
        if isinstance(color[0], (int, float)):
            col = tuple(color) + (1.0,) * (4 - len(color))
            self.c.extend([col] * len(verts))
        else:
            self.c.extend([tuple(cc) + (1.0,) * (4 - len(cc)) for cc in color])
        self.i.extend([(a + base, b + base, c + base) for a, b, c in tris])

    def node(self, name="mesh"):
        vd = GeomVertexData(name, vformat(), Geom.UH_static)
        n = len(self.v)
        vd.unclean_set_num_rows(n)
        arr = np.zeros(n, dtype=[("v", "f4", 3), ("n", "f4", 3), ("c", "u1", 4), ("k", "f4", 3)])
        arr["v"] = self.v; arr["n"] = self.n; arr["k"] = self.k
        arr["c"] = np.clip(np.array(self.c, dtype=np.float32) * 255, 0, 255)
        mv = memoryview(vd.modify_array(0)).cast("B")
        mv[:] = arr.tobytes()
        tri = GeomTriangles(Geom.UH_static)
        tri.set_index_type(Geom.NT_uint32)
        idx = np.array(self.i, dtype=np.uint32).ravel()
        ia = tri.modify_vertices(); ia.unclean_set_num_rows(len(idx))
        memoryview(ia).cast("B")[:] = idx.tobytes()
        g = Geom(vd); g.add_primitive(tri)
        gn = GeomNode(name); gn.add_geom(g)
        return NodePath(gn)

    # ---------------------------------------------------------------- primitives
    def ellipsoid(self, c, r, color, seg=18, rings=12, rot=None, flat=False):
        """Ellipsoid centred at c with radii r=(rx,ry,rz); optional 3x3 rotation matrix."""
        V, N, K, T = [], [], [], []
        c = np.array(c, float); r = np.array(r, float)
        R = np.eye(3) if rot is None else np.array(rot)
        for j in range(rings + 1):
            th = math.pi * j / rings
            for i in range(seg + 1):
                ph = 2 * math.pi * i / seg
                u = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)])
                p = R @ (u * r) + c
                nn = R @ (u / np.maximum(r, 1e-4)); nn /= (np.linalg.norm(nn) + 1e-9)
                V.append(tuple(p)); N.append(tuple(nn)); K.append(tuple(R @ u))
        for j in range(rings):
            for i in range(seg):
                a = j * (seg + 1) + i; b = a + seg + 1
                T.append((a, b, a + 1)); T.append((a + 1, b, b + 1))
        self.add(V, N, color, K, T)

    def sphere(self, c, r, color, seg=18, rings=12):
        self.ellipsoid(c, (r, r, r), color, seg, rings)

    def box(self, c, s, color, rot=None):
        """Axis box centre c, half-size s. Flat lighting normals, rounded ink normals (no hull gaps)."""
        c = np.array(c, float); s = np.array(s, float)
        R = np.eye(3) if rot is None else np.array(rot)
        faces = [((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((-1, 0, 0), (0, 0, 1), (0, 1, 0)), ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
                 ((0, -1, 0), (1, 0, 0), (0, 0, 1)), ((0, 0, 1), (1, 0, 0), (0, 1, 0)), ((0, 0, -1), (0, 1, 0), (1, 0, 0))]
        V, N, K, T = [], [], [], []
        for n, u, w in faces:
            n, u, w = np.array(n, float), np.array(u, float), np.array(w, float)
            b = len(V)
            for du, dw in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                corner = n + u * du + w * dw
                p = R @ (corner * s) + c
                V.append(tuple(p)); N.append(tuple(R @ n)); K.append(tuple(R @ (corner / np.linalg.norm(corner))))
            T += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
        self.add(V, N, color, K, T)

    def cone(self, base, h, r, color, seg=8, top_r=0.0, rot=None):
        """Cone / frustum standing on 'base' (centre), height h along +Z (rotated by rot)."""
        base = np.array(base, float); R = np.eye(3) if rot is None else np.array(rot)
        V, N, K, T = [], [], [], []
        slope = (r - top_r) / max(h, 1e-6)
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg; ca, sa = math.cos(a), math.sin(a)
            nn = np.array([ca, sa, slope]); nn /= np.linalg.norm(nn)
            for z, rr in ((0, r), (h, top_r)):
                p = R @ np.array([ca * rr, sa * rr, z]) + base
                ink = np.array([ca, sa, (z / h - 0.5) * 1.2]); ink /= np.linalg.norm(ink)
                V.append(tuple(p)); N.append(tuple(R @ nn)); K.append(tuple(R @ ink))
        for i in range(seg):
            a = i * 2
            T += [(a, a + 2, a + 1), (a + 1, a + 2, a + 3)]
        # bottom cap
        b = len(V); V.append(tuple(base)); N.append(tuple(R @ np.array([0, 0, -1.0]))); K.append(tuple(R @ np.array([0, 0, -1.0])))
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            V.append(tuple(R @ np.array([math.cos(a) * r, math.sin(a) * r, 0]) + base))
            N.append(tuple(R @ np.array([0, 0, -1.0]))); kk = np.array([math.cos(a), math.sin(a), -0.6]); K.append(tuple(R @ (kk / np.linalg.norm(kk))))
        for i in range(seg):
            T.append((b, b + 2 + i, b + 1 + i))
        if top_r > 0:
            b = len(V); top = base + R @ np.array([0, 0, h])
            V.append(tuple(top)); N.append(tuple(R @ np.array([0, 0, 1.0]))); K.append(tuple(R @ np.array([0, 0, 1.0])))
            for i in range(seg + 1):
                a = 2 * math.pi * i / seg
                V.append(tuple(R @ np.array([math.cos(a) * top_r, math.sin(a) * top_r, h]) + base))
                N.append(tuple(R @ np.array([0, 0, 1.0]))); kk = np.array([math.cos(a), math.sin(a), 0.6]); K.append(tuple(R @ (kk / np.linalg.norm(kk))))
            for i in range(seg):
                T.append((b, b + 1 + i, b + 2 + i))
        self.add(V, N, color, K, T)

    def rock(self, c, r, color, rng, seg=9, rings=6, smooth=True):
        """Faceted low-poly rock: jittered ellipsoid with flat-ish look."""
        V, N, K, T = [], [], [], []
        c = np.array(c, float)
        pts = {}
        for j in range(rings + 1):
            th = math.pi * j / rings
            for i in range(seg):
                ph = 2 * math.pi * (i + 0.5 * (j % 2)) / seg
                u = np.array([math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)])
                jit = 1.0 if j in (0, rings) else rng.uniform(0.75, 1.15)
                pts[(j, i)] = (u * np.array(r) * jit + c, u)
        def tri(a, b, cc):
            pa, ua = pts[a]; pb, ub = pts[b]; pc, uc = pts[cc]
            n = np.cross(pb - pa, pc - pa); n /= (np.linalg.norm(n) + 1e-9)
            k0 = len(V)
            for p, u in ((pa, ua), (pb, ub), (pc, uc)):
                V.append(tuple(p)); N.append(tuple(u) if smooth else tuple(n)); K.append(tuple(u))
            T.append((k0, k0 + 1, k0 + 2))
        for j in range(rings):
            for i in range(seg):
                a, b = (j, i), (j, (i + 1) % seg); cc, d = (j + 1, i), (j + 1, (i + 1) % seg)
                tri(a, cc, b); tri(b, cc, d)
        # fix winding so faces point outward
        for t_i, (a, b, cc) in enumerate(T):
            pa, pb, pc = (np.array(V[a]), np.array(V[b]), np.array(V[cc]))
            n = np.cross(pb - pa, pc - pa)
            if np.dot(n, (pa + pb + pc) / 3 - c) < 0:
                T[t_i] = (a, cc, b)
                if not smooth:
                    for q in (a, b, cc):
                        N[q] = tuple(-np.array(N[q]))
        self.add(V, N, color, K, T)


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def mm(*rs):
    out = np.eye(3)
    for r in rs:
        out = out @ np.array(r)
    return out


def node_from_arrays(v, n, c, k, name="mesh"):
    """Non-indexed triangle soup from numpy arrays (N*3 vertices)."""
    m = len(v)
    vd = GeomVertexData(name, vformat(), Geom.UH_static)
    vd.unclean_set_num_rows(m)
    arr = np.zeros(m, dtype=[("v", "f4", 3), ("n", "f4", 3), ("c", "u1", 4), ("k", "f4", 3)])
    arr["v"] = v; arr["n"] = n; arr["k"] = k
    cc = np.asarray(c, np.float32)
    if cc.shape[1] == 3:
        cc = np.concatenate([cc, np.ones((m, 1), np.float32)], axis=1)
    arr["c"] = np.clip(cc * 255, 0, 255)
    memoryview(vd.modify_array(0)).cast("B")[:] = arr.tobytes()
    tri = GeomTriangles(Geom.UH_static); tri.set_index_type(Geom.NT_uint32)
    idx = np.arange(m, dtype=np.uint32)
    ia = tri.modify_vertices(); ia.unclean_set_num_rows(m)
    memoryview(ia).cast("B")[:] = idx.tobytes()
    g = Geom(vd); g.add_primitive(tri)
    gn = GeomNode(name); gn.add_geom(g)
    return NodePath(gn)
