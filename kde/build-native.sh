#!/bin/sh
# Build the optional native parts. The app runs without them, falling back to
# an opaque window background and the Python data collectors.
#   native/          KWin blur-behind helper (C++, KF6 WindowSystem)
#   magpie-bridge/   JSON bridge to Mission Center's magpie engine (Rust),
#                    plus magpie itself from ../subprojects/magpie
set -e
cd "$(dirname "$(readlink -f "$0")")"

# CMake pins its build dir to absolute paths; start over if the checkout moved.
cache=native/build/CMakeCache.txt
if [ -f "$cache" ] && ! grep -qx "CMAKE_HOME_DIRECTORY:INTERNAL=$PWD/native" "$cache"; then
    rm -rf native/build
fi
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release >/dev/null
cmake --build native/build --parallel
echo "built native/build/librefract_effects.so"

if command -v cargo >/dev/null; then
    if [ ! -f ../subprojects/magpie/platform-linux/crates/app-rummage/Cargo.toml ]; then
        git -C .. submodule update --init --recursive subprojects/magpie
    fi
    # magpie's build patches nvtop with GNU patch; stand in with git if needed.
    if ! command -v patch >/dev/null; then
        MC_PATCH_BINARY="$PWD/tools/patch-via-git.sh"
        export MC_PATCH_BINARY
    fi
    cargo build --release --manifest-path ../subprojects/magpie/Cargo.toml
    cargo build --release --manifest-path magpie-bridge/Cargo.toml
    echo "built magpie and refract-bridge"
else
    echo "cargo not found: skipping magpie (the Python collectors will be used)"
fi
