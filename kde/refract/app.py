"""Application bootstrap: fonts, QML engine, and the Monitor bridge."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QTimer, QUrl
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow, QSGRendererInterface
from PySide6.QtQuickControls2 import QQuickStyle

from . import BASED_ON, __version__
from .bridge import Monitor
from .effects import WindowEffects

ROOT = Path(__file__).resolve().parent
APP_ID = "io.github.RobbyBobby77.Refract"


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="refract", description="Refract: your system at a glance, in Liquid Glass.")
    p.add_argument("--page", choices=["performance", "apps", "services"], help="page to open")
    p.add_argument("--device", help="performance device key to select, e.g. memory, disk:nvme0n1")
    p.add_argument("--theme", choices=["system", "light", "dark"], help="override the colour scheme")
    p.add_argument("--screenshot", metavar="PNG", help="render, save a screenshot and quit (for docs/tests)")
    p.add_argument("--delay", type=int, default=3500, help="ms to wait before --screenshot")
    p.add_argument("--size", default="", help="initial window size WxH")
    p.add_argument("--debug", action="store_true")
    return p.parse_args(argv)


def _migrate_settings() -> None:
    """Carry preferences over from the app's earlier name (Mission Center Glass)."""
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    old, new = config / "MissionCenter" / "MissionCenterGlass.conf", config / "Refract" / "Refract.conf"
    if old.exists() and not new.exists():
        new.parent.mkdir(parents=True, exist_ok=True)
        new.write_bytes(old.read_bytes())


def _load_fonts() -> None:
    for f in sorted((ROOT / "fonts").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(f))


class Session:
    """A running instance: application, bridge, QML engine and window."""

    def __init__(self, args: argparse.Namespace) -> None:
        logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                            format="%(levelname)s %(name)s: %(message)s")

        QQuickStyle.setStyle("Basic")
        # The glass shaders derive screen positions from clip space; pin the API
        # so the convention is known (OpenGL is also Qt's default on Linux).
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
        # Frameless windows draw their own rounded corners, so they need alpha.
        QQuickWindow.setDefaultAlphaBuffer(True)

        self.app = QGuiApplication(sys.argv[:1])
        _migrate_settings()
        self.app.setOrganizationName("Refract")
        self.app.setOrganizationDomain("robbybobby77.github.io")
        self.app.setApplicationName("Refract")
        self.app.setApplicationDisplayName("Refract")
        self.app.setDesktopFileName(APP_ID)
        self.app.setWindowIcon(QIcon(str(ROOT / "icons" / f"{APP_ID}.svg")))

        _load_fonts()
        font = QFont("Inter")
        font.setPointSizeF(10.0)
        self.app.setFont(font)

        self.monitor = Monitor()
        self.effects = WindowEffects()
        self.engine = QQmlApplicationEngine()
        self.engine.warnings.connect(
            lambda warnings: [logging.warning("QML: %s", w.toString()) for w in warnings])
        ctx = self.engine.rootContext()
        ctx.setContextProperty("Monitor", self.monitor)
        ctx.setContextProperty("WindowEffects", self.effects)
        ctx.setContextProperty("AppVersion", __version__)
        ctx.setContextProperty("BasedOn", BASED_ON)
        ctx.setContextProperty("AppIcon", QUrl.fromLocalFile(str(ROOT / "icons" / f"{APP_ID}.svg")).toString())
        ctx.setContextProperty("ShaderDir", QUrl.fromLocalFile(str(ROOT / "shaders") + "/").toString())
        ctx.setContextProperty("StartupOptions", {
            "page": args.page or "",
            "device": args.device or "",
            "theme": args.theme or "",
            "size": args.size,
            "screenshot": bool(args.screenshot),
        })

        self.engine.load(QUrl.fromLocalFile(str(ROOT / "qml" / "Refract" / "Main.qml")))
        roots = self.engine.rootObjects()
        self.window = roots[0] if roots else None
        if self.window is not None:
            self.monitor.watch(self.window)

    def evaluate(self, expression: str):
        """Run a JS expression in Main.qml's scope (used by tests/screenshots)."""
        expr = QQmlExpression(self.engine.contextForObject(self.window), self.window, expression)
        value, _undefined = expr.evaluate()   # PySide returns (value, isUndefined)
        if expr.hasError():
            logging.warning("evaluate(%r): %s", expression, expr.error().toString())
        return value

    def screenshot(self, path: str) -> None:
        self.window.grabWindow().save(path)

    def run(self) -> int:
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        code = self.app.exec()
        self.close(code)
        return code

    def close(self, code: int = 0) -> None:
        # Tear down QML first so the Settings singleton is written out.
        del self.engine
        if not self.monitor.shutdown():
            # A sampler is blocked in a system call; destroying its QThread
            # would abort, so leave without running destructors.
            logging.warning("sampler thread did not stop in time; exiting")
            sys.stdout.flush()
            os._exit(code)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    session = Session(args)
    if session.window is None:
        session.close(1)
        return 1

    if args.screenshot:
        def grab() -> None:
            session.screenshot(args.screenshot)
            QCoreApplication.quit()

        QTimer.singleShot(args.delay, grab)

    return session.run()
