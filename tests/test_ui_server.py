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
