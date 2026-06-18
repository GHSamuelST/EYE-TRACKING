# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec do EyeControl.

Build:
    uv run pyinstaller EyeControl.spec --noconfirm

Gera dist/EyeControl/EyeControl.exe (modo onedir, mais estável para
bibliotecas pesadas como mediapipe e opencv).
"""
from PyInstaller.utils.hooks import collect_all, collect_data_files

# --- Dependências que precisam dos seus dados/binários embutidos ---
datas = []
binaries = []
hiddenimports = []

for pacote in ("mediapipe", "qfluentwidgets", "qframelesswindow"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pacote)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

# scipy / pyautogui dependem de submódulos resolvidos em runtime
hiddenimports += [
    "scipy.spatial.transform._rotation_groups",
    "scipy._lib.array_api_compat.numpy.fft",
    "scipy.special._cdflib",
]

# --- Recursos próprios do app ---
datas += [
    ("app/core/face_landmarker.task", "core"),
    ("app/assets/images/icone.ico", "assets/images"),
    ("app/assets/images/icone.jpg", "assets/images"),
]


a = Analysis(
    ["app/main.py"],
    pathex=["app"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EyeControl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # App de janela: sem console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app/assets/images/icone.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="EyeControl",
)
