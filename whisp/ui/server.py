import os
import tempfile
import threading
import time
from urllib.parse import unquote, urlparse

from flask import Flask, abort, jsonify, render_template, request, send_file

from whisp import autostart
from whisp import config
from whisp.audio import AudioDecodeError, archive_recording, is_silent, normalize_uploaded_audio
from whisp.factory import build_pipeline
from whisp.history import HistoryStore
from whisp.logs import log
from whisp.net import is_online
from whisp.settings import Settings
from whisp.timeutil import apple_to_unix
from whisp.transcribe.chunking import duration_seconds
from whisp.transcribe.router import choose_engine


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
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_BYTES

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

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify(ok=False, error="That audio file is too large. The maximum upload size is 200 MB."), 413

    @app.route("/api/upload", methods=["POST"])
    def upload_audio():
        uploaded = request.files.get("audio")
        if uploaded is None or not uploaded.filename:
            return jsonify(ok=False, error="Choose an audio file to transcribe."), 400

        suffix = os.path.splitext(uploaded.filename)[1].lower()
        mimetype = (uploaded.mimetype or "").lower()
        if suffix not in config.UPLOAD_EXTENSIONS and not mimetype.startswith("audio/"):
            return jsonify(
                ok=False,
                error="That file type is not supported. Choose an audio file such as WAV, MP3, M4A, FLAC, or OGG.",
            ), 400

        fd, source_path = tempfile.mkstemp(suffix=suffix or ".audio", prefix="whisp_upload_source_")
        os.close(fd)
        normalized_path = ""
        try:
            uploaded.save(source_path)
            try:
                normalized_path = normalize_uploaded_audio(source_path)
            except AudioDecodeError as exc:
                return jsonify(ok=False, error=str(exc)), 400

            duration = duration_seconds(normalized_path)
            if duration <= 0:
                return jsonify(ok=False, error="The audio file contains no readable audio."), 400
            if is_silent(normalized_path):
                return jsonify(ok=False, error="No speech was detected in that audio file."), 422

            audio_url = archive_recording(normalized_path)
            current_settings = Settings.load()
            try:
                entry = build_pipeline(current_settings).run_uploaded(
                    wav_path=normalized_path,
                    duration=duration,
                    audio_url=audio_url,
                )
            except Exception as exc:
                if choose_engine(current_settings.get("groq_api_key", ""), is_online()) != "groq":
                    raise
                log(f"UPLOAD  groq failed ({str(exc)[:80]}); retrying local whisper.cpp")
                entry = build_pipeline(current_settings, force_local=True).run_uploaded(
                    wav_path=normalized_path,
                    duration=duration,
                    audio_url=audio_url,
                )

            if entry is None:
                return jsonify(ok=False, error="No speech was detected in that audio file."), 422
            return jsonify(ok=True, entry=entry_view(entry))
        except Exception as exc:
            log(f"UPLOAD  failed: {str(exc)[:160]}")
            return jsonify(ok=False, error="Whisp could not transcribe that audio file. Please try again."), 500
        finally:
            for path in (source_path, normalized_path):
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

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
