# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

datas = [
    ("mulch/templates", "mulch/templates"),
    ("mulch/static", "mulch/static"),
    ("mulch/icons", "mulch/icons"),
    ("models/densenet121_epoch-3.zip", "models"),
    ("models/densenet121_frozen-backbone.zip", "models"),
]
binaries = []
hiddenimports = [
    "mulch.app", "mulch.model", "mulch.records", "mulch.launcher",
    "torchvision.models.densenet", "torchvision.transforms.functional",
    "PIL.Image", "PIL.ImageFilter", "PIL.ImageOps", "numpy",
]

for pkg in ("torchvision", "PIL"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["mulch/launcher.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "tkinter", "IPython", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Mulch",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Mulch",
)