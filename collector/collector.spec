# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller collector/collector.spec
# Output: dist/DSR-Lap-Collector/

block_cipher = None

a = Analysis(
    ["desktop_main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("static/index.html", "collector/static"),
        ("../data/tracks.json", "data"),
        ("../data/cars.json", "data"),
        ("../data/default-api.json", "data"),
        ("../data/fingerprints/albert-park.json", "data/fingerprints"),
    ],
    hiddenimports=["collector", "collector.app", "collector.cloud", "collector.verify"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DSR-Lap-Collector",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DSR-Lap-Collector",
)
