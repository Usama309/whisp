# Tasklist — Whisp

## Pending
- [ ] Live test on this Mac: grant Microphone + Accessibility, confirm Fn hold-to-talk dictation pastes at cursor
- [ ] (Optional) Custom app icon

## Completed
- [x] History-page audio upload transcription, conversion, no-paste behavior, tests, and native arm64 packaging (2026-08-28)
- [x] Design spec (2026-06-09)
- [x] Implementation plan (2026-06-09)
- [x] Phase 0: Bootstrap (2026-06-09)
- [x] Phase 1: Core data layer — config, settings, time, history (2026-06-09)
- [x] Phase 2: Cleanup + context — Groq client, LLM cleanup, offline fallback (2026-06-09)
- [x] Phase 3: Transcription — router, Groq, local whisper.cpp (local verified) (2026-06-09)
- [x] Phase 4: Audio recorder — sounddevice + WAV archive (2026-06-09)
- [x] Phase 5: macOS integration — clipboard paste + CGEventTap hotkey (2026-06-09)
- [x] Phase 6: Orchestrator — dictation pipeline + factory (full offline chain verified) (2026-06-09)
- [x] Phase 7: Menu-bar shell — rumps app (boots cleanly) (2026-06-09)
- [x] Phase 8: Flask UI — history + settings + audio replay (2026-06-09)
- [x] Phase 9: Packaging — relocated dylibs/backends, PyInstaller .app, DMG (friend-machine verified) (2026-06-09)
