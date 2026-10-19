"""Builds derived assets from assets/cover.jpg (icon + widescreen backdrop) and procedural SFX. Run once before packaging."""
import os, wave, numpy as np
from PIL import Image, ImageFilter, ImageEnhance
A = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
cov = Image.open(os.path.join(A, "cover.jpg")).convert("RGB")
w, h = cov.size; s = min(w, h)
sq = cov.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
sq.resize((256, 256), Image.LANCZOS).save(os.path.join(A, "icon.png"))
sq.save(os.path.join(A, "icon.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
# widescreen side-fill for the start screen (the cover itself is drawn unaltered on top of this)
bg = sq.resize((1920, 1920), Image.LANCZOS).crop((0, 420, 1920, 1500)).filter(ImageFilter.GaussianBlur(28))
ImageEnhance.Brightness(bg).enhance(0.55).save(os.path.join(A, "backdrop.jpg"), quality=88)

SR = 22050
def save(name, x):
    x = np.clip(x, -1, 1); d = (x * 30000).astype(np.int16)
    os.makedirs(os.path.join(A, "sfx"), exist_ok=True)
    with wave.open(os.path.join(A, "sfx", name + ".wav"), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(d.tobytes())
def t(dur): return np.linspace(0, dur, int(SR * dur), endpoint=False)
def env(n, a=0.01, r=0.3):
    e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    return e * np.exp(-np.linspace(0, 1, n) / r)
rng = np.random.default_rng(7)
x = t(0.35); save("throw", rng.standard_normal(len(x)) * env(len(x), 0.05, 0.35) * 0.4 * np.sin(np.pi * x / 0.35))
x = t(0.18); save("wobble", np.sin(2 * np.pi * (300 + 120 * np.sin(40 * x)) * x) * env(len(x), 0.005, 0.25) * 0.6)
x = t(0.9); f = np.where(x < 0.15, 660, np.where(x < 0.3, 880, 1320))
save("catch", (np.sin(2 * np.pi * f * x) * 0.5 + 0.3 * np.sin(4 * np.pi * f * x)) * env(len(x), 0.01, 0.5))
x = t(0.5); save("breakout", (np.sin(2 * np.pi * (500 - 600 * x) * x) * 0.6 + rng.standard_normal(len(x)) * 0.2) * env(len(x), 0.005, 0.25))
x = t(0.25); save("hit", (rng.standard_normal(len(x)) * 0.7 + np.sin(2 * np.pi * 90 * x) * 0.6) * env(len(x), 0.002, 0.12))
x = t(0.4); save("super", (np.sin(2 * np.pi * 220 * x) + np.sin(2 * np.pi * 330 * x)) * 0.35 * env(len(x), 0.002, 0.3) + rng.standard_normal(len(x)) * 0.3 * env(len(x), 0.001, 0.08))
x = t(0.08); save("click", np.sin(2 * np.pi * 1200 * x) * env(len(x), 0.001, 0.2) * 0.4)
x = t(1.0); save("levelup", sum(np.sin(2 * np.pi * fr * x) * (x > d0) for fr, d0 in ((523, 0), (659, 0.15), (784, 0.3), (1046, 0.45))) * 0.2 * env(len(x), 0.01, 0.6))
x = t(0.6); save("heal", np.sin(2 * np.pi * (600 + 600 * x) * x) * 0.4 * env(len(x), 0.05, 0.5))
x = t(0.3); save("alert", np.sin(2 * np.pi * 1000 * x) * (np.sin(2 * np.pi * 14 * x) > 0) * env(len(x), 0.005, 0.4) * 0.4)
print("assets ok")
