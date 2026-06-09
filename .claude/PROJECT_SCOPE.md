# Project Scope — Whisp

## Current State
Working v1, fully built and committed:
- Menu-bar dictation app (rumps) with global Fn hold-to-talk hotkey (CGEventTap).
- Whisper transcription: Groq cloud (whisper-large-v3) primary + bundled local whisper.cpp fallback. Local engine verified end-to-end and proven self-contained on a simulated brew-free Mac.
- LLM cleanup (Groq llama-3.3-70b) with tone + frontmost-app context; offline regex fallback.
- Clipboard + Cmd-V paste at cursor; optional Enter; clipboard restored after paste.
- History stored as one JSON per dictation (Willow-compatible schema); WAV audio archived for replay.
- Local Flask UI: searchable history (replay/copy/flag/delete) + Settings (Groq key, hotkey, language, model, cleanup, press-Enter).
- Packaged as `dist/Whisp.dmg` (PyInstaller .app + Applications shortcut). Boots cleanly; UI serves.
- 30 passing unit/integration tests.

## In Progress
- Final live test on this Mac (needs Microphone + Accessibility grants and a real spoken dictation).

## Next Priorities
1. Live dictation test in the packaged app (hold Fn, speak, confirm paste + history).
2. Optional: custom app icon; larger local model option in Settings.

## Known Issues
- See KNOWN_ISSUES.md (unsigned Gatekeeper prompt; Fn-key reliability fallback to Right ⌘).

## Decisions
- See DECISIONS.md. Notable: WAV archive (no ffmpeg); @loader_path-relocated whisper/ggml libs + bundled ggml backend plugins for dependency-free local transcription.
