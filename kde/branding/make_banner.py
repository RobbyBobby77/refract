#!/usr/bin/env python3
"""Render Refract's README banner (branding/banner.png) with Qt, using the
app's own Inter fonts so the wordmark looks the same everywhere.

    python3 branding/make_banner.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QGuiApplication, QImage, QLinearGradient,
                           QPainter, QPainterPath, QRadialGradient)
from PySide6.QtSvg import QSvgRenderer

HERE = Path(__file__).resolve().parent
FONTS = HERE.parent / "refract" / "fonts"
W, H = 2000, 600

# brand palette (Apple system colours used across the app)
BLUE, VIOLET, PINK = QColor("#46A3FF"), QColor("#A37BFF"), QColor("#FF5A82")


def glow(p: QPainter, x: float, y: float, r: float, color: QColor, alpha: float) -> None:
    g = QRadialGradient(QPointF(x, y), r)
    c = QColor(color)
    c.setAlphaF(alpha)
    g.setColorAt(0, c)
    c.setAlphaF(0)
    g.setColorAt(1, c)
    p.fillRect(QRectF(0, 0, W, H), g)


def main() -> None:
    QGuiApplication(sys.argv)
    for f in FONTS.glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))

    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

    bg = QLinearGradient(0, 0, 0, H)
    bg.setColorAt(0, QColor("#1A1E3C"))
    bg.setColorAt(1, QColor("#0A0B18"))
    p.fillRect(img.rect(), bg)
    glow(p, 260, 640, 700, BLUE, 0.35)
    glow(p, 1150, 700, 700, VIOLET, 0.28)
    glow(p, 1900, 620, 620, PINK, 0.26)

    QSvgRenderer(str(HERE / "icon.svg")).render(p, QRectF(110, 90, 420, 420))

    title = QFont("Inter Display")
    title.setPixelSize(172)
    title.setWeight(QFont.Bold)
    x, y = 600, 318
    word = QPainterPath()
    word.addText(x, y, title, "Refract")
    grad = QLinearGradient(word.boundingRect().topLeft(), word.boundingRect().topRight())
    grad.setColorAt(0, BLUE)
    grad.setColorAt(0.5, VIOLET)
    grad.setColorAt(1, PINK)
    p.fillPath(word, grad)

    tagline = QFont("Inter")
    tagline.setPixelSize(44)
    tagline.setWeight(QFont.Medium)
    p.setFont(tagline)
    p.setPen(QColor(235, 235, 245, 165))
    p.drawText(QPointF(x + 8, y + 96), "Your system at a glance — through glass, for KDE Plasma.")
    p.end()

    out = HERE / "banner.png"
    img.save(str(out))
    print("wrote", out)


if __name__ == "__main__":
    main()
