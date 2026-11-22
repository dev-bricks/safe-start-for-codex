# -*- coding: utf-8 -*-
"""Build standalone Windows executable for Safe Start for Codex using PyInstaller."""

from __future__ import annotations

import shutil
from pathlib import Path

import PyInstaller.__main__

HERE = Path(__file__).resolve().parent
SRC_DIR = HERE / "src"
ASSETS_DIR = HERE / "assets"
ICON_PATH = ASSETS_DIR / "codex_safe_start.ico"
DIST_DIR = HERE / "dist"
BUILD_DIR = Path(r"C:\_Local_DEV\codex_build\safe-start-for-codex")
SPEC_DIR = Path(r"C:\_Local_DEV\codex_build\safe-start-for-codex-spec")
SYSTEM_BIN_DIR = Path(r"C:\_Local_DEV\codex-safe-start\bin")

def build() -> int:
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)
    SYSTEM_BIN_DIR.mkdir(parents=True, exist_ok=True)

    args = [
        str(SRC_DIR / "safe_start_for_codex" / "tray_app.py"),
        "--name", "CodexSafeStart",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        f"--icon={ICON_PATH}",
        f"--add-data={ICON_PATH};.",
        f"--paths={SRC_DIR}",
        "--collect-submodules=pystray",
        "--collect-submodules=PIL",
        "--hidden-import=pystray._win32",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={SPEC_DIR}",
    ]

    print("Running PyInstaller for CodexSafeStart...")
    PyInstaller.__main__.run(args)

    built_exe = DIST_DIR / "CodexSafeStart.exe"
    if not built_exe.is_file():
        print(f"[ERROR] Expected executable not found at {built_exe}")
        return 1

    # Also sync to local system bin dir
    shutil.copy2(built_exe, SYSTEM_BIN_DIR / "CodexSafeStart.exe")
    print("[SUCCESS] Standalone Windows executable built successfully:")
    print(f"  - {built_exe} ({built_exe.stat().st_size} bytes)")
    print(f"  - {SYSTEM_BIN_DIR / 'CodexSafeStart.exe'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(build())
