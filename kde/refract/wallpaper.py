"""Find the Plasma desktop wallpaper so the window can tint itself with it,
the way macOS windows pick up colour from the desktop behind them."""

from __future__ import annotations

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


def _from_plasmashell() -> Path | None:
    """Ask the running Plasma shell which image is on screen 0."""
    try:
        import dbus

        shell = dbus.Interface(
            dbus.SessionBus().get_object("org.kde.plasmashell", "/PlasmaShell", introspect=False),
            "org.kde.PlasmaShell")
        config = shell.wallpaper(dbus.UInt32(0), timeout=1.5)
    except Exception:  # noqa: BLE001 - no Plasma, no D-Bus, old Plasma…
        return None
    return _to_path(str(config.get("Image", "")))


def _kde_groups(text: str) -> dict[str, dict[str, str]]:
    """Parse a KConfig file. (configparser mangles KDE's nested
    "[Containments][1][Wallpaper]..." group names, so do it by hand.)"""
    groups: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            current = groups.setdefault(line, {})
        elif current is not None and "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            current[key.strip()] = value.strip()
    return groups


def _from_config() -> Path | None:
    """Read the wallpaper from Plasma's config, preferring desktops on screen 0."""
    try:
        groups = _kde_groups(CONFIG.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    candidates = []
    for name, entries in groups.items():
        if not name.endswith("[Wallpaper][org.kde.image][General]"):
            continue
        containment = groups.get(name.split("[Wallpaper]", 1)[0], {})
        on_first_screen = containment.get("lastScreen") == "0"
        candidates.append((not on_first_screen, entries.get("Image", "")))
    for _, image in sorted(candidates):
        p = _to_path(image)
        if p:
            return p
    for name, entries in groups.items():
        if name.endswith("[Wallpaper][org.kde.slideshow][General]"):
            for folder in entries.get("SlidePaths", "").split(","):
                p = _to_path(folder)
                if p and p.is_dir():
                    for child in sorted(p.iterdir()):
                        if (child / "contents").is_dir():
                            return child
    return None


def resolve() -> tuple[str, str]:
    """Return (light, dark) wallpaper URLs; empty strings if none found."""
    source = _from_plasmashell() or _from_config() or (_FALLBACK if _FALLBACK.exists() else None)
    light = dark = None
    if source is not None:
        if source.is_dir():
            light, dark = _from_package(source)
        elif source.suffix.lower() in _IMAGE_EXT:
            light = dark = source
    as_url = lambda p: QUrl.fromLocalFile(str(p)).toString() if p else ""  # noqa: E731
    return as_url(light), as_url(dark)
