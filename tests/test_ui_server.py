import io
import os

from whisp.ui.server import create_app
from whisp.history import HistoryStore
from whisp.settings import Settings


def client(support_dir):
    app = create_app(Settings.load())
    app.config.update(TESTING=True)
    return app.test_client()


def test_history_page_lists_entries(support_dir):
    HistoryStore().add(text="buy milk", raw_text="", duration=1, audio_url="", app_context="Notes")
    c = client(support_dir)
    resp = c.get("/")
    assert resp.status_code == 200
    assert b"buy milk" in resp.data


def test_api_delete(support_dir):
    e = HistoryStore().add(text="x", raw_text="", duration=1, audio_url="", app_context="")
    c = client(support_dir)
    resp = c.post(f"/api/transcript/{e.id}/delete")
    assert resp.status_code == 200
    assert HistoryStore().get(e.id) is None


def test_api_flag(support_dir):
    e = HistoryStore().add(text="x", raw_text="", duration=1, audio_url="", app_context="")
    c = client(support_dir)
    c.post(f"/api/transcript/{e.id}/flag", json={"flagged": True})
    assert HistoryStore().get(e.id).is_flagged is True


def test_settings_save(support_dir):
    c = client(support_dir)
    resp = c.post("/api/settings", json={"groq_api_key": "gsk_new", "press_enter": True})
    assert resp.status_code == 200
    saved = Settings.load()
    assert saved.get("groq_api_key") == "gsk_new"
    assert saved.get("press_enter") is True


def test_upload_transcribes_and_adds_history_without_pasting(support_dir, monkeypatch):
    captured = {}

    class FakePipeline:
        def run_uploaded(self, wav_path, duration, audio_url):
            captured.update(wav_path=wav_path, duration=duration, audio_url=audio_url)
            return HistoryStore().add(
                text="Uploaded transcript.",
                raw_text="uploaded transcript",
                duration=duration,
                audio_url=audio_url,
                app_context="Audio upload",
            )

    monkeypatch.setattr("whisp.ui.server.normalize_uploaded_audio", lambda path: path)
    monkeypatch.setattr("whisp.ui.server.duration_seconds", lambda path: 12.5)
    monkeypatch.setattr("whisp.ui.server.is_silent", lambda path: False)
    monkeypatch.setattr("whisp.ui.server.archive_recording", lambda path: "file:///tmp/upload.wav")
    monkeypatch.setattr("whisp.ui.server.build_pipeline", lambda settings: FakePipeline())

    c = client(support_dir)
    resp = c.post(
        "/api/upload",
        data={"audio": (io.BytesIO(b"audio bytes"), "meeting.wav")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["ok"] is True
    assert payload["entry"]["text"] == "Uploaded transcript."
    assert payload["entry"]["app_context"] == "Audio upload"
    assert captured["duration"] == 12.5
    assert not os.path.exists(captured["wav_path"])
    assert HistoryStore().list()[0].text == "Uploaded transcript."


def test_upload_rejects_non_audio_file(support_dir):
    c = client(support_dir)
    resp = c.post(
        "/api/upload",
        data={"audio": (io.BytesIO(b"not audio"), "notes.txt")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400
    assert "not supported" in resp.get_json()["error"]
