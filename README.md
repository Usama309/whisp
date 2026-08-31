# Whisp — free voice dictation for Mac

Hold a key, speak in any app, and your words are transcribed, cleaned up, and typed
at your cursor. Every dictation is saved to a searchable history. A free clone of
Willow Voice.

## Install (from the DMG)
1. Open `Whisp.dmg` and drag **Whisp** into **Applications**.
2. **First time only:** right-click `Whisp.app` → **Open** → **Open** (the app is
   unsigned, so macOS asks once).
3. When prompted, allow **Microphone** and **Accessibility** (System Settings →
   Privacy & Security). Accessibility is required for the global hotkey and paste.

## Use
- **Hold the Fn key, speak, release.** The cleaned text is pasted where your cursor is.
- Open **History**, choose an audio file, and click **Transcribe** to add its cleaned transcript to history. Uploads support WAV, MP3, M4A, FLAC, and OGG files up to 200 MB. Uploaded audio is never pasted into the frontmost app.
- Menu-bar 🎙️ icon → **History** to search / replay / copy past dictations.
- Menu-bar 🎙️ icon → **Settings** to change the hotkey, language, and tone.

## Better speed/quality (optional, free)
By default Whisp transcribes **on your Mac** (works offline, no signup, fully private).
For near-instant, higher-accuracy transcription plus AI cleanup (filler removal,
formatting, your tone):
1. Get a free key at <https://console.groq.com> (no credit card).
2. Menu → Settings → paste it into **Groq API key** → Save.

## How it works
`hold hotkey → record mic → Whisper transcribes (Groq cloud or bundled whisper.cpp)
→ LLM cleans it up in your style → paste at cursor → save to history`

The local engine is fully bundled — `whisper-cli`, its libraries, and a `base.en`
model ship inside the app, so it runs on any Mac with no dependencies.

## Build it yourself
```bash
./packaging/setup_dev.sh        # one-time: brew tools + venv + deps
source .venv/bin/activate
pytest -q                       # run the test suite
./packaging/build_app.sh        # produces dist/Whisp.dmg
```

## Notes
- Unsigned build (no paid Apple Developer account). Gatekeeper asks once; use
  right-click → Open the first time, then it launches normally.
- Built on Intel → runs on Intel and Apple Silicon (via Rosetta).
