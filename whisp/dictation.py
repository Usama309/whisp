from whisp.transcribe.base import strip_artifacts, is_hallucination
from whisp.logs import log


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

    def _prepare(self, wav_path: str, app_context=None):
        result = self._transcriber.transcribe(wav_path)
        raw = strip_artifacts((result.text or "").strip())
        if not raw or is_hallucination(raw):
            return None
        app_name = self._frontmost_app() if app_context is None else app_context
        cleaned = (self._cleanup(raw, app_name) or "").strip()
        if not cleaned:
            return None
        return raw, cleaned, app_name, result

    def _save(self, wav_path: str, duration: float, audio_url: str,
              app_context=None, insert=True):
        prepared = self._prepare(wav_path, app_context=app_context)
        if prepared is None:
            return None
        raw, cleaned, app_name, result = prepared
        if insert:
            self._inserter(cleaned, self._press_enter)
        log(f"DICTATION  app='{app_name}'  stt={result.engine}  "
            f"dur={duration:.1f}s  raw='{raw[:150]}'  =>  cleaned='{cleaned[:150]}'")
        return self._history.add(
            text=cleaned, raw_text=raw, duration=duration,
            audio_url=audio_url, app_context=app_name,
        )

    def run(self, wav_path: str, duration: float, audio_url: str):
        return self._save(
            wav_path=wav_path,
            duration=duration,
            audio_url=audio_url,
            insert=True,
        )

    def run_uploaded(self, wav_path: str, duration: float, audio_url: str):
        """Transcribe an uploaded file without pasting into the frontmost app."""
        return self._save(
            wav_path=wav_path,
            duration=duration,
            audio_url=audio_url,
            app_context="Audio upload",
            insert=False,
        )
