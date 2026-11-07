# -*- mode: python ; coding: utf-8 -*-
# Build:  double-click build_exe.bat  (or: pyinstaller Cyberpunk2077ModListTool.spec)
import os
import re
from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
                                                 StringStruct, VarFileInfo, VarStruct)

# Single source of truth: APP_VERSION in cp77mlt/__init__.py (e.g. "3.0.0" -> 3.0.0.0)
with open(os.path.join("cp77mlt", "__init__.py"), encoding="utf-8") as _f:
    _m = re.search(r'APP_VERSION\s*=\s*["\']([\d.]+)["\']', _f.read())
VERSION = tuple((list(map(int, _m.group(1).split("."))) + [0, 0, 0, 0])[:4]) if _m else (0, 0, 0, 0)
VERSION_STR = ".".join(map(str, VERSION))
ICON = "Cyberpunk 2077 Mod List Tool.ico"

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=VERSION, prodvers=VERSION, mask=0x3F, flags=0x0, fileType=0x1, subtype=0x0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable("040904B0", [
            StringStruct("CompanyName", "Nexus Mod Author Sammmy1036"),
            StringStruct("FileDescription", "Cyberpunk 2077 Mod List Tool"),
            StringStruct("FileVersion", VERSION_STR),
            StringStruct("InternalName", "Cyberpunk 2077 Mod List Tool"),
            StringStruct("LegalCopyright", "©2026 Sammmy1036"),
            StringStruct("OriginalFilename", "Cyberpunk 2077 Mod List Tool.exe"),
            StringStruct("ProductName", "Cyberpunk 2077 Mod List Tool"),
            StringStruct("ProductVersion", VERSION_STR),
        ])]),
        VarFileInfo([VarStruct("Translation", [0x0409, 1200])]),
    ],
)

datas = [("cp77mlt/web", "cp77mlt/web")]
if os.path.exists(ICON):
    datas.append((ICON, "."))
for _png in ("game_icon.png", "mod_list_tool.png"):  # launch-button fallback icon, sidebar logo
    if os.path.exists(os.path.join("icons", _png)):
        datas.append((os.path.join("icons", _png), "icons"))

a = Analysis(
    ["Cyberpunk2077ModListTool.pyw"],   # v2's spec pointed at a file that didn't exist
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=collect_submodules("webview"),
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "customtkinter", "PyQt5", "PyQt6", "PySide2", "PySide6", "gi"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Cyberpunk 2077 Mod List Tool",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    runtime_tmpdir=None, console=False,
    version=version_info,
    icon=ICON if os.path.exists(ICON) else None,
)
