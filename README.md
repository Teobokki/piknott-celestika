# PIKNOTT CELESTIKA

A fully cel-shaded monster-catching RPG for Windows. Explore the Celestika region as a boy in a red hoodie, sneak through tall grass, throw **PIKCEL balls** to catch wild **PIKNOTT**, and battle them with your team using a Legends-Arceus-style action-order system with **Normal / Strong / Agile** move styles.

©2026 EX Inc./HYPERION DIGITAL ©2026. Publisher: EX Inc./HYPERION DIGITAL. Version 1.0.0.

## Download
See [Releases](https://github.com/Teobokki/piknott-celestika/releases/latest):
- `PIKNOTT.CELESTIKA.Setup.1.0.0.exe`: installer (goes to `%LOCALAPPDATA%\Programs\PIKNOTT CELESTIKA`, with desktop and Start-menu shortcuts)
- `PIKNOTT.CELESTIKA.Portable.exe`: a single-file portable build that updates itself
- `PIKNOTT.CELESTIKA.1.0.0.Windows.x64.zip`: the plain onedir build

Saves go to `%APPDATA%\PIKNOTT CELESTIKA\save.json`.

## Controls
| Action | Key |
|---|---|
| Move / run / jump | WASD or arrows / Shift / Space |
| Camera | Mouse |
| Crouch / sneak | C or Ctrl (you're hidden when crouching in tall grass) |
| Aim / throw PIKCEL ball | Hold right mouse / left click |
| Pick ball | 1-3 or the mouse wheel |
| Send out your PIKNOTT (starts a battle) | G |
| Team / CELESTIKA DOK / region map | Tab / P / M |
| Rest and heal at the camp fire | E |
| Menu | Esc |
| Battle: styles | Z Normal, X Strong, C Agile; 1-4 pick a move |

Gamepad (basic): left stick moves, right stick turns the camera, A jumps, LT aims, RB throws, X sends out your PIKNOTT, B crouches.

## Build
- Engine: Python 3 + Panda3D 1.10, with custom GLSL toon shaders (3-step ramp) and inverted-hull ink outlines
- `blender -b -P blender/pikcel_balls.py` models the three PIKCEL balls, exports `assets/models/*.glb` and renders `docs/pikcel_balls_render.png`. Then convert with `gltf2bam` (panda3d-gltf)
- `python make_assets.py` builds the icon and backdrop from `assets/cover.jpg`, plus the procedural SFX
- `./build.sh` builds PyInstaller onedir, Inno Setup, onefile portable and the zip (under Wine)

## Credits
- UI font: Lilita One by Juan Montoreano (SIL Open Font License 1.1)
- Cover art: supplied by EX Inc.
- All models, PIKNOTT designs and sound effects are original. They are made procedurally or in Blender
