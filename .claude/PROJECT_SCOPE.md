# Project Scope — Whisp

## Current State
Production-track v1, built/committed/deployed (distributed via `.pkg` installer that auto-installs Rosetta, removes quarantine, sets up launch-at-login; baked Groq key):
- Menu-bar dictation app (rumps), Fn hold-to-talk; records via blocking read thread (no PortAudio callback → no GIL deadlock under Rosetta on Apple Silicon).
- Transcription: Groq cloud whisper-large-v3 primary + bundled local whisper.cpp fallback. **Any-length via parallel chunking** (1hr verified ~72s) with RPM pacing + 429 backoff. Falls back to local on ANY Groq failure; all blocking steps time-bounded (never permanently freezes).
- Cleanup: Groq llama-3.3-70b with a **transcribe-only guardrail** (never answers/opines; 50/50 tested) + offline regex fallback; long transcripts cleaned in blocks.
- Mute system audio while recording (default). Clipboard + Cmd-V paste; optional Enter.
- History (one JSON/dictation, Willow schema) + WAV archive.
- **Production UI (dark pro-tool)**: history (stats, day-grouping, play/copy/expand/flag/delete/search) + settings (premium toggles, launch-at-login control). Served by local Flask.
- Launch-at-login via LaunchAgent (RunAtLoad + relaunch on crash).
- 59 passing tests.
- Target machine: Apple M1 Pro (app currently x86_64 under Rosetta; native arm64 build is a possible future improvement). Noise handling: user uses macOS Voice Isolation.

## In Progress
- Final live test on this Mac (needs Microphone + Accessibility grants and a real spoken dictation).

## Next Priorities
1. Live dictation test in the packaged app (hold Fn, speak, confirm paste + history).
2. Optional: custom app icon; larger local model option in Settings.

## Known Issues
- See KNOWN_ISSUES.md (unsigned Gatekeeper prompt; Fn-key reliability fallback to Right ⌘).

## Decisions
- See DECISIONS.md. Notable: WAV archive (no ffmpeg); @loader_path-relocated whisper/ggml libs + bundled ggml backend plugins for dependency-free local transcription.
