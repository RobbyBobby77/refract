#!/bin/sh
# Regenerate cargo-sources.json, the Rust crates the Flatpak build uses
# offline (Flathub builds have no network). Run it whenever magpie (the
# submodule) or magpie-bridge/Cargo.lock changes, and commit the result.
#
# Uses the upstream flatpak-cargo-generator.py kept in ../../flatpak/, in a
# throwaway virtualenv for its two dependencies.
set -eu
cd "$(dirname "$(readlink -f "$0")")"
venv="${XDG_CACHE_HOME:-$HOME/.cache}/refract-flatpak/cargo-generator"
[ -x "$venv/bin/python" ] || { python3 -m venv "$venv" && "$venv/bin/pip" install -q aiohttp tomlkit; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
"$venv/bin/python" ../../flatpak/flatpak-cargo-generator.py ../../subprojects/magpie/Cargo.lock -o "$tmp/magpie.json"
"$venv/bin/python" ../../flatpak/flatpak-cargo-generator.py ../magpie-bridge/Cargo.lock -o "$tmp/bridge.json"
python3 - "$tmp/magpie.json" "$tmp/bridge.json" <<'EOF'
import json, sys
merged, seen = [], set()
for path in sys.argv[1:]:
    for source in json.load(open(path)):
        key = json.dumps(source, sort_keys=True)
        if key not in seen:
            seen.add(key)
            merged.append(source)
json.dump(merged, open("cargo-sources.json", "w"), indent=4)
print(f"cargo-sources.json: {len(merged)} sources")
EOF
