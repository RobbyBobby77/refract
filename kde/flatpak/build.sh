#!/bin/sh
# Build Refract as a Flatpak and write refract.flatpak, a single-file bundle
# that installs on any distribution (it fetches KDE's runtime from Flathub).
#
#   ./build.sh            build refract.flatpak
#   ./build.sh --install  also install it for the current user
#
# Needs flatpak; flatpak-builder, the SDKs and the Flathub remote are set up
# for the current user if missing. Build files go to ~/.cache/refract-flatpak.
set -eu
cd "$(dirname "$(readlink -f "$0")")"
APP_ID=io.github.RobbyBobby77.Refract
WORK="${XDG_CACHE_HOME:-$HOME/.cache}/refract-flatpak"
FLATHUB=https://dl.flathub.org/repo/flathub.flatpakrepo

flatpak remote-add --user --if-not-exists flathub "$FLATHUB"
if command -v flatpak-builder >/dev/null; then
    builder=flatpak-builder
else
    flatpak install --user --noninteractive flathub org.flatpak.Builder
    builder="flatpak run org.flatpak.Builder"
fi

$builder --user --install-deps-from=flathub --force-clean --ccache \
    --state-dir="$WORK/state" --repo="$WORK/repo" "$WORK/build" "$APP_ID.yml"
flatpak build-bundle --runtime-repo="$FLATHUB" "$WORK/repo" refract.flatpak "$APP_ID"
echo "wrote $PWD/refract.flatpak"

if [ "${1:-}" = "--install" ]; then
    flatpak install --user --noninteractive --reinstall refract.flatpak
fi
