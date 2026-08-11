# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['backend\\src\\server.py'],
    pathex=[],
    binaries=[],
    datas=[('backend', 'backend'), ('src', 'src')],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops.auto', 'fastapi', 'aiosqlite', 'aiohttp', 'yaml', 'cryptography', 'jsonschema'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['nicegui', 'pystray', 'PIL', 'torch', 'numpy', 'pandas'],
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
    name='llm-router-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
