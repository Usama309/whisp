from whisp.dictation import DictationPipeline
from whisp.transcribe.base import TranscriptionResult
from whisp.history import HistoryStore


class FakeTranscriber:
    def __init__(self, text):
        self._text = text

    def transcribe(self, wav_path):
        return TranscriptionResult(text=self._text, engine="local")


def test_pipeline_transcribes_cleans_inserts_and_records(support_dir):
    inserted = {}
    pipeline = DictationPipeline(
        transcriber=FakeTranscriber("um hello world"),
        cleanup=lambda raw, app: "Hello world.",
        inserter=lambda text, press_enter: inserted.update(text=text),
        history=HistoryStore(),
        frontmost_app=lambda: "TextEdit",
        press_enter=False,
    )
    entry = pipeline.run(wav_path="/tmp/x.wav", duration=2.0, audio_url="file:///a.opus")
    assert inserted["text"] == "Hello world."
    assert entry.text == "Hello world."
    assert entry.raw_text == "um hello world"
    assert entry.app_context == "TextEdit"
    # persisted to history
    assert HistoryStore().get(entry.id).text == "Hello world."


def test_pipeline_skips_empty_transcript(support_dir):
    calls = []
    pipeline = DictationPipeline(
        transcriber=FakeTranscriber("   "),
        cleanup=lambda raw, app: "",
        inserter=lambda text, press_enter: calls.append(text),
        history=HistoryStore(),
        frontmost_app=lambda: "TextEdit",
        press_enter=False,
    )
    entry = pipeline.run(wav_path="/tmp/x.wav", duration=0.3, audio_url="")
    assert entry is None
    assert calls == []
