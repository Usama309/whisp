import os
import threading
import time
from urllib.parse import unquote, urlparse

from flask import Flask, abort, jsonify, render_template, request, send_file

from whisp import autostart
from whisp.history import HistoryStore
from whisp.settings import Settings
from whisp.timeutil import apple_to_unix


def _day_label(unix_ts: float) -> str:
    """Human day bucket for grouping: Today / Yesterday / 'Mon D'."""
    if not unix_ts:
        return "Earlier"
    day = time.strftime("%Y-%m-%d", time.localtime(unix_ts))
    today = time.strftime("%Y-%m-%d", time.localtime())
    yest = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    if day == today:
        return "Today"
    if day == yest:
        return "Yesterday"
    return time.strftime("%b %-d", time.localtime(unix_ts))


def _compute_stats(entries) -> dict:
    """Totals shown in the history header (over ALL entries, not the filter)."""
    words = sum(len((e.text or "").split()) for e in entries)
    talk = sum((e.duration or 0) for e in entries)
    return {"count": len(entries), "words": words, "hours": round(talk / 3600.0, 1)}


def _audio_path(audio_url: str) -> str:
    """Convert a stored file:// audio URL back to a local filesystem path."""
    if not audio_url:
        return ""
    return unquote(urlparse(audio_url).path)


def vocab_to_text(dictionary: dict) -> str:
    lines = []
    for spoken, written in (dictionary or {}).items():
        lines.append(written if spoken == written else f"{spoken} => {written}")
    return "\n".join(lines)


def parse_vocab(text: str) -> dict:
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if "=>" in line:
            spoken, written = line.split("=>", 1)
            spoken, written = spoken.strip(), written.strip()
            if spoken and written:
                out[spoken] = written
        else:
            out[line] = line   # word maps to itself (biases STT + fixes casing)
    return out


def _ui_dir(name: str) -> str:
    """Absolute path to a UI folder, working both in dev and inside a PyInstaller bundle."""
    import sys
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "whisp", "ui", name)  # type: ignore[attr-defined]
    return os.path.join(os.path.dirname(__file__), name)


def create_app(settings: Settings) -> Flask:
    app = Flask(__name__, template_folder=_ui_dir("templates"), static_folder=_ui_dir("static"))

    def entry_view(e):
        ts = apple_to_unix(e.date)
        dur = e.duration or 0
        mins, secs = divmod(int(dur), 60)
        return {
            "id": e.id, "text": e.text, "raw_text": e.raw_text,
            "app_context": e.app_context, "is_flagged": e.is_flagged,
            "duration": round(dur, 1),
            "dur_label": f"{mins}:{secs:02d}",
            "words": len((e.text or "").split()),
            "unix_date": ts,
            "day": _day_label(ts),
            "has_audio": os.path.exists(_audio_path(e.audio_url)),
        }

    @app.route("/audio/<entry_id>")
    def audio(entry_id):
        entry = HistoryStore().get(entry_id)
        if not entry:
            abort(404)
        path = _audio_path(entry.audio_url)
        if not path or not os.path.exists(path):
            abort(404)
        return send_file(path, mimetype="audio/wav")

    @app.route("/")
    def history():
        q = request.args.get("q", "")
        store = HistoryStore()
        all_entries = store.list()
        shown = store.search(q) if q else all_entries
        return render_template(
            "history.html",
            entries=[entry_view(e) for e in shown],
            stats=_compute_stats(all_entries),
            q=q,
        )

    @app.route("/settings")
    def settings_page():
        data = Settings.load().as_dict()
        data["vocabulary_text"] = vocab_to_text(data.get("custom_dictionary", {}))
        data["launch_at_login"] = autostart.is_enabled()
        return render_template("settings.html", settings=data)

    @app.route("/api/launch-at-login", methods=["POST"])
    def set_launch_at_login():
        if bool(request.json.get("enabled")):
            autostart.enable()
        else:
            autostart.disable()
        return jsonify(ok=True, enabled=autostart.is_enabled())

    @app.route("/api/transcript/<entry_id>/delete", methods=["POST"])
    def delete(entry_id):
        HistoryStore().delete(entry_id)
        return jsonify(ok=True)

    @app.route("/api/transcript/<entry_id>/flag", methods=["POST"])
    def flag(entry_id):
        HistoryStore().set_flag(entry_id, bool(request.json.get("flagged")))
        return jsonify(ok=True)

    @app.route("/api/settings", methods=["POST"])
    def save_settings():
        s = Settings.load()
        payload = dict(request.json or {})
        if "vocabulary_text" in payload:
            s.set("custom_dictionary", parse_vocab(payload.pop("vocabulary_text")))
        for key, value in payload.items():
            s.set(key, value)
        s.save()
        return jsonify(ok=True)

    return app


def start_server(settings: Settings) -> int:
    """Start Flask on an ephemeral localhost port in a daemon thread; return the port."""
    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    app = create_app(settings)
    threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    ).start()
    return port
