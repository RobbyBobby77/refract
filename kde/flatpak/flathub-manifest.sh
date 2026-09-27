#!/bin/sh
# Write the Flathub version of the manifest to flathub/ (next to this file):
# the same manifest, but building a tagged release from GitHub instead of the
# working tree. Copy the files in flathub/ into the Flathub repository.
#
#   ./flathub-manifest.sh refract-v1.1.0
#
# The tag must be pushed to GitHub, and the repository must be public.
set -eu
cd "$(dirname "$(readlink -f "$0")")"
APP_ID=io.github.RobbyBobby77.Refract
# REFRACT_GIT_URL=file://… tries it out from a local clone before the tag is public.
URL="${REFRACT_GIT_URL:-https://github.com/RobbyBobby77/refract.git}"
tag="${1:?usage: $0 TAG (e.g. refract-v1.1.0)}"
commit=$(git rev-list -n 1 "$tag")
git ls-remote --exit-code --tags "$URL" "$tag" >/dev/null 2>&1 \
    || echo "warning: $tag isn't on $URL (yet?)" >&2

mkdir -p flathub
python3 - "$APP_ID.yml" "flathub/$APP_ID.yml" "$URL" "$tag" "$commit" <<'EOF'
import re, sys
src, out, url, tag, commit = sys.argv[1:]
text = open(src).read()
block = re.compile(r"^( *)# refract-source: begin.*?# refract-source: end\n", re.S | re.M)
indent = block.search(text).group(1)
git = (f"{indent}- type: git\n{indent}  url: {url}\n"
       f"{indent}  tag: {tag}\n{indent}  commit: {commit}\n"
       f"{indent}  x-checker-data:\n{indent}    type: git\n"
       f"{indent}    tag-pattern: ^refract-v([\\d.]+)$\n")
text = block.sub(lambda m: git, text, count=1)
text = re.sub(r"\A(#[^\n]*\n)+", f"# Flathub manifest for Refract, generated from kde/flatpak/ in {url}\n# at {tag}.\n", text)
open(out, "w").write(text)
EOF
cp cargo-sources.json flathub/
echo "wrote $PWD/flathub/ ($tag = $commit)"
