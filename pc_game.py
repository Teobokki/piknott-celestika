"""Overworld: the boy, camera, wild PIKNOTT, PIKCEL throwing/catching, minimap, region map, CELESTIKA DOK, party, saving."""
import math, random, json, os, time
import numpy as np
from panda3d.core import (Vec3, Point3, Texture, SamplerState, TextNode, WindowProperties, TransparencyAttrib, NodePath,
                          BitMask32, CardMaker)
from direct.gui.DirectGui import DirectFrame, DGG
from direct.gui.OnscreenImage import OnscreenImage
import pc_data as D
import pc_world as W
import pc_ui as U
from pc_models import Boy, creature_node, ball_node, blob_shadow
from pc_toon import Mesh, outlined

SPAWNS = {
    "Starter Meadow": [(1, 3, 3, 5), (2, 5, 2, 5), (3, 2, 3, 5), (7, 2, 3, 6), (9, 1, 4, 6)],
    "Ink Forest": [(2, 3, 5, 8), (6, 5, 6, 10), (9, 3, 6, 9), (10, 0.6, 14, 18)],
    "Rocky Ridge": [(5, 5, 6, 10), (4, 3, 7, 10), (7, 3, 6, 9)],
    "Mirror Lake": [(3, 5, 4, 8), (8, 1.5, 10, 14)],
    "Ash Slopes": [(4, 4, 10, 14), (12, 1, 16, 20), (5, 2, 9, 13)],
    "Snowline": [(11, 4, 14, 18), (7, 2, 12, 15)],
    "Summit": [(13, 1, 30, 30)],
}
MAX_WILD = 26


class Wild:
    def __init__(self, game, mon, x, y):
        self.g = game; self.mon = mon; self.sp = mon.sp
        self.root, self.bob = creature_node(self.sp, game.world_np)
        self.shadow = blob_shadow(self.root, 0.45)
        self.x, self.y = x, y; self.h = random.uniform(0, 360)
        self.state = "wander"; self.t = random.uniform(0, 3); self.aware = 0.0
        self.tx, self.ty = x, y; self.home = (x, y); self.phase = random.uniform(0, 6)
        self.swim = self.sp["model"] == "fish"
        self.flyer = self.sp["model"] in ("bird", "moth")
        self.icon = None
        self.place()

    @property
    def radius(self):
        return 0.55 * self.sp["size"]

    def ground(self):
        if self.swim:
            return W.WATER - 0.35
        return self.g.region.height(self.x, self.y)

    def place(self):
        self.z = self.ground()
        self.root.set_pos(self.x, self.y, self.z); self.root.set_h(self.h)

    def set_icon(self, txt, col):
        if self.icon:
            self.icon.remove_node(); self.icon = None
        if txt:
            tn = TextNode("icon"); tn.set_text(txt); tn.set_align(TextNode.A_center); tn.set_text_color(*col)
            if U.FONT: tn.set_font(U.FONT)
            self.icon = self.root.attach_new_node(tn); self.icon.set_scale(0.9 / self.sp["size"])
            self.icon.set_z(1.6); self.icon.set_billboard_point_eye(); self.icon.set_shader_off(); self.icon.set_bin("fixed", 50)
            self.icon.set_depth_test(False); self.icon.set_depth_write(False)

    def update(self, dt, px, py, detect):
        self.phase += dt
        sp = self.sp
        bobz = abs(math.sin(self.phase * (3.0 if self.state != "wander" else 2.0))) * 0.08
        if self.flyer:
            bobz += 0.6 + math.sin(self.phase * 2) * 0.15
        self.bob.set_z(bobz); self.bob.set_sz(1 + math.sin(self.phase * 4) * 0.03)
        if self.state in ("battle", "caught", "frozen"):
            return
        dx, dy = px - self.x, py - self.y; dist = math.hypot(dx, dy)
        # awareness: front cone sees farther; crouching in grass hides you
        fwd = (-math.sin(math.radians(self.h)), math.cos(math.radians(self.h)))
        facing = (fwd[0] * dx + fwd[1] * dy) / max(dist, 0.01)
        r = detect * (1.0 if facing > -0.2 else 0.45)
        if dist < r:
            self.aware = min(1.0, self.aware + dt * (1.6 if dist < r * 0.5 else 0.8))
        else:
            self.aware = max(0.0, self.aware - dt * 0.3)
        speed = 0.0
        if self.state == "wander":
            self.t -= dt
            if self.t <= 0:
                self.t = random.uniform(2, 5)
                hx, hy = self.home
                self.tx, self.ty = hx + random.uniform(-10, 10), hy + random.uniform(-10, 10)
            ddx, ddy = self.tx - self.x, self.ty - self.y
            if math.hypot(ddx, ddy) > 0.5 and self.t > 1.0:
                speed = 1.4; self._turn_to(ddx, ddy, dt)
            if self.aware >= 1.0:
                self.state = "alert"; self.t = 0.8
                self.set_icon("!", (1, 0.85, 0.1, 1)); self.g.sfx("alert", 0.5)
        elif self.state == "alert":
            self._turn_to(dx, dy, dt * 3); self.t -= dt
            if self.t <= 0:
                self.state = "charge" if sp["aggro"] else "flee"; self.t = 6.0
                self.set_icon("!!" if sp["aggro"] else "?", (1, 0.3, 0.2, 1) if sp["aggro"] else (0.6, 0.85, 1, 1))
        elif self.state == "flee":
            self._turn_to(-dx, -dy, dt * 3); speed = 5.5; self.t -= dt
            if self.t <= 0 or dist > 40:
                self.state = "wander"; self.aware = 0.0; self.home = (self.x, self.y); self.set_icon(None, None)
        elif self.state == "charge":
            self._turn_to(dx, dy, dt * 4); speed = 4.8; self.t -= dt
            if dist < 1.2 + self.radius:
                self.g.start_battle(self)
                return
            if self.t <= 0 or dist > 45:
                self.state = "wander"; self.aware = 0.0; self.set_icon(None, None)
        if speed:
            rad = math.radians(self.h)
            nx = self.x - math.sin(rad) * speed * dt; ny = self.y + math.cos(rad) * speed * dt
            nx, ny = self.g.region.push_out(nx, ny, self.radius)
            okw = (self.g.region.height(nx, ny) < W.WATER - 0.4) if self.swim else (self.g.region.height(nx, ny) > W.WATER + 0.2)
            if okw:
                self.x, self.y = nx, ny
            else:
                self.h += 120 * dt * 3; self.tx, self.ty = self.home
        self.place()

    def _turn_to(self, dx, dy, dt):
        want = math.degrees(math.atan2(-dx, dy))
        d = (want - self.h + 180) % 360 - 180
        self.h += max(-200 * dt, min(200 * dt, d))

    def destroy(self):
        self.root.remove_node()


class Ball:
    """A PIKCEL ball in flight. kind: pikcel/nova/astral; own=True when it carries the player's PIKNOTT (battle start)."""
    def __init__(self, game, kind, pos, vel, own=False):
        self.g = game; self.kind = kind; self.own = own
        self.node = ball_node(game.app, game.app.BASE, kind, game.world_np)
        self.pos = Vec3(pos); self.vel = Vec3(vel); self.t = 0.0; self.rest = 0.0; self.dead = False
        self.node.set_pos(self.pos)

    def update(self, dt):
        self.t += dt
        self.vel.z -= 20 * dt
        self.pos += self.vel * dt
        gz = self.g.region.ground(self.pos.x, self.pos.y) + 0.17
        if self.pos.z < gz:
            self.pos.z = gz
            if abs(self.vel.z) > 2:
                self.vel.z = -self.vel.z * 0.4; self.vel.x *= 0.6; self.vel.y *= 0.6
            else:
                self.vel = Vec3(self.vel.x * 0.9, self.vel.y * 0.9, 0); self.rest += dt
        self.node.set_pos(self.pos)
        self.node.set_hpr(self.t * 600, self.t * 400, 0)


class Game:
    def __init__(self, app, save=None):
        self.app = app; self.base = app
        self.world_np = app.render.attach_new_node("world")
        self.region = W.Region()
        self.region.build(self.world_np)
        self.boy = Boy(self.world_np)
        self.boy_shadow = blob_shadow(self.boy.root, 0.45)
        self.party = []; self.storage = []
        self.items = {"pikcel": 10, "nova": 3, "astral": 1, "potion": 3}
        self.seen = set(); self.caught = set()
        self.x, self.y = W.CAMP[0] + 9, W.CAMP[1] + 12; self.z = self.region.height(self.x, self.y)
        self.h = 0.0; self.vz = 0.0; self.on_ground = True
        self.cam_yaw = 0.0; self.cam_pitch = -14.0; self.cam_dist = 7.5
        self.ball_sel = 0; self.playtime = 0.0
        if save:
            self.load(save)
        else:
            self.party = [D.Mon(1, 5)]
            self.seen.add(1); self.caught.add(1)
        self.wilds = []; self.balls = []; self.effects = []; self.catching = None
        self.pickups = [[x, y, None, 0.0, None] for (x, y) in self.region.pickups]
        self.battle = None; self.overlay = None; self.paused = False
        self.mode = "explore"; self.aiming = False; self.throw_anim = 0.0; self.throw_cd = 0.0
        self.msgs = []
        self.keys = {}
        self.build_hud()
        self._bind()
        self.capture_mouse(True)
        for _ in range(MAX_WILD):
            self.try_spawn(initial=True)
        self.ensure_starter_wilds()
        self.update_pickups(0)
        self.app.task_mgr.add(self.update, "pc-game")
        self.toast("Welcome to the Celestika region!  Right-click to aim, left-click to throw a PIKCEL ball.")

    def sfx(self, name, vol=1.0):
        self.app.sfx(name, vol)

    # ------------------------------------------------------------------ input
    def _bind(self):
        a = self.app
        for k in ("w", "a", "s", "d", "arrow_up", "arrow_down", "arrow_left", "arrow_right", "shift", "space", "lshift", "rshift"):
            a.accept(k, self._key, [k, True]); a.accept(k + "-up", self._key, [k, False])
        a.accept("mouse3", self.set_aim, [True]); a.accept("mouse3-up", self.set_aim, [False])
        a.accept("mouse1", self.on_click)
        a.accept("wheel_up", self.cycle_ball, [-1]); a.accept("wheel_down", self.cycle_ball, [1])
        for i in range(3):
            a.accept(str(i + 1), self.pick_ball, [i])
        a.accept("g", self.throw_own); a.accept("c", self.toggle_crouch); a.accept("control", self.toggle_crouch)
        a.accept("m", self.toggle_map); a.accept("p", self.toggle_dok); a.accept("tab", self.toggle_party)
        a.accept("e", self.interact); a.accept("escape", self.on_escape)
        self.crouch = False
        self.pad = None
        try:
            from panda3d.core import InputDevice
            devs = a.devices.get_devices(InputDevice.DeviceClass.gamepad)
            if devs:
                self.pad = devs[0]; a.attach_input_device(self.pad, prefix="pad")
                a.accept("pad-face_a", self._key, ["space", True]); a.accept("pad-face_a-up", self._key, ["space", False])
                a.accept("pad-face_x", self.throw_own); a.accept("pad-face_b", self.toggle_crouch)
                a.accept("pad-rshoulder", self.on_click); a.accept("pad-lshoulder", self.cycle_ball, [1])
                a.accept("pad-start", self.on_escape); a.accept("pad-back", self.toggle_map)
        except Exception:
            self.pad = None

    def _unbind(self):
        self.app.ignore_all()
        self.app.accept("window-event", self.app._on_window_event)

    def _key(self, k, v):
        self.keys[k] = v

    def down(self, *ks):
        return any(self.keys.get(k) for k in ks)

    def capture_mouse(self, on):
        self.mouse_captured = on
        wp = WindowProperties(); wp.set_cursor_hidden(on)
        wp.set_mouse_mode(WindowProperties.M_confined if on else WindowProperties.M_absolute)
        try:
            self.app.win.request_properties(wp)
        except Exception:
            pass
        if on:
            self._center_mouse()

    def _center_mouse(self):
        w = self.app.win
        if w:
            w.move_pointer(0, w.get_x_size() // 2, w.get_y_size() // 2)

    def set_aim(self, on):
        if self.mode != "explore" or self.overlay:
            self.aiming = False; return
        self.aiming = on
        self.crosshair.show() if on else self.crosshair.hide()

    def cycle_ball(self, d):
        if self.battle:
            return
        self.ball_sel = (self.ball_sel + d) % 3; self.refresh_hud()

    def pick_ball(self, i):
        if self.battle:
            return
        self.ball_sel = i; self.refresh_hud()

    def toggle_crouch(self):
        if self.mode == "explore":
            self.crouch = not self.crouch

    def on_click(self):
        if self.mode == "explore" and not self.overlay and self.mouse_captured:
            self.throw_capture()

    def on_escape(self):
        if self.overlay:
            self.close_overlay()
        elif self.mode == "explore":
            self.app.show_pause()

    # ------------------------------------------------------------------ throwing
    def aim_vector(self):
        yaw = math.radians(self.cam_yaw); pitch = math.radians(self.cam_pitch + (14 if self.aiming else 18))
        d = Vec3(-math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), math.sin(pitch))
        return d

    def hand_pos(self):
        rad = math.radians(self.h)
        return Point3(self.x + math.cos(rad) * 0.35 - math.sin(rad) * 0.3, self.y + math.sin(rad) * 0.35 + math.cos(rad) * 0.3, self.z + 1.55)

    def throw_capture(self):
        if self.throw_cd > 0 or self.catching:
            return
        kind = D.BALLS[self.ball_sel][0]
        if self.items.get(kind, 0) <= 0:
            self.toast("No %ss left!" % D.BALLS[self.ball_sel][1]); return
        self.items[kind] -= 1
        self._throw(kind, False)

    def throw_own(self):
        if self.mode != "explore" or self.overlay or self.throw_cd > 0 or self.catching:
            return
        if not any(m.hp > 0 for m in self.party):
            self.toast("Your PIKNOTT are too tired. Rest at the camp fire!"); return
        self._throw("pikcel", True)

    def _throw(self, kind, own):
        self.h = self.cam_yaw
        v = self.aim_vector() * 21.0
        self.balls.append(Ball(self, kind, self.hand_pos(), v, own))
        self.throw_anim = 1.0; self.throw_cd = 0.45
        self.sfx("throw", 0.7); self.refresh_hud()

    def update_balls(self, dt):
        for b in list(self.balls):
            b.update(dt)
            hit = None
            for wd in self.wilds:
                if wd.state in ("caught",):
                    continue
                c = Vec3(wd.x, wd.y, wd.z + 0.5 * wd.sp["size"] + (0.6 if wd.flyer else 0))
                if (b.pos - c).length() < wd.radius + 0.35:
                    hit = wd; break
            if b.own:
                if hit is None and b.rest > 0.05:
                    near = [w for w in self.wilds if w.state not in ("caught",) and math.hypot(w.x - b.pos.x, w.y - b.pos.y) < 8]
                    hit = min(near, key=lambda w: math.hypot(w.x - b.pos.x, w.y - b.pos.y)) if near else None
                    if hit is None:
                        self.toast("No wild PIKNOTT nearby - %s hops back." % self.lead().name)
                        b.node.remove_node(); self.balls.remove(b); continue
                if hit is not None:
                    b.node.remove_node(); self.balls.remove(b)
                    self.start_battle(hit, (b.pos.x, b.pos.y)); return
            else:
                if hit is not None:
                    self.balls.remove(b); self.begin_catch(b, hit); continue
            if b.rest > 0.8 or b.t > 6:
                self.items[b.kind] = self.items.get(b.kind, 0) + 1         # missed balls are picked back up
                b.node.remove_node(); self.balls.remove(b); self.refresh_hud()

    def begin_catch(self, ball, wd, in_battle=False, on_done=None):
        """Shrink the PIKNOTT into the ball, drop it, wobble 1-3 times, then catch or break out."""
        mult = dict((k, m) for k, _, m, _ in D.BALLS)[ball.kind]
        stealth = 1.0; note = ""
        if not in_battle:
            vx, vy = ball.vel.x, ball.vel.y
            fwd = (-math.sin(math.radians(wd.h)), math.cos(math.radians(wd.h)))
            along = (vx * fwd[0] + vy * fwd[1]) / max(0.01, math.hypot(vx, vy))
            if wd.state in ("wander", "frozen"):
                stealth = 1.5; note = "Unaware bonus!"
                if along > 0.4:
                    stealth = 2.2; note = "Back strike! Big catch bonus!"
            elif wd.state == "charge":
                stealth = 0.8
        p = D.catch_chance(wd.mon, mult, stealth, in_battle)
        success = random.random() < p
        shakes = 3 if success else (1 + (random.random() < p * 1.6) + (random.random() < p))
        shakes = min(shakes, 3)
        self.seen.add(wd.sp["id"])
        wd.state = "caught" if not in_battle else wd.state
        ball.vel = Vec3(0, 0, 0)
        self.catching = {"ball": ball, "wild": wd, "t": 0.0, "shakes": shakes, "ok": success, "battle": in_battle,
                         "done": on_done, "phase": "absorb", "p": p, "prev_state": "wander"}
        if note:
            self.toast(note)

    def update_catch(self, dt):
        c = self.catching
        if not c:
            return
        c["t"] += dt; b = c["ball"]; wd = c["wild"]; t = c["t"]
        if c["phase"] == "absorb":
            k = max(0.0, 1 - t / 0.35)
            wd.root.set_scale(wd.sp["size"] * max(0.01, k))
            wd.bob.set_shader_input("flash", 1.0)
            b.node.set_hpr(0, 0, 0)
            if t > 0.4:
                wd.root.hide(); c["phase"] = "drop"; c["t"] = 0
                gz = self.region.ground(b.pos.x, b.pos.y) + 0.17
                c["gz"] = gz
        elif c["phase"] == "drop":
            gz = c["gz"]
            b.pos.z = max(gz, b.pos.z - dt * 6); b.node.set_pos(b.pos); b.node.set_h(self.cam_yaw + 180)
            if t > 0.5:
                c["phase"] = "shake"; c["t"] = 0; c["n"] = 0
        elif c["phase"] == "shake":
            n = int(t / 0.75)
            frac = (t % 0.75) / 0.75
            if n >= c["shakes"]:
                c["phase"] = "result"; c["t"] = 0
                if c["ok"]:
                    self.sfx("catch"); self.burst(b.pos, (1, 0.9, 0.3), 1.6, star=True)
                else:
                    self.sfx("breakout"); self.burst(b.pos, (1, 1, 1), 1.2)
                return
            if n != c.get("n"):
                c["n"] = n; self.sfx("wobble", 0.7)
            ang = math.sin(frac * math.pi * 2) * 28 if frac < 0.5 else 0
            b.node.set_r(ang)
            b.node.set_shader_input("flash", 0.0)
        elif c["phase"] == "result":
            if t < 0.6:
                return
            b.node.remove_node()
            self.catching = None
            if c["ok"]:
                wd.state = "caught"
                self.add_caught(wd.mon)
                self.remove_wild(wd)
            else:
                wd.root.show(); wd.root.set_scale(wd.sp["size"]); wd.bob.set_shader_input("flash", 0.0)
                if not c["battle"]:
                    wd.state = "alert"; wd.t = 0.6; wd.aware = 1.0; wd.set_icon("!", (1, 0.85, 0.1, 1))
                    self.toast("Oh no! %s broke free!" % wd.sp["name"])
            if c["done"]:
                c["done"](c["ok"])
            self.refresh_hud()

    def add_caught(self, mon):
        sid = mon.sp["id"]; new = sid not in self.caught
        self.caught.add(sid); self.seen.add(sid)
        if len(self.party) < 6:
            self.party.append(mon); where = "joined your team"
        else:
            self.storage.append(mon); where = "was sent to storage"
        self.toast("Gotcha! %s (Lv %d) %s!%s" % (mon.name, mon.level, where, "  New CELESTIKA DOK entry!" if new else ""))
        if self.party and self.party[0].hp > 0:
            ups = self.party[0].gain_xp(int(mon.sp["xp"] * mon.level / 10))
            if ups:
                self.toast("%s grew to Lv %d!" % (self.party[0].name, ups[-1])); self.sfx("levelup", 0.7)

    # ------------------------------------------------------------------ effects
    def burst(self, pos, col, size=1.0, star=False):
        m = Mesh(); n = 5 if star else 8
        V = [(0, 0, 0)]; T = []
        for i in range(n * 2 + 1):
            a = i * math.pi / n; r = 1.0 if i % 2 == 0 else 0.42
            V.append((math.cos(a) * r, 0, math.sin(a) * r))
        for i in range(n * 2):
            T.append((0, i + 2, i + 1))
        m.add(V, [(0, -1, 0)] * len(V), col, [(0, -1, 0)] * len(V), T)
        holder = self.world_np.attach_new_node("fx")
        ink = m.node("burst_ink"); ink.reparent_to(holder); ink.set_scale(1.18); ink.set_color_scale(0.05, 0.05, 0.09, 1); ink.set_bin("fixed", 39)
        g = m.node("burst"); g.reparent_to(holder); g.set_bin("fixed", 41)
        holder.set_pos(pos); holder.set_billboard_point_eye(); holder.set_two_sided(True)
        holder.set_depth_test(False); holder.set_depth_write(False)
        holder.set_shader_input("flash", 0.0)
        self.effects.append([holder, 0.0, size])

    def update_effects(self, dt):
        for e in list(self.effects):
            e[1] += dt
            k = e[1] / 0.45
            if k >= 1:
                e[0].remove_node(); self.effects.remove(e); continue
            e[0].set_scale(e[2] * (0.3 + k)); e[0].set_r(k * 60)

    # ------------------------------------------------------------------ wilds
    def try_spawn(self, initial=False):
        if len(self.wilds) >= MAX_WILD:
            return
        for _ in range(10):
            a = random.uniform(0, 2 * math.pi); d = random.uniform(12 if initial else 45, 105)
            x, y = self.x + math.cos(a) * d, self.y + math.sin(a) * d
            if math.hypot(x, y) > 185 or math.hypot(x - W.CAMP[0], y - W.CAMP[1]) < 14:
                continue
            h = self.region.height(x, y); zone = self.region.zone(x, y)
            table = SPAWNS.get(zone)
            if not table:
                continue
            sid, _, lo, hi = random.choices(table, weights=[t[1] for t in table])[0]
            sp = D.BY_ID[sid]
            if sid == 13 and any(w.sp["id"] == 13 for w in self.wilds):
                continue
            if sp["model"] == "fish":
                if h > W.WATER - 1.0: continue
            elif h < W.WATER + 0.3:
                continue
            if sid == 13:
                x, y = W.VOLCANO[0] + 4, W.VOLCANO[1] - 16
            self.wilds.append(Wild(self, D.Mon(sid, random.randint(lo, hi)), x, y))
            return

    def ensure_starter_wilds(self):
        """Guarantee a few friendly PIKNOTT near camp so a new player can catch straight away."""
        for sid, dx, dy in ((2, 10, -126), (1, -14, -118), (3, 18, -112)):
            self.wilds.append(Wild(self, D.Mon(sid, random.randint(3, 4)), dx, dy))

    def remove_wild(self, wd):
        if wd in self.wilds:
            self.wilds.remove(wd)
        wd.destroy()

    def update_wilds(self, dt):
        grass = self.region.in_grass(self.x, self.y)
        run = self.down("shift", "lshift", "rshift") and not self.crouch
        det = 3.0 if (self.crouch and grass) else (7.0 if self.crouch else (20.0 if run else 13.0))
        self.hidden = self.crouch and grass
        for wd in list(self.wilds):
            if math.hypot(wd.x - self.x, wd.y - self.y) > 130 and wd.state == "wander":
                self.remove_wild(wd); continue
            if math.hypot(wd.x - self.x, wd.y - self.y) < 30:
                self.seen.add(wd.sp["id"])
            wd.update(dt, self.x, self.y, det)
            if self.battle:
                return
        if random.random() < dt * 0.8:
            self.try_spawn()

    def update_pickups(self, dt):
        for p in self.pickups:
            x, y, node, cd = p[:4]
            if node is None:
                p[3] = cd - dt
                if p[3] <= 0:
                    kind = random.choice(["pikcel", "pikcel", "nova", "potion", "astral"] if random.random() < 0.15 else ["pikcel", "pikcel", "potion"])
                    if kind == "potion":
                        m = Mesh(); m.ellipsoid((0, 0, 0.3), (0.18, 0.18, 0.26), (0.95, 0.35, 0.75)); m.box((0, 0, 0.62), (0.07, 0.07, 0.08), (0.9, 0.9, 0.95))
                        n = outlined(m.node("potion"), self.world_np, 0.02, name="potion")
                    else:
                        n = ball_node(self.app, self.app.BASE, kind, self.world_np)
                    n.set_pos(x, y, self.region.height(x, y) + 0.4)
                    p[2] = n; p[4] = kind
            else:
                node.set_h(node.get_h() + dt * 90)
                node.set_z(self.region.height(x, y) + 0.45 + math.sin(time.time() * 3) * 0.1)
                if math.hypot(self.x - x, self.y - y) < 1.4:
                    kind = p[4]; amount = 2 if kind == "pikcel" else 1
                    self.items[kind] = self.items.get(kind, 0) + amount
                    names = {"pikcel": "Pikcel Ball", "nova": "Nova Pikcel", "astral": "Astral Pikcel", "potion": "Potion"}
                    self.toast("Found %d x %s!" % (amount, names[kind])); self.sfx("heal", 0.5)
                    node.remove_node(); p[2] = None; p[3] = 150.0; self.refresh_hud()

    # ------------------------------------------------------------------ battle hook
    def lead(self):
        for m in self.party:
            if m.hp > 0:
                return m
        return self.party[0]

    def start_battle(self, wd, at=None):
        if self.battle or self.catching:
            return
        if not any(m.hp > 0 for m in self.party):
            wd.state = "flee"; wd.t = 3
            self.toast("Your PIKNOTT are too tired to battle! Rest at camp (E at the fire).")
            return
        import pc_battle
        self.mode = "battle"; self.aiming = False; self.crosshair.hide()
        self.capture_mouse(False)
        for w in self.wilds:
            if w is not wd and w.state in ("charge", "alert"):
                w.state = "wander"; w.set_icon(None, None)
        wd.set_icon(None, None)
        self.battle = pc_battle.Battle(self, wd)

    def end_battle(self, result):
        self.battle = None; self.mode = "explore"
        self.capture_mouse(True)
        if result == "blackout":
            for m in self.party:
                m.heal_full()
            self.x, self.y = W.CAMP[0] + 3, W.CAMP[1] + 6
            self.toast("You hurried back to camp. Your PIKNOTT were healed.")
        self.save()
        self.refresh_hud()

    # ------------------------------------------------------------------ camp
    def interact(self):
        if self.mode != "explore" or self.overlay:
            return
        if math.hypot(self.x - W.CAMP[0], self.y - W.CAMP[1]) < 6:
            for m in self.party + self.storage:
                m.heal_full()
            self.sfx("heal"); self.toast("You rested by the camp fire. All PIKNOTT fully healed!  Game saved.")
            self.save(); self.refresh_hud()

    # ------------------------------------------------------------------ main update
    def update(self, task):
        dt = min(globalClock.get_dt(), 0.05)
        if self.paused:
            return task.cont
        self.playtime += dt
        self.throw_cd = max(0, self.throw_cd - dt); self.throw_anim = max(0, self.throw_anim - dt * 2.5)
        if self.mode == "explore" and not self.overlay:
            self.update_player(dt)
        else:
            self.boy.animate(dt, 0, False, False)
        self.update_camera(dt)
        if self.mode == "explore":
            self.update_balls(dt)
        self.update_catch(dt)
        if not self.battle:
            self.update_wilds(dt)
        else:
            self.battle.update(dt)
        self.update_effects(dt)
        self.update_pickups(dt)
        self.region.fire.set_sz(1 + math.sin(task.time * 11) * 0.12); self.region.fire.set_h(task.time * 40)
        self.region.sky.set_pos(self.app.camera.get_pos(self.app.render))
        self.update_hud(dt)
        return task.cont

    def update_player(self, dt):
        mx = (self.down("d", "arrow_right") - self.down("a", "arrow_left"))
        my = (self.down("w", "arrow_up") - self.down("s", "arrow_down"))
        if self.pad:
            try:
                from panda3d.core import InputDevice
                lx = self.pad.find_axis(InputDevice.Axis.left_x).value; ly = self.pad.find_axis(InputDevice.Axis.left_y).value
                if abs(lx) > 0.2: mx = lx
                if abs(ly) > 0.2: my = ly
                rx = self.pad.find_axis(InputDevice.Axis.right_x).value; ry = self.pad.find_axis(InputDevice.Axis.right_y).value
                if abs(rx) > 0.2: self.cam_yaw -= rx * 140 * dt
                if abs(ry) > 0.2: self.cam_pitch = max(-60, min(25, self.cam_pitch + ry * 90 * dt))
                lt = self.pad.find_axis(InputDevice.Axis.left_trigger).value
                if (lt > 0.5) != self.aiming: self.set_aim(lt > 0.5)
            except Exception:
                pass
        run = self.down("shift", "lshift", "rshift") and not self.crouch
        spd = 2.4 if self.crouch else (8.5 if run else 5.0)
        if self.aiming:
            spd = min(spd, 2.6)
        moving = abs(mx) + abs(my) > 0.01
        if moving:
            yaw = math.radians(self.cam_yaw)
            fx, fy = -math.sin(yaw), math.cos(yaw)
            rx, ry = math.cos(yaw), math.sin(yaw)
            vx, vy = fx * my + rx * mx, fy * my + ry * mx
            l = math.hypot(vx, vy); vx, vy = vx / l, vy / l
            nx, ny = self.x + vx * spd * dt, self.y + vy * spd * dt
            nx, ny = self.region.push_out(nx, ny, 0.4)
            nh = self.region.height(nx, ny)
            if nh < W.WATER - 0.9 and self.region.in_lake(nx, ny):
                pass                                                   # too deep - stay on shore
            elif nh - self.z < 1.2 or not self.on_ground:
                self.x, self.y = nx, ny
            want = math.degrees(math.atan2(-vx, vy))
            if not self.aiming:
                d = (want - self.h + 180) % 360 - 180
                self.h += max(-720 * dt, min(720 * dt, d))
        if self.aiming:
            self.h = self.cam_yaw
        gz = self.region.ground(self.x, self.y)
        if self.keys.get("space") and self.on_ground and not self.crouch:
            self.vz = 7.5; self.on_ground = False
        self.vz -= 22 * dt
        self.z += self.vz * dt
        if self.z <= gz:
            self.z = gz; self.vz = 0; self.on_ground = True
        elif self.on_ground and self.z - gz < 0.6:
            self.z = gz; self.vz = 0
        else:
            self.on_ground = self.z - gz < 0.05
        self.boy.root.set_pos(self.x, self.y, self.z); self.boy.root.set_h(self.h)
        self.boy.animate(dt, spd if moving else 0, self.crouch, not self.on_ground, self.throw_anim)
        self.boy_shadow.set_z(gz - self.z + 0.03)

    def update_camera(self, dt):
        a = self.app
        if self.battle:
            self.battle.update_camera(dt); return
        if self.mouse_captured and a.win and a.mouseWatcherNode.has_mouse() and not self.overlay:
            md = a.win.get_pointer(0)
            cx, cy = a.win.get_x_size() // 2, a.win.get_y_size() // 2
            dx, dy = md.get_x() - cx, md.get_y() - cy
            sens = 0.15 * float(a.settings.get("sensitivity", 1.0))
            if abs(dx) < 300 and abs(dy) < 300:
                self.cam_yaw -= dx * sens
                self.cam_pitch -= dy * sens * (-1 if a.settings.get("invert_y") else 1)
                self.cam_pitch = max(-60, min(25, self.cam_pitch))
            self._center_mouse()
        dist = 3.2 if self.aiming else self.cam_dist
        yaw = math.radians(self.cam_yaw); pitch = math.radians(self.cam_pitch)
        side = 1.0 if self.aiming else 0.0
        fx, fy = -math.sin(yaw), math.cos(yaw)
        tx, ty, tz = self.x + math.cos(yaw) * side, self.y + math.sin(yaw) * side, self.z + (1.7 if self.aiming else 1.5)
        cx = tx - fx * math.cos(pitch) * dist; cy = ty - fy * math.cos(pitch) * dist; cz = tz - math.sin(pitch) * dist
        cz = max(cz, self.region.ground(cx, cy) + 0.6)
        a.camera.set_pos(cx, cy, cz)
        a.camera.look_at(tx + fx * 2, ty + fy * 2, tz - (0.0 if self.aiming else 0.3))
        if self.aiming:
            self.update_arc()
        else:
            self.arc.hide()

    def update_arc(self):
        self.arc.show()
        p = Vec3(self.hand_pos()); v = self.aim_vector() * 21.0
        for i, dot in enumerate(self.arc_dots):
            for _ in range(3):
                v.z -= 20 * 0.016; p += v * 0.016
            dot.set_pos(p)
            dot.set_color_scale(1, 1, 1, 1) if p.z > self.region.ground(p.x, p.y) else dot.set_color_scale(1, 1, 1, 0)

    # ------------------------------------------------------------------ HUD
    def build_hud(self):
        a = self.app; ar = a.getAspectRatio()
        self.hud = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0))
        # minimap (always on, top-right)
        img = self.region.map_image(512)
        self.map_tex = Texture("minimap"); self.map_tex.setup_2d_texture(512, 512, Texture.T_unsigned_byte, Texture.F_rgb)
        self.map_tex.set_ram_image(np.ascontiguousarray(img[:, :, ::-1]).tobytes())
        self.map_tex.set_wrap_u(SamplerState.WM_border_color); self.map_tex.set_wrap_v(SamplerState.WM_border_color)
        self.map_tex.set_border_color((0.1, 0.1, 0.14, 1))
        S = 0.27
        self.mm_center = (ar - S - 0.05, 1 - S - 0.05)
        U.panel(self.hud, -S, S, -S, S, (0.1, 0.1, 0.14, 1), 0.016, self.mm_center)
        self.mm = OnscreenImage(parent=self.hud, image=self.map_tex, pos=(self.mm_center[0], 0, self.mm_center[1]), scale=S)
        self.mm_S = S; self.mm_span = 120.0
        self.mm_dots = []
        for i in range(MAX_WILD + 6):
            d = DirectFrame(parent=self.hud, frameColor=U.INK, frameSize=(-0.016, 0.016, -0.016, 0.016))
            d.inner = DirectFrame(parent=d, frameColor=(1, 0.3, 0.3, 1), frameSize=(-0.010, 0.010, -0.010, 0.010))
            d.hide(); self.mm_dots.append(d)
        self.mm_arrow = self._arrow(self.hud, 0.045); self.mm_arrow.set_pos(self.mm_center[0], 0, self.mm_center[1])
        U.text(self.hud, "N", (self.mm_center[0], self.mm_center[1] + S - 0.05), 0.045, (1, 1, 1, 1))
        self.zone_lbl = U.text(self.hud, "", (self.mm_center[0], self.mm_center[1] - S - 0.075), 0.05, (1, 0.92, 0.4, 1))
        U.text(self.hud, "[M] Region map", (self.mm_center[0], self.mm_center[1] - S - 0.13), 0.035, (0.9, 0.9, 0.95, 1))
        # lead PIKNOTT card (top-left)
        U.panel(self.hud, 0, 0.62, -0.12, 0, (0.12, 0.13, 0.22, 0.96), 0.012, (-ar + 0.05, 0.95))
        self.lead_lbl = U.text(self.hud, "", (-ar + 0.08, 0.875), 0.045, (1, 1, 1, 1), TextNode.A_left)
        self.lead_bar = U.bar(self.hud, (-ar + 0.08, 0.85 - 0.05), 0.55, 0.012, 1.0)
        self.team_lbl = U.text(self.hud, "", (-ar + 0.05, 0.76), 0.035, (1, 1, 1, 1), TextNode.A_left)
        # satchel (bottom-right)
        self.ball_frames = []
        for i, (k, name, mult, col) in enumerate(D.BALLS):
            f = U.panel(self.hud, -0.17, 0.17, -0.05, 0.05, (*col, 1), 0.012, (ar - 0.95 + i * 0.37, -0.90))
            t = U.text(f, "", (0, -0.015), 0.04, (1, 1, 1, 1))
            self.ball_frames.append((f, t))
        self.potion_lbl = U.text(self.hud, "", (ar - 0.05, -0.80), 0.04, (1, 0.8, 0.95, 1), TextNode.A_right)
        self.help_lbl = U.text(self.hud, "WASD move  Shift run  Space jump  C crouch  RMB aim  LMB throw  1-3/wheel ball  G send PIKNOTT (battle)  "
                                         "Tab team  P CELESTIKA DOK  M map  E rest at camp  Esc menu", (-ar + 0.04, -0.975), 0.031, (0.92, 0.92, 0.95, 1), TextNode.A_left)
        self.toast_lbl = U.text(self.hud, "", (0, 0.62), 0.055, (1, 1, 1, 1))
        self.status_lbl = U.text(self.hud, "", (0, -0.72), 0.045, (0.7, 1.0, 0.7, 1))
        self.crosshair = U.text(self.hud, "+", (0, -0.03), 0.12, (1, 1, 1, 1)); self.crosshair.hide()
        # throw arc preview dots
        self.arc = self.world_np.attach_new_node("arc")
        self.arc_dots = []
        for i in range(14):
            m = Mesh(); m.sphere((0, 0, 0), 0.06, (1, 1, 1)); n = m.node("dot"); n.reparent_to(self.arc)
            n.set_transparency(TransparencyAttrib.M_alpha); self.arc_dots.append(n)
        self.arc.hide()
        self.refresh_hud()

    def _arrow(self, parent, s):
        holder = parent.attach_new_node("arrow")
        for scale, col in ((1.45, (0.04, 0.04, 0.08, 1)), (1.0, (1, 0.9, 0.2, 1))):
            m = Mesh()
            m.add([(0, 0, s * scale), (-s * 0.7 * scale, 0, -s * 0.7 * scale), (0, 0, -s * 0.3 * scale), (s * 0.7 * scale, 0, -s * 0.7 * scale)],
                  [(0, -1, 0)] * 4, col, [(0, -1, 0)] * 4, [(0, 1, 2), (0, 2, 3)])
            n = m.node("arr"); n.reparent_to(holder); n.set_two_sided(True)
        return holder

    def toast(self, msg, dur=4.0):
        self.msgs.append([msg, dur])
        if len(self.msgs) > 3:
            self.msgs.pop(0)

    def refresh_hud(self):
        for i, (f, t) in enumerate(self.ball_frames):
            k, name, _, _ = D.BALLS[i]
            t.setText("%s%s x%d" % ("> " if i == self.ball_sel else "", name.replace(" Pikcel", "").replace(" Ball", ""), self.items.get(k, 0)))
            f.set_scale(1.12 if i == self.ball_sel else 0.92)
        self.potion_lbl.setText("Potions x%d" % self.items.get("potion", 0))
        if self.party:
            L = self.party[0]
            self.lead_lbl.setText("%s  Lv %d   HP %d/%d" % (L.name, L.level, L.hp, L.maxhp))
            f = L.hp / L.maxhp
            self.lead_bar[1].set_sx(max(0.001, f)); self.lead_bar[1]["frameColor"] = U.hp_col(f)
            self.team_lbl.setText("Team: " + "  ".join("%s%s" % (m.name, "" if m.hp > 0 else "(x)") for m in self.party[1:]) if len(self.party) > 1 else "Team: just %s - catch more PIKNOTT!" % L.name)

    def update_hud(self, dt):
        if self.msgs:
            self.msgs[0][1] -= dt
            if self.msgs[0][1] <= 0:
                self.msgs.pop(0)
        self.toast_lbl.setText("\n".join(m[0] for m in self.msgs[-2:]))
        zone = self.region.zone(self.x, self.y)
        if math.hypot(self.x - W.CAMP[0], self.y - W.CAMP[1]) < 14:
            zone = "Camp  (E: rest)" if math.hypot(self.x - W.CAMP[0], self.y - W.CAMP[1]) < 6 else "Celestika Camp"
        self.zone_lbl.setText(zone)
        st = ""
        if self.mode == "explore":
            if getattr(self, "hidden", False):
                st = "Hidden in tall grass"
            elif self.crouch:
                st = "Sneaking"
        self.status_lbl.setText(st)
        # minimap window
        S = self.mm_S; span = self.mm_span; sc = span / (2 * W.SIZE)
        u = (self.x + W.SIZE) / (2 * W.SIZE); v = (self.y + W.SIZE) / (2 * W.SIZE)
        from panda3d.core import TextureStage
        ts = TextureStage.get_default()
        self.mm.set_tex_scale(ts, sc, sc); self.mm.set_tex_offset(ts, u - sc / 2, v - sc / 2)
        self.mm_arrow.set_r(-self.h)
        cx, cy = self.mm_center
        k = 0
        for wd in self.wilds:
            if k >= len(self.mm_dots): break
            dx, dy = (wd.x - self.x) / (span / 2), (wd.y - self.y) / (span / 2)
            if abs(dx) < 0.95 and abs(dy) < 0.95 and wd.root and not wd.root.is_hidden():
                d = self.mm_dots[k]; d.show(); d.set_pos(cx + dx * S, 0, cy + dy * S)
                d.inner["frameColor"] = (*D.TYPE_COL[wd.sp["types"][0]], 1)
                k += 1
        for d in self.mm_dots[k:]:
            d.hide()
        if self.overlay is not None and getattr(self, "_map_upd", None):
            self._map_upd()

    # ------------------------------------------------------------------ overlays
    def open_overlay(self):
        self.close_overlay()
        self.overlay = DirectFrame(parent=self.app.aspect2d, frameColor=(0.02, 0.03, 0.08, 0.72), frameSize=(-4, 4, -2, 2))
        self.capture_mouse(False); self.aiming = False; self.crosshair.hide()
        return self.overlay

    def close_overlay(self):
        if self.overlay:
            self.overlay.destroy(); self.overlay = None; self._map_upd = None
            if self.mode == "explore":
                self.capture_mouse(True)

    def toggle_map(self):
        if self.overlay and getattr(self, "_ov", "") == "map":
            self.close_overlay(); return
        if self.mode != "explore" and not self.battle:
            return
        o = self.open_overlay(); self._ov = "map"
        S = 0.86
        U.panel(o, -S, S, -S, S, (0.1, 0.1, 0.14, 1), 0.02, (0, 0.02))
        OnscreenImage(parent=o, image=self.map_tex, pos=(0, 0, 0.02), scale=S)
        U.text(o, "CELESTIKA REGION", (0, 0.93), 0.07, (1, 0.9, 0.3, 1))
        for name, (x, y) in W.ZONE_LABEL_POS.items():
            U.text(o, name, (x / W.SIZE * S, 0.02 + y / W.SIZE * S), 0.045 if name != "Camp" else 0.04, (1, 1, 1, 1))
        arrow = self._arrow(o, 0.04)
        dots = []
        for wd in self.wilds:
            d = DirectFrame(parent=o, frameColor=U.INK, frameSize=(-0.013, 0.013, -0.013, 0.013), pos=(wd.x / W.SIZE * S, 0, 0.02 + wd.y / W.SIZE * S))
            DirectFrame(parent=d, frameColor=(*D.TYPE_COL[wd.sp["types"][0]], 1), frameSize=(-0.008, 0.008, -0.008, 0.008))
        def upd():
            arrow.set_pos(self.x / W.SIZE * S, 0, 0.02 + self.y / W.SIZE * S); arrow.set_r(-self.h)
        self._map_upd = upd; upd()
        U.text(o, "Coloured dots = wild PIKNOTT    Red = Camp    Gold = Star Shrine    [M] close", (0, -0.93), 0.04, (0.9, 0.9, 0.95, 1))

    def toggle_dok(self, sel=None):
        if self.overlay and getattr(self, "_ov", "") == "dok" and sel is None:
            self.close_overlay(); return
        if self.mode != "explore":
            return
        o = self.open_overlay(); self._ov = "dok"
        ar = self.app.getAspectRatio()
        U.panel(o, -1.55, 1.55, -0.9, 0.9, (0.12, 0.13, 0.22, 0.96), 0.018)
        DirectFrame(parent=o, frameColor=(0.85, 0.15, 0.15, 1), frameSize=(-1.55, 1.55, 0.74, 0.9))
        U.text(o, "CELESTIKA DOK", (-1.45, 0.79), 0.085, (1, 1, 1, 1), TextNode.A_left)
        U.text(o, "Seen %d   Caught %d   / %d" % (len(self.seen), len(self.caught), len(D.SPECIES)), (1.45, 0.79), 0.05, (1, 0.95, 0.5, 1), TextNode.A_right)
        sel = sel or 1
        for i, sp in enumerate(D.SPECIES):
            sid = sp["id"]
            known = sid in self.seen
            label = "%03d  %s%s" % (sid, sp["name"] if known else "?????", "  *" if sid in self.caught else "")
            col = (*D.TYPE_COL[sp["types"][0]], 1) if known else (0.55, 0.55, 0.6, 1)
            if sid == sel:
                col = (1, 1, 1, 1)
            U.button(o, label, (-1.05, 0.64 - i * 0.118), self.toggle_dok, w=0.42, h=0.048, col=col, scale=0.042,
                     fg=(1, 1, 1, 1), extra=[sid])
        sp = D.BY_ID[sel]; known = sel in self.seen
        U.panel(o, 0, 1.0, -0.7, 0.6, (0.20, 0.22, 0.34, 1), 0.012, (-0.45, 0))
        if known:
            U.text(o, "No.%03d  %s" % (sel, sp["name"]), (0.05, 0.48), 0.075, (1, 0.9, 0.3, 1))
            for j, t in enumerate(sp["types"]):
                U.panel(o, -0.15, 0.15, -0.035, 0.035, (*D.TYPE_COL[t], 1), 0.01, (-0.2 + j * 0.36 + (0.18 if len(sp["types"]) == 1 else 0), 0.37))
                U.text(o, t, (-0.2 + j * 0.36 + (0.18 if len(sp["types"]) == 1 else 0), 0.355), 0.04)
            U.text(o, sp["text"], (0.05, 0.24), 0.042, (0.92, 0.92, 0.96, 1), outline=False, wrap=21)
            for j, (lab, v) in enumerate(zip(("HP", "ATK", "DEF", "SPD"), sp["base"])):
                U.text(o, lab, (-0.35, -0.08 - j * 0.08), 0.042, (1, 1, 1, 1), TextNode.A_left)
                U.bar(o, (-0.15, -0.065 - j * 0.08), 0.6 * v / 100, 0.018, 1.0, (*D.TYPE_COL[sp["types"][0]], 1))
            U.text(o, "Habitat: " + ", ".join(sp["zones"]), (0.05, -0.44), 0.042, (0.92, 0.92, 0.96, 1), outline=False)
            U.text(o, "Moves: " + ", ".join(sp["moves"]), (0.05, -0.53), 0.036, (0.92, 0.92, 0.96, 1), outline=False, wrap=26)
            U.text(o, "CAUGHT" if sel in self.caught else "SEEN", (0.05, -0.65), 0.06, (0.3, 0.9, 0.4, 1) if sel in self.caught else (1, 0.7, 0.2, 1))
        else:
            U.text(o, "No.%03d  ?????" % sel, (0.05, 0.4), 0.075)
            U.text(o, "Not seen yet. Explore the Celestika region!", (0.05, 0.1), 0.045, (0.85, 0.85, 0.9, 1), outline=False)
        U.text(o, "[P] close", (1.45, -0.85), 0.04, (0.85, 0.85, 0.9, 1), TextNode.A_right, outline=False)

    def toggle_party(self, refresh=False):
        if self.overlay and getattr(self, "_ov", "") == "party" and not refresh:
            self.close_overlay(); return
        if self.mode != "explore":
            return
        o = self.open_overlay(); self._ov = "party"
        U.panel(o, -1.5, 1.5, -0.88, 0.88, (0.12, 0.13, 0.22, 0.96), 0.018)
        U.text(o, "YOUR TEAM", (-0.75, 0.75), 0.075, (1, 0.9, 0.3, 1))
        U.text(o, "STORAGE (%d)" % len(self.storage), (0.78, 0.75), 0.075, (0.6, 0.85, 1, 1))
        for i, m in enumerate(self.party):
            y = 0.58 - i * 0.22
            U.panel(o, -0.68, 0.68, -0.09, 0.09, (*D.TYPE_COL[m.types[0]], 1), 0.012, (-0.75, y))
            U.text(o, "%s%s  Lv %d   %s" % ("LEAD  " if i == 0 else "", m.name, m.level, "/".join(m.types)), (-1.38, y + 0.025), 0.045, (1, 1, 1, 1), TextNode.A_left)
            f = m.hp / m.maxhp
            U.bar(o, (-1.38, y - 0.045), 0.45, 0.014, f, U.hp_col(f))
            U.text(o, "%d/%d" % (m.hp, m.maxhp), (-0.86, y - 0.06), 0.035, (1, 1, 1, 1), TextNode.A_left)
            if i > 0:
                U.button(o, "Lead", (-0.43, y + 0.035), self._party_act, w=0.09, h=0.035, scale=0.033, extra=["lead", i])
            if len(self.party) > 1:
                U.button(o, "Store", (-0.23, y + 0.035), self._party_act, w=0.09, h=0.035, scale=0.033, col=(0.5, 0.75, 1, 1), extra=["store", i])
            U.button(o, "Potion", (-0.33, y - 0.045), self._party_act, w=0.12, h=0.032, scale=0.03, col=(0.95, 0.45, 0.8, 1), extra=["potion", i],
                     enabled=self.items.get("potion", 0) > 0 and 0 < m.hp < m.maxhp)
        for i, m in enumerate(self.storage[:12]):
            y = 0.6 - i * 0.12
            U.panel(o, -0.62, 0.62, -0.05, 0.05, (*D.TYPE_COL[m.types[0]], 1), 0.01, (0.78, y))
            U.text(o, "%s  Lv %d" % (m.name, m.level), (0.2, y - 0.015), 0.04, (1, 1, 1, 1), TextNode.A_left)
            U.button(o, "To team", (1.2, y), self._party_act, w=0.14, h=0.035, scale=0.032, extra=["take", i], enabled=len(self.party) < 6)
        U.text(o, "Potions: %d     Pikcel %d   Nova %d   Astral %d          [Tab] close" % (
            self.items.get("potion", 0), self.items["pikcel"], self.items["nova"], self.items["astral"]), (0, -0.82), 0.04, (0.9, 0.9, 0.95, 1), outline=False)

    def _party_act(self, act, i):
        if act == "lead":
            self.party.insert(0, self.party.pop(i))
        elif act == "store" and len(self.party) > 1:
            self.storage.append(self.party.pop(i))
        elif act == "take" and len(self.party) < 6:
            self.party.append(self.storage.pop(i))
        elif act == "potion" and self.items.get("potion", 0) > 0:
            m = self.party[i]; m.hp = min(m.maxhp, m.hp + 30); self.items["potion"] -= 1; self.sfx("heal")
        self.refresh_hud(); self.toggle_party(refresh=True)

    # ------------------------------------------------------------------ save / load
    def to_json(self):
        return {"version": self.app.VERSION, "pos": [self.x, self.y, self.z], "h": self.h, "cam_yaw": self.cam_yaw,
                "party": [m.to_json() for m in self.party], "storage": [m.to_json() for m in self.storage],
                "items": self.items, "seen": sorted(self.seen), "caught": sorted(self.caught), "playtime": self.playtime,
                "saved": time.time()}

    def load(self, d):
        self.x, self.y, self.z = d.get("pos", [self.x, self.y, self.z])
        self.h = d.get("h", 0.0); self.cam_yaw = d.get("cam_yaw", self.h)
        self.party = [D.Mon.from_json(m) for m in d.get("party", [])] or [D.Mon(1, 5)]
        self.storage = [D.Mon.from_json(m) for m in d.get("storage", [])]
        self.items.update(d.get("items", {}))
        self.seen = set(d.get("seen", [1])); self.caught = set(d.get("caught", [1]))
        self.playtime = d.get("playtime", 0.0)

    def save(self):
        try:
            p = self.app.save_path()
            tmp = p + ".tmp"
            json.dump(self.to_json(), open(tmp, "w", encoding="utf-8"), indent=1)
            os.replace(tmp, p)
        except Exception as e:
            self.app.log_error("save: %r" % e)

    def destroy(self):
        self.app.task_mgr.remove("pc-game")
        if self.battle:
            self.battle.destroy(); self.battle = None
        self.close_overlay()
        self._unbind()
        self.capture_mouse(False)
        self.hud.destroy()
        self.world_np.remove_node()
