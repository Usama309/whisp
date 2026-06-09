from whisp.context import style_key_for_app


def test_messaging_apps_are_casual():
    for app in ["Slack", "Messages", "Discord", "WhatsApp"]:
        assert style_key_for_app(app) == "casual"


def test_mail_apps_are_email():
    for app in ["Mail", "Microsoft Outlook", "Spark"]:
        assert style_key_for_app(app) == "email"


def test_ai_and_code_apps_are_prompt():
    for app in ["Cursor", "Code", "ChatGPT", "Claude", "Terminal", "iTerm2"]:
        assert style_key_for_app(app) == "prompt"


def test_unknown_app_is_work():
    assert style_key_for_app("Numbers") == "work"
    assert style_key_for_app("") == "work"
