#!/bin/sh
# Minimal stand-in for `patch -p1 -i FILE`, used when GNU patch isn't
# installed (magpie's build applies nvtop patches this way; see
# MC_PATCH_BINARY in subprojects/magpie/platform-linux/build.rs).
strip=1
file=""
while [ $# -gt 0 ]; do
    case "$1" in
        -p*) strip="${1#-p}" ;;
        -i) shift; file="$1" ;;
        *) echo "patch-via-git: unsupported argument $1" >&2; exit 2 ;;
    esac
    shift
done
[ -n "$file" ] || { echo "patch-via-git: no patch file" >&2; exit 2; }
# Like GNU patch (which the build expects), tolerate a little context drift
# (-C1 ~ fuzz) and apply the hunks that fit, rejecting the rest (--reject).
# Keep git from discovering an enclosing repository (the sources are unpacked
# under magpie's target/ dir), otherwise it resolves paths from that repo root.
GIT_CEILING_DIRECTORIES="$(dirname "$PWD")" exec git apply -p"$strip" -C1 --reject --verbose "$file"
