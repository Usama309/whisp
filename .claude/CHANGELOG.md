# Changelog — Whisp

## [Unreleased]
### Added
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
- [2026-06-09] Archive recordings as WAV instead of opus to drop the ffmpeg bundling dependency.

### Fixed
- [2026-06-09] PyInstaller could not find the `whisp` package (added `--paths .` / `--collect-submodules whisp`).
