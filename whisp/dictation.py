from whisp.transcribe.base import strip_artifacts


class DictationPipeline:
    """Wires transcription -> cleanup -> insertion -> history. Dependencies injected."""

    def __init__(self, transcriber, cleanup, inserter, history,
                 frontmost_app, press_enter):
        self._transcriber = transcriber
        self._cleanup = cleanup            # callable(raw, app_name) -> str
        self._inserter = inserter          # callable(text, press_enter)
        self._history = history
        self._frontmost_app = frontmost_app  # callable -> str
        self._press_enter = press_enter

    def run(self, wav_path: str, duration: float, audio_url: str):
        result = self._transcriber.transcribe(wav_path)
        raw = strip_artifacts((result.text or "").strip())
        if not raw:
            return None
        app_name = self._frontmost_app()
        cleaned = (self._cleanup(raw, app_name) or "").strip()
        if not cleaned:
            return None
        self._inserter(cleaned, self._press_enter)
        return self._history.add(
            text=cleaned, raw_text=raw, duration=duration,
            audio_url=audio_url, app_context=app_name,
        )
