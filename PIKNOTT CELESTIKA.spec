# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files
import os
DROP = ('avcodec', 'avformat', 'avutil', 'swresample', 'swscale', 'libp3ffmpeg', 'fmod', 'assimp', 'ptloader',
        'bullet', 'pandaode', 'pandaai', 'vrpn', 'p3vision', 'pandadx9', 'd3dx9', 'cgd3d9', 'pandaphysics', 'pandafx')
b = [x for x in collect_dynamic_libs('panda3d') if not any(k in os.path.basename(x[0]).lower() for k in DROP)]
d = collect_data_files('panda3d', includes=['etc/*'])
assets = [('assets/cover.jpg', 'assets'), ('assets/backdrop.jpg', 'assets'), ('assets/icon.ico', 'assets'), ('assets/icon.png', 'assets'),
          ('assets/ui_font.ttf', 'assets'), ('assets/sfx', 'assets/sfx'),
          ('assets/models/pikcel_ball.bam', 'assets/models'), ('assets/models/nova_ball.bam', 'assets/models'), ('assets/models/astral_ball.bam', 'assets/models')]
a = Analysis(['piknott_celestika.py'], datas=assets + d, binaries=b,
             hiddenimports=['panda3d.core', 'panda3d.direct', 'direct.showbase.ShowBase', 'direct.gui.DirectGui',
                            'pc_game', 'pc_battle', 'pc_world', 'pc_models', 'pc_toon', 'pc_data', 'pc_ui'],
             excludes=['matplotlib', 'scipy', 'pandas', 'IPython', 'pytest', 'tkinter', 'PIL', 'cv2', 'wx', 'PyQt5', 'imageio_ffmpeg'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='PIKNOTT CELESTIKA', console=False, upx=False,
          version='version.txt', icon=['assets/icon.ico'])
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='PIKNOTT CELESTIKA')
