#!/bin/bash
# Windows build via Wine: PyInstaller onedir + Inno Setup installer + onefile portable + zip
set -e
export WINEPREFIX=/workspace/exwifi/.wine WINEDEBUG=-all
cd "$(dirname "$0")"
V=$(grep -oP 'APP_VERSION = "\K[^"]+' piknott_celestika.py)
PY='C:\Python311\python.exe'
wine "$PY" -m PyInstaller --noconfirm "PIKNOTT CELESTIKA.spec" > build_dir.log 2>&1; echo DIR_DONE
wine "C:\\InnoSetup\\ISCC.exe" installer.iss > build_iss.log 2>&1; echo ISS_DONE
wine "$PY" -m PyInstaller --noconfirm --workpath build_onefile --distpath dist_onefile "PIKNOTT CELESTIKA onefile.spec" > build_1f.log 2>&1
cp "dist_onefile/PIKNOTT CELESTIKA.exe" dist/PIKNOTT.CELESTIKA.Portable.exe; echo ONEFILE_DONE
cd dist && rm -f PIKNOTT.CELESTIKA.$V.Windows.x64.zip && python3 -c "import shutil; shutil.make_archive('PIKNOTT.CELESTIKA.$V.Windows.x64', 'zip', '.', 'PIKNOTT CELESTIKA')" && echo ZIP_DONE
ls -la
