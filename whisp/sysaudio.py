"""Mute system output while recording so the mic doesn't pick up playing audio
(mirrors Willow's auto-mute). All best-effort; never raises into the caller."""
import subprocess


def _osascript(script: str) -> str:
    try:
        out = subprocess.run(["osascript", "-e", script],
                             capture_output=True, text=True, timeout=3)
        return out.stdout.strip()
    except Exception:
        return ""


def is_output_muted() -> bool:
    return _osascript("output muted of (get volume settings)") == "true"


def mute_output() -> None:
    _osascript("set volume with output muted")


def unmute_output() -> None:
    _osascript("set volume without output muted")
