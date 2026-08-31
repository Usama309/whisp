# Changelog — Whisp

## [Unreleased]
### Added
- [2026-08-28] History-page audio upload transcription: accepts up to 200 MB of supported audio, normalizes it to 16 kHz mono WAV, uses the existing Groq/local fallback and cleanup pipeline, saves the transcript/audio to history, and never pastes upload results into the frontmost app. Added upload UI, endpoint coverage, conversion coverage, and bundled soundfile support.
- [2026-06-26] Native Apple Silicon (arm64) build: compiled whisper.cpp v1.7.4 from source (CPU+Accelerate), arm64 venv + PyInstaller; new packaging/fetch_assets_arm64.sh + build_app_arm64.sh. App now runs native (no Rosetta). Distributed installer is arm64 (v2.0).
- [2026-06-26] Built-in gentle noise reduction (high-pass + spectral subtraction, numpy-only) with a Settings toggle; complements macOS Voice Isolation.
- [2026-06-26] Long-audio support: parallel chunked transcription (any length, 1hr+ works) with Groq RPM pacing + 429 backoff. Verified 1hr in ~72s.
- [2026-06-26] Production UI overhaul (dark pro-tool): redesigned history (stats, day-grouping, play/copy/expand/flag/delete/search) and settings (premium toggles), shared design system.
- [2026-06-26] Launch-at-login: LaunchAgent (RunAtLoad + KeepAlive on crash) installed by the .pkg and toggleable from Settings (whisp/autostart.py).
- [2026-06-26] Transcribe-only guardrail in cleanup: rejects output that "answered" instead of transcribing and falls back to faithful formatting; long transcripts cleaned in blocks. 50/50 scenario test passes.
- [2026-06-09] Design spec and implementation plan.
- [2026-06-09] Phase 0 bootstrap: venv, dependencies, package skeleton, governance files.
- [2026-06-09] Core data layer: config (single source of truth), settings, Apple-epoch time, Willow-schema history store.
- [2026-06-09] App-context tone mapping, Groq HTTP client, cleanup service (LLM + offline regex fallback).
- [2026-06-09] Transcription: engine router, Groq cloud (whisper-large-v3), local whisper.cpp; local path verified end-to-end.
- [2026-06-09] Push-to-talk audio recorder (sounddevice), WAV archive for history replay.
- [2026-06-09] macOS integration: clipboard paste + Cmd-V inserter, global CGEventTap hold-to-talk hotkey.
- [2026-06-09] Dictation orchestration pipeline + factory; full offline chain verified (transcribe→cleanup→history).
- [2026-06-09] rumps menu-bar shell with hotkey-driven dictation.
- [2026-06-09] Flask history + settings UI with audio replay.
- [2026-06-09] Packaging: relocated whisper/ggml dylibs and backend plugins to @loader_path; PyInstaller .app + DMG; verified self-contained on a simulated brew-free Mac.

### Changed
- [2026-06-26] Settings now reload at the start of each dictation, so toggles (mute, sound cues, noise reduction, mic) apply immediately without an app restart.
- [2026-06-26] Default noise_reduction OFF (Groq whisper is noise-robust; DSP pre-processing slightly hurt accuracy).
- [2026-06-09] Archive recordings as WAV instead of opus to drop the ffmpeg bundling dependency.

### Removed
- [2026-06-26] Pause-background-media feature (media-key toggle was unreliable: started already-paused songs). Mute-while-recording is the reliable replacement; deleted orphaned media.py.

### Fixed
- [2026-06-26] Intermittent freeze/deadlock: record via a blocking read on our own thread instead of a PortAudio callback (eliminates GIL deadlock vs stream close, esp. under Rosetta on Apple Silicon).
- [2026-06-26] Long recordings failed (>25MB / upload timeout): fixed via chunking + generous per-chunk timeout; bounded all blocking steps so the app can never permanently freeze.
- [2026-06-26] Groq→local fallback now triggers on any Groq failure (bad key/quota/outage), not just when fully offline; fast connect timeout.
- [2026-06-09] PyInstaller could not find the `whisp` package (added `--paths .` / `--collect-submodules whisp`).
