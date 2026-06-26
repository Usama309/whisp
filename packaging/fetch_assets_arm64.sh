#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Stage the arm64 whisper.cpp binaries (built from source in build-arm64/) and
# relocate their dylibs to @loader_path so local transcription is self-contained.
B="build-arm64/whisper.cpp/build"
A="packaging/assets-arm64"
rm -rf "$A"; mkdir -p "$A"

cp "$B/bin/whisper-cli"                        "$A/whisper-cli"
cp "$B/src/libwhisper.1.7.4.dylib"             "$A/libwhisper.1.dylib"
cp "$B/ggml/src/libggml.dylib"                 "$A/libggml.dylib"
cp "$B/ggml/src/libggml-base.dylib"            "$A/libggml-base.dylib"
cp "$B/ggml/src/libggml-cpu.dylib"             "$A/libggml-cpu.dylib"
cp "$B/ggml/src/ggml-blas/libggml-blas.dylib"  "$A/libggml-blas.dylib"
cp "packaging/assets/ggml-base.en.bin"         "$A/ggml-base.en.bin"
chmod u+w "$A/whisper-cli" "$A"/*.dylib

DEPS="libwhisper.1.dylib libggml.dylib libggml-base.dylib libggml-cpu.dylib libggml-blas.dylib"

# portable ids
for lib in $DEPS; do
  install_name_tool -id "@loader_path/$lib" "$A/$lib"
done

# rewrite every @rpath/<dep> cross-reference to @loader_path/<dep>
for f in whisper-cli $DEPS; do
  for d in $DEPS; do
    install_name_tool -change "@rpath/$d" "@loader_path/$d" "$A/$f" 2>/dev/null || true
  done
done

# re-sign ad-hoc (install_name_tool invalidates signatures)
codesign --force --sign - "$A/whisper-cli" "$A"/*.dylib 2>/dev/null || true

echo "Staged arm64 assets in $A:"
ls -la "$A"
echo "--- whisper-cli linkage (should be @loader_path only) ---"
otool -L "$A/whisper-cli"
