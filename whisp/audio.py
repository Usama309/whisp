import os
import shutil
import subprocess
import tempfile
import threading
import time
import wave
from urllib.parse import quote

import numpy as np
import sounddevice as sd

from whisp import config

SAMPLE_RATE = 16000
CHANNELS = 1


class AudioDecodeError(ValueError):
    """Raised when an uploaded file cannot be converted to Whisp's WAV format."""


def _write_pcm_wav(path: str, samples, sample_rate: int) -> None:
    samples = np.asarray(samples, dtype=np.float32).reshape(-1)
    if not len(samples) or sample_rate <= 0:
        raise AudioDecodeError("The audio file contains no readable audio.")
    if sample_rate != SAMPLE_RATE:
        target_frames = max(1, round(len(samples) * SAMPLE_RATE / sample_rate))
        source_positions = np.arange(len(samples), dtype=np.float64)
        target_positions = np.linspace(0, len(samples) - 1, target_frames)
        samples = np.interp(target_positions, source_positions, samples).astype(np.float32)
    pcm = np.clip(np.rint(samples), -32768, 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm.tobytes())


def _normalize_with_soundfile(source_path: str, output_path: str) -> None:
    # soundfile handles WAV, FLAC, OGG, and other libsndfile formats. It is
    # imported lazily so the app can still report a useful conversion error if
    # a packaged runtime ever loses this optional decoder.
    import soundfile as sf

    data, sample_rate = sf.read(
        source_path, dtype="int16", always_2d=True,
    )
    if data.size == 0:
        raise AudioDecodeError("The audio file contains no readable audio.")
    mono = data.astype(np.float32).mean(axis=1)
    _write_pcm_wav(output_path, mono, int(sample_rate))


def _normalize_with_afconvert(source_path: str, output_path: str) -> None:
    # afconvert ships with macOS and covers common compressed formats such as
    # MP3, M4A, AAC, and AIFF without adding ffmpeg to the distributed app.
    fd, converted_path = tempfile.mkstemp(suffix=".wav", prefix="whisp_afconvert_")
    os.close(fd)
    # afconvert expects to create its destination and may leave an existing
    # mkstemp placeholder untouched.
    os.remove(converted_path)
    try:
        proc = subprocess.run(
            ["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1",
             source_path, converted_path],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[:160]
            raise AudioDecodeError(detail or "macOS could not decode this audio file.")
        # macOS may emit WAVE_FORMAT_EXTENSIBLE here. Read it with libsndfile
        # and write a plain PCM WAV so Python's duration reader and whisper-cli
        # see the same format as microphone recordings.
        _normalize_with_soundfile(converted_path, output_path)
    except AudioDecodeError:
        raise
    except Exception as exc:
        raise AudioDecodeError("The converted audio file is invalid.") from exc
    finally:
        try:
            os.remove(converted_path)
        except OSError:
            pass


def normalize_uploaded_audio(source_path: str) -> str:
    """Convert an uploaded audio file to a temporary 16 kHz mono WAV.

    The caller owns the returned temporary file and must remove it after the
    transcription job finishes. libsndfile is attempted first for formats it
    supports; macOS's built-in afconvert handles common compressed formats.
    """
    fd, output_path = tempfile.mkstemp(suffix=".wav", prefix="whisp_upload_")
    os.close(fd)
    try:
        try:
            _normalize_with_soundfile(source_path, output_path)
        except Exception as soundfile_error:
            try:
                _normalize_with_afconvert(source_path, output_path)
            except Exception as afconvert_error:
                if isinstance(afconvert_error, AudioDecodeError):
                    raise AudioDecodeError(
                        "Whisp could not read this audio file. Try WAV, MP3, M4A, FLAC, or OGG."
                    ) from soundfile_error
                raise AudioDecodeError(
                    "Audio conversion is unavailable on this Mac."
                ) from afconvert_error
        return output_path
    except Exception:
        try:
            os.remove(output_path)
        except OSError:
            pass
        raise


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


def _denoise_block(x, rate, hp_hz, sub, floor):
    """Gentle spectral-subtraction + high-pass on one block of float32 samples."""
    n = len(x)
    if n < 512:
        return x
    win = 1024
    hop = win // 4
    pad = (-(n - win)) % hop if n > win else (win - n)
    xp = np.concatenate([x, np.zeros(pad, np.float32)])
    nf = 1 + (len(xp) - win) // hop
    window = np.hanning(win).astype(np.float32)
    idx = np.arange(win)[None, :] + hop * np.arange(nf)[:, None]
    frames = xp[idx] * window
    spec = np.fft.rfft(frames, axis=1)
    mag = np.abs(spec)
    phase = np.angle(spec)
    noise = np.percentile(mag, 20, axis=0)               # steady-noise floor per bin
    clean = np.maximum(mag - sub * noise, floor * mag)   # conservative subtraction
    freqs = np.fft.rfftfreq(win, 1.0 / rate)
    clean[:, freqs < hp_hz] = 0.0                        # high-pass: kill fan/AC rumble
    iframes = (np.fft.irfft(clean * np.exp(1j * phase), n=win, axis=1) * window).astype(np.float32)
    out = np.zeros(len(xp), np.float32)
    norm = np.zeros(len(xp), np.float32)
    np.add.at(out, idx.ravel(), iframes.ravel())
    np.add.at(norm, idx.ravel(), np.tile(window ** 2, nf))
    norm[norm < 1e-6] = 1.0
    return (out / norm)[:n]


def reduce_noise(samples_int16, rate, hp_hz=85.0, sub=1.0, floor=0.2):
    """Gentle, dependency-free noise reduction (fan/AC rumble + steady hiss).
    Processed in 30s blocks so memory stays bounded on hour-long recordings.
    Verified to preserve transcription quality; safe to run alongside macOS
    Voice Isolation."""
    x = np.asarray(samples_int16, dtype=np.int16).reshape(-1)
    if len(x) < rate // 2:        # < 0.5s: not worth it
        return x
    xf = x.astype(np.float32)
    block = rate * 30
    out = np.empty_like(xf)
    for s in range(0, len(xf), block):
        seg = xf[s:s + block]
        out[s:s + len(seg)] = _denoise_block(seg, rate, hp_hz, sub, floor)
    return np.clip(out, -32768, 32767).astype(np.int16)


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

    def __init__(self, device=None, denoise=False):
        self._device = device
        self._denoise = denoise
        self._frames = []
        self._start_time = None
        self._stop_flag = threading.Event()
        self._thread = None
        self.level = 0.0   # live input level 0..1 for the menu-bar VU meter

    def start(self):
        self._frames = []
        self._stop_flag.clear()
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def _record_loop(self):
        # Read audio on our OWN thread via a blocking read, not via a PortAudio
        # callback. A Python callback fired on PortAudio's audio thread can
        # deadlock against stream close over the GIL (very likely under Rosetta
        # on Apple Silicon); a blocking read on a thread we control cannot. The
        # `with` block opens and (on exit) cleanly closes the stream on this same
        # thread, after the read loop has stopped, so there is no close-vs-callback race.
        blocksize = SAMPLE_RATE // 10   # 0.1s chunks
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                dtype="int16", device=self._device,
                                blocksize=blocksize) as stream:
                while not self._stop_flag.is_set():
                    data, _overflowed = stream.read(blocksize)
                    self._frames.append(data.copy())
                    try:
                        rms = float(np.sqrt(np.mean(data.astype(np.float64) ** 2)))
                        self.level = min(1.0, rms / 8000.0)
                    except Exception:
                        pass
        except Exception:
            pass

    def stop(self):
        duration = time.time() - (self._start_time or time.time())
        self._stop_flag.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=3.0)   # loop exits and the stream closes on its own thread
        frames = list(self._frames)
        wav_path = tempfile.mktemp(suffix=".wav", prefix="whisp_")
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            if self._denoise and frames:
                samples = np.concatenate([c.reshape(-1) for c in frames])
                try:
                    samples = reduce_noise(samples, SAMPLE_RATE)
                except Exception:
                    pass        # never let denoise break a recording
                wf.writeframes(samples.tobytes())
            else:
                for chunk in frames:
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
