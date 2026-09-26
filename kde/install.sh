#!/usr/bin/env bash
# Install (or remove with --uninstall) Refract for the current user.
# Everything goes under $PREFIX (default ~/.local); no root needed, except that
# --deps first installs the required distribution packages with sudo.
set -euo pipefail

APP_ID=io.github.RobbyBobby77.Refract
PREFIX="${PREFIX:-$HOME/.local}"
SRC="$(dirname "$(readlink -f "$0")")"
DATA="$PREFIX/share/refract"
BIN="$PREFIX/bin/refract"
DESKTOP="$PREFIX/share/applications/$APP_ID.desktop"
ICON="$PREFIX/share/icons/hicolor/scalable/apps/$APP_ID.svg"
METAINFO="$PREFIX/share/metainfo/$APP_ID.metainfo.xml"

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

# Install everything Refract needs with the distribution's package manager.
# Fedora names are verified; the others follow the same packages' usual names.
install_deps() {
    local id=""
    [[ -r /etc/os-release ]] && id="$(. /etc/os-release; echo " ${ID:-} ${ID_LIKE:-} ")"
    local cmd
    case "$id" in
        *" fedora "*|*" rhel "*|*" centos "*)
            cmd=(sudo dnf install -y python3-pyside6 python3-psutil python3-dbus kf6-kirigami
                 cmake gcc gcc-c++ qt6-qtbase-devel kf6-kwindowsystem-devel rust cargo
                 pkgconf-pkg-config libdrm-devel mesa-libgbm-devel systemd-devel git patch) ;;
        *" arch "*)
            cmd=(sudo pacman -S --needed --noconfirm pyside6 python-psutil python-dbus kirigami
                 cmake gcc qt6-base kwindowsystem rust pkgconf libdrm mesa systemd-libs git patch) ;;
        *" opensuse"*|*" suse "*)
            cmd=(sudo zypper install -y python3-pyside6 python3-psutil python3-dbus-python kf6-kirigami
                 cmake gcc-c++ qt6-base-devel kf6-kwindowsystem-devel rust cargo pkgconf-pkg-config
                 libdrm-devel libgbm-devel systemd-devel git patch) ;;
        *" debian "*|*" ubuntu "*)
            cmd=(sudo apt-get install -y python3-pyside6.qtquick python3-pyside6.qtquickcontrols2
                 python3-psutil python3-dbus qml6-module-org-kde-kirigami qml6-module-qtquick
                 qml6-module-qtquick-controls qml6-module-qtquick-layouts qml6-module-qtquick-shapes
                 qml6-module-qtquick-effects qml6-module-qtquick-window qml6-module-qtcore
                 cmake g++ qt6-base-dev libkf6windowsystem-dev cargo rustc pkg-config libdrm-dev
                 libgbm-dev libudev-dev git patch) ;;
        *)
            echo "Don't know this distribution's packages; see README for the list." >&2
            return 1 ;;
    esac
    echo "Installing dependencies:"
    echo "  ${cmd[*]}"
    "${cmd[@]}"
}

case "${1:-}" in
    -h|--help)
        echo "usage: ./install.sh [--deps | --uninstall]"
        echo "  --deps       first install the required packages (asks for your password)"
        echo "  --uninstall  remove Refract"
        exit 0 ;;
    --deps)
        install_deps ;;
esac

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -rf "$DATA" "$BIN" "$DESKTOP" "$ICON" "$METAINFO" "${LEGACY[@]}"
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
    echo "Run ./install.sh --deps to install them."
    exit 1
fi

# magpie lives in a submodule; fetch it if the clone skipped submodules.
if [[ ! -f "$SRC/../subprojects/magpie/platform-linux/crates/app-rummage/Cargo.toml" ]] \
        && git -C "$SRC/.." rev-parse --git-dir >/dev/null 2>&1; then
    git -C "$SRC/.." submodule update --init --recursive subprojects/magpie \
        || echo "note: couldn't fetch the magpie submodule; using the built-in data collectors"
fi

rm -rf "${LEGACY[@]}"
mkdir -p "$DATA" "$(dirname "$BIN")" "$(dirname "$DESKTOP")" "$(dirname "$ICON")" "$(dirname "$METAINFO")"
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
            cp "$SRC/native/build/hw.db" "$native/" 2>/dev/null || true
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
cp "$SRC/$APP_ID.metainfo.xml" "$METAINFO"
refresh

echo "Installed. Launch \"Refract\" from the app launcher, or run: $BIN"
