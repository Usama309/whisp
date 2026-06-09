# Decisions — Whisp

- Groq `whisper-large-v3` primary STT + local `whisper.cpp` fallback (mirrors Willow's cloud+offline strategy).
- LLM cleanup via Groq `llama-3.3-70b-versatile`; offline falls back to regex filler-strip.
- History stored as one JSON per dictation in Willow's schema for familiarity/compatibility.
- Packaged unsigned (no Apple Developer account); first-run via right-click → Open.
