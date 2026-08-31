# Known Issues — Whisp

- Unsigned app triggers Gatekeeper; open via right-click → Open the first time.
- Fn-key capture may be unreliable on some macOS builds; Right ⌘ is the fallback default.
- Live upload smoke test: Groq STT succeeded, but the configured Groq cleanup model returned HTTP 404, so Whisp used its local faithful cleanup fallback. Upload transcription still completed successfully.
