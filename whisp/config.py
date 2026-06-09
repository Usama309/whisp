import os
from pathlib import Path

APP_ID = "com.usama.whisp"
APP_NAME = "Whisp"


def support_dir() -> Path:
    override = os.environ.get("WHISP_SUPPORT_DIR")
    base = Path(override) if override else Path.home() / "Library" / "Application Support" / APP_ID
    base.mkdir(parents=True, exist_ok=True)
    return base


def settings_path() -> Path:
    return support_dir() / "settings.json"


def transcripts_dir() -> Path:
    d = support_dir() / "Transcripts"
    d.mkdir(parents=True, exist_ok=True)
    return d


def recordings_dir() -> Path:
    d = support_dir() / "Recordings"
    d.mkdir(parents=True, exist_ok=True)
    return d


# Groq endpoints
GROQ_BASE = "https://api.groq.com/openai/v1"
GROQ_STT_URL = f"{GROQ_BASE}/audio/transcriptions"
GROQ_CHAT_URL = f"{GROQ_BASE}/chat/completions"
GROQ_STT_MODEL = "whisper-large-v3"
GROQ_CHAT_MODEL = "llama-3.3-70b-versatile"

# Default hotkey: the Fn key. Hold to dictate, double-tap to lock (hands-free),
# single-tap while locked to unlock. (Combo mode with Left Shift + Left Control
# remains available by setting mode="combo".)
DEFAULT_HOTKEY = {
    "mode": "fn",
    "name": "Fn",
    "combo": [56, 59],
    "comboNames": ["Left Shift", "Left Control"],
    "lockKeyCode": 56,
}

DEFAULT_SETTINGS = {
    "groq_api_key": "",
    "hotkey": DEFAULT_HOTKEY,
    "local_model": "base.en",
    "microphone": None,            # None = system default
    "language": "en",
    "press_enter": False,
    "cleanup_enabled": True,
    "mute_while_recording": False,
    "pause_media_while_recording": True,
    "sounds_enabled": True,
    "tones": {
        "email": "Professional, complete sentences, polite sign-offs.",
        "work": "Clear and concise, direct, lightly formal.",
        "casual": "Relaxed and friendly, contractions are fine.",
        "prompt": "Imperative and precise, good for instructing an AI or writing code comments.",
        "other": "Neutral and clear.",
    },
    "custom_dictionary": {},        # spoken -> written, e.g. {"groq": "Groq"}
}
