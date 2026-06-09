from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    engine: str   # "groq" or "local"
