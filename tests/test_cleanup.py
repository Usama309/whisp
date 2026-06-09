from whisp.cleanup import CleanupService, build_system_prompt, local_fallback


def test_build_system_prompt_includes_tone_and_app():
    sp = build_system_prompt(tone="Relaxed and friendly.", app_name="Slack")
    assert "Relaxed and friendly." in sp
    assert "Slack" in sp
    assert "only" in sp.lower()  # instructs to output only the cleaned text


def test_local_fallback_strips_fillers_and_fixes_caps():
    out = local_fallback("um so i think uh we should, you know, ship it")
    assert "um" not in out.split()
    assert "uh" not in out.split()
    assert out[0].isupper()
    assert out.endswith(".")


def test_local_fallback_applies_custom_dictionary():
    out = local_fallback("i love groq", dictionary={"groq": "Groq"})
    assert "Groq" in out


def test_local_fallback_handles_spoken_formatting_commands():
    out = local_fallback("buy milk new line buy eggs new paragraph call mom")
    lines = out.split("\n")
    assert "Buy milk" in lines[0]
    assert any("buy eggs" in ln.lower() for ln in lines)
    assert "\n\n" in out  # new paragraph produced a blank line


def test_clean_uses_groq_when_key_and_online(monkeypatch):
    captured = {}

    def fake_chat(api_key, system, user):
        captured["system"] = system
        captured["user"] = user
        return "We should ship it."

    monkeypatch.setattr("whisp.cleanup.groq_client.chat", fake_chat)
    svc = CleanupService(api_key="gsk_x", online=lambda: True,
                         tones={"casual": "Relaxed."}, dictionary={})
    result = svc.clean("um we should ship it", app_name="Slack")
    assert result == "We should ship it."
    assert "um we should ship it" in captured["user"]


def test_clean_uses_local_when_offline(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("should not call Groq when offline")

    monkeypatch.setattr("whisp.cleanup.groq_client.chat", boom)
    svc = CleanupService(api_key="gsk_x", online=lambda: False,
                         tones={"work": "Clear."}, dictionary={})
    result = svc.clean("um hello uh there", app_name="Numbers")
    assert "um" not in result.split()
