#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VERSION=${1:?Usage: build_runtime.sh VERSION SOURCE_SHA256 OUTPUT_DIRECTORY}
SOURCE_SHA256=${2:?Usage: build_runtime.sh VERSION SOURCE_SHA256 OUTPUT_DIRECTORY}
OUTPUT=${3:?Usage: build_runtime.sh VERSION SOURCE_SHA256 OUTPUT_DIRECTORY}
OUTPUT=$(mkdir -p "$OUTPUT" && realpath "$OUTPUT")
WORK="$ROOT/build/wpewebkit-$VERSION"
ARCHIVE="$WORK/wpewebkit-$VERSION.tar.xz"

rm -rf "$WORK"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

curl --fail --location --retry 3 \
  "https://wpewebkit.org/releases/wpewebkit-$VERSION.tar.xz" \
  -o "$ARCHIVE"
printf '%s  %s\n' "$SOURCE_SHA256" "$ARCHIVE" | sha256sum --check -
tar --no-same-owner -xJf "$ARCHIVE" -C "$WORK"
python3 "$ROOT/scripts/patch_runtime.py" "$WORK/wpewebkit-$VERSION"

export CC=clang CXX=clang++
cmake \
  -S "$WORK/wpewebkit-$VERSION" \
  -B "$WORK/build" \
  -G Ninja \
  -DPORT=WPE \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX=/usr \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_INSTALL_LIBEXECDIR=lib \
  -DCMAKE_SKIP_RPATH=ON \
  -DCMAKE_C_FLAGS_RELEASE='-O2 -DNDEBUG -fcf-protection=none' \
  -DCMAKE_CXX_FLAGS_RELEASE='-O2 -DNDEBUG -fcf-protection=none' \
  -DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld \
  -DCMAKE_SHARED_LINKER_FLAGS=-fuse-ld=lld \
  -DUSE_LIBBACKTRACE=OFF \
  -DDEVELOPER_MODE=OFF \
  -DENABLE_BUBBLEWRAP_SANDBOX=ON \
  -DENABLE_DOCUMENTATION=OFF \
  -DENABLE_MINIBROWSER=OFF \
  -DENABLE_API_TESTS=OFF \
  -DENABLE_LAYOUT_TESTS=OFF \
  -DENABLE_SPEECH_SYNTHESIS=OFF

cmake --build "$WORK/build" --parallel "${WPE_BUILD_JOBS:-2}"
DESTDIR="$OUTPUT" cmake --install "$WORK/build" --strip

license_directory="$OUTPUT/usr/lib/wpe-webkit-2.0/licenses"
mkdir -p "$license_directory"
find "$WORK/wpewebkit-$VERSION/Source" -type f \
  \( -name 'COPYING*' -o -name 'LICENSE*' \) -print0 | sort -z |
  while IFS= read -r -d '' file; do
    printf '\n### %s\n' "${file#"$WORK/wpewebkit-$VERSION/"}"
    cat "$file"
  done > "$license_directory/THIRD_PARTY_NOTICES"
