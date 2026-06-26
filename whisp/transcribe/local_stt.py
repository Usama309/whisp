import os
import subprocess
import time

from whisp.logs import log
from whisp.transcribe.base import TranscriptionResult
from whisp.transcribe.chunking import transcribe_chunked


class LocalTranscriber:
    """Runs whisper.cpp `whisper-cli` and reads plain-text output from stdout."""

    def __init__(self, binary: str, model_path: str, language: str = "en", threads: int = None):
        self._binary = binary
        self._model = model_path
        self._language = language
        # whisper.cpp defaults to 4 threads; use more cores for ~35% faster runs.
        self._threads = threads or min(8, os.cpu_count() or 4)

    def _transcribe_one(self, wav_path: str) -> str:
        cmd = [
            self._binary,
            "-m", self._model,
            "-f", wav_path,
            "-l", self._language or "auto",
            "-t", str(self._threads),
            "-nt",          # no timestamps
            "-np",          # no progress prints
        ]
        # Per ~2-min chunk; generous enough for slow local decode under Rosetta.
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            raise RuntimeError(f"whisper-cli failed: {proc.stderr[:200]}")
        return " ".join(line.strip() for line in proc.stdout.splitlines() if line.strip())

    def transcribe(self, wav_path: str) -> TranscriptionResult:
        t = time.time()
        # Sequential chunks for the local engine (it is CPU-bound and already
        # multi-threaded; running chunks in parallel would oversubscribe cores).
        text = transcribe_chunked(wav_path, self._transcribe_one, parallel=False)
        log(f"STT  engine=local  model={os.path.basename(self._model)}  secs={time.time() - t:.2f}")
        return TranscriptionResult(text=text.strip(), engine="local")
