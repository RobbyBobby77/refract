#!/bin/sh
# Build and install Refract into /app. Run by flatpak-builder from the
# repository root (see io.github.RobbyBobby77.Refract.yml).
set -eu
APP_ID=io.github.RobbyBobby77.Refract
DATA=/app/share/refract
NATIVE=$DATA/refract/native

# The app itself: the same layout install.sh uses under ~/.local/share/refract.
mkdir -p "$DATA"
cp -r kde/refract "$DATA/"
find "$DATA" -name __pycache__ -type d -prune -exec rm -rf {} +
mkdir -p "$NATIVE"

# KWin blur-behind helper.
cmake -S kde/native -B build-native -DCMAKE_BUILD_TYPE=Release
cmake --build build-native --parallel
install -m755 build-native/librefract_effects.so "$NATIVE/"

# magpie (runs on the host; see refract/sandbox.py) and the bridge to it.
# magpie's build downloads and patches nvtop unless it finds it in place: the
# manifest provides it, so patch it and put it there. Like magpie's own build
# (and Mission Center's Flatpak), a patch that doesn't apply is only a warning.
nvtop_dir=subprojects/magpie/platform-linux/3rdparty/nvtop
nvtop=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["directory"])' "$nvtop_dir/nvtop.json")
if [ -d "$nvtop" ]; then
    for patch in $(python3 -c 'import json, sys; print(*json.load(open(sys.argv[1]))["patches"])' "$nvtop_dir/nvtop.json"); do
        patch -d "$nvtop" -p1 -i "$PWD/$nvtop_dir/$patch" || echo "warning: $patch didn't fully apply"
    done
    mkdir -p subprojects/magpie/target/release/build/native
    mv "$nvtop" subprojects/magpie/target/release/build/native/
fi
cargo build --release --manifest-path subprojects/magpie/Cargo.toml
cargo build --release --manifest-path kde/magpie-bridge/Cargo.toml
install -m755 subprojects/magpie/target/release/magpie "$NATIVE/magpie"
install -m755 kde/magpie-bridge/target/release/refract-bridge "$NATIVE/refract-bridge"
hwdb=subprojects/magpie/platform-linux/hwdb
python3 "$hwdb/generate_hwdb.py" -o "$NATIVE" "$hwdb"/*.hwdb
strip "$NATIVE/magpie" "$NATIVE/refract-bridge" "$NATIVE/librefract_effects.so"

# Launcher, desktop entry, icon, AppStream metadata.
mkdir -p /app/bin
cat > /app/bin/refract <<LAUNCHER
#!/bin/sh
export PYTHONPATH="$DATA\${PYTHONPATH:+:\$PYTHONPATH}"
exec python3 -m refract "\$@"
LAUNCHER
chmod 755 /app/bin/refract
install -Dm644 "kde/$APP_ID.desktop" "/app/share/applications/$APP_ID.desktop"
install -Dm644 "kde/refract/icons/$APP_ID.svg" "/app/share/icons/hicolor/scalable/apps/$APP_ID.svg"
install -Dm644 "kde/$APP_ID.metainfo.xml" "/app/share/metainfo/$APP_ID.metainfo.xml"
