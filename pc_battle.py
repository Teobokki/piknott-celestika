"""Seamless overworld battles with a Legends-Arceus-style action-order queue and Normal / Strong / Agile move styles."""
import math, random
from panda3d.core import Vec3, Point3, TextNode
from direct.gui.DirectGui import DirectFrame
from direct.showbase.DirectObject import DirectObject
import pc_data as D
import pc_ui as U
from pc_models import creature_node, ball_node, blob_shadow

ALLY_COL = (0.30, 0.62, 1.0, 1); WILD_COL = (1.0, 0.36, 0.30, 1)
STYLE_COL = {"Normal": (0.85, 0.85, 0.80, 1), "Strong": (1.0, 0.45, 0.25, 1), "Agile": (0.35, 0.85, 1.0, 1)}


class Battle:
    def __init__(self, game, wd):
        self.g = game; self.app = game.app; self.wd = wd; self.wild = wd.mon
        wd.state = "battle"
        game.seen.add(wd.sp["id"])
        self.ai = next(i for i, m in enumerate(game.party) if m.hp > 0)
        # place the fighters facing each other in the overworld
        wx, wy = wd.x, wd.y
        dx, dy = game.x - wx, game.y - wy; l = math.hypot(dx, dy) or 1.0
        self.dir = (dx / l, dy / l)
        gap = 4.5 + 1.2 * wd.sp["size"]
        self.ally_pos = game.region.push_out(wx + self.dir[0] * gap, wy + self.dir[1] * gap, 0.6)
        game.x, game.y = game.region.push_out(wx + self.dir[0] * (gap + 3.2), wy + self.dir[1] * (gap + 3.2), 0.5)
        game.z = game.region.ground(game.x, game.y)
        face = math.degrees(math.atan2(-(wx - game.x), wy - game.y))
        game.h = face; game.boy.root.set_pos(game.x, game.y, game.z); game.boy.root.set_h(face)
        wd.h = math.degrees(math.atan2(-self.dir[0], self.dir[1])); wd.place()
        self.ally_node = None; self.spawn_ally()
        self.next_t = {"ally": D.action_time(self.ally) * 0.5, "wild": D.action_time(self.wild) * 0.5 + 0.01}
        self.style = "Normal"; self.menu = None
        self.steps = []; self.cur = None; self.step_t = 0.0; self.waiting = False; self.over = False
        self.lunge = None; self.disp = {"ally": self.ally.hp, "wild": self.wild.hp}
        self.cam_pos = None
        self.do = DirectObject()
        for k in ("1", "2", "3", "4"):
            self.do.accept(k, self.hotkey, [k])
        for k, st in (("z", "Normal"), ("x", "Strong"), ("c", "Agile")):
            self.do.accept(k, self.set_style, [st])
        self.do.accept("escape", self.back)
        self.build_ui()
        self.say("A wild %s (Lv %d) wants to battle!" % (self.wild.name, self.wild.level), 1.4)
        self.say("Go, %s!" % self.ally.name, 0.9)
        self.g.sfx("alert", 0.6)

    @property
    def ally(self):
        return self.g.party[self.ai]

    def spawn_ally(self):
        if self.ally_node:
            self.ally_node.remove_node()
        self.ally_node, self.ally_bob = creature_node(self.ally.sp, self.g.world_np)
        blob_shadow(self.ally_node, 0.45)
        x, y = self.ally_pos
        self.ally_node.set_pos(x, y, self.g.region.ground(x, y) if self.ally.sp["model"] != "fish" else max(self.g.region.ground(x, y), 0) )
        self.ally_node.set_h(math.degrees(math.atan2(self.dir[0], -self.dir[1])))
        self.g.burst(self.ally_node.get_pos() + Vec3(0, 0, 0.6), (1, 1, 1), 1.2, star=True)

    # ------------------------------------------------------------------ UI
    def build_ui(self):
        a = self.app; ar = a.getAspectRatio()
        self.ui = DirectFrame(parent=a.aspect2d, frameColor=(0, 0, 0, 0))
        self.g.help_lbl.hide(); self.g.status_lbl.hide()
        # wild HP (top centre)
        U.panel(self.ui, -0.5, 0.5, -0.08, 0.08, (0.12, 0.13, 0.22, 0.96), 0.014, (0, 0.86))
        self.w_lbl = U.text(self.ui, "", (-0.46, 0.875), 0.045, (1, 1, 1, 1), TextNode.A_left)
        self.w_bar = U.bar(self.ui, (-0.46, 0.825), 0.92, 0.016, 1.0)
        # ally HP (right, mid)
        U.panel(self.ui, -0.5, 0.5, -0.1, 0.1, (0.12, 0.13, 0.22, 0.96), 0.014, (ar - 0.6, -0.30))
        self.a_lbl = U.text(self.ui, "", (ar - 1.06, -0.25), 0.045, (1, 1, 1, 1), TextNode.A_left)
        self.a_bar = U.bar(self.ui, (ar - 1.06, -0.31), 0.92, 0.016, 1.0)
        self.a_hp = U.text(self.ui, "", (ar - 0.14, -0.375), 0.036, (1, 1, 1, 1), TextNode.A_right)
        # turn-order queue (left)
        U.panel(self.ui, 0, 0.46, -0.98, 0, (0.10, 0.11, 0.18, 0.92), 0.014, (-ar + 0.04, 0.62))
        U.text(self.ui, "TURN ORDER", (-ar + 0.27, 0.55), 0.05, (1, 0.9, 0.3, 1))
        self.q_frames = []
        for i in range(8):
            f = U.panel(self.ui, -0.2, 0.2, -0.042, 0.042, ALLY_COL, 0.01, (-ar + 0.27, 0.45 - i * 0.108))
            t = U.text(f, "", (0, -0.014), 0.036, (1, 1, 1, 1))
            self.q_frames.append((f, t))
        self.q_note = U.text(self.ui, "", (-ar + 0.27, -0.42), 0.032, (0.85, 0.85, 0.9, 1), wrap=12)
        # message box
        U.panel(self.ui, -0.85, 0.85, -0.06, 0.06, (0.10, 0.11, 0.18, 0.92), 0.014, (0, 0.66))
        self.msg = U.text(self.ui, "", (0, 0.645), 0.048, (1, 1, 1, 1))
        self.flash = U.text(self.ui, "", (0, 0.25), 0.11, (1, 0.85, 0.2, 1)); self.flash_t = 0
        self.menu_root = DirectFrame(parent=self.ui, frameColor=(0, 0, 0, 0))
        self.refresh()

    def refresh(self):
        w, al = self.wild, self.ally
        self.w_lbl.setText("Wild %s  Lv %d   %s" % (w.name, w.level, "/".join(w.types)))
        self.a_lbl.setText("%s  Lv %d   %s" % (al.name, al.level, "/".join(al.types)))
        for key, mon, bar in (("wild", w, self.w_bar), ("ally", al, self.a_bar)):
            f = max(0.0, self.disp[key] / mon.maxhp)
            bar[1].set_sx(max(0.001, f)); bar[1]["frameColor"] = U.hp_col(f)
        self.a_hp.setText("HP %d/%d   XP %d%%" % (round(self.disp["ally"]), al.maxhp,
                                                 max(0, min(100, int(100 * (al.xp - D.xp_for(al.level)) / max(1, D.xp_for(al.level + 1) - D.xp_for(al.level)))))))
        self.show_queue()

    def preview(self, n=8, first_style=None):
        t = dict(self.next_t); out = []; first = True
        for _ in range(n):
            who = "ally" if t["ally"] <= t["wild"] else "wild"
            out.append(who)
            mon = self.ally if who == "ally" else self.wild
            st = first_style if (who == "ally" and first and first_style) else "Normal"
            if who == "ally": first = False
            t[who] += D.action_time(mon, st)
        return out

    def show_queue(self, style=None):
        q = self.preview(8, style if self.waiting else None)
        for i, (f, t) in enumerate(self.q_frames):
            who = q[i]
            mon = self.ally if who == "ally" else self.wild
            f.inner["frameColor"] = ALLY_COL if who == "ally" else WILD_COL
            t.setText(("> " if i == 0 else "") + ("" if who == "ally" else "Wild ") + mon.name)
            f.set_scale(1.1 if i == 0 else 0.95)
        if self.waiting and style and style != "Normal":
            self.q_note.setText("%s style preview: %s" % (style, "acts sooner, weaker hit" if style == "Agile" else "hits harder, acts later"))
        else:
            self.q_note.setText("Strong = more power, you act later.  Agile = less power, act sooner.")

    def clear_menu(self):
        self.menu_root.destroy()
        self.menu_root = DirectFrame(parent=self.ui, frameColor=(0, 0, 0, 0))

    def main_menu(self):
        self.clear_menu(); self.menu = "main"
        r = self.menu_root
        labels = [("FIGHT", self.move_menu, (1.0, 0.45, 0.25, 1)), ("PIKCEL", self.ball_menu, (0.25, 0.62, 1.0, 1)),
                  ("SWITCH", self.switch_menu, (0.4, 0.8, 0.4, 1)), ("SATCHEL", self.item_menu, (0.95, 0.45, 0.8, 1)),
                  ("RUN", self.run, (0.6, 0.6, 0.65, 1))]
        for i, (t, c, col) in enumerate(labels):
            U.button(r, t, (-1.0 + i * 0.5, -0.86), c, w=0.22, h=0.07, col=col, scale=0.055)
        self.msg.setText("What will %s do?" % self.ally.name)

    def move_menu(self):
        self.clear_menu(); self.menu = "moves"
        r = self.menu_root
        U.panel(r, -1.15, 1.15, -0.22, 0.12, (0.10, 0.11, 0.18, 0.9), 0.014, (0, -0.76))
        for i, st in enumerate(("Normal", "Strong", "Agile")):
            col = STYLE_COL[st]
            b = U.button(r, ("[%s] " % "ZXC"[i]) + st.upper(), (-0.5 + i * 0.5, -0.585), self.set_style, w=0.21, h=0.045, col=col, scale=0.042, extra=[st])
            if st == self.style:
                b.set_scale(1.12)
        for i, mv in enumerate(self.ally.sp["moves"]):
            mt, pw, acc, pp, kind = D.MOVES[mv]
            left = self.ally.pp.get(mv, 0); need = 1 if self.style == "Normal" else 2
            power = "-" if not pw else str(int(pw * D.STYLES[self.style][0]))
            label = "%d  %s   %s  Pow %s  PP %d/%d" % (i + 1, mv, mt, power, left, pp)
            U.button(r, label, (-0.57 + (i % 2) * 1.14, -0.70 - (i // 2) * 0.13), self.choose_move, w=0.54, h=0.05,
                     col=D.TYPE_COL[mt] + (1,), scale=0.038, extra=[mv], enabled=left >= need)
        U.button(r, "Back [Esc]", (0.95, -0.585), self.main_menu, w=0.17, h=0.04, col=(0.6, 0.6, 0.65, 1), scale=0.035)
        self.msg.setText("Pick a style, then a move.  %s style uses %d PP." % (self.style, 1 if self.style == "Normal" else 2))
        self.show_queue(self.style)

    def set_style(self, st):
        if not self.waiting:
            return
        self.style = st
        if self.menu == "moves":
            self.move_menu()
        else:
            self.show_queue(st)

    def hotkey(self, k):
        if not self.waiting:
            return
        if self.menu == "main" and k == "1":
            self.move_menu(); return
        if self.menu == "moves":
            mv = self.ally.sp["moves"][int(k) - 1]
            if self.ally.pp.get(mv, 0) >= (1 if self.style == "Normal" else 2):
                self.choose_move(mv)

    def back(self):
        if self.waiting and self.menu not in ("main", "forced"):
            self.main_menu()

    def ball_menu(self):
        self.clear_menu(); self.menu = "balls"
        r = self.menu_root
        for i, (k, name, mult, col) in enumerate(D.BALLS):
            n = self.g.items.get(k, 0)
            U.button(r, "%s  x%d" % (name, n), (-0.75 + i * 0.6, -0.80), self.throw_ball, w=0.27, h=0.06, col=col + (1,), scale=0.042,
                     extra=[k], enabled=n > 0)
        U.button(r, "Back", (0, -0.94), self.main_menu, w=0.15, h=0.04, col=(0.6, 0.6, 0.65, 1), scale=0.035)
        c = D.catch_chance(self.wild, 1.0, 1.0, True)
        self.msg.setText("Throw a PIKCEL ball!  Weaker PIKNOTT are easier to catch (Pikcel ~%d%%)." % (c * 100))

    def switch_menu(self, forced=False):
        self.clear_menu(); self.menu = "forced" if forced else "switch"
        r = self.menu_root
        for i, m in enumerate(self.g.party):
            ok = m.hp > 0 and i != self.ai
            U.button(r, "%s Lv%d  %d/%d" % (m.name, m.level, m.hp, m.maxhp), (-1.0 + (i % 3) * 0.75, -0.74 - (i // 3) * 0.13),
                     self.do_switch, w=0.34, h=0.05, col=D.TYPE_COL[m.types[0]] + (1,), scale=0.038, extra=[i], enabled=ok)
        if not forced:
            U.button(r, "Back", (1.15, -0.95), self.main_menu, w=0.13, h=0.035, col=(0.6, 0.6, 0.65, 1), scale=0.032)
        self.msg.setText("Choose a PIKNOTT to send out." if not forced else "%s fainted! Choose your next PIKNOTT." % self.ally.name)

    def item_menu(self):
        self.clear_menu(); self.menu = "items"
        r = self.menu_root
        n = self.g.items.get("potion", 0)
        U.button(r, "Potion (+30 HP)  x%d" % n, (-0.3, -0.82), self.use_potion, w=0.33, h=0.06, col=(0.95, 0.45, 0.8, 1), scale=0.042,
                 enabled=n > 0 and self.ally.hp < self.ally.maxhp)
        U.button(r, "Back", (0.35, -0.82), self.main_menu, w=0.15, h=0.05, col=(0.6, 0.6, 0.65, 1), scale=0.04)
        self.msg.setText("Satchel")

    # ------------------------------------------------------------------ steps
    def say(self, text, dur=1.0, fn=None):
        self.steps.append((dur, text, fn))

    def call(self, fn, dur=0.0):
        self.steps.append((dur, None, fn))

    def player_act_done(self, cost_style="Normal"):
        self.next_t["ally"] += D.action_time(self.ally, cost_style)
        self.clear_menu(); self.waiting = False; self.menu = None

    def choose_move(self, mv):
        if not self.waiting:
            return
        st = self.style
        self.player_act_done(st)
        self.attack("ally", mv, st)
        self.style = "Normal"

    def attack(self, who, mv, st):
        att = self.ally if who == "ally" else self.wild
        dfn = self.wild if who == "ally" else self.ally
        mt, pw, acc, pp, kind = D.MOVES[mv]
        att.pp[mv] = max(0, att.pp.get(mv, pp) - (1 if st == "Normal" else 2))
        prefix = "" if who == "ally" else "Wild "
        tag = "" if st == "Normal" else "  (%s Style!)" % st
        node = self.ally_node if who == "ally" else self.wd.root
        tnode = self.wd.root if who == "ally" else self.ally_node
        tkey = "wild" if who == "ally" else "ally"

        def start():
            self.lunge = [node, Vec3(node.get_pos()), Vec3(tnode.get_pos()), 0.0]
            if st != "Normal":
                self.flash_text(st.upper() + "!", STYLE_COL[st])
        self.say("%s%s used %s!%s" % (prefix, att.name, mv, tag), 0.75, start)
        if kind == "heal":
            def heal():
                att.hp = min(att.maxhp, att.hp + int(att.maxhp * 0.4)); self.disp["ally" if who == "ally" else "wild"] = att.hp
                self.g.sfx("heal"); self.g.burst(node.get_pos() + Vec3(0, 0, 0.8), (0.6, 1, 0.6), 1.2, star=True)
            self.say("%s%s recovered HP!" % (prefix, att.name), 0.9, heal); return
        if kind == "boost":
            def boost():
                att.atk_boost = min(3, att.atk_boost + 1); self.g.burst(node.get_pos() + Vec3(0, 0, 0.8), (1, 0.6, 0.2), 1.0)
            self.say("%s%s's attack rose!" % (prefix, att.name), 0.9, boost); return
        if random.randint(1, 100) > acc:
            self.say("But it missed!", 0.8); return
        dmg, eff = D.damage(att, dfn, mv, st)

        def hit():
            dfn.hp = max(0, dfn.hp - dmg)
            self.g.burst(tnode.get_pos() + Vec3(0, 0, 0.7 * dfn.sp["size"]), D.TYPE_COL[mt], 1.3 + 0.5 * (eff > 1), star=eff > 1)
            self.g.sfx("super" if eff > 1 else "hit")
            self.float_dmg(tnode, "-%d" % dmg, (1, 0.3, 0.25, 1) if eff > 1 else (1, 1, 1, 1))
            self.hit_flash = [tnode, 0.3]
            if eff > 1:
                self.flash_text("Super effective!", (1, 0.85, 0.2, 1))
            elif eff < 1:
                self.flash_text("Not very effective...", (0.7, 0.8, 1, 1))
        self.call(hit, 0.7)
        self.call(lambda: self.check_faint(tkey))

    def check_faint(self, key):
        if key == "wild" and self.wild.hp <= 0:
            self.steps.clear()
            self.say("The wild %s fainted!" % self.wild.name, 1.0, lambda: self.wd.root.set_scale(self.wd.sp["size"] * 0.5))
            gain = int(self.wild.sp["xp"] * self.wild.level / 7) + 5
            self.say("%s gained %d XP!" % (self.ally.name, gain), 1.0)
            ups = self.ally.gain_xp(gain)
            if ups:
                self.say("%s grew to Lv %d!" % (self.ally.name, ups[-1]), 1.2, lambda: self.g.sfx("levelup"))
            for m in self.g.party:          # the rest of the team learns a little too
                if m is not self.ally and m.hp > 0:
                    m.gain_xp(gain // 3)
            self.call(lambda: self.finish("win"))
        elif key == "ally" and self.ally.hp <= 0:
            self.steps.clear()
            self.say("%s fainted!" % self.ally.name, 1.1, lambda: self.ally_node.set_scale(0.01))
            if any(m.hp > 0 for m in self.g.party):
                self.call(lambda: self._force_switch())
            else:
                self.say("You have no PIKNOTT left who can battle...", 1.4)
                self.call(lambda: self.finish("blackout"))

    def _force_switch(self):
        self.waiting = True; self.switch_menu(forced=True)

    def do_switch(self, i):
        forced = self.menu == "forced"
        old = self.ally.name
        self.ai = i
        if not forced:
            self.player_act_done("Normal")
        else:
            self.clear_menu(); self.waiting = False; self.menu = None
        self.say(("Come back, %s! " % old if not forced else "") + "Go, %s!" % self.ally.name, 0.9, self.spawn_ally)
        self.call(lambda: self.disp.__setitem__("ally", self.ally.hp))

    def use_potion(self):
        self.player_act_done("Normal")
        self.g.items["potion"] -= 1
        def heal():
            self.ally.hp = min(self.ally.maxhp, self.ally.hp + 30); self.g.sfx("heal")
            self.g.burst(self.ally_node.get_pos() + Vec3(0, 0, 0.8), (0.6, 1, 0.6), 1.2, star=True)
        self.say("You used a Potion on %s." % self.ally.name, 1.0, heal)

    def run(self):
        self.player_act_done("Normal")
        if self.wild.sid == 13 and random.random() < 0.5:
            self.say("Couldn't get away!", 0.9)
        else:
            self.say("You got away safely!", 0.8)
            self.call(lambda: self.finish("ran"))

    def throw_ball(self, kind):
        self.player_act_done("Normal")
        self.g.items[kind] -= 1; self.g.refresh_hud()
        name = dict((k, n) for k, n, _, _ in D.BALLS)[kind]
        self.say("You threw a %s!" % name, 0.2, lambda: self._launch(kind))
        self.steps.append((999, None, None))     # parked until the catch finishes

    def _launch(self, kind):
        from pc_game import Ball
        g = self.g
        start = g.hand_pos(); tgt = self.wd.root.get_pos() + Vec3(0, 0, 0.6 * self.wd.sp["size"])
        T = 0.7; v = (tgt - start) / T; v.z += 0.5 * 20 * T
        b = Ball(g, kind, start, v)
        g.throw_anim = 1.0; g.sfx("throw")
        self.flying = [b, T]

    def _caught_result(self, ok):
        if self.cur is not None and self.cur[0] == 999:
            self.cur = None
        if ok:
            self.wd = None
            self.call(lambda: self.finish("caught"))
        else:
            self.say("Argh! The wild %s broke free!" % self.wild.name, 1.0)

    # ------------------------------------------------------------------ wild AI
    def wild_turn(self):
        w = self.wild; a = self.ally
        opts = [m for m in w.sp["moves"] if w.pp.get(m, 0) > 0] or ["Tackle Hop"]
        def score(m):
            mt, pw, acc, pp, kind = D.MOVES[m]
            if kind == "heal":
                return 70 if w.hp < w.maxhp * 0.35 else 1
            if kind == "boost":
                return 25 if w.atk_boost < 1 else 2
            return pw * D.effectiveness(mt, a.types) * (1.5 if mt in w.types else 1) * acc / 100
        mv = max(opts, key=lambda m: score(m) * random.uniform(0.6, 1.4))
        if w.pp.get(mv, 0) < 2:
            st = "Normal"
        else:
            r = random.random()
            st = "Strong" if (r < 0.2 or a.hp < a.maxhp * 0.3 and r < 0.5) else ("Agile" if r > 0.8 else "Normal")
        self.next_t["wild"] += D.action_time(w, st)
        if mv not in w.pp:
            w.pp[mv] = D.MOVES[mv][3]
        self.attack("wild", mv, st)

    # ------------------------------------------------------------------ frame update
    def update(self, dt):
        if self.over:
            return
        # animations
        if self.wd is not None:
            self.wd.update(dt, 0, 0, 0)
        if self.ally_node:
            ph = globalClock.get_frame_time()
            self.ally_bob.set_z(abs(math.sin(ph * 2.5)) * 0.08 + (0.6 if self.ally.sp["model"] in ("bird", "moth") else 0))
        if self.lunge:
            n, a, b, t = self.lunge; t += dt; self.lunge[3] = t
            k = math.sin(min(1, t / 0.45) * math.pi) * 0.45
            if not n.is_empty():
                n.set_pos(a + (b - a) * k)
            if t >= 0.45:
                if not n.is_empty(): n.set_pos(a)
                self.lunge = None
        hf = getattr(self, "hit_flash", None)
        if hf:
            hf[1] -= dt
            if not hf[0].is_empty():
                hf[0].set_shader_input("flash", 0.8 if int(hf[1] * 20) % 2 == 0 and hf[1] > 0 else 0.0)
            if hf[1] <= 0:
                self.hit_flash = None
        for key, mon in (("wild", self.wild), ("ally", self.ally)):
            d = self.disp[key]
            if abs(d - mon.hp) > 0.01:
                self.disp[key] = d + max(-dt * mon.maxhp * 1.2, min(dt * mon.maxhp * 1.2, mon.hp - d))
        if self.flash_t > 0:
            self.flash_t -= dt
            self.flash.set_scale(1 + max(0, self.flash_t - 0.8) * 1.5)
            if self.flash_t <= 0:
                self.flash.setText("")
        fl = getattr(self, "flying", None)
        if fl:
            b, T = fl; b.update(dt)
            if b.t >= T - 0.02:
                self.flying = None
                self.g.begin_catch(b, self.wd, in_battle=True, on_done=self._caught_result)
        for ft in list(getattr(self, "floats", [])):
            ft[1] += dt; ft[0].set_z(ft[0].get_z() + dt * 1.2)
            if ft[1] > 1.0:
                ft[0].remove_node(); self.floats.remove(ft)
        self.refresh_hud_values()
        # step queue
        if self.waiting:
            return
        if self.cur is None and self.steps:
            self.cur = self.steps.pop(0); self.step_t = 0.0
            dur, text, fn = self.cur
            if text:
                self.msg.setText(text)
            if fn:
                fn()
            if self.over:
                return
        if self.cur is not None:
            self.step_t += dt
            if self.cur is not None and self.step_t >= self.cur[0]:
                self.cur = None
            return
        # decide the next actor from the action-order queue
        if self.next_t["ally"] <= self.next_t["wild"]:
            self.waiting = True; self.style = "Normal"; self.main_menu(); self.show_queue()
        else:
            self.wild_turn()

    def refresh_hud_values(self):
        try:
            self.refresh()
        except Exception:
            pass

    def flash_text(self, t, col):
        self.flash.setText(t); self.flash["fg"] = col; self.flash_t = 1.1

    def float_dmg(self, node, t, col):
        tn = TextNode("dmg"); tn.set_text(t); tn.set_align(TextNode.A_center); tn.set_text_color(*col)
        if U.FONT: tn.set_font(U.FONT)
        n = self.g.world_np.attach_new_node(tn); n.set_pos(node.get_pos() + Vec3(0, 0, 1.6)); n.set_scale(0.8)
        n.set_billboard_point_eye(); n.set_shader_off(); n.set_bin("fixed", 60); n.set_depth_test(False); n.set_depth_write(False)
        if not hasattr(self, "floats"): self.floats = []
        self.floats.append([n, 0.0])

    def update_camera(self, dt):
        cam = self.app.camera
        if self.wd is not None and not self.wd.root.is_empty():
            wp = self.wd.root.get_pos()
        else:
            wp = Point3(self.ally_pos[0] - self.dir[0] * 5, self.ally_pos[1] - self.dir[1] * 5, self.ally_node.get_z())
        ap = self.ally_node.get_pos()
        mid = (wp + ap) * 0.5
        perp = Vec3(-self.dir[1], self.dir[0], 0)
        span = (wp - ap).length()
        want = mid + perp * (span * 1.15 + 2.5) + Vec3(self.dir[0], self.dir[1], 0) * (span * 0.55) + Vec3(0, 0, 2.6 + span * 0.2)
        gz = self.g.region.ground(want.x, want.y) + 1.0
        if want.z < gz: want.z = gz
        if self.cam_pos is None:
            self.cam_pos = Vec3(cam.get_pos())
        self.cam_pos += (want - self.cam_pos) * min(1, dt * 3)
        cam.set_pos(self.cam_pos)
        cam.look_at(mid + Vec3(0, 0, 0.7))

    # ------------------------------------------------------------------ end
    def finish(self, result):
        if self.over:
            return
        self.over = True; self.steps.clear(); self.cur = None
        g = self.g
        if result == "win" and self.wd is not None:
            g.remove_wild(self.wd)
        elif result == "ran" and self.wd is not None:
            self.wd.state = "flee"; self.wd.t = 4; self.wd.root.set_scale(self.wd.sp["size"])
        elif result == "blackout" and self.wd is not None:
            self.wd.state = "wander"; self.wd.aware = 0
        for m in g.party:
            m.atk_boost = 0
        self.destroy()
        g.end_battle(result)

    def destroy(self):
        self.do.ignore_all()
        if self.ally_node:
            self.ally_node.remove_node(); self.ally_node = None
        for ft in getattr(self, "floats", []):
            ft[0].remove_node()
        self.ui.destroy()
        self.g.help_lbl.show(); self.g.status_lbl.show()
