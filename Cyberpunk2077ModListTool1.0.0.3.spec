# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

block_cipher = None

# Define version info
version_info = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 0, 0, 3),
        prodvers=(1, 0, 0, 3),
        mask=0x3f,
        flags=0x0,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    '040904B0',
                    [
                        StringStruct('CompanyName', 'Nexus Mod Author Sammmy1036'),
                        StringStruct('FileDescription', 'Cyberpunk 2077 Mod List Tool'),
                        StringStruct('FileVersion', '1.0.0.3'),
                        StringStruct('InternalName', 'Cyberpunk 2077 Mod List Tool'),
                        StringStruct('LegalCopyright', '©2025 Sammmy1036'),
                        StringStruct('OriginalFilename', 'Cyberpunk 2077 Mod List Tool.exe'),
                        StringStruct('ProductName', 'Cyberpunk 2077 Mod List Tool'),
                        StringStruct('ProductVersion', '1.0.0.3')
                    ]
                )
            ]
        ),
        VarFileInfo([VarStruct('Translation', [0x0409, 1200])])
    ]
)

a = Analysis(['Cyberpunk2077ModListTool1.0.0.3.pyw'],
             pathex=[],
             binaries=[],
             datas=[
                 ('Cyberpunk 2077 Mod List Tool.ico', '.'),
                 ('Cyberpunk 2077 Mod List Tool.png', '.')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)
exe = EXE(pyz,
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
          icon='Cyberpunk 2077 Mod List Tool.ico')
