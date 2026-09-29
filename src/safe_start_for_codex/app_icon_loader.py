"""App-Icon-Loader für Safe Start for Codex.

Lädt das Anwendungs-Icon mit robuster Multi-Pfad-Auflösung (PyInstaller-Bundle,
assets/app_icon.ico, assets/codex_safe_start.ico, Root-ICOs und PNG-Fallback)
sowohl als PIL-Image (für System-Tray / Pystray) als auch optional als QIcon.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PIL import Image


def get_project_root() -> Path:
    """Liefert das Basisverzeichnis für Ressourcen im Repo oder gefrorenen Bundle."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[2]


def get_app_icon_path() -> Path | None:
    """Findet den besten verfügbaren Pfad zur Icon-Datei."""
    root = get_project_root()
    candidates = [
        root / "assets" / "codex_safe_start.ico",
        root / "assets" / "app_icon.ico",
        root / "assets" / "DesktopIcon.ico",
        root / "assets" / "icon.ico",
        root / "DesktopIcon.ico",
        root / "codex_safe_start.ico",
        root / "icon.ico",
        root / "ICO.ico",
        root / "assets" / "DesktopIcon.png",
        root / "assets" / "icon.png",
        root / "assets" / "codex_safe_start.png",
        root / "DesktopIcon.png",
        root / "icon.png",
        root / "codex_safe_start.png",
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def load_app_icon_pil(size: int = 64) -> Image.Image:
    """Lädt das Anwendungs-Icon als PIL Image für Tray / Pystray mit Fallback."""
    from PIL import Image, ImageDraw

    icon_path = get_app_icon_path()
    if icon_path is not None:
        try:
            with Image.open(icon_path) as img:
                return img.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
        except Exception:
            pass

    # Deterministischer Fallback falls Datei nicht lesbar
    image = Image.new("RGBA", (size, size), (12, 23, 38, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((3, 3, size - 4, size - 4), radius=max(2, size // 5), fill=(12, 34, 52, 255))
    draw.polygon(
        [
            (size * 0.5, size * 0.14),
            (size * 0.78, size * 0.26),
            (size * 0.72, size * 0.68),
            (size * 0.5, size * 0.86),
            (size * 0.28, size * 0.68),
            (size * 0.22, size * 0.26),
        ],
        fill=(27, 164, 179, 255),
    )
    draw.rectangle((size * 0.36, size * 0.33, size * 0.43, size * 0.66), fill=(245, 248, 250, 255))
    draw.rectangle((size * 0.57, size * 0.33, size * 0.64, size * 0.66), fill=(245, 248, 250, 255))
    draw.arc(
        (size * 0.30, size * 0.23, size * 0.70, size * 0.73),
        300,
        80,
        fill=(125, 220, 114, 255),
        width=max(1, size // 16),
    )
    return image


def load_app_icon() -> Any:
    """Lädt ein valides QIcon falls PySide6/PyQt verfügbar ist, sonst None."""
    try:
        from PySide6.QtGui import QGuiApplication, QIcon
    except ImportError:
        try:
            from PyQt6.QtGui import QGuiApplication, QIcon
        except ImportError:
            return None

    if QGuiApplication.instance() is None:
        try:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            _ = QGuiApplication([])
        except Exception:
            return None

    icon_path = get_app_icon_path()
    if icon_path is not None:
        try:
            icon = QIcon(str(icon_path))
            if not icon.isNull():
                return icon
        except Exception:
            pass

    return QIcon()


def get_app_icon() -> Any:
    """Alias für load_app_icon."""
    return load_app_icon()
