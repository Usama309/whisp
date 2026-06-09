_CASUAL = {"slack", "messages", "discord", "whatsapp", "telegram", "signal"}
_EMAIL = {"mail", "microsoft outlook", "outlook", "spark", "airmail"}
_PROMPT = {"cursor", "code", "visual studio code", "chatgpt", "claude",
           "terminal", "iterm2", "iterm", "xcode", "antigravity", "windsurf"}


def style_key_for_app(app_name: str) -> str:
    name = (app_name or "").lower()
    if name in _CASUAL:
        return "casual"
    if name in _EMAIL:
        return "email"
    if name in _PROMPT:
        return "prompt"
    return "work"


def frontmost_app_name() -> str:
    """Name of the frontmost application (best-effort; '' if unavailable)."""
    try:
        from AppKit import NSWorkspace
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return app.localizedName() if app else ""
    except Exception:
        return ""
