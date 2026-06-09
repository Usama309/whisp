import json
import time
import uuid
from dataclasses import dataclass

from whisp import config
from whisp.timeutil import unix_to_apple


@dataclass
class TranscriptEntry:
    id: str
    text: str
    raw_text: str
    audio_url: str
    duration: float
    date: float          # Apple-epoch seconds (Willow-compatible)
    is_flagged: bool
    app_context: str

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "isFlagged": self.is_flagged,
            "audioURL": self.audio_url,
            "recordingDuration": self.duration,
            "text": self.text,
            "rawText": self.raw_text,
            "appContext": self.app_context,
            "date": self.date,
        }

    @classmethod
    def from_json(cls, d: dict) -> "TranscriptEntry":
        return cls(
            id=d["id"],
            text=d.get("text", ""),
            raw_text=d.get("rawText", ""),
            audio_url=d.get("audioURL", ""),
            duration=d.get("recordingDuration", 0.0),
            date=d.get("date", 0.0),
            is_flagged=d.get("isFlagged", False),
            app_context=d.get("appContext", ""),
        )


class HistoryStore:
    def __init__(self):
        self._dir = config.transcripts_dir()

    def _path(self, entry_id: str):
        return self._dir / f"{entry_id}.json"

    def add(self, text, raw_text, duration, audio_url, app_context) -> TranscriptEntry:
        entry = TranscriptEntry(
            id=str(uuid.uuid4()).upper(),
            text=text,
            raw_text=raw_text,
            audio_url=audio_url,
            duration=duration,
            date=unix_to_apple(time.time()),
            is_flagged=False,
            app_context=app_context,
        )
        self._write(entry)
        return entry

    def _write(self, entry: TranscriptEntry):
        self._path(entry.id).write_text(json.dumps(entry.to_json(), indent=2))

    def get(self, entry_id: str):
        p = self._path(entry_id)
        if not p.exists():
            return None
        return TranscriptEntry.from_json(json.loads(p.read_text()))

    def list(self):
        entries = []
        for p in self._dir.glob("*.json"):
            try:
                entries.append(TranscriptEntry.from_json(json.loads(p.read_text())))
            except (json.JSONDecodeError, KeyError, OSError):
                continue
        return sorted(entries, key=lambda e: e.date, reverse=True)

    def search(self, query: str):
        q = query.lower().strip()
        return [e for e in self.list() if q in e.text.lower()]

    def set_flag(self, entry_id: str, flagged: bool):
        entry = self.get(entry_id)
        if entry:
            entry.is_flagged = flagged
            self._write(entry)

    def delete(self, entry_id: str):
        p = self._path(entry_id)
        if p.exists():
            p.unlink()
