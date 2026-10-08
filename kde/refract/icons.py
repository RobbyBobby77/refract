"""Original portable action icons for platforms without the KDE icon theme."""
from urllib.parse import parse_qs, unquote
from PySide6.QtCore import QByteArray, QRectF, QSize, QUrl
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

_PATHS = {
    "edit-find": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    "edit-copy": '<rect x="8" y="8" width="12" height="13" rx="2"/><path d="M15 8V3H3v13h5"/>',
    "help-about": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
    "dialog-warning": '<path d="M12 3 2 21h20Z M12 9v5m0 3v1"/>',
    "dialog-ok-apply": '<path d="m4 12 5 5L21 5"/>',
    "media-playback-start": '<path d="m7 3 14 9-14 9Z"/>',
    "media-playback-pause": '<path d="M7 3v18M17 3v18" stroke-width="4"/>',
    "media-playback-stop": '<rect x="5" y="5" width="14" height="14" rx="1"/>',
    "process-stop": '<path d="m6 3-3 3v12l3 3h12l3-3V6l-3-3Z M8 8l8 8m0-8-8 8"/>',
    "application-exit": '<path d="M11 3H3v18h8m-2-9h13m-5-5 5 5-5 5"/>',
    "view-refresh": '<path d="M20 9a8 8 0 1 0 0 7M20 3v6h-6"/>',
    "list-add": '<path d="M12 4v16M4 12h16"/>',
    "list-remove": '<path d="M4 12h16"/>',
    "configure": '<path d="M5 3v18M12 3v18M19 3v18"/><path d="M2 8h6m1 9h6m1-11h6" stroke-width="4"/>',
    "system-run": '<path d="m12 2 2 4 4-1 1 4 3 3-3 3-1 4-4-1-2 4-2-4-4 1-1-4-3-3 3-3 1-4 4 1Z"/><circle cx="12" cy="12" r="3"/>',
    "window-close": '<path d="m6 6 12 12m0-12L6 18"/>',
    "go-next": '<path d="m8 4 8 8-8 8"/>',
    "go-previous": '<path d="m16 4-8 8 8 8"/>',
    "view-more": '<circle cx="4" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="20" cy="12" r="1"/>',
}


class IconProvider(QQuickImageProvider):
    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, name: str, size: QSize, requestedSize: QSize) -> QImage:
        name, _, query = name.partition("?")
        name = unquote(name)
        options = parse_qs(query)
        edge = max(requestedSize.width(), requestedSize.height(), 32)
        image = QImage(edge, edge, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        size.setWidth(edge)
        size.setHeight(edge)
        painter = QPainter(image)
        if name.startswith("file:"):
            path = QUrl(name).toLocalFile()
            if path.lower().endswith(".svg"):
                QSvgRenderer(path).render(painter, QRectF(0, 0, edge, edge))
            else:
                painter.drawImage(QRectF(0, 0, edge, edge), QImage(path))
        else:
            body = _PATHS.get(name.removesuffix("-symbolic"), '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M3 8h18M8 8v13"/>')
            svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="white" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>'
            QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, edge, edge))
        if "color" in options:
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            painter.fillRect(image.rect(), QColor(options["color"][0]))
        painter.end()
        return image
