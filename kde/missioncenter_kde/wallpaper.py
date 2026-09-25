"""Find the Plasma desktop wallpaper so the window can tint itself with it,
the way macOS windows pick up colour from the desktop behind them."""

from __future__ import annotations

import configparser
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QUrl

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".jxl", ".bmp"}
_FALLBACK = Path("/usr/share/wallpapers/Next")
CONFIG = Path.home() / ".config" / "plasma-org.kde.plasma.desktop-appletsrc"


def _to_path(value: str) -> Path | None:
    value = value.strip().split("#", 1)[0]
    if not value:
        return None
    if value.startswith("file:"):
        value = unquote(urlparse(value).path)
    p = Path(os.path.expanduser(value))
    return p if p.exists() else None


def _best_image(folder: Path) -> Path | None:
    """Pick the image closest to a 16:10 laptop panel, preferring large ones."""
    best, best_score = None, None
    for f in folder.iterdir() if folder.is_dir() else []:
        if f.suffix.lower() not in _IMAGE_EXT:
            continue
        try:
            w, h = (int(x) for x in f.stem.split("x", 1))
        except ValueError:
            w, h = 1920, 1080
        score = (abs(w / max(h, 1) - 1.6), -min(w, 5120))
        if best_score is None or score < best_score:
            best, best_score = f, score
    return best


def _from_package(pkg: Path) -> tuple[Path | None, Path | None]:
    light = _best_image(pkg / "contents" / "images")
    dark = _best_image(pkg / "contents" / "images_dark") or light
    return light, dark


def _configured() -> Path | None:
    if not CONFIG.exists():
        return None
    parser = configparser.RawConfigParser(strict=False, interpolation=None)
    parser.optionxform = str
    try:
        parser.read(CONFIG, encoding="utf-8")
    except (configparser.Error, UnicodeDecodeError):
        return None
    for section in parser.sections():
        if not section.endswith("[Wallpaper][org.kde.image][General]"):
            continue
        image = parser.get(section, "Image", fallback="")
        p = _to_path(image)
        if p:
            return p
    for section in parser.sections():
        if section.endswith("[Wallpaper][org.kde.slideshow][General]"):
            for folder in parser.get(section, "SlidePaths", fallback="").split(","):
                p = _to_path(folder)
                if p and p.is_dir():
                    for child in sorted(p.iterdir()):
                        if (child / "contents").is_dir():
                            return child
    return None


def resolve() -> tuple[str, str]:
    """Return (light, dark) wallpaper URLs; empty strings if none found."""
    source = _configured() or (_FALLBACK if _FALLBACK.exists() else None)
    light = dark = None
    if source is not None:
        if source.is_dir():
            light, dark = _from_package(source)
        elif source.suffix.lower() in _IMAGE_EXT:
            light = dark = source
    as_url = lambda p: QUrl.fromLocalFile(str(p)).toString() if p else ""  # noqa: E731
    return as_url(light), as_url(dark)
