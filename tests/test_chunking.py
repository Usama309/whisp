import wave

from whisp.transcribe import chunking


def _make_wav(path, seconds, rate=16000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * rate * seconds)


def test_short_audio_passes_through_single_call(tmp_path):
    wav = tmp_path / "short.wav"
    _make_wav(wav, 5)
    calls = []
    out = chunking.transcribe_chunked(str(wav), lambda p: calls.append(p) or "hello", chunk_secs=120)
    assert out == "hello"
    assert len(calls) == 1                 # not chunked


def test_long_audio_is_split_and_joined_in_order(tmp_path):
    wav = tmp_path / "long.wav"
    _make_wav(wav, 300)                     # 5 min -> 3 chunks at 120s
    seen = []

    def fake(p):
        seen.append(p)
        return f"part{len(seen)}"

    out = chunking.transcribe_chunked(str(wav), fake, parallel=False, chunk_secs=120)
    assert len(seen) == 3
    assert out == "part1 part2 part3"       # joined in order


def test_duration_seconds(tmp_path):
    wav = tmp_path / "d.wav"
    _make_wav(wav, 7)
    assert 6.9 < chunking.duration_seconds(str(wav)) < 7.1
