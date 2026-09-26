#!/bin/sh
# Recompile the GLSL sources into Qt's portable .qsb shader packs.
# Needs `qsb` from qt6-qtshadertools; the compiled packs are committed, so this
# is only required after editing a shader.
set -e
cd "$(dirname "$(readlink -f "$0")")/refract/shaders"
QSB="${QSB:-$(command -v qsb-qt6 || command -v qsb || echo /usr/lib64/qt6/bin/qsb)}"
for src in *.vert *.frag; do
    "$QSB" --glsl "100 es,120,150" --hlsl 50 --msl 12 -o "$src.qsb" "$src"
    echo "compiled $src"
done
