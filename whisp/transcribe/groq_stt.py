import time

from whisp import config, groq_client
from whisp.logs import log
from whisp.transcribe.base import TranscriptionResult
from whisp.transcribe.chunking import transcribe_chunked


class GroqTranscriber:
    def __init__(self, api_key: str, language: str = "en", prompt: str = None):
        self._api_key = api_key
        self._language = language
        self._prompt = prompt

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        t = time.time()
        # Long recordings are split into short chunks and uploaded in parallel,
        # so any length transcribes fast without hitting size/timeout limits.
        text = transcribe_chunked(
            wav_path,
            lambda p: groq_client.transcribe(self._api_key, p, self._language, self._prompt),
            parallel=True,
        )
        log(f"STT  engine=groq  model={config.GROQ_STT_MODEL}  "
            f"secs={time.time() - t:.2f}  words={len(text.split())}")
        return TranscriptionResult(text=text.strip(), engine="groq")
