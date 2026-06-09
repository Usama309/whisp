import os
import subprocess
import time

from whisp.logs import log
from whisp.transcribe.base import TranscriptionResult


class LocalTranscriber:
    """Runs whisper.cpp `whisper-cli` and reads plain-text output from stdout."""

    def __init__(self, binary: str, model_path: str, language: str = "en", threads: int = None):
        self._binary = binary
        self._model = model_path
        self._language = language
        # whisper.cpp defaults to 4 threads; use more cores for ~35% faster runs.
        self._threads = threads or min(8, os.cpu_count() or 4)

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        cmd = [
            self._binary,
            "-m", self._model,
            "-f", wav_path,
            "-l", self._language or "auto",
            "-t", str(self._threads),
            "-nt",          # no timestamps
            "-np",          # no progress prints
        ]
        t = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            raise RuntimeError(f"whisper-cli failed: {proc.stderr[:200]}")
        text = " ".join(line.strip() for line in proc.stdout.splitlines() if line.strip())
        log(f"STT  engine=local  model={os.path.basename(self._model)}  secs={time.time() - t:.2f}")
        return TranscriptionResult(text=text.strip(), engine="local")
