"""PyInstaller entry point (package-relative imports need an absolute entry)."""
import sys

# Explicit imports allow PyInstaller to collect Qt's QML plugins.
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtQuickControls2, QtSvg  # noqa: F401

from refract.app import main

sys.exit(main())
