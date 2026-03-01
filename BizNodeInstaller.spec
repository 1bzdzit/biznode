# -*- mode: python ; coding: utf-8 -*-
# BizNode Installer — PyInstaller spec

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['run_installer.py'],
    pathex=['C:\\Users\\shashikanth ramamurt\\projects\\1bzbiznodev2\\biznode_fixed'],
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
    hooksconfig={},
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
