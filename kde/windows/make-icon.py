"""Render the existing Refract brand SVG into a Windows application icon."""
from pathlib import Path
from PySide6.QtCore import QSize
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

app = QGuiApplication([])
root = Path(__file__).resolve().parent
image = QImage(QSize(256, 256), QImage.Format.Format_ARGB32)
image.fill(0)
painter = QPainter(image)
QSvgRenderer(str(root.parent / "refract/icons/io.github.RobbyBobby77.Refract.svg")).render(painter)
painter.end()
(root / "build").mkdir(exist_ok=True)
if not image.save(str(root / "build/refract.ico")):
    raise RuntimeError("Could not save the Windows icon")
