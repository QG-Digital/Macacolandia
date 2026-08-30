# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['E:\\Tree\\backend.py'],
    pathex=[],
    binaries=[],
    datas=[('E:\\Tree\\index.html', '.'), ('E:\\Tree\\desktop.js', '.'), ('E:\\Tree\\desktop.css', '.'), ('E:\\Tree\\macacolandia-logo.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Macacolandia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['E:\\Tree\\macacolandia-logo.ico'],
)
