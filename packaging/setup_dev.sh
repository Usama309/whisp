#!/usr/bin/env bash
set -euo pipefail
# Brew tools used at dev + bundled at build time
brew list python@3.11 >/dev/null 2>&1 || brew install python@3.11
brew list portaudio   >/dev/null 2>&1 || brew install portaudio
brew list ffmpeg      >/dev/null 2>&1 || brew install ffmpeg
brew list whisper-cpp >/dev/null 2>&1 || brew install whisper-cpp
brew list create-dmg  >/dev/null 2>&1 || brew install create-dmg

PY=/usr/local/opt/python@3.11/bin/python3.11
[ -x "$PY" ] || PY=$(command -v python3.11)
"$PY" -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "Dev env ready. Activate with: source .venv/bin/activate"
