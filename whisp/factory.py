import os

from whisp.net import is_online
from whisp.cleanup import CleanupService
from whisp.context import frontmost_app_name
from whisp.history import HistoryStore
from whisp.inserter import paste_text
from whisp.settings import Settings
from whisp.transcribe.router import choose_engine
from whisp.transcribe.groq_stt import GroqTranscriber
from whisp.transcribe.local_stt import LocalTranscriber
from whisp.dictation import DictationPipeline


def _resource(*parts) -> str:
    """Locate a bundled resource both in dev and inside a PyInstaller .app."""
    import sys
    if getattr(sys, "frozen", False):
        base = os.path.join(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = os.path.join(os.path.dirname(__file__), "..", "packaging", "assets")
    return os.path.join(base, *parts)


def whisper_binary() -> str:
    bundled = _resource("whisper-cli")
    return bundled if os.path.exists(bundled) else "/usr/local/bin/whisper-cli"


def model_path(local_model: str) -> str:
    bundled = _resource(f"ggml-{local_model}.bin")
    if os.path.exists(bundled):
        return bundled
    return os.path.expanduser(f"~/.whisp-models/ggml-{local_model}.bin")


def build_pipeline(settings: Settings) -> DictationPipeline:
    key = settings.get("groq_api_key", "")
    language = settings.get("language", "en")
    engine = choose_engine(api_key=key, online=is_online())
    if engine == "groq":
        transcriber = GroqTranscriber(api_key=key, language=language)
    else:
        transcriber = LocalTranscriber(
            binary=whisper_binary(),
            model_path=model_path(settings.get("local_model", "base.en")),
            language=language,
        )
    cleanup_enabled = settings.get("cleanup_enabled", True)
    cleaner = CleanupService(
        api_key=key if cleanup_enabled else "",
        online=is_online,
        tones=settings.get("tones", {}),
        dictionary=settings.get("custom_dictionary", {}),
    )
    return DictationPipeline(
        transcriber=transcriber,
        cleanup=cleaner.clean,
        inserter=paste_text,
        history=HistoryStore(),
        frontmost_app=frontmost_app_name,
        press_enter=settings.get("press_enter", False),
    )
