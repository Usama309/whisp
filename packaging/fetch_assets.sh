#!/usr/bin/env bash
set -euo pipefail
# Stage the binaries + model that get bundled into the .app, and relocate the
# whisper.cpp dylibs to @loader_path so local transcription works on any Mac
# (no Homebrew required on the target machine).
ASSETS="packaging/assets"
mkdir -p "$ASSETS"

# 1) whisper model — reuse a local copy if present, else download (~142MB)
if [ ! -f "$ASSETS/ggml-base.en.bin" ]; then
  if [ -f "$HOME/.whisp-models/ggml-base.en.bin" ]; then
    cp "$HOME/.whisp-models/ggml-base.en.bin" "$ASSETS/ggml-base.en.bin"
  else
    curl -L -o "$ASSETS/ggml-base.en.bin" \
      https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
  fi
fi

# 2) whisper-cli + its three dylibs + the runtime backend plugins ggml dlopens
#    (cp follows symlinks -> copies real files)
cp "$(command -v whisper-cli)" "$ASSETS/whisper-cli"
cp /usr/local/opt/whisper-cpp/lib/libwhisper.1.dylib "$ASSETS/libwhisper.1.dylib"
cp /usr/local/opt/ggml/lib/libggml.0.dylib           "$ASSETS/libggml.0.dylib"
cp /usr/local/opt/ggml/lib/libggml-base.0.dylib      "$ASSETS/libggml-base.0.dylib"
cp /usr/local/opt/ggml/libexec/libggml-cpu.so        "$ASSETS/libggml-cpu.so"
cp /usr/local/opt/ggml/libexec/libggml-blas.so       "$ASSETS/libggml-blas.so"
chmod u+w "$ASSETS"/whisper-cli "$ASSETS"/*.dylib "$ASSETS"/*.so

# 3) set portable ids
install_name_tool -id @loader_path/libwhisper.1.dylib   "$ASSETS/libwhisper.1.dylib"
install_name_tool -id @loader_path/libggml.0.dylib      "$ASSETS/libggml.0.dylib"
install_name_tool -id @loader_path/libggml-base.0.dylib "$ASSETS/libggml-base.0.dylib"

# 4) rewrite cross-references to @loader_path
install_name_tool \
  -change @rpath/libwhisper.1.dylib @loader_path/libwhisper.1.dylib \
  -change /usr/local/opt/ggml/lib/libggml.0.dylib @loader_path/libggml.0.dylib \
  -change /usr/local/opt/ggml/lib/libggml-base.0.dylib @loader_path/libggml-base.0.dylib \
  "$ASSETS/whisper-cli"
install_name_tool \
  -change /usr/local/opt/ggml/lib/libggml.0.dylib @loader_path/libggml.0.dylib \
  -change /usr/local/opt/ggml/lib/libggml-base.0.dylib @loader_path/libggml-base.0.dylib \
  "$ASSETS/libwhisper.1.dylib"
install_name_tool \
  -change @rpath/libggml-base.0.dylib @loader_path/libggml-base.0.dylib \
  "$ASSETS/libggml.0.dylib"

# backend plugins -> find libggml-base next to themselves
for so in libggml-cpu.so libggml-blas.so; do
  install_name_tool -id "@loader_path/$so" "$ASSETS/$so"
  install_name_tool \
    -change @rpath/libggml-base.0.dylib @loader_path/libggml-base.0.dylib \
    "$ASSETS/$so"
done

# 5) re-sign ad-hoc (install_name_tool invalidates signatures)
codesign --force --sign - "$ASSETS/whisper-cli" "$ASSETS"/*.dylib "$ASSETS"/*.so 2>/dev/null || true

echo "Assets staged in $ASSETS:"
ls -la "$ASSETS"
echo "--- whisper-cli linkage (should be @loader_path only) ---"
otool -L "$ASSETS/whisper-cli"
