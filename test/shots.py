# scripted screenshot tour (dev only, event-driven).  app = App instance
import os, math
from panda3d.core import Filename, Vec3
OUT = os.environ.get("PC_SHOTS", "/workspace/piknott-celestika/docs")
S = {"i": 0, "t": 0.0}
def shot(name):
    app.win.save_screenshot(Filename.from_os_specific(os.path.join(OUT, name)))
    print("SHOT", name, flush=True)
G = lambda: app.game
def aim():
    g = G(); w = min([w for w in g.wilds if w.sp["id"] != 1], key=lambda w: math.hypot(w.x - g.x, w.y - g.y))
    w.state = "frozen"; S["w"] = w
    g.x, g.y = w.x, w.y - 7; g.z = g.region.height(g.x, g.y)
    g.cam_yaw = 0.0; g.cam_pitch = -6; w.h = 0.0          # wild faces away -> back strike
    g.set_aim(True)
def throw():
    g = G(); g.set_aim(False); w = S["w"]
    from pc_game import Ball
    s = g.hand_pos(); t = Vec3(w.x, w.y, w.z + 0.5); T = 0.6
    v = (Vec3(t) - Vec3(s)) / T; v.z += 0.5 * 20 * T
    g.items["astral"] -= 1; g.balls.append(Ball(g, "astral", s, v)); g.throw_anim = 1
def battle():
    g = G(); g.close_overlay()
    w = min([w for w in g.wilds if w.state != "caught"], key=lambda w: math.hypot(w.x - g.x, w.y - g.y))
    g.party[0].level = 7; g.party[0].recalc(); g.party[0].hp = g.party[0].maxhp
    g.start_battle(w)
def fight():
    b = G().battle; b.move_menu(); b.set_style("Strong")
def go():
    b = G().battle; b.choose_move(G().party[b.ai].sp["moves"][2])
def auto():  # keep battling with agile moves until it ends
    b = G().battle
    if b and b.waiting and b.menu in ("main", "moves"):
        b.set_style("Agile"); b.choose_move(G().party[b.ai].sp["moves"][1])
    elif b and b.waiting and b.menu == "forced":
        b.do_switch(next(i for i, m in enumerate(G().party) if m.hp > 0))
PLAN = [
    (lambda: True, lambda: shot("screenshot_start.png"), 0.5),
    (lambda: True, app.show_menu, 0.8),
    (lambda: True, lambda: shot("screenshot_menu.png"), 0.2),
    (lambda: True, lambda: app.new_game(force=True), 0.5),
    (lambda: G() is not None, lambda: setattr(G(), "cam_yaw", 20.0), 2.0),
    (lambda: True, lambda: shot("screenshot_overworld.png"), 0.2),
    (lambda: True, lambda: (setattr(G(), "h", -90.0), setattr(G(), "cam_yaw", 90.0), setattr(G(), "cam_pitch", -8.0), setattr(G(), "cam_dist", 4.0)), 1.0),
    (lambda: True, lambda: (shot("screenshot_boy.png"), setattr(G(), "cam_dist", 7.5)), 0.3),
    (lambda: True, aim, 1.2),
    (lambda: True, lambda: shot("screenshot_aim.png"), 0.1),
    (lambda: True, throw, 1.3),
    (lambda: True, lambda: shot("screenshot_catch_wobble.png"), 0.1),
    (lambda: G().catching is None, lambda: None, 0.3),
    (lambda: True, lambda: shot("screenshot_catch_result.png"), 0.2),
    (lambda: True, lambda: G().toggle_dok(2), 0.6),
    (lambda: True, lambda: shot("screenshot_celestika_dok.png"), 0.2),
    (lambda: True, lambda: (G().close_overlay(), G().toggle_map()), 0.6),
    (lambda: True, lambda: shot("screenshot_map.png"), 0.2),
    (lambda: True, lambda: (G().close_overlay(), G().toggle_party()), 0.6),
    (lambda: True, lambda: shot("screenshot_team.png"), 0.2),
    (lambda: True, battle, 0.5),
    (lambda: G().battle and G().battle.waiting, fight, 0.8),
    (lambda: True, lambda: shot("screenshot_battle.png"), 0.1),
    (lambda: True, go, 1.1),
    (lambda: True, lambda: shot("screenshot_battle_hit.png"), 0.1),
    (lambda: (auto() or True) and G().battle is None, lambda: None, 1.5),
    (lambda: True, lambda: shot("screenshot_after_battle.png"), 0.2),
    (lambda: True, lambda: (G().save(), print("SAVED", os.path.exists(app.save_path()), flush=True)), 0.2),
    (lambda: True, app.quit_to_title, 1.0),
    (lambda: True, app.continue_game, 0.5),
    (lambda: G() is not None, lambda: print("CONTINUED party", [m.name for m in G().party], flush=True), 1.0),
    (lambda: True, app.userExit, 0),
]
def runner(task):
    if S["i"] >= len(PLAN):
        return task.done
    cond, act, wait = PLAN[S["i"]]
    if S["t"] > 0:
        S["t"] -= globalClock.get_dt(); return task.cont
    try:
        ok = cond()
    except Exception as e:
        ok = False
    if ok:
        act(); S["t"] = wait; S["i"] += 1
    return task.cont
app.task_mgr.add(runner, "test-runner")
