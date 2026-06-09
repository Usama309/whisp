from whisp.transcribe.local_stt import LocalTranscriber
from whisp.transcribe.base import TranscriptionResult


def test_builds_command_and_parses_output(monkeypatch, tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"x")
    model = tmp_path / "ggml-base.en.bin"
    model.write_bytes(b"x")
    captured = {}

    class FakeProc:
        returncode = 0
        stdout = "  Hello from whisper.  \n"
        stderr = ""

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return FakeProc()

    monkeypatch.setattr("whisp.transcribe.local_stt.subprocess.run", fake_run)
    t = LocalTranscriber(binary="/usr/local/bin/whisper-cli", model_path=str(model), language="en")
    result = t.transcribe(str(wav))
    assert isinstance(result, TranscriptionResult)
    assert result.text == "Hello from whisper."
    assert result.engine == "local"
    assert "/usr/local/bin/whisper-cli" in captured["cmd"]
    assert str(model) in captured["cmd"]
    assert str(wav) in captured["cmd"]
