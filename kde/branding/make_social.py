#!/usr/bin/env python3
"""Render the GitHub social preview (branding/social-preview.png, 1280x640):
icon, wordmark and tagline beside a screenshot of the app.

    python3 branding/make_social.py        # needs screenshots/performance-dark.png

Upload it under the repository's Settings > General > Social preview.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QGuiApplication, QImage, QLinearGradient,
                           QPainter, QPainterPath, QRadialGradient)
from PySide6.QtSvg import QSvgRenderer

HERE = Path(__file__).resolve().parent
KDE = HERE.parent
W, H = 1280, 640
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
    for f in (KDE / "refract" / "fonts").glob("*.ttf"):
        QFontDatabase.addApplicationFont(str(f))

    img = QImage(W, H, QImage.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
    bg = QLinearGradient(0, 0, 0, H)
    bg.setColorAt(0, QColor("#1A1E3C"))
    bg.setColorAt(1, QColor("#0A0B18"))
    p.fillRect(img.rect(), bg)
    glow(p, 120, 700, 600, BLUE, 0.35)
    glow(p, 700, 760, 600, VIOLET, 0.30)
    glow(p, 1260, 560, 520, PINK, 0.28)

    # the app, as a floating window cut off by the right edge
    shot = QImage(str(KDE / "screenshots" / "performance-dark.png"))
    frame = QRectF(610, 120, 820, 820 * shot.height() / shot.width())
    for i in range(18):   # soft shadow
        a = 0.022 * (1 - i / 18)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, int(255 * a)))
        p.drawRoundedRect(frame.adjusted(-i, -i + 18, i, i + 18), 22 + i, 22 + i)
    clip = QPainterPath()
    clip.addRoundedRect(frame, 22, 22)
    p.save()
    p.setClipPath(clip)
    p.drawImage(frame, shot)
    p.restore()

    QSvgRenderer(str(HERE / "icon.svg")).render(p, QRectF(64, 110, 190, 190))

    title = QFont("Inter Display")
    title.setPixelSize(112)
    title.setWeight(QFont.Bold)
    word = QPainterPath()
    word.addText(70, 420, title, "Refract")
    grad = QLinearGradient(word.boundingRect().topLeft(), word.boundingRect().topRight())
    grad.setColorAt(0, BLUE)
    grad.setColorAt(0.5, VIOLET)
    grad.setColorAt(1, PINK)
    p.fillPath(word, grad)

    tagline = QFont("Inter")
    tagline.setPixelSize(30)
    tagline.setWeight(QFont.Medium)
    p.setFont(tagline)
    p.setPen(QColor(235, 235, 245, 175))
    p.drawText(QRectF(76, 448, 520, 120), Qt.TextWordWrap,
               "Your system at a glance — in Liquid Glass, for KDE Plasma.")
    p.end()

    out = HERE / "social-preview.png"
    img.save(str(out))
    print("wrote", out)


if __name__ == "__main__":
    main()
