"""Flat, thick-outlined UI helpers (cel-style)."""
from direct.gui.DirectGui import DirectFrame, DirectButton, DGG
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, Vec4

INK = (0.04, 0.04, 0.08, 1)
FONT = None
FONT_PLAIN = None
SFX = None


def init_fonts(loader, path):
    global FONT, FONT_PLAIN
    from panda3d.core import Filename
    try:
        FONT = loader.load_font(Filename.from_os_specific(path).get_fullpath())
        FONT.set_pixels_per_unit(96)
        FONT.set_outline(Vec4(0.04, 0.04, 0.08, 1), 0.2, 0.0)
        FONT_PLAIN = loader.load_font(Filename.from_os_specific(path).get_fullpath())
        FONT_PLAIN.set_pixels_per_unit(64)
    except Exception:
        FONT = FONT_PLAIN = None


def panel(parent, l, r, b, t, col=(0.97, 0.94, 0.86, 0.97), border=0.012, pos=(0, 0)):
    outer = DirectFrame(parent=parent, frameColor=INK, frameSize=(l - border, r + border, b - border, t + border),
                        pos=(pos[0], 0, pos[1]), relief=DGG.FLAT)
    outer.inner = DirectFrame(parent=outer, frameColor=col, frameSize=(l, r, b, t), relief=DGG.FLAT)
    return outer


def text(parent, t, pos, scale=0.05, fg=(1, 1, 1, 1), align=TextNode.A_center, outline=True, wrap=None):
    o = OnscreenText(parent=parent, text=t, pos=pos, scale=scale, fg=fg, align=align, mayChange=True,
                     font=(FONT if outline else FONT_PLAIN) or None, wordwrap=wrap)
    return o


def button(parent, label, pos, cmd, w=0.3, h=0.055, col=(1.0, 0.82, 0.18, 1), scale=0.05, fg=(1, 1, 1, 1), extra=None, enabled=True):
    b = 0.012
    outer = DirectFrame(parent=parent, frameColor=INK, frameSize=(-w - b, w + b, -h - b, h + b), pos=(pos[0], 0, pos[1]), relief=DGG.FLAT)
    c = Vec4(*col)
    hi = Vec4(min(1, c[0] * 1.15 + 0.08), min(1, c[1] * 1.15 + 0.08), min(1, c[2] * 1.15 + 0.08), 1)
    dn = Vec4(c[0] * 0.8, c[1] * 0.8, c[2] * 0.8, 1)
    dis = Vec4(0.45, 0.45, 0.48, 1)

    def clicked(*a):
        if SFX:
            SFX("click")
        if cmd:
            cmd(*(extra or []))
    btn = DirectButton(parent=outer, text=label, text_scale=scale, text_fg=fg, text_font=FONT or None,
                       text_pos=(0, -scale * 0.33), frameSize=(-w, w, -h, h), frameColor=(c, dn, hi, dis),
                       relief=DGG.FLAT, command=clicked, pressEffect=1, rolloverSound=None, clickSound=None)
    if not enabled:
        btn["state"] = DGG.DISABLED
    outer.btn = btn
    return outer


def bar(parent, pos, w, h, frac, col=(0.3, 0.9, 0.35, 1)):
    """Flat outlined bar; returns (outer, fill) - update fill.set_sx(frac)."""
    outer = DirectFrame(parent=parent, frameColor=INK, frameSize=(-0.008, w + 0.008, -h - 0.008, h + 0.008), pos=(pos[0], 0, pos[1]))
    DirectFrame(parent=outer, frameColor=(0.25, 0.22, 0.25, 1), frameSize=(0, w, -h, h))
    fill = DirectFrame(parent=outer, frameColor=col, frameSize=(0, w, -h, h))
    fill.set_sx(max(0.001, frac))
    return outer, fill


def hp_col(f):
    return (0.30, 0.88, 0.35, 1) if f > 0.5 else ((1.0, 0.80, 0.15, 1) if f > 0.2 else (0.95, 0.25, 0.2, 1))
