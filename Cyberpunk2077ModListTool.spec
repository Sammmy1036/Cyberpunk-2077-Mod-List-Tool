# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

block_cipher = None

# Define version info
version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(2, 0, 0, 1),    # File version
        prodvers=(2, 0, 0, 1),   # Product version
        mask=0x3f,                # Valid fields mask
        flags=0x0,                # File flags (0 = no special flags)
        fileType=0x1,             # File type (0x1 = application)
        subtype=0x0,              # Subtype (0x0 = none)
        date=(0, 0)               # Typically unused, set to (0, 0)
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    '040904B0',  # Language: US English, Codepage: Unicode
                    [
                        StringStruct('CompanyName', 'Nexus Mod Author Sammmy1036'),
                        StringStruct('FileDescription', 'Cyberpunk 2077 Mod List Tool'),
                        StringStruct('FileVersion', '2.0.0.1'),
                        StringStruct('InternalName', 'Cyberpunk 2077 Mod List Tool'),
                        StringStruct('LegalCopyright', '©2025 Sammmy1036'),
                        StringStruct('OriginalFilename', 'Cyberpunk 2077 Mod List Tool.exe'),
                        StringStruct('ProductName', 'Cyberpunk 2077 Mod List Tool'),
                        StringStruct('ProductVersion', '2.0.0.1')
                    ]
                )
            ]
        ),
        VarFileInfo([VarStruct('Translation', [0x0409, 1200])])  # US English, Unicode
    ]
)

a = Analysis(
    ['Cyberpunk2077ModListTool2.0.0.0.pyw'],
    pathex=[],
    binaries=[],
    datas=[
        ('icons/*.png', 'icons'),  # Include all .png files in the icons directory
        ('Cyberpunk 2077 Mod List Tool.ico', '.')  # Include the .ico file in the root of the bundled app
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Cyberpunk 2077 Mod List Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    version=version_info,
    icon='Cyberpunk 2077 Mod List Tool.ico',
    onefile=True
)

