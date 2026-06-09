import shutil
import tempfile
import time
import wave
from urllib.parse import quote

import numpy as np
import sounddevice as sd

from whisp import config

SAMPLE_RATE = 16000
CHANNELS = 1


def rms_level(wav_path: str) -> float:
    """Root-mean-square amplitude of a 16-bit mono WAV (0..32768). 0.0 on error."""
    import numpy as np
    try:
        with wave.open(wav_path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
        if not frames:
            return 0.0
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float64)
        if samples.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(samples ** 2)))
    except Exception:
        return 0.0


def is_silent(wav_path: str, threshold: float = 200.0) -> bool:
    """True when the recording is essentially silence/noise (no real speech).
    Prevents Whisper from hallucinating phantom text on empty audio."""
    return rms_level(wav_path) < threshold


def prewarm_microphone() -> None:
    """Briefly open and close an input stream to trigger the macOS mic prompt
    early, so the first real dictation doesn't stall on a permission dialog."""
    try:
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16")
        stream.start()
        stream.stop()
        stream.close()
    except Exception:
        pass


class Recorder:
    """Push-to-talk recorder: start() begins capture, stop() returns (wav_path, duration)."""

    def __init__(self, device=None):
        self._device = device
        self._stream = None
        self._frames = []
        self._start_time = None
        self.level = 0.0   # live input level 0..1 for the menu-bar VU meter

    def start(self):
        self._frames = []
        self._start_time = time.time()

        def callback(indata, frames, time_info, status):
            self._frames.append(indata.copy())
            try:
                rms = float(np.sqrt(np.mean(indata.astype(np.float64) ** 2)))
                self.level = min(1.0, rms / 8000.0)
            except Exception:
                pass

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16",
            device=self._device, callback=callback,
        )
        self._stream.start()

    def stop(self):
        duration = time.time() - (self._start_time or time.time())
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        wav_path = tempfile.mktemp(suffix=".wav", prefix="whisp_")
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            for chunk in self._frames:
                wf.writeframes(chunk.tobytes())
        return wav_path, duration


def archive_recording(wav_path: str) -> str:
    """Copy the recording WAV into the Recordings dir; returns a file:// URL.

    WAV is kept (rather than transcoding to opus) so playback needs no external
    binary and works natively in the history page. Best-effort; returns "" on error.
    """
    ts = time.strftime("%Y-%m-%dT%H-%M-%S")
    out = config.recordings_dir() / f"recording_{ts}.wav"
    try:
        shutil.copyfile(wav_path, out)
        return "file://" + quote(str(out))
    except OSError:
        return ""
