import re
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    text: str
    engine: str   # "groq" or "local"


# Whisper emits bracketed markers for non-speech audio, e.g. "[BLANK_AUDIO]",
# "[ Silence ]", "(music)". Strip them so they never get pasted.
_ARTIFACT = re.compile(
    r"[\[(]\s*(blank[ _]?audio|silence|inaudible|music[^)\]]*|sound[^)\]]*|"
    r"pause|noise|no speech|applause|laughter|beep|click|"
    r"clears throat|coughs?|sighs?|breathing|wind)\s*[\])]",
    re.IGNORECASE,
)


def strip_artifacts(text: str) -> str:
    cleaned = _ARTIFACT.sub("", text or "")
    return re.sub(r"\s+", " ", cleaned).strip()
