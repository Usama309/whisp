import subprocess

from whisp.transcribe.base import TranscriptionResult


class LocalTranscriber:
    """Runs whisper.cpp `whisper-cli` and reads plain-text output from stdout."""

    def __init__(self, binary: str, model_path: str, language: str = "en"):
        self._binary = binary
        self._model = model_path
        self._language = language

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        cmd = [
            self._binary,
            "-m", self._model,
            "-f", wav_path,
            "-l", self._language or "auto",
            "-nt",          # no timestamps
            "-np",          # no progress prints
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"whisper-cli failed: {proc.stderr[:200]}")
        text = " ".join(line.strip() for line in proc.stdout.splitlines() if line.strip())
        return TranscriptionResult(text=text.strip(), engine="local")
