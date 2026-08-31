import os
import wave

import numpy as np
from whisp.audio import normalize_uploaded_audio, reduce_noise, Recorder


def test_normalize_uploaded_audio_writes_mono_16khz_wav(tmp_path):
    source = tmp_path / "meeting.wav"
    frames = (np.arange(8000 * 2, dtype=np.int16) % 800) - 400
    with wave.open(str(source), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(frames.tobytes())

    normalized = normalize_uploaded_audio(str(source))
    try:
        with wave.open(normalized, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            assert wf.getnframes() == 16000
    finally:
        os.remove(normalized)


def test_reduce_noise_same_length_and_dtype():
    rate = 16000
    rng = np.random.default_rng(0)
    sig = (np.sin(2 * np.pi * 220 * np.arange(rate) / rate) * 4000).astype(np.int16)
    noisy = (sig + rng.normal(0, 300, rate)).astype(np.int16)
    out = reduce_noise(noisy, rate)
    assert out.dtype == np.int16
    assert len(out) == len(noisy)


def test_reduce_noise_lowers_noise_floor():
    rate = 16000
    rng = np.random.default_rng(1)
    # mostly low-frequency rumble + hiss, little speech-band content
    noise = (rng.normal(0, 500, rate * 2)).astype(np.int16)
    out = reduce_noise(noise, rate)
    assert np.sqrt(np.mean(out.astype(float) ** 2)) < np.sqrt(np.mean(noise.astype(float) ** 2))


def test_reduce_noise_skips_tiny_clips():
    out = reduce_noise(np.zeros(100, np.int16), 16000)
    assert len(out) == 100


def test_recorder_stores_denoise_flag():
    assert Recorder(denoise=True)._denoise is True
    assert Recorder()._denoise is False
