"""The Celestika region: heightfield terrain, zones, scenery, collision and the minimap image."""
import math, random
import numpy as np
from pc_toon import Mesh, node_from_arrays, outlined, rot_z, rot_x, mm, LIGHT
LIGHT_XY = (LIGHT.x, LIGHT.y)

SIZE = 220.0          # region spans -SIZE..SIZE on x and y
N = 176               # grid cells per side
CELL = 2 * SIZE / N
WATER = 0.0
CAMP = (0.0, -150.0)
VOLCANO = (0.0, 135.0)
LAKE = (-25.0, 5.0)
LAKE_R = 40.0
SHRINE = (28.0, 62.0)
BOUND_R = 196.0

ZONE_COL = {
    "Starter Meadow": (0.50, 0.78, 0.36), "Ink Forest": (0.20, 0.36, 0.34), "Rocky Ridge": (0.50, 0.52, 0.58),
    "Mirror Lake": (0.30, 0.58, 0.90), "Ash Slopes": (0.30, 0.32, 0.40), "Snowline": (0.93, 0.95, 1.0), "Summit": (0.80, 0.84, 0.95),
}
ZONE_LABEL_POS = {"Starter Meadow": (30, -78), "Ink Forest": (-130, -20), "Rocky Ridge": (130, -20), "Mirror Lake": (-25, 5),
                  "Ash Slopes": (-50, 95), "Snowline": (30, 125), "Summit": (0, 150), "Camp": CAMP}
PATHS = [[CAMP, (0, -90), (-10, -45), LAKE], [(0, -90), (60, -60), (120, -30)], [(-10, -45), (-70, -30), (-130, -10)],
         [(-10, -45), (20, 10), SHRINE, (5, 95)]]


def _fbm(x, y, seed=3, octaves=4, scale=0.02):
    rng = np.random.default_rng(seed)
    h = np.zeros_like(x, dtype=np.float64); amp = 1.0; f = scale
    for _ in range(octaves):
        for _k in range(3):
            a = rng.uniform(0, 2 * math.pi); p1, p2 = rng.uniform(0, 2 * math.pi, 2)
            dx, dy = math.cos(a), math.sin(a)
            h += amp * np.sin((x * dx + y * dy) * f + p1) * np.cos((x * dy - y * dx) * f * 0.7 + p2) / 3
        amp *= 0.5; f *= 2.03
    return h


def raw_height(x, y):
    h = 2.6 + 2.0 * _fbm(x, y)
    dv = np.hypot(x - VOLCANO[0], y - VOLCANO[1])
    v = np.clip(1 - dv / 92.0, 0, 1)
    h += 74 * v ** 1.7
    h -= np.clip(10 - dv, 0, None) * 1.4                     # crater
    rx = np.clip((x - 55) / 45, 0, 1)
    h += rx * rx * (5 + 9 * np.abs(_fbm(x, y, 9, 3, 0.035)) * 2.2)
    fx = np.clip((-x - 60) / 40, 0, 1)
    h += fx * 2.5 * (_fbm(x, y, 5, 2, 0.05) + 0.6)
    dl = np.hypot(x - LAKE[0], y - LAKE[1])
    h = np.where(dl < LAKE_R, h - 7.5 * np.clip(1 - dl / LAKE_R, 0, 1) ** 0.6 - 1.2, h)
    h = np.where(dl < LAKE_R + 6, np.minimum(h, 1.0 + (dl - LAKE_R) * 0.5 + 1.2), h)
    h = np.where(dl < LAKE_R + 6, np.maximum(h, -5.5), h)
    r = np.hypot(x, y)
    h += np.minimum(np.clip(r - 188, 0, None) ** 1.15 * 1.0, 34.0) * (0.75 + 0.25 * np.sin(np.arctan2(y, x) * 9))
    dc = np.hypot(x - CAMP[0], y - CAMP[1])                 # flatten camp
    t = np.clip((dc - 10) / 14, 0, 1)
    h = h * t + 2.4 * (1 - t)
    return h


def fb(y):
    return -60 + 12 * np.sin(y * 0.031)


def rb(y):
    return 55 + 10 * np.sin(y * 0.027 + 1.0)


def zone_of(x, y, h):
    dv = math.hypot(x - VOLCANO[0], y - VOLCANO[1])
    if math.hypot(x - LAKE[0], y - LAKE[1]) < LAKE_R + 4:
        return "Mirror Lake"
    if dv < 92 and h > 8:
        if dv < 26 and h > 52:
            return "Summit"
        return "Snowline" if h > 36 else "Ash Slopes"
    if x < fb(y):
        return "Ink Forest"
    if x > rb(y):
        return "Rocky Ridge"
    return "Starter Meadow"


def _seg_dist(px, py, a, b):
    ax, ay = a; bx, by = b
    vx, vy = bx - ax, by - ay
    t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy), 0, 1)
    return np.hypot(px - (ax + t * vx), py - (ay + t * vy))


def path_dist(px, py):
    d = np.full(np.shape(px), 1e9)
    for pl in PATHS:
        for a, b in zip(pl, pl[1:]):
            d = np.minimum(d, _seg_dist(px, py, a, b))
    return d


def colour_field(x, y, h, slope):
    """Flat cel palette per sample."""
    c = np.zeros(x.shape + (3,))
    dv = np.hypot(x - VOLCANO[0], y - VOLCANO[1])
    meadow = np.array(ZONE_COL["Starter Meadow"]); forest = np.array(ZONE_COL["Ink Forest"])
    ridge = np.array(ZONE_COL["Rocky Ridge"]); ash = np.array(ZONE_COL["Ash Slopes"]); snow = np.array(ZONE_COL["Snowline"])
    c[:] = meadow
    F, Rr = fb(y), rb(y)
    c[x < F] = forest
    c[(x < F + 8) & (x >= F)] = (meadow + forest) / 2
    c[x > Rr] = ridge
    c[(x > Rr - 8) & (x <= Rr)] = (meadow + ridge) / 2
    vol = (dv < 92) & (h > 8)
    c[vol] = ash
    c[vol & (h > 22) & (slope > 0.9)] = ash * 0.8
    sn = vol & (h > 36 + 4 * np.sin(np.arctan2(y - VOLCANO[1], x - VOLCANO[0]) * 7))
    c[sn] = snow
    c[(h > 3) & (slope > 1.1) & ~vol] = ridge * 0.85
    pd = path_dist(x, y)
    c[(pd < 2.6) & ~vol] = (0.74, 0.62, 0.42)
    nl = np.hypot(x - LAKE[0], y - LAKE[1]) < LAKE_R + 9
    c[nl & (h < 1.4) & (h > -0.5)] = (0.86, 0.80, 0.58)          # sand at the shore
    c[nl & (h <= -0.5)] = (0.42, 0.50, 0.55)
    dc = np.hypot(x - CAMP[0], y - CAMP[1])
    c[dc < 9] = (0.70, 0.60, 0.42)
    rr_ = np.hypot(x, y)
    c[rr_ > 192] = (0.52, 0.56, 0.68)
    c[(rr_ > 192) & (h > 20)] = (0.92, 0.94, 1.0)
    return c


class Region:
    def __init__(self, seed=2026):
        self.rng = np.random.default_rng(seed)
        xs = np.linspace(-SIZE, SIZE, N + 1)
        self.gx, self.gy = np.meshgrid(xs, xs)            # [j, i] -> y=xs[j], x=xs[i]
        self.H = raw_height(self.gx, self.gy)
        gy_, gx_ = np.gradient(self.H, CELL)
        self.slope = np.hypot(gx_, gy_)
        nrm = np.dstack([-gx_, -gy_, np.ones_like(self.H)])
        self.VN = nrm / np.linalg.norm(nrm, axis=2, keepdims=True)
        self.trees = []; self.rocks = []; self.grass = []; self.obstacles = []; self.pickups = []

    # ------------------------------------------------------------------ queries
    def height(self, x, y):
        fx = (x + SIZE) / CELL; fy = (y + SIZE) / CELL
        i = int(min(max(fx, 0), N - 1.001)); j = int(min(max(fy, 0), N - 1.001))
        tx, ty = min(max(fx - i, 0), 1), min(max(fy - j, 0), 1)
        H = self.H
        # match the triangle split used by the mesh
        if tx + ty <= 1:
            return float(H[j, i] + (H[j, i + 1] - H[j, i]) * tx + (H[j + 1, i] - H[j, i]) * ty)
        return float(H[j + 1, i + 1] + (H[j + 1, i] - H[j + 1, i + 1]) * (1 - tx) + (H[j, i + 1] - H[j + 1, i + 1]) * (1 - ty))

    def ground(self, x, y):
        return max(self.height(x, y), WATER - 0.6) if self.in_lake(x, y) else self.height(x, y)

    def in_lake(self, x, y):
        return math.hypot(x - LAKE[0], y - LAKE[1]) < LAKE_R + 2 and self.height(x, y) < WATER

    def zone(self, x, y):
        return zone_of(x, y, self.height(x, y))

    def in_grass(self, x, y):
        for gx, gy, r in self.grass:
            if (x - gx) ** 2 + (y - gy) ** 2 < r * r:
                return True
        return False

    def push_out(self, x, y, rad=0.45):
        for ox, oy, r in self.obstacles:
            dx, dy = x - ox, y - oy
            d2 = dx * dx + dy * dy; rr = r + rad
            if d2 < rr * rr and d2 > 1e-6:
                d = math.sqrt(d2); x = ox + dx / d * rr; y = oy + dy / d * rr
        rr = math.hypot(x, y)
        if rr > BOUND_R:
            x *= BOUND_R / rr; y *= BOUND_R / rr
        return x, y

    # ------------------------------------------------------------------ geometry
    def build(self, parent, progress=None):
        root = parent.attach_new_node("region")
        H, gx, gy = self.H, self.gx, self.gy
        # two triangles per cell, unshared vertices, flat normals, smooth ink normals
        j, i = np.mgrid[0:N, 0:N]
        P = np.dstack([gx, gy, H])
        a = P[j, i]; b = P[j, i + 1]; c = P[j + 1, i]; d = P[j + 1, i + 1]
        na, nb, nc, nd = self.VN[j, i], self.VN[j, i + 1], self.VN[j + 1, i], self.VN[j + 1, i + 1]
        t1 = np.stack([a, b, c], 2).reshape(-1, 3, 3); t2 = np.stack([d, c, b], 2).reshape(-1, 3, 3)
        k1 = np.stack([na, nb, nc], 2).reshape(-1, 3, 3); k2 = np.stack([nd, nc, nb], 2).reshape(-1, 3, 3)
        tris = np.concatenate([t1, t2]); inks = np.concatenate([k1, k2])
        fn = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]); fn /= np.linalg.norm(fn, axis=1, keepdims=True)
        cen = tris.mean(1)
        sl = np.hypot(fn[:, 0], fn[:, 1]) / np.maximum(fn[:, 2], 0.05)
        col = colour_field(cen[:, 0], cen[:, 1], cen[:, 2], sl)
        # subtle 2-tone checker so flat areas still read as cel facets
        v = tris.reshape(-1, 3); k = inks.reshape(-1, 3); cc = np.repeat(col, 3, 0)
        # smooth (rounded) lighting normals so hills get a crisp anime terminator instead of flat facets
        terr = node_from_arrays(v.astype(np.float32), k.astype(np.float32), cc, k.astype(np.float32), "terrain")
        t = outlined(terr, root, 0.10, name="terrain"); t.set_shader_input("rim_k", 0.0)
        if progress: progress(0.35)
        # water
        m = Mesh(); seg = 48
        V = [(LAKE[0], LAKE[1], WATER)]; T = []
        for s in range(seg + 1):
            ang = 2 * math.pi * s / seg; V.append((LAKE[0] + math.cos(ang) * (LAKE_R + 8), LAKE[1] + math.sin(ang) * (LAKE_R + 8), WATER))
        for s in range(seg):
            T.append((0, s + 1, s + 2))
        m.add(V, [(0, 0, 1)] * len(V), (0.26, 0.55, 0.92, 0.9), [(0, 0, 1)] * len(V), T)
        # stylised ripple rings (cel streaks)
        for rr in (12, 24, 34):
            Vr, Tr = [], []
            for s in range(seg + 1):
                ang = 2 * math.pi * s / seg
                for q in (rr, rr + 0.5):
                    Vr.append((LAKE[0] + math.cos(ang) * q, LAKE[1] + math.sin(ang) * q, WATER + 0.03))
            for s in range(seg):
                if s % 3 == 0: continue
                a0 = s * 2; Tr += [(a0, a0 + 2, a0 + 1), (a0 + 1, a0 + 2, a0 + 3)]
            m.add(Vr, [(0, 0, 1)] * len(Vr), (0.75, 0.88, 1.0, 0.9), [(0, 0, 1)] * len(Vr), Tr)
        for r0, r1, colw in ((LAKE_R - 6, LAKE_R + 8, (0.50, 0.80, 1.0, 0.85)), (LAKE_R + 0.5, LAKE_R + 1.6, (1, 1, 1, 0.95))):
            Vr, Tr = [], []
            for q in range(seg + 1):
                ang = 2 * math.pi * q / seg
                for rr_ in (r0, r1):
                    Vr.append((LAKE[0] + math.cos(ang) * rr_, LAKE[1] + math.sin(ang) * rr_, WATER + 0.015))
            for q in range(seg):
                a0 = q * 2; Tr += [(a0, a0 + 2, a0 + 1), (a0 + 1, a0 + 2, a0 + 3)]
            m.add(Vr, [(0, 0, 1)] * len(Vr), colw, [(0, 0, 1)] * len(Vr), Tr)
        w = m.node("water"); w.reparent_to(root); w.set_shader_input("rim_k", 0.0); w.set_shader_input("unlit", 1.0)
        from panda3d.core import TransparencyAttrib
        w.set_transparency(TransparencyAttrib.M_alpha); w.set_bin("transparent", 5); w.set_depth_write(False)
        self.scatter()
        if progress: progress(0.55)
        self.build_scenery(root)
        if progress: progress(0.9)
        return root

    def scatter(self):
        rng = self.rng; R = random.Random(11)
        def ok(x, y, minh=0.8):
            h = self.height(x, y)
            if h < minh or math.hypot(x, y) > 185: return False
            if math.hypot(x - CAMP[0], y - CAMP[1]) < 16: return False
            if float(path_dist(np.array(x), np.array(y))) < 4: return False
            return True
        # Ink Forest: dense dark pines
        for _ in range(900):
            if len(self.trees) > 240: break
            x, y = R.uniform(-185, -55), R.uniform(-170, 120)
            if ok(x, y) and self.zone(x, y) == "Ink Forest":
                self.trees.append((x, y, R.uniform(0.9, 1.5), "pine"))
        for _ in range(500):
            x, y = R.uniform(-150, 150), R.uniform(-180, 60)
            if len([t for t in self.trees if t[3] == "round"]) > 55: break
            if ok(x, y) and self.zone(x, y) == "Starter Meadow" and R.random() < 0.5:
                self.trees.append((x, y, R.uniform(0.8, 1.2), "round"))
        for _ in range(300):
            x, y = R.uniform(-90, 90), R.uniform(50, 200)
            if ok(x, y) and self.zone(x, y) == "Ash Slopes" and R.random() < 0.3:
                self.trees.append((x, y, R.uniform(0.7, 1.1), "pine"))
        for _ in range(700):
            if len(self.rocks) > 150: break
            x, y = R.uniform(-185, 185), R.uniform(-185, 185)
            z = self.zone(x, y)
            p = {"Rocky Ridge": 0.6, "Ash Slopes": 0.25, "Snowline": 0.1, "Starter Meadow": 0.04, "Ink Forest": 0.05}.get(z, 0)
            if ok(x, y) and R.random() < p:
                self.rocks.append((x, y, R.uniform(0.7, 2.4)))
        for (x, y, s, kind) in self.trees:
            self.obstacles.append((x, y, 0.55 * s))
        for (x, y, s) in self.rocks:
            if s > 1.1: self.obstacles.append((x, y, s * 0.8))
        # tall grass patches (crouch inside to sneak)
        spots = []
        for _ in range(400):
            x, y = R.uniform(-170, 120), R.uniform(-175, 70)
            z = self.zone(x, y)
            if ok(x, y) and z in ("Starter Meadow", "Ink Forest") and len(spots) < 34:
                if all((x - a) ** 2 + (y - b) ** 2 > 400 for a, b, _ in spots):
                    spots.append((x, y, R.uniform(4.5, 7.5)))
        spots[:0] = [(14, -128, 6.0), (-16, -120, 5.0)]     # two patches right by camp
        self.grass = spots
        # pickups (balls / potions), respawn later
        for _ in range(200):
            x, y = R.uniform(-170, 170), R.uniform(-170, 160)
            if ok(x, y) and len(self.pickups) < 18 and self.height(x, y) < 45:
                self.pickups.append((x, y))

    def build_scenery(self, root):
        R = random.Random(5)
        m = Mesh()
        for (x, y, s, kind) in self.trees:
            z = self.height(x, y) - 0.2
            if kind == "pine":
                m.cone((x, y, z), 1.6 * s, 0.32 * s, (0.30, 0.22, 0.20), seg=10, top_r=0.2 * s)
                dark = R.choice([(0.14, 0.24, 0.27), (0.18, 0.30, 0.30), (0.12, 0.20, 0.26)])
                for q, (hh, rr) in enumerate(((1.2, 2.2), (2.6, 1.7), (3.8, 1.15))):
                    m.cone((x, y, z + hh * s), 2.0 * s, rr * s, dark, seg=14)
            else:
                m.cone((x, y, z), 1.8 * s, 0.3 * s, (0.45, 0.30, 0.20), seg=10, top_r=0.22 * s)
                g = R.choice([(0.36, 0.66, 0.28), (0.30, 0.58, 0.26), (0.42, 0.70, 0.30)])
                m.ellipsoid((x, y, z + 2.8 * s), (1.5 * s, 1.5 * s, 1.3 * s), g, seg=16, rings=10)
                for q in range(3):
                    a = R.uniform(0, 6.28)
                    m.ellipsoid((x + math.cos(a) * 0.9 * s, y + math.sin(a) * 0.9 * s, z + (2.3 + q * 0.4) * s), (0.85 * s, 0.85 * s, 0.75 * s), g, seg=14, rings=9)
        trees = m.node("trees")
        outlined(trees, root, 0.07, name="trees")
        # cel drop shadows (hard-edged, cool tinted) under trees, rocks and camp props
        sh = Mesh(); seg = 20
        def disc(x, y, r):
            z = self.height(x, y) + 0.06
            off = (-LIGHT_XY[0] * r * 0.5, -LIGHT_XY[1] * r * 0.5)
            V = [(x + off[0], y + off[1], z)] + [(x + off[0] + math.cos(a / seg * 6.283) * r * 1.25, y + off[1] + math.sin(a / seg * 6.283) * r,
                                                 self.height(x + off[0] + math.cos(a / seg * 6.283) * r * 1.25, y + off[1] + math.sin(a / seg * 6.283) * r) + 0.06) for a in range(seg + 1)]
            sh.add(V, [(0, 0, 1)] * len(V), (0.10, 0.14, 0.30, 0.38), [(0, 0, 1)] * len(V), [(0, i + 1, i + 2) for i in range(seg)])
        for (x, y, s_, kind) in self.trees:
            disc(x, y, (1.6 if kind == "round" else 1.4) * s_)
        for (x, y, s_) in self.rocks:
            disc(x, y, s_ * 0.9)
        shn = sh.node("shadows"); shn.reparent_to(root)
        from panda3d.core import TransparencyAttrib
        shn.set_transparency(TransparencyAttrib.M_alpha); shn.set_depth_write(False); shn.set_bin("transparent", 2)
        shn.set_shader_input("unlit", 1.0)
        m = Mesh(); rr = np.random.default_rng(4)
        for (x, y, s) in self.rocks:
            z = self.height(x, y)
            zn = self.zone(x, y)
            col = (0.80, 0.84, 0.92) if zn == "Snowline" else ((0.32, 0.33, 0.40) if zn == "Ash Slopes" else (0.55, 0.56, 0.62))
            m.rock((x, y, z + 0.2 * s), (s, s * rr.uniform(0.8, 1.2), s * rr.uniform(0.6, 1.0)), col, rr)
        outlined(m.node("rocks"), root, 0.07, name="rocks")
        # tall grass
        m = Mesh()
        for (gx, gy, r) in self.grass:
            n = int(r * r * 1.6)
            for _ in range(n):
                a = R.uniform(0, 2 * math.pi); d = r * math.sqrt(R.random())
                x, y = gx + math.cos(a) * d, gy + math.sin(a) * d
                z = self.height(x, y) - 0.05
                col = R.choice([(0.30, 0.62, 0.22), (0.38, 0.70, 0.25), (0.26, 0.55, 0.22)])
                lean = mm(rot_z(R.uniform(0, 6.28)), rot_x(R.uniform(-0.25, 0.25)))
                m.cone((x, y, z), R.uniform(0.75, 1.15), 0.2, col, seg=5, rot=lean)
        gr = outlined(m.node("grass"), root, 0.025, name="grass"); gr.set_shader_input("rim_k", 0.4)
        # camp: tent, campfire (heal spot), crates, banner
        m = Mesh()
        cx, cy = CAMP; z = 2.4
        m.cone((cx - 5, cy + 3, z), 3.4, 3.0, (0.85, 0.25, 0.22), seg=4, rot=rot_z(math.pi / 4))
        m.box((cx - 5, cy + 0.9, z + 0.8), (0.5, 0.05, 0.8), (0.25, 0.10, 0.10))
        for a in range(5):
            ang = a * 2 * math.pi / 5
            m.box((cx + math.cos(ang) * 0.9, cy + math.sin(ang) * 0.9, z + 0.15), (0.6, 0.15, 0.15), (0.45, 0.28, 0.16), rot=rot_z(ang + math.pi / 2))
        for a in range(8):
            ang = a * 2 * math.pi / 8
            m.rock((cx + math.cos(ang) * 1.6, cy + math.sin(ang) * 1.6, z), (0.35, 0.35, 0.25), (0.45, 0.45, 0.5), np.random.default_rng(a))
        m.box((cx + 4.5, cy + 3.5, z + 0.5), (0.5, 0.5, 0.5), (0.65, 0.45, 0.25))
        m.box((cx + 5.3, cy + 2.6, z + 0.4), (0.4, 0.4, 0.4), (0.60, 0.42, 0.22))
        m.cone((cx + 6, cy - 3, z), 5, 0.12, (0.4, 0.3, 0.2), seg=5, top_r=0.1)
        m.box((cx + 6.7, cy - 3, z + 4.4), (0.7, 0.04, 0.45), (1.0, 0.85, 0.15))
        # Star Shrine near the volcano path
        sx, sy = SHRINE; sz = self.height(sx, sy)
        for q in range(3):
            m.box((sx, sy, sz + 0.4 + q * 0.8), (2.2 - q * 0.6, 2.2 - q * 0.6, 0.4), (0.55, 0.56, 0.66))
        m.cone((sx, sy, sz + 2.4), 3.0, 0.3, (0.95, 0.85, 0.3), seg=5)
        self.obstacles.append((sx, sy, 2.4)); self.obstacles.append((cx - 5, cy + 3, 2.4))
        outlined(m.node("camp"), root, 0.05, name="camp")
        self.build_sky(root)
        # fire flame (separate so it can flicker)
        m = Mesh()
        m.cone((0, 0, 0), 1.3, 0.55, (1.0, 0.55, 0.12), seg=6)
        m.cone((0, 0, 0.05), 0.8, 0.32, (1.0, 0.92, 0.35), seg=6)
        self.fire = outlined(m.node("flame"), root, 0.03, name="fire")
        self.fire.set_pos(cx, cy, z + 0.2)

    def build_sky(self, parent):
        """Cel sky: banded gradient dome, a sun disc and outlined stylised clouds."""
        from panda3d.core import TransparencyAttrib
        self.sky = parent.attach_new_node("sky")
        m = Mesh(); seg, rings, R = 32, 16, 900.0
        bands = [(-0.2, (0.86, 0.90, 0.96)), (0.06, (0.80, 0.87, 0.97)), (0.16, (0.66, 0.80, 0.97)), (0.32, (0.52, 0.70, 0.95)),
                 (0.55, (0.40, 0.60, 0.93))]
        def skycol(zn):
            c = bands[0][1]
            for t, cc in bands:
                if zn >= t: c = cc
            return c
        V, N, C, T = [], [], [], []
        for j in range(rings + 1):
            th = math.pi * j / rings
            for i in range(seg + 1):
                ph = 2 * math.pi * i / seg
                u = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
                V.append((u[0] * R, u[1] * R, u[2] * R)); N.append((-u[0], -u[1], -u[2])); C.append(skycol(u[2]))
        for j in range(rings):
            for i in range(seg):
                a = j * (seg + 1) + i; b = a + seg + 1
                T.append((a, a + 1, b)); T.append((a + 1, b + 1, b))
        m.add(V, N, C, N, T)
        # sun disc + halo, placed along the light direction
        sx, sy, sz = LIGHT.x * 860, LIGHT.y * 860, LIGHT.z * 860
        for rr, cc in ((70, (1.0, 0.98, 0.86)), (42, (1.0, 1.0, 0.97))):
            m.sphere((sx, sy, sz), rr, cc, seg=20, rings=12)
        dome = m.node("dome"); dome.reparent_to(self.sky)
        dome.set_shader_input("unlit", 1.0); dome.set_two_sided(True); dome.set_bin("background", 0); dome.set_depth_write(False)
        dome.set_light_off(); dome.set_fog_off()
        self.sky.set_compass()
        # clouds (lit by the toon shader, outlined, no fog)
        R2 = random.Random(21); cm = Mesh()
        for _ in range(26):
            a = R2.uniform(0, 2 * math.pi); d = R2.uniform(230, 420)
            cx, cy, cz = math.cos(a) * d, math.sin(a) * d, R2.uniform(95, 150)
            for q in range(R2.randint(4, 7)):
                rr = R2.uniform(10, 20)
                cm.ellipsoid((cx + R2.uniform(-22, 22), cy + R2.uniform(-12, 12), cz + R2.uniform(-3, 5)), (rr * 1.4, rr, rr * 0.7),
                             (1.0, 1.0, 1.0), seg=14, rings=8)
        self.clouds = outlined(cm.node("clouds"), parent, 0.9, name="clouds")
        self.clouds.set_shader_input("fog_far", 5000.0); self.clouds.set_shader_input("rim_k", 0.6)

    # ------------------------------------------------------------------ minimap
    def map_image(self, res=512):
        xs = np.linspace(-SIZE, SIZE, res)
        X, Y = np.meshgrid(xs, xs)
        Hh = raw_height(X, Y)
        gy_, gx_ = np.gradient(Hh, xs[1] - xs[0])
        sl = np.hypot(gx_, gy_)
        c = colour_field(X, Y, Hh, sl)
        dl = np.hypot(X - LAKE[0], Y - LAKE[1])
        c[(Hh < WATER) & (dl < LAKE_R + 6)] = (0.32, 0.62, 0.95)
        # contour ink lines every 10 m (cel map look)
        band = np.floor(Hh / 10.0)
        edge = (np.abs(np.diff(band, axis=0, prepend=band[:1])) + np.abs(np.diff(band, axis=1, prepend=band[:, :1]))) > 0
        c[edge & (Hh > 4)] *= 0.55
        # trees as dark dots
        px = lambda v: int((v + SIZE) / (2 * SIZE) * (res - 1))
        for (x, y, s, k) in self.trees:
            i, j = px(x), px(y)
            c[max(0, j - 1):j + 2, max(0, i - 1):i + 2] = (0.08, 0.16, 0.16) if k == "pine" else (0.20, 0.45, 0.18)
        for (x, y, r) in self.grass:
            rr = int(r / (2 * SIZE) * res) + 1; i, j = px(x), px(y)
            yy, xx = np.ogrid[-rr:rr + 1, -rr:rr + 1]
            sub = c[max(0, j - rr):j + rr + 1, max(0, i - rr):i + rr + 1]
            msk = (xx ** 2 + yy ** 2 <= rr * rr)[:sub.shape[0], :sub.shape[1]]
            sub[msk] = (0.22, 0.52, 0.18)
        i, j = px(CAMP[0]), px(CAMP[1]); c[j - 4:j + 5, i - 4:i + 5] = (0.9, 0.25, 0.2)
        i, j = px(SHRINE[0]), px(SHRINE[1]); c[j - 3:j + 4, i - 3:i + 4] = (1.0, 0.85, 0.2)
        c[np.hypot(X, Y) > BOUND_R + 4] *= 0.45
        img = (np.clip(c, 0, 1) * 255).astype(np.uint8)
        return img
