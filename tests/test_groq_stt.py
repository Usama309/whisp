from whisp.transcribe.groq_stt import GroqTranscriber
from whisp.transcribe.base import TranscriptionResult


def test_transcribe_calls_client_and_wraps_result(monkeypatch, tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF....")

    def fake_transcribe(api_key, wav_path, language, prompt=None):
        assert api_key == "gsk_x"
        assert wav_path == str(wav)
        return "  hello there  "

    monkeypatch.setattr("whisp.transcribe.groq_stt.groq_client.transcribe", fake_transcribe)
    t = GroqTranscriber(api_key="gsk_x", language="en")
    result = t.transcribe(str(wav))
    assert isinstance(result, TranscriptionResult)
    assert result.text == "hello there"
    assert result.engine == "groq"
