"""KWin blur-behind for the translucent window (via the small native helper).

The helper (`native/libmcglass.so`, built from kde/native) wraps
KWindowEffects. Without it, or outside KWin, `available` is False and the UI
falls back to an opaque background.
"""

from __future__ import annotations

import ctypes
import logging
import math
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

log = logging.getLogger(__name__)

_HERE = Path(__file__).resolve().parent
_CANDIDATES = (
    _HERE / "native" / "libmcglass.so",                       # installed / copied
    _HERE.parent / "native" / "build" / "libmcglass.so",      # source checkout
)


def _load() -> ctypes.CDLL | None:
    for path in _CANDIDATES:
        if not path.exists():
            continue
        try:
            lib = ctypes.CDLL(str(path))
        except OSError as error:
            log.warning("could not load %s: %s", path, error)
            continue
        lib.mcglass_available.restype = ctypes.c_bool
        lib.mcglass_apply.argtypes = [
            ctypes.c_void_p, ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.c_int,
            ctypes.c_double, ctypes.c_double, ctypes.c_double,
        ]
        return lib
    return None


def rounded_region(width: int, height: int, radius: float) -> list[tuple[int, int, int, int]]:
    """Approximate a rounded rectangle with one-pixel-tall strips at the
    corners (KWin takes blur regions as rectangles)."""
    r = int(min(radius, width / 2, height / 2))
    if r <= 0:
        return [(0, 0, width, height)]
    rects = [(0, r, width, height - 2 * r)]
    for y in range(r):
        dy = r - y - 0.5
        inset = int(math.ceil(r - math.sqrt(max(r * r - dy * dy, 0.0))))
        rects.append((inset, y, width - 2 * inset, 1))
        rects.append((inset, height - 1 - y, width - 2 * inset, 1))
    return rects


class WindowEffects(QObject):
    """Exposed to QML as `WindowEffects`."""

    availableChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._lib = _load()
        self._available = False
        self._polls = 0
        # On Wayland, KWindowSystem learns about KWin's blur protocol only after
        # the first registry round-trips, so availability is polled briefly.
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._poll)
        if self._lib:
            self._timer.start()
        else:
            log.info("native helper not built; using an opaque window background")

    def _poll(self) -> None:
        self._polls += 1
        if self._lib.mcglass_available():
            self._timer.stop()
            self._available = True
            self.availableChanged.emit()
        elif self._polls >= 20:
            self._timer.stop()
            log.info("KWin blur-behind unavailable; using an opaque window background")

    def _get_available(self) -> bool:
        return self._available

    available = Property(bool, _get_available, notify=availableChanged)

    @Slot(QObject, bool, float)
    def apply(self, window: QObject, enable: bool, radius: float) -> None:
        """Blur behind `window`, clipped to its rounded outline."""
        if not self._lib or window is None:
            return
        import shiboken6

        rects = rounded_region(int(window.width()), int(window.height()), radius) if enable else []
        flat = [v for rect in rects for v in rect]
        array = (ctypes.c_int * len(flat))(*flat)
        pointer = shiboken6.getCppPointer(window)[0]
        # A touch of extra saturation keeps colours behind the glass lively.
        self._lib.mcglass_apply(pointer, enable, array, len(rects), 1.0, 1.0, 1.35)
