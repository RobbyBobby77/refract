#!/usr/bin/env python3
"""Render the widget outside Plasma, over the desktop wallpaper, to a PNG.

    python3 plasmoid/preview.py [--theme dark|light] [--tinted] [--seconds 12] [--out FILE]

GlassCard.qml and SystemStats.qml are plain QML, so this runs them with the
same system sensors plasmashell uses (plus a stand-in for Plasma's i18n) and
grabs the window offscreen, which works even with the screen off or locked.
Wait a few seconds so the graphs have some history.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Slot
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

HERE = Path(__file__).resolve().parent
KDE = HERE.parent
UI = HERE / "package" / "contents" / "ui"
sys.path.insert(0, str(KDE))


class Plasma(QObject):
    """What KLocalizedContext gives the widget in plasmashell: i18n()."""

    @Slot(str, result=str)
    @Slot(str, str, result=str)
    @Slot(str, str, str, result=str)
    def i18n(self, text: str, *args: str) -> str:
        for i, arg in enumerate(args, 1):
            text = text.replace(f"%{i}", str(arg))
        return text


SCENE = """
import QtQuick
import QtQuick.Window
import "%(ui)s" as Widget

Window {
    width: 420; height: %(height)d
    visible: true
    color: "black"
    Image {
        anchors.fill: parent
        source: "%(wallpaper)s"
        fillMode: Image.PreserveAspectCrop
    }
    Widget.SystemStats { id: sensors }
    Widget.GlassCard {
        anchors.centerIn: parent
        width: 306
        height: implicitHeight
        stats: sensors
        dark: %(dark)s
        tinted: %(tinted)s
        fontFamily: "Inter"
    }
}
"""


def main() -> int:
    print("start", flush=True)
    cli = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    cli.add_argument("--theme", choices=["dark", "light"], default="dark")
    cli.add_argument("--tinted", action="store_true")
    cli.add_argument("--seconds", type=float, default=12)
    cli.add_argument("--wallpaper", help="image to put behind the card (default: the Plasma wallpaper)")
    cli.add_argument("--out", default="/tmp/refract-widget.png")
    args = cli.parse_args()

    app = QGuiApplication(sys.argv)
    for font in (KDE / "refract" / "fonts").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(font))
    if args.wallpaper:
        wallpaper = QUrl.fromLocalFile(str(Path(args.wallpaper).resolve())).toString()
    else:
        from refract import wallpaper as plasma_wallpaper
        light, dark = plasma_wallpaper.resolve()
        wallpaper = dark if args.theme == "dark" else light

    engine = QQmlApplicationEngine()
    plasma = Plasma()
    engine.rootContext().setContextObject(plasma)
    engine.warnings.connect(lambda ws: [print("QML:", w.toString(), file=sys.stderr) for w in ws])
    engine.loadData(bytes(SCENE % {
        "ui": QUrl.fromLocalFile(str(UI)).toString(), "wallpaper": wallpaper, "height": 460,
        "dark": str(args.theme == "dark").lower(), "tinted": str(args.tinted).lower(),
    }, "utf-8"), QUrl.fromLocalFile(str(HERE / "preview.qml")))
    if not engine.rootObjects():
        return 1
    print("loaded", flush=True)
    window = engine.rootObjects()[0]

    def shoot() -> None:
        print("shooting", flush=True)
        window.grabWindow().save(args.out)
        print("saved", args.out)
        app.quit()

    QTimer.singleShot(int(args.seconds * 1000), shoot)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
