#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate
pip install --quiet --upgrade pyinstaller

# Stage + relocate the bundled binaries/model
./packaging/fetch_assets.sh >/dev/null

rm -rf build dist
pyinstaller --noconfirm --windowed --name "Whisp" \
  --osx-bundle-identifier com.usama.whisp \
  --add-data "whisp/ui/templates:whisp/ui/templates" \
  --add-data "whisp/ui/static:whisp/ui/static" \
  --add-data "packaging/assets/ggml-base.en.bin:." \
  --add-binary "packaging/assets/whisper-cli:." \
  --add-binary "packaging/assets/libwhisper.1.dylib:." \
  --add-binary "packaging/assets/libggml.0.dylib:." \
  --add-binary "packaging/assets/libggml-base.0.dylib:." \
  --add-binary "packaging/assets/libggml-cpu.so:." \
  --add-binary "packaging/assets/libggml-blas.so:." \
  --hidden-import rumps \
  --collect-all sounddevice \
  packaging/launcher.py

PLIST="dist/Whisp.app/Contents/Info.plist"
# Menu-bar only (no Dock icon)
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$PLIST" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$PLIST"
# Permission usage strings
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string 'Whisp records your voice for dictation.'" "$PLIST" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSAppleEventsUsageDescription string 'Whisp pastes transcribed text into the active app.'" "$PLIST" 2>/dev/null || true

# Ad-hoc sign so it launches locally (unsigned = right-click Open on first run)
codesign --force --deep --sign - \
  --entitlements packaging/Whisp.entitlements dist/Whisp.app

# Build the DMG
rm -f dist/Whisp.dmg
create-dmg --volname "Whisp" --app-drop-link 480 180 \
  --window-size 720 400 --icon "Whisp.app" 200 180 \
  dist/Whisp.dmg dist/Whisp.app 2>/dev/null \
  || hdiutil create -volname "Whisp" -srcfolder dist/Whisp.app -ov -format UDZO dist/Whisp.dmg

echo "Built: dist/Whisp.dmg"
ls -lh dist/Whisp.dmg
