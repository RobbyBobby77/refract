#!/bin/sh
# Install the Refract desktop widget for the current user, then add it from
# the desktop's "Add Widgets…". Runs again to upgrade.
#
#   ./install.sh              install or upgrade
#   ./install.sh --uninstall  remove it
#   ./install.sh --package    write refract-widget.plasmoid (for "Install from File…" or the KDE Store)
#
# The widget reads Plasma's own system sensors, so it works without Refract;
# clicking it opens Refract if the Flatpak or a source install is present.
set -eu
cd "$(dirname "$(readlink -f "$0")")"
ID=io.github.RobbyBobby77.Refract.Widget

if [ "${1:-}" = "--uninstall" ]; then
    kpackagetool6 --type Plasma/Applet --remove "$ID"
    exit 0
fi

# The package plus Refract's typeface (kept once, in ../refract/fonts).
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
cp -r package "$stage/$ID"
mkdir -p "$stage/$ID/contents/fonts"
cp ../refract/fonts/Inter-Medium.ttf ../refract/fonts/Inter-SemiBold.ttf ../refract/fonts/Inter-LICENSE.txt \
    "$stage/$ID/contents/fonts/"

if [ "${1:-}" = "--package" ]; then
    python3 - "$stage/$ID" refract-widget.plasmoid <<'PY'
import os, sys, zipfile
root, out = sys.argv[1:]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for folder, _, files in os.walk(root):
        for f in files:
            path = os.path.join(folder, f)
            z.write(path, os.path.relpath(path, root))
PY
    echo "wrote $PWD/refract-widget.plasmoid"
    exit 0
fi

if kpackagetool6 --type Plasma/Applet --show "$ID" >/dev/null 2>&1; then
    kpackagetool6 --type Plasma/Applet --upgrade "$stage/$ID"
else
    kpackagetool6 --type Plasma/Applet --install "$stage/$ID"
fi
echo "Installed. Right-click the desktop → Add Widgets… → Refract."
