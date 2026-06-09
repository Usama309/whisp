from whisp.settings import Settings


def test_defaults_when_no_file(support_dir):
    s = Settings.load()
    assert s.get("local_model") == "base.en"
    assert s.get("hotkey")["keyCode"] == 63
    assert s.get("groq_api_key") == ""


def test_set_and_persist(support_dir):
    s = Settings.load()
    s.set("groq_api_key", "gsk_test")
    s.save()
    again = Settings.load()
    assert again.get("groq_api_key") == "gsk_test"


def test_unknown_keys_from_file_are_preserved_and_defaults_filled(support_dir):
    s = Settings.load()
    s.set("press_enter", True)
    s.save()
    again = Settings.load()
    assert again.get("press_enter") is True
    # a default the user never touched is still present
    assert again.get("cleanup_enabled") is True
