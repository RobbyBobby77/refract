"""Find the Plasma desktop wallpaper so the window can tint itself with it,
the way macOS windows pick up colour from the desktop behind them."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QUrl

from . import sandbox

_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".avif", ".jxl", ".bmp"}
_FALLBACK = Path("/usr/share/wallpapers/Next")
CONFIG = Path.home() / ".config" / "plasma-org.kde.plasma.desktop-appletsrc"


class _Files:
    """The file system the wallpaper is on: here, the one we can see."""

    def is_file(self, p: Path) -> bool:
        return p.is_file()

    def is_dir(self, p: Path) -> bool:
        return p.is_dir()

    def children(self, p: Path) -> list[Path]:
        try:
            return sorted(p.iterdir())
        except OSError:
            return []

    def probe(self, roots: list[Path]) -> None:
        """Get ready to answer questions about `roots` and what's under them."""

    def local(self, p: Path) -> Path:
        """A path we can open for `p`."""
        return p

    def done(self) -> None:
        pass


class _HostFiles(_Files):
    """The host's files as seen from the Flatpak sandbox, which can't read
    them: a host call lists everything under the candidate paths, and the
    chosen images are copied into our cache (the same path on both sides)."""

    _LIST = 'for p; do find -L "$p" -maxdepth 4 -type d | sed "s/^/d /"; ' \
            'find -L "$p" -maxdepth 4 -type f | sed "s/^/f /"; done'

    def __init__(self) -> None:
        self._dirs: set[Path] = set()
        self._files: set[Path] = set()
        self._copies: set[Path] = set()
        self._cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "refract" / "wallpaper"

    def probe(self, roots: list[Path]) -> None:
        try:
            out = subprocess.run(sandbox.host(["sh", "-c", self._LIST, "sh", *map(str, roots)]),
                                 capture_output=True, text=True, errors="replace", timeout=10).stdout
        except (OSError, subprocess.TimeoutExpired):
            return
        for line in out.splitlines():
            kind, _, path = line.partition(" ")
            (self._dirs if kind == "d" else self._files).add(Path(path))

    def is_file(self, p: Path) -> bool:
        return p in self._files

    def is_dir(self, p: Path) -> bool:
        return p in self._dirs

    def children(self, p: Path) -> list[Path]:
        return sorted(c for c in self._dirs | self._files if c.parent == p)

    def local(self, p: Path) -> Path:
        name = hashlib.sha1(str(p).encode()).hexdigest()[:16] + p.suffix.lower()
        copy = self._cache / name
        self._cache.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(sandbox.host(["cp", "-u", str(p), str(copy)]), capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass
        self._copies.add(copy)
        return copy

    def done(self) -> None:
        """Forget copies of earlier wallpapers."""
        for f in self._cache.iterdir() if self._cache.is_dir() else []:
            if f not in self._copies:
                f.unlink(missing_ok=True)


def _to_path(value: str) -> Path | None:
    value = value.strip().split("#", 1)[0]
    if not value:
        return None
    if value.startswith("file:"):
        value = unquote(urlparse(value).path)
    return Path(os.path.expanduser(value))


def _best_image(folder: Path, fs: _Files) -> Path | None:
    """Pick the image closest to a 16:10 laptop panel, preferring large ones."""
    best, best_score = None, None
    for f in fs.children(folder):
        if f.suffix.lower() not in _IMAGE_EXT or not fs.is_file(f):
            continue
        try:
            w, h = (int(x) for x in f.stem.split("x", 1))
        except ValueError:
            w, h = 1920, 1080
        score = (abs(w / max(h, 1) - 1.6), -min(w, 5120))
        if best_score is None or score < best_score:
            best, best_score = f, score
    return best


def _from_package(pkg: Path, fs: _Files = _Files()) -> tuple[Path | None, Path | None]:
    light = _best_image(pkg / "contents" / "images", fs)
    dark = _best_image(pkg / "contents" / "images_dark", fs) or light
    return light, dark


def _from_plasmashell() -> Path | None:
    """Ask the running Plasma shell which image is on screen 0. (Not from the
    Flatpak: talking to plasmashell would let it script the desktop.)"""
    if sandbox.IN_FLATPAK:
        return None
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


def _from_config() -> tuple[list[Path], list[Path]]:
    """Plasma's config: the desktops' images (screen 0 first) and slideshow folders."""
    try:
        if sandbox.IN_FLATPAK:
            text = subprocess.run(sandbox.host(["cat", str(CONFIG)]), capture_output=True, text=True,
                                  errors="replace", timeout=5).stdout
        else:
            text = CONFIG.read_text(encoding="utf-8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return [], []
    groups = _kde_groups(text)
    candidates = []
    folders = []
    for name, entries in groups.items():
        if name.endswith("[Wallpaper][org.kde.image][General]"):
            containment = groups.get(name.split("[Wallpaper]", 1)[0], {})
            on_first_screen = containment.get("lastScreen") == "0"
            candidates.append((not on_first_screen, entries.get("Image", "")))
        elif name.endswith("[Wallpaper][org.kde.slideshow][General]"):
            folders += [_to_path(f) for f in entries.get("SlidePaths", "").split(",")]
    images = [_to_path(image) for _, image in sorted(candidates)]
    return [p for p in images if p], [p for p in folders if p]


def resolve() -> tuple[str, str]:
    """Return (light, dark) wallpaper URLs; empty strings if none found."""
    if sys.platform == "win32":
        from .backend.windows_native import wallpaper_path
        path = wallpaper_path()
        url = QUrl.fromLocalFile(path).toString() if path and Path(path).is_file() else ""
        return url, url
    shell = _from_plasmashell()
    images, folders = _from_config()
    candidates = [p for p in (shell, *images) if p]
    fs = _HostFiles() if sandbox.IN_FLATPAK else _Files()
    fs.probe([*candidates, _FALLBACK])

    source = next((p for p in candidates if fs.is_file(p) or fs.is_dir(p)), None)
    if source is None and folders:   # a slideshow: its first wallpaper package
        fs.probe(folders)
        source = next((child for folder in folders for child in fs.children(folder)
                       if fs.is_dir(child / "contents")), None)
    if source is None and fs.is_dir(_FALLBACK):
        source = _FALLBACK
    light = dark = None
    if source is not None:
        if fs.is_dir(source):
            light, dark = _from_package(source, fs)
        elif source.suffix.lower() in _IMAGE_EXT:
            light = dark = source
    as_url = lambda p: QUrl.fromLocalFile(str(fs.local(p))).toString() if p else ""  # noqa: E731
    urls = as_url(light), as_url(dark)
    fs.done()
    return urls
