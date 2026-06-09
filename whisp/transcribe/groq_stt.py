from whisp import groq_client
from whisp.transcribe.base import TranscriptionResult


class GroqTranscriber:
    def __init__(self, api_key: str, language: str = "en", prompt: str = None):
        self._api_key = api_key
        self._language = language
        self._prompt = prompt

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        text = groq_client.transcribe(self._api_key, wav_path, self._language, self._prompt)
        return TranscriptionResult(text=text.strip(), engine="groq")
