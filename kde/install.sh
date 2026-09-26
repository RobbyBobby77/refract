#!/usr/bin/env bash
# Install (or remove with --uninstall) Refract for the current user.
# Everything goes under $PREFIX (default ~/.local); no root needed.
set -euo pipefail

APP_ID=io.github.RobbyBobby77.Refract
PREFIX="${PREFIX:-$HOME/.local}"
SRC="$(dirname "$(readlink -f "$0")")"
DATA="$PREFIX/share/refract"
BIN="$PREFIX/bin/refract"
DESKTOP="$PREFIX/share/applications/$APP_ID.desktop"
ICON="$PREFIX/share/icons/hicolor/scalable/apps/$APP_ID.svg"

# What earlier versions (named "Mission Center Glass") installed.
LEGACY=(
    "$PREFIX/share/missioncenter-glass"
    "$PREFIX/bin/missioncenter-glass"
    "$PREFIX/share/applications/io.missioncenter.MissionCenter.Glass.desktop"
    "$PREFIX/share/icons/hicolor/scalable/apps/io.missioncenter.MissionCenter.Glass.svg"
)

refresh() {
    command -v update-desktop-database >/dev/null && update-desktop-database -q "$PREFIX/share/applications" || true
    # KDE's icon cache notices theme changes by directory mtime; GTK has its own cache.
    touch "$PREFIX/share/icons/hicolor" 2>/dev/null || true
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t -f "$PREFIX/share/icons/hicolor" 2>/dev/null || true
    command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
}

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -rf "$DATA" "$BIN" "$DESKTOP" "$ICON" "${LEGACY[@]}"
    refresh
    echo "Refract removed."
    exit 0
fi

missing=()
python3 -c "import PySide6.QtQuick" 2>/dev/null || missing+=("PySide6 (python3-pyside6)")
python3 -c "import psutil" 2>/dev/null || missing+=("psutil (python3-psutil)")
python3 -c "import dbus" 2>/dev/null || missing+=("dbus-python (python3-dbus)")
qml_dirs="$(python3 -c 'from PySide6.QtCore import QLibraryInfo as L; print(L.path(L.LibraryPath.QmlImportsPath))' 2>/dev/null || true)"
[[ -n "$qml_dirs" && -d "$qml_dirs/org/kde/kirigami" ]] || missing+=("Kirigami for Qt 6 (kf6-kirigami)")
if (( ${#missing[@]} )); then
    printf 'Missing dependencies:\n'; printf '  - %s\n' "${missing[@]}"
    exit 1
fi

rm -rf "${LEGACY[@]}"
mkdir -p "$DATA" "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$(dirname "$ICON")"
rm -rf "$DATA/refract"
cp -r "$SRC/refract" "$DATA/"
find "$DATA" -name __pycache__ -type d -prune -exec rm -rf {} +

# Optional native helpers (see build-native.sh); skipped without a toolchain.
if command -v cmake >/dev/null && command -v g++ >/dev/null; then
    if "$SRC/build-native.sh"; then
        native="$DATA/refract/native"
        mkdir -p "$native"
        cp "$SRC/native/build/librefract_effects.so" "$native/"
        magpie="$SRC/../subprojects/magpie/target/release/magpie"
        bridge="$SRC/magpie-bridge/target/release/refract-bridge"
        if [[ -x "$magpie" && -x "$bridge" ]]; then
            cp "$magpie" "$native/magpie"
            cp "$bridge" "$native/refract-bridge"
        fi
    else
        echo "note: native parts failed to build; installing without them"
    fi
else
    echo "note: cmake/g++ not found; installing without KWin blur or magpie"
fi

cat > "$BIN" <<LAUNCHER
#!/bin/sh
export PYTHONPATH="$DATA\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m refract "\$@"
LAUNCHER
chmod +x "$BIN"

sed "s|^Exec=.*|Exec=$BIN|" "$SRC/$APP_ID.desktop" > "$DESKTOP"
cp "$SRC/refract/icons/$APP_ID.svg" "$ICON"
refresh

echo "Installed. Launch \"Refract\" from the app launcher, or run: $BIN"
