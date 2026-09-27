#!/usr/bin/env python3
"""Regenerate the README screenshots (kde/screenshots/) from the real app.

    python3 tools/screenshots.py dark     # performance, apps, gpu, services, about
    python3 tools/screenshots.py light    # memory, settings

Uses KDE's own "Nuvole" wallpaper (LGPL, ships with Plasma) in Wallpaper mode
so the glass shows, and a throwaway config dir so the user's
preferences are neither used nor changed. Graphs need about a minute of
history, so each run takes ~80 s.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

KDE = Path(__file__).resolve().parent.parent
OUT = KDE / "screenshots"
WALLPAPER = Path("/usr/share/wallpapers/Nuvole")

os.environ["XDG_CONFIG_HOME"] = tempfile.mkdtemp(prefix="refract-shots-")
sys.path.insert(0, str(KDE))

from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl  # noqa: E402

from refract import wallpaper  # noqa: E402
from refract.app import Session, parse_args  # noqa: E402

light, dark = wallpaper._from_package(WALLPAPER)
wallpaper.resolve = lambda: tuple(QUrl.fromLocalFile(str(p)).toString() for p in (light, dark))

SHOTS = {
    "dark": [
        (500, "Prefs.backdropMode = 1", None),
        (65000, "", "performance-dark"),
        (300, "win.page = 'apps'", None),
        (3000, "Monitor.processes.select(Monitor.processes.get(1).key)", None),
        (900, "", "apps-dark"),
        (300, "Monitor.processes.select(''); win.page = 'performance'; win.device = "
              "Array.from({ length: Monitor.devices.count }, (_, i) => Monitor.devices.get(i).key)"
              ".find(k => k.startsWith('gpu:')) || 'cpu'", None),
        (1500, "", "gpu-dark"),
        (300, "win.page = 'services'", None),
        (3500, "Monitor.services.select(Monitor.services.get(4).key)", None),
        (900, "", "services-dark"),
        (300, "Monitor.services.select(''); win.page = 'performance'; win.device = 'cpu'; aboutSheet.open()", None),
        (1500, "", "about-dark"),
    ],
    "light": [
        (500, "Prefs.backdropMode = 1", None),
        (65000, "win.device = 'memory'", None),
        (1500, "", "memory-light"),
        (300, "settingsSheet.open()", None),
        (1500, "", "settings-light"),
    ],
}


def main() -> int:
    theme = sys.argv[1] if len(sys.argv) > 1 else "dark"
    session = Session(parse_args(["--size", "1320x860", "--page", "performance", "--device", "cpu",
                                  "--theme", theme, "--screenshot", "-"]))

    def shoot(name: str) -> None:
        img = session.window.grabWindow().scaledToWidth(1600, Qt.SmoothTransformation)
        img.save(str(OUT / f"{name}.png"))
        print("saved", OUT / f"{name}.png", flush=True)

    t = 0
    for delay, js, name in SHOTS[theme]:
        t += delay
        QTimer.singleShot(t, lambda js=js, name=name: (js and session.evaluate(js), name and shoot(name)))
    QTimer.singleShot(t + 500, QCoreApplication.quit)
    return session.run()


if __name__ == "__main__":
    sys.exit(main())
