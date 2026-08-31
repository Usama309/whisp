#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv-arm64/bin/activate

# Native Apple Silicon build. Uses the arm64 venv + the arm64 whisper.cpp assets
# staged by fetch_assets_arm64.sh. Outputs to dist-arm64/ so the working x86
# build in dist/ is never touched until this one is verified.
A="packaging/assets-arm64"
[ -f "$A/whisper-cli" ] || ./packaging/fetch_assets_arm64.sh >/dev/null

rm -rf build-arm64/pyi dist-arm64
pyinstaller --noconfirm --windowed --name "Whisp" \
  --osx-bundle-identifier com.usama.whisp \
  --distpath dist-arm64 --workpath build-arm64/pyi \
  --target-arch arm64 \
  --add-data "whisp/ui/templates:whisp/ui/templates" \
  --add-data "whisp/ui/static:whisp/ui/static" \
  --add-data "$A/ggml-base.en.bin:." \
  --add-binary "$A/whisper-cli:." \
  --add-binary "$A/libwhisper.1.dylib:." \
  --add-binary "$A/libggml.dylib:." \
  --add-binary "$A/libggml-base.dylib:." \
  --add-binary "$A/libggml-cpu.dylib:." \
  --add-binary "$A/libggml-blas.dylib:." \
  --paths . \
  --collect-submodules whisp \
  --hidden-import rumps \
  --collect-all sounddevice \
  --collect-all soundfile \
  packaging/launcher.py

PLIST="dist-arm64/Whisp.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'Whisp records your voice for dictation.'" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSAppleEventsUsageDescription string 'Whisp pastes transcribed text into the active app.'" "$PLIST" 2>/dev/null || true

codesign --force --deep --sign - \
  --entitlements packaging/Whisp.entitlements dist-arm64/Whisp.app

echo "Built native arm64: dist-arm64/Whisp.app"
lipo -archs dist-arm64/Whisp.app/Contents/MacOS/Whisp
