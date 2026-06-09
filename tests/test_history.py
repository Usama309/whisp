from whisp.history import HistoryStore, TranscriptEntry


def test_add_and_get(support_dir):
    store = HistoryStore()
    entry = store.add(text="Hello world.", raw_text="hello world um",
                      duration=2.5, audio_url="file:///tmp/a.opus",
                      app_context="TextEdit")
    assert entry.id
    fetched = store.get(entry.id)
    assert fetched.text == "Hello world."
    assert fetched.raw_text == "hello world um"
    assert fetched.is_flagged is False


def test_list_sorted_newest_first(support_dir):
    store = HistoryStore()
    a = store.add(text="first", raw_text="", duration=1, audio_url="", app_context="")
    b = store.add(text="second", raw_text="", duration=1, audio_url="", app_context="")
    ids = [e.id for e in store.list()]
    assert ids[0] == b.id and ids[1] == a.id


def test_search(support_dir):
    store = HistoryStore()
    store.add(text="buy milk and eggs", raw_text="", duration=1, audio_url="", app_context="")
    store.add(text="call the dentist", raw_text="", duration=1, audio_url="", app_context="")
    results = store.search("milk")
    assert len(results) == 1 and "milk" in results[0].text


def test_flag_and_delete(support_dir):
    store = HistoryStore()
    e = store.add(text="x", raw_text="", duration=1, audio_url="", app_context="")
    store.set_flag(e.id, True)
    assert store.get(e.id).is_flagged is True
    store.delete(e.id)
    assert store.get(e.id) is None


def test_persisted_file_matches_willow_schema(support_dir):
    import json
    from pathlib import Path
    store = HistoryStore()
    e = store.add(text="hi", raw_text="hi", duration=1.0, audio_url="file:///a.opus", app_context="Mail")
    raw = json.loads((Path(support_dir) / "Transcripts" / f"{e.id}.json").read_text())
    for key in ("id", "isFlagged", "audioURL", "recordingDuration", "text", "date"):
        assert key in raw
