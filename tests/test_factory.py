from whisp.factory import build_pipeline
from whisp.settings import Settings
from whisp.transcribe.local_stt import LocalTranscriber
from whisp.transcribe.groq_stt import GroqTranscriber


def test_online_with_key_uses_groq(support_dir, monkeypatch):
    monkeypatch.setattr("whisp.factory.is_online", lambda: True)
    s = Settings.load()
    s.set("groq_api_key", "gsk_dummy")
    assert isinstance(build_pipeline(s)._transcriber, GroqTranscriber)


def test_offline_falls_back_to_local(support_dir, monkeypatch):
    monkeypatch.setattr("whisp.factory.is_online", lambda: False)
    s = Settings.load()
    s.set("groq_api_key", "gsk_dummy")
    assert isinstance(build_pipeline(s)._transcriber, LocalTranscriber)


def test_force_local_uses_bundled_whisper_and_offline_cleanup(support_dir, monkeypatch):
    # Even online with a valid key, force_local must use the bundled engine and
    # skip Groq cleanup entirely (the safety net for a failing Groq).
    monkeypatch.setattr("whisp.factory.is_online", lambda: True)
    s = Settings.load()
    s.set("groq_api_key", "gsk_dummy")
    pipeline = build_pipeline(s, force_local=True)
    assert isinstance(pipeline._transcriber, LocalTranscriber)
    assert pipeline._cleanup.__self__._api_key == ""
