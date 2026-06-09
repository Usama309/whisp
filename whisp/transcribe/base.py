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


# Phrases Whisper hallucinates on silent/near-silent audio (learned from subtitle
# training data). These are never legitimately dictated, so a transcript that is
# ONLY one of these is treated as empty.
_HALLUCINATION_MARKERS = (
    "amara.org",
    "subtitles by",
    "thanks for watching",
    "thank you for watching",
    "subscribe to my channel",
    "transcription by",
    "transcribed by",
)


def is_hallucination(text: str) -> bool:
    t = (text or "").strip().lower().strip(".!?,… ")
    if not t:
        return False
    return any(marker in t for marker in _HALLUCINATION_MARKERS)
