"""PIKNOTT CELESTIKA - a cel-shaded monster catching RPG. (c)2026 EX Inc./HYPERION DIGITAL (c)2026"""
import os, sys, json, time, math, random, threading, tempfile, urllib.request, shutil, traceback

APP_NAME = "PIKNOTT CELESTIKA"
APP_VERSION = "1.0.1"
REPO = "Teobokki/piknott-celestika"
UPDATE_URL = "https://raw.githubusercontent.com/%s/main/latest.json" % REPO
RELEASES_URL = "https://github.com/%s/releases/latest" % REPO
COPYRIGHT = "\u00a92026 EX Inc./HYPERION DIGITAL \u00a92026"

BASE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
if os.environ.get("PC_DATA_DIR"):
    DATA = os.environ["PC_DATA_DIR"]
elif os.name == "nt":
    DATA = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), APP_NAME)
else:
    DATA = os.path.join(os.path.expanduser("~"), ".piknott-celestika")
os.makedirs(DATA, exist_ok=True)


def log_error(msg):
    try:
        with open(os.path.join(DATA, "error.log"), "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except Exception:
        pass


from panda3d.core import loadPrcFileData, Filename
_icon = os.path.join(BASE, "assets", "icon.ico")
loadPrcFileData("", """
window-title PIKNOTT CELESTIKA
win-size 1280 720
sync-video true
audio-library-name p3openal_audio
textures-power-2 none
framebuffer-multisample 0
notify-level warning
default-directnotify-level warning
load-display pandagl
want-pstats false
""")
if os.path.exists(_icon):
    loadPrcFileData("", "icon-filename " + Filename.from_os_specific(_icon).get_fullpath())

from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectSlider, DGG
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui import DirectGuiGlobals
from panda3d.core import TextNode, TransparencyAttrib, WindowProperties
import pc_ui as U
import pc_toon


def vtuple(v):
    out = []
    for p in str(v).strip().lstrip("vV").split("."):
        n = "".join(ch for ch in p if ch.isdigit())
        out.append(int(n) if n else 0)
    return tuple(out + [0] * (3 - len(out)))


def is_portable():
    """True for the single-file portable build, False for the installed/onedir copy or source."""
    if not getattr(sys, "frozen", False) or not hasattr(sys, "_MEIPASS"):
        return False
    exe = os.path.normcase(os.path.abspath(sys.executable))
    meipass = os.path.normcase(os.path.abspath(sys._MEIPASS))
    if meipass.startswith(os.path.dirname(exe) + os.sep):
        return False
    la = os.environ.get("LOCALAPPDATA")
    if la and exe.startswith(os.path.normcase(os.path.join(la, "Programs", APP_NAME)) + os.sep):
        return False
    return True


def check_update():
    req = urllib.request.Request(UPDATE_URL + "?t=%d" % time.time(), headers={"User-Agent": "PIKNOTT-CELESTIKA/" + APP_VERSION})
    m = json.loads(urllib.request.urlopen(req, timeout=10).read(65536).decode("utf-8"))
    ver = str(m["version"])
    if vtuple(ver) > vtuple(APP_VERSION):
        if is_portable() and m.get("portable_url"):
            return "newer", {"version": ver, "notes": m.get("notes", ""), "link": m["portable_url"], "portable": True}
        return "newer", {"version": ver, "notes": m.get("notes", ""), "link": m.get("installer_url") or m.get("url") or RELEASES_URL}
    return "latest", "You have the latest version (%s)." % APP_VERSION


DEFAULT_SETTINGS = {"sensitivity": 1.0, "invert_y": False, "fullscreen": False, "sfx_volume": 0.8}


class App(ShowBase):
    VERSION = APP_VERSION
    BASE = BASE

    def __init__(self):
        ShowBase.__init__(self)
        self.disable_mouse()
        self.log_error = log_error
        self.settings = dict(DEFAULT_SETTINGS)
        try:
            self.settings.update(json.load(open(os.path.join(DATA, "settings.json"), encoding="utf-8")))
        except Exception:
            pass
        U.init_fonts(self.loader, os.path.join(BASE, "assets", "ui_font.ttf"))
        U.SFX = lambda n: self.sfx(n, 0.5)
        DirectGuiGlobals.setDefaultClickSound(None); DirectGuiGlobals.setDefaultRolloverSound(None)
        self.set_background_color(0.84, 0.89, 0.96, 1)
        pc_toon.setup_root(self.render, fog=(0.84, 0.89, 0.96), fog_far=320.0)
        self.camLens.set_fov(72); self.camLens.set_near_far(0.1, 1300)
        self._sfx = {}
        for n in ("throw", "wobble", "catch", "breakout", "hit", "super", "click", "levelup", "heal", "alert"):
            try:
                self._sfx[n] = self.loader.load_sfx(Filename.from_os_specific(os.path.join(BASE, "assets", "sfx", n + ".wav")))
            except Exception:
                pass
        self.tex_cover = self.loader.load_texture(Filename.from_os_specific(os.path.join(BASE, "assets", "cover.jpg")))
        self.tex_backdrop = self.loader.load_texture(Filename.from_os_specific(os.path.join(BASE, "assets", "backdrop.jpg")))
        self.game = None; self.screen = None; self.overlay = None; self._bgh = None; self.pause_ui = None
        self._upd_result = None
        self.apply_fullscreen()
        self.exitFunc = self.on_exit
        self.accept("window-event", self._on_window_event)
        self.show_start()
        if os.environ.get("PC_AUTOPLAY"):
            self.do_method_later(0.5, lambda t: self.new_game(force=True), "autoplay")
        ts = os.environ.get("PC_TESTSCRIPT")
        if ts and not getattr(sys, "frozen", False):
            self.do_method_later(float(os.environ.get("PC_TESTDELAY", "3")),
                                 lambda t: exec(open(ts).read(), {"app": self, "__name__": "pctest"}) or t.done, "pc-test")

    # ---------------------------------------------------------------- helpers
    def sfx(self, name, vol=1.0):
        s = self._sfx.get(name)
        if s:
            s.set_volume(vol * float(self.settings.get("sfx_volume", 0.8))); s.play()

    def save_path(self):
        return os.path.join(DATA, "save.json")

    def has_save(self):
        return os.path.exists(self.save_path())

    def save_settings(self):
        try:
            json.dump(self.settings, open(os.path.join(DATA, "settings.json"), "w", encoding="utf-8"), indent=1)
        except Exception as e:
            log_error("settings: %r" % e)

    def apply_fullscreen(self):
        wp = WindowProperties()
        if self.settings.get("fullscreen"):
            wp.set_fullscreen(True); wp.set_size(self.pipe.get_display_width(), self.pipe.get_display_height())
        else:
            wp.set_fullscreen(False); wp.set_size(1280, 720)
        if self.win:
            self.win.request_properties(wp)

    def _on_window_event(self, win):
        if win and win.is_closed():
            self.userExit()

    def on_exit(self):
        if self.game:
            try:
                self.game.save()
            except Exception as e:
                log_error("save on exit: %r" % e)

    def clear_screen(self):
        if self.screen:
            self.screen.destroy(); self.screen = None

    def new_screen(self, dim=0.0):
        self.clear_screen()
        self.screen = DirectFrame(parent=self.aspect2d, frameColor=(0, 0, 0, dim), frameSize=(-4, 4, -2, 2))
        return self.screen

    def show_art(self, on=True):
        """Start/menu backdrop: blurred widescreen side-fill, then the cover art unaltered, centred at full height."""
        if on and getattr(self, "_bgh", None) is None:
            ar = max(self.getAspectRatio(), 1.0)
            self._bgh = self.aspect2d.attach_new_node("art"); self._bgh.set_bin("background", 0)
            OnscreenImage(parent=self._bgh, image=self.tex_backdrop, pos=(0, 0, 0), scale=(ar, 1, 1))
            OnscreenImage(parent=self._bgh, image=self.tex_cover, pos=(0, 0, 0), scale=(1, 1, 1))
        elif not on and getattr(self, "_bgh", None) is not None:
            self._bgh.remove_node(); self._bgh = None

    # ---------------------------------------------------------------- start screen
    def show_start(self):
        self.show_art(True)
        s = self.new_screen(0.0)
        b = U.button(s, "PRESS PLAY", (0, -0.80), self.show_menu, w=0.36, h=0.085, col=(1.0, 0.80, 0.10, 1), scale=0.085)
        self._pp = b
        self._pk = U.text(s, "Press any key", (0, -0.94), 0.045, (1, 1, 1, 1))
        self.task_mgr.add(self._pulse, "pp-pulse")
        self.buttonThrowers[0].node().set_button_down_event("pc-anykey")
        self.accept("pc-anykey", self._anykey)
        ar = self.getAspectRatio()
        U.text(s, "v" + APP_VERSION, (-ar + 0.03, -0.96), 0.04, (1, 1, 1, 1), TextNode.A_left)
        U.text(s, COPYRIGHT, (ar - 0.03, -0.96), 0.04, (1, 1, 1, 1), TextNode.A_right)

    def _anykey(self, btn):
        if btn.startswith("mouse") or btn.startswith("wheel"):
            return
        self.show_menu()

    def _pulse(self, task):
        if not getattr(self, "_pp", None) or self._pp.is_empty():
            return task.done
        k = 1 + 0.07 * math.sin(task.time * 5)
        self._pp.set_scale(k)
        self._pk["fg"] = (1, 1, 1, 0.55 + 0.45 * abs(math.sin(task.time * 2.5)))
        return task.cont

    # ---------------------------------------------------------------- main menu
    def show_menu(self):
        self.ignore("pc-anykey"); self._pp = None
        self.show_art(True)
        s = self.new_screen(0.0)
        ar = self.getAspectRatio()
        x = (1.0 + ar) / 2 if ar > 1.5 else 0.0
        U.panel(s, -0.36, 0.36, -0.62, 0.62, (0.08, 0.09, 0.16, 0.88), 0.016, (x, -0.05))
        U.text(s, "PIKNOTT", (x, 0.43), 0.09, (1.0, 0.82, 0.12, 1))
        U.text(s, "CELESTIKA", (x, 0.34), 0.065, (1, 1, 1, 1))
        items = [("New Game", self.new_game, (1.0, 0.80, 0.12, 1), True),
                 ("Continue", self.continue_game, (0.35, 0.80, 0.40, 1), self.has_save()),
                 ("Settings", lambda: self.open_settings(self.show_menu), (0.30, 0.62, 1.0, 1), True),
                 ("Check for updates", self.start_update_check, (0.62, 0.40, 0.95, 1), True),
                 ("Quit", self.userExit, (0.90, 0.30, 0.25, 1), True)]
        for i, (t, c, col, en) in enumerate(items):
            U.button(s, t, (x, 0.18 - i * 0.15), c, w=0.29, h=0.055, col=col, scale=0.05, enabled=en)
        U.text(s, "v" + APP_VERSION, (-ar + 0.03, -0.96), 0.04, (1, 1, 1, 1), TextNode.A_left)
        U.text(s, COPYRIGHT, (ar - 0.03, -0.96), 0.04, (1, 1, 1, 1), TextNode.A_right)

    def new_game(self, force=False):
        if self.has_save() and not force:
            self._dialog("Start a new adventure?\nYour current save will be replaced.", [("New Game", lambda: (self._close_dialog(), self.new_game(True))), ("Cancel", self._close_dialog)])
            return
        try:
            if os.path.exists(self.save_path()):
                shutil.copy(self.save_path(), self.save_path() + ".bak")
        except Exception:
            pass
        self.start_game(None)

    def continue_game(self):
        try:
            d = json.load(open(self.save_path(), encoding="utf-8"))
        except Exception as e:
            log_error("load: %r" % e)
            self._dialog("Could not load the save file.", [("OK", self._close_dialog)]); return
        self.start_game(d)

    def start_game(self, save):
        self.task_mgr.remove("pp-pulse"); self.ignore("pc-anykey")
        s = self.new_screen(1.0); s["frameColor"] = (0.06, 0.07, 0.12, 1)
        self.show_art(False)
        U.text(s, "Travelling to the Celestika region...", (0, 0.05), 0.07, (1, 0.85, 0.2, 1))
        U.text(s, "Tip: crouch (C) in tall grass and throw from behind for a catch bonus!", (0, -0.1), 0.045, (0.9, 0.9, 0.95, 1))
        def go(task):
            from pc_game import Game
            try:
                self.game = Game(self, save)
            except Exception:
                log_error(traceback.format_exc()); raise
            self.clear_screen()
            return task.done
        self.do_method_later(0.15, go, "start-game")

    def quit_to_title(self):
        if self.game:
            self.game.save(); self.game.destroy(); self.game = None
        self.hide_pause()
        self.accept("window-event", self._on_window_event)
        self.camera.set_pos(0, 0, 0)
        self.show_start()

    # ---------------------------------------------------------------- pause
    def show_pause(self):
        if not self.game or self.pause_ui:
            return
        g = self.game; g.paused = True; g.capture_mouse(False)
        o = self.pause_ui = DirectFrame(parent=self.aspect2d, frameColor=(0, 0, 0, 0.6), frameSize=(-4, 4, -2, 2))
        U.panel(o, -0.45, 0.45, -0.55, 0.55, (0.08, 0.09, 0.16, 0.95), 0.016)
        U.text(o, "PAUSED", (0, 0.4), 0.08, (1, 0.85, 0.2, 1))
        for i, (t, c, col) in enumerate((("Resume", self.hide_pause, (0.35, 0.8, 0.4, 1)), ("Save", self._pause_save, (0.3, 0.62, 1, 1)),
                                         ("Settings", lambda: self.open_settings(None), (0.62, 0.4, 0.95, 1)),
                                         ("Quit to Title", self.quit_to_title, (0.9, 0.3, 0.25, 1)))):
            U.button(o, t, (0, 0.2 - i * 0.16), c, w=0.3, h=0.055, col=col, scale=0.05)
        self.accept("escape", self.hide_pause)

    def _pause_save(self):
        self.game.save()
        self._dialog("Game saved.", [("OK", self._close_dialog)])

    def hide_pause(self):
        if self.pause_ui:
            self.pause_ui.destroy(); self.pause_ui = None
        if self.game:
            self.game.paused = False
            if self.game.mode == "explore" and not self.game.overlay:
                self.game.capture_mouse(True)
            self.accept("escape", self.game.on_escape)

    # ---------------------------------------------------------------- settings
    def open_settings(self, back):
        o = DirectFrame(parent=self.aspect2d, frameColor=(0, 0, 0, 0.7), frameSize=(-4, 4, -2, 2))
        U.panel(o, -0.8, 0.8, -0.7, 0.7, (0.08, 0.09, 0.16, 0.97), 0.016)
        U.text(o, "SETTINGS", (0, 0.55), 0.08, (1, 0.85, 0.2, 1))
        st = self.settings
        def slider(label, key, rng, z, fmt):
            t = U.text(o, "", (0, z + 0.06), 0.05)
            def upd():
                st[key] = round(float(sl["value"]), 2); t.setText(label + ": " + fmt(st[key]))
            sl = DirectSlider(parent=o, range=rng, value=st[key], pageSize=0.05, scale=0.5, pos=(0, 0, z - 0.02),
                              frameColor=(0.3, 0.3, 0.35, 1), thumb_frameColor=(1, 0.82, 0.15, 1), command=upd)
            upd()
        slider("Mouse Sensitivity", "sensitivity", (0.2, 3.0), 0.32, lambda v: "%d%%" % round(v * 100))
        slider("Sound Effects", "sfx_volume", (0.0, 1.0), 0.10, lambda v: "%d%%" % round(v * 100))
        def tog(key, lbl):
            def f():
                st[key] = not st[key]; b.btn["text"] = "%s: %s" % (lbl, "ON" if st[key] else "OFF")
                if key == "fullscreen": self.apply_fullscreen()
            b = U.button(o, "%s: %s" % (lbl, "ON" if st[key] else "OFF"), (0, 0), f, w=0.3, h=0.05, col=(0.3, 0.62, 1, 1), scale=0.045)
            return b
        tog("invert_y", "Invert camera Y").set_pos(0, 0, -0.12)
        tog("fullscreen", "Fullscreen").set_pos(0, 0, -0.26)
        def done():
            self.save_settings(); o.destroy()
            if back: back()
        U.button(o, "Done", (0, -0.55), done, w=0.2, h=0.055, col=(0.35, 0.8, 0.4, 1), scale=0.05)

    # ---------------------------------------------------------------- dialogs / updates
    def _dialog(self, msg, buttons):
        self._close_dialog()
        o = self.overlay = DirectFrame(parent=self.aspect2d, frameColor=(0, 0, 0, 0.6), frameSize=(-4, 4, -2, 2))
        U.panel(o, -0.9, 0.9, -0.38, 0.38, (0.08, 0.09, 0.16, 0.97), 0.016)
        U.text(o, msg, (0, 0.2), 0.05, wrap=30)
        n = len(buttons)
        for i, (t, c) in enumerate(buttons):
            U.button(o, t, ((i - (n - 1) / 2) * 0.62, -0.25), c, w=0.28, h=0.05, scale=0.042)

    def _close_dialog(self):
        if self.overlay:
            self.overlay.destroy(); self.overlay = None

    def start_update_check(self):
        self._dialog("Checking for updates...", [])
        def work():
            try:
                self._upd_result = check_update()
            except Exception as e:
                self._upd_result = ("error", "Could not check for updates.\n(%s)" % (str(e)[:90]))
        threading.Thread(target=work, daemon=True).start()
        self.task_mgr.add(self._poll_update, "poll-update")

    def _poll_update(self, task):
        r = self._upd_result
        if r is None:
            return task.cont
        self._upd_result = None
        kind, data = r
        if kind == "newer":
            self._dialog("PIKNOTT CELESTIKA %s is available!\n%s\n\nDownload and install it now?" % (data["version"], data["notes"][:160]),
                         [("Download & Install", lambda: (self.download_portable(data["link"]) if data.get("portable") else self.download_install(data["link"]))),
                          ("Not now", self._close_dialog)])
        else:
            self._dialog(data, [("OK", self._close_dialog)])
        return task.done

    def download_install(self, link):
        if not link.lower().endswith(".exe"):
            self._open_browser(link); return
        self._dialog("Downloading update...", [])
        def work():
            try:
                dst = os.path.join(tempfile.gettempdir(), os.path.basename(link.split("?")[0]) or "PIKNOTT.CELESTIKA.Setup.exe")
                req = urllib.request.Request(link, headers={"User-Agent": "PIKNOTT-CELESTIKA/" + APP_VERSION})
                with urllib.request.urlopen(req, timeout=60) as r, open(dst, "wb") as f:
                    shutil.copyfileobj(r, f)
                self._upd_result = ("install", dst)
            except Exception as e:
                self._upd_result = ("dlerror", (link, str(e)[:90]))
        threading.Thread(target=work, daemon=True).start()
        self.task_mgr.add(self._poll_download, "poll-dl")

    def _poll_download(self, task):
        r = self._upd_result
        if r is None:
            return task.cont
        self._upd_result = None
        if r[0] == "install":
            try:
                os.startfile(r[1]); self.userExit()
            except Exception as e:
                self._dialog("Could not start the installer:\n%s" % e, [("Open download page", lambda: self._open_browser(RELEASES_URL)), ("Close", self._close_dialog)])
        else:
            self._dialog("Download failed.\n%s" % r[1][1], [("Open download page", lambda: self._open_browser(RELEASES_URL)), ("Close", self._close_dialog)])
        return task.done

    # ---- portable self-update: download <exe>.new next to the exe, swap it in with a helper script after we exit
    def download_portable(self, link):
        exe = os.path.abspath(sys.executable)
        new = exe + ".new"
        self._dialog("Downloading portable update...", [])
        def work():
            try:
                req = urllib.request.Request(link, headers={"User-Agent": "PIKNOTT-CELESTIKA/" + APP_VERSION})
                with urllib.request.urlopen(req, timeout=60) as r, open(new, "wb") as f:
                    shutil.copyfileobj(r, f)
                with open(new, "rb") as f:
                    ok = f.read(2) == b"MZ"
                if not ok or os.path.getsize(new) < 5_000_000:
                    os.remove(new)
                    raise IOError("downloaded file is not a valid PIKNOTT CELESTIKA executable")
                self._upd_result = ("swap", new)
            except Exception as e:
                try:
                    if os.path.exists(new): os.remove(new)
                except OSError:
                    pass
                self._upd_result = ("dlerror", (link, str(e)[:90]))
        threading.Thread(target=work, daemon=True).start()
        self.task_mgr.add(self._poll_portable, "poll-dl")

    def _poll_portable(self, task):
        r = self._upd_result
        if r is None:
            return task.cont
        self._upd_result = None
        if r[0] == "swap":
            try:
                self._launch_swap_helper(os.path.abspath(sys.executable), r[1]); self.userExit()
            except Exception as e:
                log_error("portable update: %r" % e)
                self._dialog("Could not apply the update:\n%s" % str(e)[:90], [("Open download page", lambda: self._open_browser(RELEASES_URL)), ("Close", self._close_dialog)])
        else:
            self._dialog("Download failed.\n%s" % r[1][1], [("Open download page", lambda: self._open_browser(RELEASES_URL)), ("Close", self._close_dialog)])
        return task.done

    def _launch_swap_helper(self, exe, new):
        """Write a small .bat that waits for this game to close, replaces the exe (same name/path), relaunches it and deletes itself."""
        import subprocess
        pids = [os.getpid()]
        try:
            pids.append(os.getppid())        # onefile bootloader process that holds the exe open
        except Exception:
            pass
        bat = os.path.join(tempfile.gettempdir(), "piknott_update_%d.bat" % os.getpid())
        lines = ["@echo off", "setlocal EnableDelayedExpansion", "set N=0"]
        for p in pids:
            lines += [":w%d" % p,
                      'tasklist /FI "PID eq %d" 2>NUL | find " %d " >NUL' % (p, p),
                      "if not errorlevel 1 (ping -n 2 127.0.0.1 >NUL & set /a N+=1 & if !N! LSS 120 goto w%d)" % p]
        lines += ["set T=0", ":swap",
                  'move /Y "%s" "%s" >NUL 2>&1' % (new, exe),
                  "if errorlevel 1 (ping -n 2 127.0.0.1 >NUL & set /a T+=1 & if !T! LSS 60 goto swap)",
                  'start "" "%s"' % exe,
                  '(goto) 2>NUL & del "%~f0"']
        with open(bat, "w", encoding="mbcs" if os.name == "nt" else "utf-8") as f:
            f.write("\r\n".join(lines) + "\r\n")
        flags = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(["cmd.exe", "/c", bat], creationflags=flags, close_fds=True, cwd=os.path.dirname(exe),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _open_browser(self, url):
        import webbrowser
        webbrowser.open(url); self._close_dialog()


def main():
    try:
        App().run()
    except SystemExit:
        raise
    except Exception:
        log_error(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
