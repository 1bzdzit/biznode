"""
Build BizNode Installer as Windows .exe
========================================
Uses PyInstaller to package the GUI into a single self-contained executable.

Usage:
    pip install pyinstaller PySide6
    python build_exe.py

Output:
    dist/BizNodeInstaller.exe
"""

import os
import sys
import subprocess
import shutil

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR     = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR    = os.path.join(PROJECT_ROOT, "build")
SPEC_FILE    = os.path.join(PROJECT_ROOT, "BizNodeInstaller.spec")


def check_pyinstaller():
    if shutil.which("pyinstaller"):
        return True
    try:
        subprocess.check_call(
            [sys.executable, "-m", "PyInstaller", "--version"],
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False


def write_spec():
    """Write a PyInstaller .spec file for reliable PySide6 packaging."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
# BizNode Installer — PyInstaller spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['run_installer.py'],
    pathex=['{root}'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'installer.main',
        'installer.core.diagnostics',
        'installer.core.service_detector',
        'installer.core.compose_builder',
        'installer.core.env_writer',
        'installer.core.usb_deployer',
        'installer.core.instance_guard',
        'requests',
        'yaml',
        'ctypes',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BizNodeInstaller',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowless GUI
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='installer/resources/icon.ico',  # uncomment if you have an icon
)
'''.format(root=PROJECT_ROOT.replace("\\", "\\\\"))

    with open(SPEC_FILE, "w") as f:
        f.write(spec_content)
    print(f"Wrote spec: {SPEC_FILE}")


def build():
    print("=" * 55)
    print("  BizNode Installer — .exe Builder")
    print("=" * 55)

    if not check_pyinstaller():
        print("\nPyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    write_spec()

    print("\nRunning PyInstaller...\n")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller",
         "--clean",
         "--noconfirm",
         SPEC_FILE],
        cwd=PROJECT_ROOT,
    )

    if result.returncode == 0:
        exe_path = os.path.join(DIST_DIR, "BizNodeInstaller.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / 1024 / 1024
            print(f"\n{'=' * 55}")
            print(f"  [OK] Build successful!")
            print(f"  Output:  {exe_path}")
            print(f"  Size:    {size_mb:.1f} MB")
            print(f"{'=' * 55}\n")
        else:
            print("\n[!] Build finished but .exe not found in dist/")
    else:
        print(f"\n[FAIL] PyInstaller exited with code {result.returncode}")
        sys.exit(result.returncode)


if __name__ == "__main__":
    build()
