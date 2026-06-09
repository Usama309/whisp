import os
import threading
from urllib.parse import unquote, urlparse

from flask import Flask, abort, jsonify, render_template, request, send_file

from whisp.history import HistoryStore
from whisp.settings import Settings
from whisp.timeutil import apple_to_unix


def _audio_path(audio_url: str) -> str:
    """Convert a stored file:// audio URL back to a local filesystem path."""
    if not audio_url:
        return ""
    return unquote(urlparse(audio_url).path)


def create_app(settings: Settings) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    def entry_view(e):
        return {
            "id": e.id, "text": e.text, "raw_text": e.raw_text,
            "app_context": e.app_context, "is_flagged": e.is_flagged,
            "duration": round(e.duration, 1),
            "unix_date": apple_to_unix(e.date),
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
        entries = store.search(q) if q else store.list()
        return render_template("history.html", entries=[entry_view(e) for e in entries], q=q)

    @app.route("/settings")
    def settings_page():
        return render_template("settings.html", settings=Settings.load().as_dict())

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
        for key, value in (request.json or {}).items():
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
