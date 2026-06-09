"""Audible cues for recording start / done / no-speech, like Willow's bumps.
Uses built-in macOS system sounds via `afplay` (non-blocking, best-effort)."""
import subprocess

_SOUNDS = {
    "start": "/System/Library/Sounds/Pop.aiff",
    "done": "/System/Library/Sounds/Glass.aiff",
    "empty": "/System/Library/Sounds/Funk.aiff",
}


def play(name: str) -> None:
    path = _SOUNDS.get(name)
    if not path:
        return
    try:
        subprocess.Popen(["afplay", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass
