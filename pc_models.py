"""Procedural cel-shaded models: the red-hoodie boy and the 13 PIKNOTT. Balls come from Blender (assets/models/*.bam)."""
import math, os
import numpy as np
from pc_toon import Mesh, outlined, material_to_flat_colour, rot_x, rot_y, rot_z, mm
from panda3d.core import Filename, NodePath

SKIN = (1.0, 0.80, 0.64); HOOD = (0.86, 0.13, 0.13); HOOD_D = (0.70, 0.09, 0.10); JEANS = (0.18, 0.30, 0.60)
HAIR = (0.42, 0.25, 0.12); SHOE = (0.45, 0.27, 0.14); BLACK = (0.05, 0.05, 0.08); WHITE = (1, 1, 1)


class Boy:
    def __init__(self, parent):
        self.root = parent.attach_new_node("boy")
        self.model = self.root.attach_new_node("model")
        def part(name, build, pos=(0, 0, 0), w=0.032):
            m = Mesh(); build(m)
            holder = self.model.attach_new_node(name + "_pivot"); holder.set_pos(*pos)
            o = outlined(m.node(name), holder, w, name=name); o.set_shader_input("spec_k", 1.0)
            return holder
        def torso(m):
            m.ellipsoid((0, 0, 1.12), (0.27, 0.19, 0.33), HOOD)
            m.ellipsoid((0, 0, 0.86), (0.25, 0.18, 0.10), HOOD_D)            # hoodie hem
            m.ellipsoid((0, -0.15, 1.40), (0.20, 0.10, 0.12), HOOD_D)          # hood behind the neck
            m.ellipsoid((0, 0.165, 1.00), (0.15, 0.04, 0.07), HOOD_D)           # front pocket
            m.box((-0.05, 0.19, 1.25), (0.012, 0.012, 0.08), WHITE); m.box((0.05, 0.19, 1.25), (0.012, 0.012, 0.08), WHITE)
        def head(m):
            m.sphere((0, 0, 1.68), 0.25, SKIN, seg=22, rings=16)
            m.ellipsoid((0, -0.04, 1.80), (0.27, 0.27, 0.19), HAIR, seg=22, rings=14)
            m.ellipsoid((0, 0.12, 1.86), (0.22, 0.16, 0.08), HAIR)              # fringe
            for a in range(7):
                ang = a / 7 * 2 * math.pi
                m.cone((math.cos(ang) * 0.12, math.sin(ang) * 0.12 - 0.05, 1.86), 0.20, 0.09, HAIR, seg=5,
                       rot=mm(rot_z(ang), rot_y(0.6)))
            for sx in (-0.085, 0.085):
                m.ellipsoid((sx, 0.215, 1.67), (0.035, 0.02, 0.055), BLACK, seg=8, rings=5)
                m.sphere((sx + 0.012, 0.232, 1.69), 0.012, WHITE, seg=6, rings=4)
                m.sphere((sx * 3, 0.0, 1.66), 0.05, SKIN, seg=6, rings=4)
            m.ellipsoid((0, 0.24, 1.57), (0.05, 0.01, 0.012), (0.75, 0.35, 0.30), seg=6, rings=3)
        def arm(m):
            m.ellipsoid((0, 0, -0.24), (0.09, 0.09, 0.27), HOOD)
            m.sphere((0, 0, -0.55), 0.075, SKIN, seg=8, rings=6)
        def leg(m):
            m.ellipsoid((0, 0, -0.36), (0.11, 0.11, 0.40), JEANS)
            m.ellipsoid((0, 0.06, -0.78), (0.11, 0.19, 0.08), SHOE)
            m.ellipsoid((0, 0.0, -0.70), (0.115, 0.115, 0.05), (0.14, 0.24, 0.50))
        self.torso = part("torso", torso)
        self.head = part("head", head)
        self.arm_l = part("arm_l", arm, (-0.33, 0, 1.36)); self.arm_r = part("arm_r", arm, (0.33, 0, 1.36))
        self.leg_l = part("leg_l", leg, (-0.12, 0, 0.84)); self.leg_r = part("leg_r", leg, (0.12, 0, 0.84))
        self.phase = 0.0

    def animate(self, dt, speed, crouch=False, airborne=False, throwing=0.0):
        self.phase += dt * (4 + speed * 1.3)
        sw = min(1.0, speed / 4.0) * 0.8
        s = math.sin(self.phase) * sw
        if airborne:
            self.leg_l.set_p(30); self.leg_r.set_p(-20); self.arm_l.set_p(-40); self.arm_r.set_p(-40)
        else:
            self.leg_l.set_p(math.degrees(s)); self.leg_r.set_p(-math.degrees(s))
            self.arm_l.set_p(-math.degrees(s) * 0.9); self.arm_r.set_p(math.degrees(s) * 0.9)
        self.arm_l.set_r(-8); self.arm_r.set_r(8)
        if throwing > 0:
            self.arm_r.set_p(-160 + 220 * (1 - throwing))
        self.model.set_z(-0.35 if crouch else abs(math.sin(self.phase)) * 0.05 * sw)
        self.model.set_sz(0.82 if crouch else 1.0)
        self.torso.set_p(15 if crouch else 0); self.head.set_p(10 if crouch else 0)


def _eyes(m, y, z, sx, r=0.06, up=0.0):
    for s in (-sx, sx):
        m.ellipsoid((s, y, z), (r * 0.75, r * 0.5, r), BLACK, seg=8, rings=5)
        m.sphere((s + r * 0.25, y + r * 0.4, z + r * 0.35), r * 0.3, WHITE, seg=6, rings=4)


def _legs4(m, col, w, l, h, r=0.08):
    for sx in (-w, w):
        for sy in (-l, l):
            m.ellipsoid((sx, sy, h / 2), (r, r, h / 2 + 0.03), col, seg=7, rings=4)


def build_creature(sp):
    """Return a Mesh for the species recipe; model space: feet at z=0, facing +Y, ~1 unit tall at size 1."""
    m = Mesh(); c = sp["col"]; c2 = sp["col2"]; k = sp["model"]
    dark = tuple(x * 0.7 for x in c)
    if k == "rabbit":
        m.ellipsoid((0, -0.05, 0.38), (0.30, 0.34, 0.34), c)
        m.ellipsoid((0, 0.14, 0.30), (0.18, 0.12, 0.20), c2)                       # belly
        m.sphere((0, 0.20, 0.78), 0.25, c, seg=14, rings=10)
        for s in (-1, 1):
            m.ellipsoid((s * 0.11, 0.12, 1.20), (0.075, 0.05, 0.30), c, rot=rot_y(s * 0.25))
            m.ellipsoid((s * 0.11, 0.15, 1.20), (0.04, 0.02, 0.22), c2, rot=rot_y(s * 0.25))
            m.ellipsoid((s * 0.16, 0.12, 0.05), (0.09, 0.16, 0.06), c)               # feet
        m.ellipsoid((s * 0.11, 0.12, 1.47), (0.06, 0.04, 0.05), BLACK)               # one ear tip ink-dipped
        m.ellipsoid((-0.11, 0.12, 1.47), (0.06, 0.04, 0.05), BLACK)
        m.sphere((0, -0.40, 0.30), 0.12, c2)
        _eyes(m, 0.40, 0.82, 0.10, 0.055)
        m.sphere((0, 0.45, 0.74), 0.03, (0.9, 0.5, 0.5))
    elif k == "blob":
        m.ellipsoid((0, 0, 0.36), (0.38, 0.36, 0.34), c)
        m.ellipsoid((0, 0.12, 0.28), (0.24, 0.24, 0.2), c2)
        m.cone((0, 0, 0.66), 0.25, 0.04, (0.35, 0.25, 0.15), seg=5)
        m.ellipsoid((0.14, 0, 0.92), (0.20, 0.08, 0.035), (0.25, 0.65, 0.22), rot=rot_y(-0.4))
        m.ellipsoid((-0.12, 0, 0.88), (0.16, 0.07, 0.03), (0.30, 0.72, 0.25), rot=rot_y(0.5))
        _eyes(m, 0.32, 0.46, 0.13, 0.06)
        for s in (-1, 1): m.ellipsoid((s * 0.18, 0.08, 0.04), (0.1, 0.12, 0.05), dark)
    elif k == "frog":
        m.ellipsoid((0, 0, 0.30), (0.42, 0.36, 0.28), c)
        m.ellipsoid((0, 0.14, 0.24), (0.30, 0.22, 0.18), c2)
        for s in (-1, 1):
            m.sphere((s * 0.2, 0.15, 0.58), 0.13, WHITE)
            m.sphere((s * 0.2, 0.25, 0.60), 0.06, BLACK)
            m.ellipsoid((s * 0.32, 0.1, 0.06), (0.14, 0.18, 0.05), dark)
        m.ellipsoid((0, 0.33, 0.33), (0.16, 0.02, 0.02), BLACK)
    elif k == "fox":
        m.ellipsoid((0, 0, 0.45), (0.22, 0.38, 0.22), c)
        _legs4(m, dark, 0.13, 0.22, 0.36)
        m.sphere((0, 0.40, 0.72), 0.22, c)
        m.ellipsoid((0, 0.60, 0.66), (0.09, 0.12, 0.08), c2)
        m.sphere((0, 0.72, 0.68), 0.035, BLACK)
        for s in (-1, 1):
            m.cone((s * 0.12, 0.38, 0.86), 0.26, 0.09, c, seg=5, rot=rot_y(s * 0.3))
        m.ellipsoid((0, -0.45, 0.62), (0.13, 0.25, 0.13), c, rot=rot_x(0.7))
        m.cone((0, -0.62, 0.78), 0.35, 0.13, (1.0, 0.75, 0.15), seg=6, rot=rot_x(0.5))
        m.cone((0, -0.60, 0.80), 0.22, 0.08, (1.0, 0.95, 0.5), seg=6, rot=rot_x(0.5))
        _eyes(m, 0.58, 0.78, 0.09, 0.045)
    elif k == "beetle":
        m.rock((0, 0, 0.30), (0.38, 0.45, 0.30), c, np.random.default_rng(3))
        m.ellipsoid((0, 0.02, 0.42), (0.30, 0.38, 0.22), c2)
        m.box((0, 0.02, 0.52), (0.015, 0.36, 0.16), dark)
        m.sphere((0, 0.42, 0.28), 0.17, dark)
        m.cone((0, 0.52, 0.36), 0.28, 0.06, (0.2, 0.18, 0.18), seg=5, rot=rot_x(-1.0))
        for s in (-1, 1):
            for q in (-0.2, 0.0, 0.2):
                m.ellipsoid((s * 0.36, q, 0.08), (0.12, 0.03, 0.03), BLACK, rot=rot_y(s * 0.5))
        _eyes(m, 0.55, 0.32, 0.08, 0.035)
    elif k == "moth":
        m.ellipsoid((0, 0, 0.75), (0.13, 0.13, 0.30), c)
        m.sphere((0, 0.06, 1.08), 0.15, c2)
        for s in (-1, 1):
            m.ellipsoid((s * 0.40, -0.05, 0.92), (0.38, 0.03, 0.26), c, rot=rot_y(s * -0.3))
            m.ellipsoid((s * 0.32, -0.05, 0.55), (0.25, 0.03, 0.18), dark, rot=rot_y(s * 0.4))
            m.sphere((s * 0.46, -0.01, 0.95), 0.08, c2)
            m.sphere((s * 0.46, 0.02, 0.95), 0.04, BLACK)
            m.cone((s * 0.05, 0.08, 1.20), 0.30, 0.015, BLACK, seg=4, rot=rot_y(s * 0.5))
        _eyes(m, 0.18, 1.10, 0.07, 0.045)
    elif k == "bird":
        m.sphere((0, 0, 0.55), 0.30, c)
        m.ellipsoid((0, 0.14, 0.48), (0.2, 0.18, 0.2), c2)
        m.cone((0, 0.30, 0.60), 0.16, 0.06, (1.0, 0.75, 0.15), seg=5, rot=rot_x(-1.57))
        for s in (-1, 1):
            m.ellipsoid((s * 0.30, -0.05, 0.58), (0.06, 0.24, 0.16), tuple(x * 0.8 for x in c), rot=rot_y(s * 0.3))
            m.ellipsoid((s * 0.09, 0.0, 0.18), (0.03, 0.06, 0.12), (1.0, 0.7, 0.2))
        m.ellipsoid((0, -0.34, 0.62), (0.12, 0.18, 0.03), c, rot=rot_x(0.4))
        m.cone((0, 0.0, 0.82), 0.18, 0.06, c, seg=4, rot=rot_x(-0.4))
        _eyes(m, 0.25, 0.66, 0.11, 0.045)
    elif k == "fish":
        m.ellipsoid((0, 0, 0.55), (0.28, 0.55, 0.32), c)
        m.ellipsoid((0, 0.10, 0.42), (0.20, 0.40, 0.18), c2)
        m.cone((0, -0.5, 0.55), 0.45, 0.25, tuple(x * 0.8 for x in c), seg=4, rot=rot_x(1.57))
        m.cone((0, 0, 0.82), 0.40, 0.18, c2, seg=4, rot=rot_x(-0.3))
        for s in (-1, 1):
            m.ellipsoid((s * 0.30, 0.1, 0.45), (0.2, 0.12, 0.03), c2, rot=rot_y(s * 0.6))
        _eyes(m, 0.44, 0.65, 0.16, 0.06)
    elif k == "squirrel":
        m.ellipsoid((0, 0, 0.36), (0.20, 0.22, 0.30), c)
        m.sphere((0, 0.10, 0.75), 0.20, c)
        for s in (-1, 1):
            m.cone((s * 0.1, 0.08, 0.88), 0.18, 0.06, c, seg=4)
            m.ellipsoid((s * 0.12, 0.12, 0.05), (0.07, 0.12, 0.05), c)
        for q, (y, z, r) in enumerate(((-0.30, 0.40, 0.18), (-0.40, 0.70, 0.20), (-0.30, 0.98, 0.16))):
            m.sphere((0, y, z), r, c2)
        m.cone((0, -0.22, 1.08), 0.25, 0.08, c2, seg=4, rot=rot_x(0.6))
        _eyes(m, 0.27, 0.78, 0.08, 0.045)
    elif k == "lion":
        m.ellipsoid((0, -0.05, 0.62), (0.32, 0.55, 0.32), c)
        _legs4(m, tuple(x * 0.8 for x in c), 0.2, 0.35, 0.45, 0.11)
        m.sphere((0, 0.55, 0.92), 0.26, c)
        for a in range(10):
            ang = a / 10 * 2 * math.pi
            m.sphere((math.cos(ang) * 0.30, 0.45, 0.92 + math.sin(ang) * 0.30), 0.14, c2)
        m.rock((0.18, 0.42, 1.22), (0.1, 0.1, 0.08), (0.55, 0.55, 0.6), np.random.default_rng(2))
        m.ellipsoid((0, 0.78, 0.86), (0.12, 0.08, 0.08), (0.80, 0.75, 0.6))
        m.ellipsoid((0, -0.62, 0.75), (0.06, 0.25, 0.06), c, rot=rot_x(0.6))
        m.sphere((0, -0.80, 0.90), 0.09, c2)
        _eyes(m, 0.76, 0.98, 0.10, 0.045)
    elif k == "deer":
        m.ellipsoid((0, 0, 0.75), (0.20, 0.40, 0.22), c)
        _legs4(m, tuple(x * 0.85 for x in c), 0.11, 0.25, 0.62, 0.05)
        m.ellipsoid((0, 0.30, 1.00), (0.08, 0.08, 0.22), c, rot=rot_x(-0.5))
        m.ellipsoid((0, 0.42, 1.20), (0.12, 0.18, 0.12), c)
        m.sphere((0, 0.58, 1.17), 0.035, BLACK)
        for s in (-1, 1):
            m.cone((s * 0.07, 0.36, 1.30), 0.40, 0.05, c2, seg=4, rot=rot_y(s * 0.4))
            m.cone((s * 0.17, 0.36, 1.50), 0.20, 0.035, c2, seg=4, rot=rot_y(s * 1.0))
            m.ellipsoid((s * 0.13, 0.34, 1.26), (0.08, 0.02, 0.04), c)
        for q in range(4):
            m.sphere((0.12 * (q % 2 * 2 - 1), -0.1 + q * 0.08, 0.92), 0.03, WHITE)
        _eyes(m, 0.52, 1.24, 0.08, 0.035)
    elif k == "golem":
        rg = np.random.default_rng(8)
        m.rock((0, 0, 0.75), (0.50, 0.42, 0.55), c, rg)
        m.rock((0, 0.15, 1.30), (0.28, 0.25, 0.22), c, rg)
        for s in (-1, 1):
            m.rock((s * 0.55, 0.1, 0.72), (0.18, 0.18, 0.32), c, rg)
            m.rock((s * 0.25, 0.0, 0.18), (0.18, 0.2, 0.18), c, rg)
            m.cone((s * 0.2, 0.3, 0.9), 0.4, 0.06, c2, seg=4, rot=rot_y(s * 0.8))
        m.cone((0, 0.38, 0.6), 0.45, 0.07, c2, seg=4, rot=rot_x(0.3))
        for s in (-1, 1):
            m.sphere((s * 0.10, 0.36, 1.33), 0.05, c2)
    elif k == "lynx":
        m.ellipsoid((0, 0, 0.62), (0.26, 0.50, 0.26), c)
        _legs4(m, c, 0.15, 0.32, 0.45, 0.08)
        m.sphere((0, 0.50, 0.90), 0.24, c)
        for s in (-1, 1):
            m.cone((s * 0.13, 0.48, 1.08), 0.25, 0.08, c, seg=4)
            m.cone((s * 0.13, 0.48, 1.30), 0.12, 0.02, c2, seg=4)
        for q in range(9):
            a = q * 2.4
            m.sphere((math.cos(a) * 0.22, -0.3 + q * 0.07, 0.62 + math.sin(a) * 0.22), 0.035, c2)
        m.ellipsoid((0, -0.62, 0.85), (0.05, 0.28, 0.05), c, rot=rot_x(0.8))
        m.sphere((0, -0.82, 1.06), 0.07, c2)
        _eyes(m, 0.70, 0.95, 0.10, 0.045)
        for s in (-1, 1):
            m.sphere((s * 0.10, 0.72, 0.96), 0.035, c2)
    return m


_cache = {}


def creature_node(sp, parent):
    """Toon creature with outline; root carries a 'bob' child for idle animation."""
    if sp["id"] not in _cache:
        _cache[sp["id"]] = build_creature(sp).node(sp["name"])
    root = parent.attach_new_node(sp["name"])
    bob = root.attach_new_node("bob")
    geom = _cache[sp["id"]].copy_to(NodePath("tmp"))
    o = outlined(geom, bob, 0.034, name="mesh"); o.set_shader_input("spec_k", 1.0)
    root.set_scale(sp["size"])
    return root, bob


_balls = {}


def ball_node(app, base, kind, parent):
    if kind not in _balls:
        p = os.path.join(base, "assets", "models", kind + "_ball.bam")
        mdl = app.loader.load_model(Filename.from_os_specific(p))
        material_to_flat_colour(mdl)
        _balls[kind] = mdl
    holder = parent.attach_new_node("ball-" + kind)
    g = _balls[kind].copy_to(NodePath("tmp"))
    o = outlined(g, holder, 0.022, use_normals=True, name="ball"); o.set_shader_input("spec_k", 1.0)
    holder.set_scale(0.17)
    return holder


def blob_shadow(parent, r=0.5):
    m = Mesh(); seg = 28
    V = [(0, 0, 0)] + [(math.cos(a / seg * 6.283) * r, math.sin(a / seg * 6.283) * r, 0) for a in range(seg + 1)]
    m.add(V, [(0, 0, 1)] * len(V), (0.12, 0.14, 0.32, 0.55), [(0, 0, 1)] * len(V), [(0, i + 1, i + 2) for i in range(seg)])
    n = m.node("shadow"); n.reparent_to(parent)
    from panda3d.core import TransparencyAttrib
    n.set_transparency(TransparencyAttrib.M_alpha); n.set_depth_write(False); n.set_bin("transparent", 1)
    n.set_shader_input("flash", 0.0); n.set_shader_input("unlit", 1.0); n.set_z(0.04)
    return n
