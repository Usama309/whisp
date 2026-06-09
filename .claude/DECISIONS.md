# Decisions — Whisp

- Groq `whisper-large-v3` primary STT + local `whisper.cpp` fallback (mirrors Willow's cloud+offline strategy).
- LLM cleanup via Groq `llama-3.3-70b-versatile`; offline falls back to regex filler-strip.
- History stored as one JSON per dictation in Willow's schema for familiarity/compatibility.
- Packaged unsigned (no Apple Developer account); first-run via right-click → Open.
- Archive recordings as WAV (not opus) to avoid bundling ffmpeg; WAV plays natively in the history page.
- Bundle whisper.cpp self-contained: copy whisper-cli + libwhisper/libggml/libggml-base dylibs AND the runtime backend plugins (libggml-cpu.so, libggml-blas.so), relocated to @loader_path. ggml falls back to the executable's directory for backends, verified by hiding Homebrew and re-running the bundled binary.
- Flask UI served on an ephemeral 127.0.0.1 port from a daemon thread; opened in the default browser.
